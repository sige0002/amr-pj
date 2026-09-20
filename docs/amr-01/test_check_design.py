"""計算の回帰テスト。実機適合性・安全性のテストではない。"""
from __future__ import annotations
import copy
import json
import math
from pathlib import Path
import unittest
from check_design import cg, evaluate, front_tip, support_margin, validate_finite


class DesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parent
        cls.config = json.loads((cls.root / "design_parameters.json").read_text(encoding="utf-8"))
        cls.result = evaluate(cls.config)

    def test_internal_structure_is_prioritized(self):
        self.assertTrue(self.config["design_policy"]["internal_structure_first"])

    def test_cosmetic_exterior_not_required_but_guards_required(self):
        policy = self.config["design_policy"]
        self.assertFalse(policy["cosmetic_exterior_required"])
        self.assertTrue(policy["functional_guards_required"])

    def test_generated_images_are_excluded(self):
        self.assertFalse(self.config["design_policy"]["concept_images_included"])
        self.assertFalse(self.config["design_policy"]["concept_image_is_manufacturing_drawing"])
        image_suffixes = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}
        self.assertFalse(any(p.suffix.lower() in image_suffixes for p in self.root.rglob("*")))
        self.assertNotIn("!" + "[", (self.root / "DESIGN.ja.md").read_text(encoding="utf-8"))

    def test_current_layout_baseline(self):
        self.assertEqual(self.config["calculation_baseline_version"], "0.4.1")
        self.assertEqual(self.config["geometry"]["drive_axle_x_mm"], 90)
        self.assertEqual(self.config["geometry"]["drive_track_mm"], 354)

    def test_weighted_cg(self):
        self.assertEqual(cg([(1, 0, 0, 0), (3, 4, 0, 0)]), (4, 3, 0, 0))

    def test_invalid_mass(self):
        for parts in ([], [(0, 0, 0, 0)], [(-1, 0, 0, 0)]):
            with self.assertRaises(ValueError):
                cg(parts)

    def test_signed_support_distances(self):
        poly = [(0, 0), (1, 0), (0, 1)]
        self.assertGreater(support_margin((0.1, 0.1), poly), 0)
        self.assertAlmostEqual(support_margin((0, 0.2), poly), 0)
        self.assertLess(support_margin((1, 1), poly), 0)

    def test_clockwise_polygon_rejected(self):
        with self.assertRaises(ValueError):
            support_margin((0, 0), [(0, 0), (0, 1), (1, 0)])

    def test_front_moment_ratio(self):
        value = front_tip([(2, 0, 0, 0), (1, 2, 0, 0)], 1)
        self.assertAlmostEqual(value["static_moment_ratio"], 2)

    def test_zero_overturning_ratio_is_null(self):
        self.assertIsNone(front_tip([(1, 0, 0, 0)], 1)["static_moment_ratio"])

    def test_small_current_requirements(self):
        r = self.config["requirements"]
        self.assertEqual(r["cargo_limit_kg"], 2)
        self.assertEqual(r["base_upper_budget_kg"], 10)
        self.assertEqual(r["gross_mass_calculation_limit_kg"], 14)
        self.assertIsNone(r["arm_object_lifting_limit_kg"])
        self.assertEqual(self.result["envelope_LW_mm"], [500, 400])

    def test_mass_budget(self):
        self.assertAlmostEqual(self.result["estimated_base_mass_kg"], 6.78)
        self.assertAlmostEqual(self.result["base_mass_margin_to_upper_budget_kg"], 3.22)
        self.assertTrue(self.result["estimated_base_within_upper_budget"])
        self.assertAlmostEqual(self.result["max_config_mass_at_estimate_kg"], 10.78)
        self.assertEqual(self.result["max_config_mass_at_upper_budget_kg"], 14)

    def test_mass_overrun_is_reported_without_clamping_estimate(self):
        config = copy.deepcopy(self.config)
        config["mass_estimate_kg"]["battery_and_adapter"] += 4
        result = evaluate(config)
        self.assertAlmostEqual(result["estimated_base_mass_kg"], 10.78)
        self.assertAlmostEqual(result["base_mass_margin_to_upper_budget_kg"], -0.78)
        self.assertFalse(result["estimated_base_within_upper_budget"])

    def test_drive_sizes_for_upper_mass_independently_of_estimate(self):
        config = copy.deepcopy(self.config)
        config["mass_estimate_kg"]["battery_and_adapter"] += 1
        self.assertEqual(evaluate(config)["drive"], self.result["drive"])
        config["requirements"]["base_upper_budget_kg"] = 6
        config["requirements"]["gross_mass_calculation_limit_kg"] = 10
        self.assertAlmostEqual(self.result["drive"]["force_N"] / evaluate(config)["drive"]["force_N"], 1.4)

    def test_drive_calculation(self):
        d = self.result["drive"]
        self.assertAlmostEqual(d["wheel_torque_with_margin_Nm"], 0.7077934164, places=8)
        self.assertLess(d["outer_wheel_rpm"], d["loaded_wheel_speed_target_rpm"])
        self.assertLess(d["wheel_torque_with_margin_Nm"], d["continuous_torque_target_range_Nm"][0])

    def test_offset_pivot_sweep(self):
        self.assertAlmostEqual(self.result["turning"]["body_only_pivot_swept_diameter_mm"], 788.923316932641, places=6)
        self.assertGreater(self.result["turning"]["body_only_pivot_swept_diameter_mm"], math.hypot(500, 400))

    def test_selected_motor_does_not_claim_both_later_maxima(self):
        d = self.result['drive']
        self.assertTrue(d['initial_combined_command_fits_cap'])
        self.assertFalse(d['later_combined_command_fits_cap'])
        self.assertFalse(d['selected_motor_continuous_rating_verified'])

    def test_invalid_command_rpm_cap_rejected(self):
        config = copy.deepcopy(self.config)
        config['drive']['planned_wheel_rpm_cap'] = 0
        with self.assertRaises(ValueError):
            evaluate(config)

    def test_frame_3030_and_stock_spares(self):
        frame = self.result["frame"]
        self.assertEqual(self.config["geometry"]["extrusion_size_mm"], 30)
        self.assertAlmostEqual(frame["extrusion_total_m"], 2.2)
        self.assertAlmostEqual(frame["extrusion_mass_kg"], 1.672)
        self.assertEqual(frame["stock_plan"]["assembled_outer_LW_mm"], [460, 300])
        self.assertEqual([row["spare"] for row in frame["stock_plan"]["stock"]], [0, 2])

    def test_purchase_cost_includes_spares_but_vehicle_mass_does_not(self):
        self.assertEqual(self.result["frame"]["stock_plan"]["purchase_material_subtotal_incl_tax_jpy"], 3419)
        config = copy.deepcopy(self.config)
        config["procurement"]["frame_stock"][0]["packs"] = 2
        result = evaluate(config)
        self.assertEqual(result["frame"]["stock_plan"]["purchase_material_subtotal_incl_tax_jpy"], 5371)
        self.assertEqual(result["frame"]["extrusion_mass_kg"], self.result["frame"]["extrusion_mass_kg"])

    def test_stock_length_includes_both_end_members(self):
        config = copy.deepcopy(self.config)
        config["geometry"]["frame_length_mm"] = 400
        with self.assertRaisesRegex(ValueError, "組立外寸"):
            evaluate(config)

    def test_missing_stock_length_rejected(self):
        config = copy.deepcopy(self.config)
        config["procurement"]["frame_stock"][1]["length_mm"] = 250
        with self.assertRaisesRegex(ValueError, "定尺の購入本数"):
            evaluate(config)

    def test_insufficient_stock_quantity_rejected(self):
        config = copy.deepcopy(self.config)
        config["procurement"]["frame_stock"][1]["pieces_per_pack"] = 1
        with self.assertRaisesRegex(ValueError, "定尺の購入本数"):
            evaluate(config)

    def test_frame_must_fit_body(self):
        config = copy.deepcopy(self.config)
        config["geometry"]["body_width_mm"] = 250
        with self.assertRaisesRegex(ValueError, "車体外形"):
            evaluate(config)

    def test_frame_stock_and_mass_list_must_agree(self):
        config = copy.deepcopy(self.config)
        config["frame"]["cuts_mm_count"][1][1] = 3
        with self.assertRaisesRegex(ValueError, "使用材一覧"):
            evaluate(config)

    def test_current_wheel_and_caster_envelopes_fit(self):
        checks = self.result["envelope_checks_simplified"]
        self.assertTrue(checks["wheel_rectangles_inside"])
        self.assertTrue(checks["caster_assembly_swept_circle_inside"])

    def test_stopping_examples(self):
        self.assertAlmostEqual(self.result["stopping_examples"]["0.15_m_s"], 0.0525)
        self.assertAlmostEqual(self.result["stopping_examples"]["0.3_m_s"], 0.15)

    def test_2kg_forward_pick_is_not_stable_in_examples(self):
        for base in (5, 6):
            case = self.result["stability_cases"][f"base_{base}kg/forward_object_2kg_NOT_APPROVED"]
            self.assertLess(case["front_edge_margin_mm"], 0)
            self.assertLess(case["front_tip"]["static_moment_ratio"], 1)
            self.assertFalse(case["sampled_flat_static_cg_inside"])

    def test_no_case_is_operation_approval(self):
        self.assertTrue(all(not case["operation_approved"] for case in self.result["stability_cases"].values()))

    def test_estimated_mass_stability_is_not_replaced_by_upper_limit(self):
        cases = self.result["stability_cases"]
        estimated = cases["base_6.78kg/forward_object_2kg_NOT_APPROVED"]
        upper = cases["base_10kg/forward_object_2kg_NOT_APPROVED"]
        self.assertGreater(estimated["front_edge_margin_mm"], 0)
        self.assertLess(estimated["front_edge_margin_mm"], 6)
        self.assertGreater(upper["front_edge_margin_mm"], estimated["front_edge_margin_mm"])

    def test_parameter_change_affects_results(self):
        config = copy.deepcopy(self.config)
        config["drive"]["acceleration_m_s2"] = 0.4
        self.assertGreater(evaluate(config)["drive"]["force_N"], self.result["drive"]["force_N"])

    def test_invalid_geometry_rejected(self):
        config = copy.deepcopy(self.config)
        config["geometry"]["wheel_diameter_mm"] = 0
        with self.assertRaises(ValueError):
            evaluate(config)

    def test_budget_overrun_rejected(self):
        config = copy.deepcopy(self.config)
        config["requirements"]["gross_mass_calculation_limit_kg"] = 9
        with self.assertRaises(ValueError):
            evaluate(config)

    def test_nonfinite_rejected(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(ValueError):
                validate_finite({"value": value})

    def test_saved_result_matches_current_config(self):
        saved = json.loads((self.root / "calculation_results.json").read_text(encoding="utf-8"))
        self.assertEqual(saved, self.result)

    def test_json_is_strictly_serializable(self):
        json.dumps(self.result, ensure_ascii=False, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
