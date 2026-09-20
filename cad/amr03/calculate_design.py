"""Calculate A2 drive, shaft and assumed static support cases.

Run: python3 cad/amr03/calculate_design.py
Numerical functions are imported from the existing, checked implementation.
Its historical mechanical design is not selected or copied into these results.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NUMERICAL_SOURCE = HERE.parent / "amr02/calculate_design.py"


def load_numerical_functions():
    spec = importlib.util.spec_from_file_location("_amr_numerical_functions", NUMERICAL_SOURCE)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load numerical functions: {NUMERICAL_SOURCE}")
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def evaluate(config, original, validation):
    numerical = load_numerical_functions()
    numerical.validate_finite(validation)
    mass = validation["mass"]
    estimated = numerical.positive(mass["estimated_complete_base_kg"], "estimated base mass")
    upper = numerical.positive(config["requirements"]["base_upper_budget_kg"], "base upper budget")
    if not math.isclose(mass["mechanical_estimate_kg"] + sum(config["mass_electrical_budget_kg"].values()), estimated):
        raise ValueError("CAD mass and electrical budgets are inconsistent")
    if not math.isclose(validation["drive_track_mm"], config["geometry"]["drive_track_mm"]):
        raise ValueError("Validated CAD track differs from the calculation input")
    inputs = copy.deepcopy(config)
    inputs["stability"]["base_mass_cases_kg"] = [estimated, upper]
    inputs["drive"]["selected_motor"] = inputs["drive"]["geometry_reference_motor"]
    raw = numerical.evaluate(inputs, original)
    raw["drive"]["geometry_reference_motor"] = raw["drive"].pop("selected_motor")
    raw["drive"]["selection_status"] = config["drive"]["selection_status"]
    assumptions = raw["stability_assumptions"]
    original_contacts = assumptions["first_design_A_contact_geometry"]
    current_contacts = assumptions["second_design_B_contact_geometry"]
    support_unchanged = original_contacts == current_contacts
    shaft_unchanged = raw["shaft_comparison"]["old"] == raw["shaft_comparison"]["new"]
    if not support_unchanged or not shaft_unchanged:
        raise ValueError("A2 no longer has the original A shaft/support layout; review the comparison")

    cases = []
    comparison_identical = True
    max_equilibrium_residual = {"vertical_force_N": 0.0, "x_weight_moment_Nmm": 0.0, "y_weight_moment_Nmm": 0.0}
    for key, case in raw["stability_cases"].items():
        response = case["second_design_B"]
        comparison_identical &= response == case["first_design_A"]
        for axis, value in response["equilibrium_max_abs_residual"].items():
            max_equilibrium_residual[axis] = max(max_equilibrium_residual[axis], value)
        cases.append({
            "base_mass_kg": case["components_kg_xyz_mm"][0][0],
            "scenario": key.split("/", 1)[1],
            "gross_mass_kg": case["total_mass_kg"],
            "assumed_cg_xyz_mm": case["cg_xyz_mm"],
            "worst_sampled_support_margin_mm": response["worst_sampled_caster_support_margin_mm"],
            "worst_margin_caster_angle_deg": response["worst_margin_caster_angle_deg"],
            "wheel_reaction_min_max_N": {wheel: [values["min_signed_N"], values["max_signed_N"]]
                                        for wheel, values in response["wheel_reaction_ranges_N"].items()},
            "all_sampled_reactions_nonnegative": response["all_sampled_reactions_nonnegative"],
            "front_static_moment_ratio": response["front_tip"]["static_moment_ratio"],
            "operation_approved": False,
        })

    frame_entries = [entry for entry in mass["breakdown"] if entry["part"].startswith("NFSL6-3030 ")]
    if len(frame_entries) != 1:
        raise ValueError("Expected one catalog frame-mass entry")
    frame_mass = frame_entries[0]["kg"]
    battery_mass = config["mass_electrical_budget_kg"]["battery_and_adapter"]
    reserved = config["geometry"]["battery_space_xyz_size_mm"]
    old_battery_z, new_battery_z = 139.5, reserved[2] + reserved[5] / 2
    old_frame_z = 90.0
    new_frame_z = (config["geometry"]["frame_bottom_z_mm"] + config["geometry"]["frame_top_z_mm"]) / 2
    battery_moment = battery_mass * (new_battery_z - old_battery_z)
    frame_moment = frame_mass * (new_frame_z - old_frame_z)
    relocation_cases = [{
        "assumed_fixed_total_mass_kg": total,
        "battery_only_contribution_mm": battery_moment / total,
        "frame_only_contribution_mm": frame_moment / total,
        "sum_of_only_these_two_terms_mm": (battery_moment + frame_moment) / total,
    } for total in (estimated, upper)]

    first_100 = next(item for item in raw["shaft_comparison"]["new"] if item["load_N"] == 100)
    checks = {
        "100N_shaft_moment_is_3p2_Nm": math.isclose(first_100["max_bending_moment_Nm"], 3.2, abs_tol=1e-10),
        "100N_max_bearing_reaction_is_218p518519_N": math.isclose(first_100["max_abs_bearing_reaction_N"], 218.51851851851853, abs_tol=1e-9),
        "shaft_response_equals_original_A": shaft_unchanged,
        "same_xy_support_and_same_mass_CG_give_identical_static_results": support_unchanged and comparison_identical,
        "14kg_margin_torque_is_0p707793_Nm": math.isclose(raw["drive"]["wheel_torque_with_margin_Nm"], 0.707793, abs_tol=1e-6),
        "battery_only_moment_change_is_minus54_kg_mm": math.isclose(battery_moment, -54, abs_tol=1e-9),
        "frame_only_moment_change_is_minus10p032_kg_mm": math.isclose(frame_moment, -10.032, abs_tol=1e-9),
        "force_and_moment_equilibrium": all(value < 1e-8 for value in max_equilibrium_residual.values()),
    }
    if not all(checks.values()):
        raise ValueError(f"Calculation self-check failed: {checks}")
    return {
        "version": config["version"], "design": config["design"],
        "status": "A2_calculations_with_assumed_CG_not_operation_approval",
        "note_ja": "CAD質量と電装仮枠の合計を使用。軸の定格、締結剛性、段差衝撃、実機重心、動的転倒、アーム把持能力を認定する結果ではない。",
        "mass_inputs": {
            "mechanical_estimate_kg": mass["mechanical_estimate_kg"],
            "electrical_budget_kg": mass["additional_electrical_budget_kg"],
            "estimated_complete_base_kg": estimated,
            "base_upper_budget_kg": upper,
            "note_ja": "台車質量は実測前の積上げ値。10kgは上限であり、実在する復元質量として推計機体へ加算しない。",
        },
        "drive": {**raw["drive"], "sizing_inputs": {
            "gravity_m_s2": numerical.G,
            "slope_deg": config["drive"]["slope_for_sizing_deg"],
            "acceleration_m_s2": config["drive"]["acceleration_m_s2"],
            "rolling_resistance_assumed": config["drive"]["rolling_resistance_assumed"],
            "wheel_diameter_mm": config["geometry"]["wheel_diameter_mm"],
            "track_mm": config["geometry"]["drive_track_mm"],
        }},
        "shaft": {
            "diameter_mm": config["shaft_comparison"]["diameter_mm"],
            "elastic_modulus_assumed_N_mm2": config["shaft_comparison"]["elastic_modulus_assumed_N_mm2"],
            "same_as_original_A": shaft_unchanged,
            "cases": raw["shaft_comparison"]["new"],
            "note_ja": "軸受中心118/145mm、輪中心177mm、張出し32mmはAと同じ。反転・スペーサー撤去によってこの軸の曲げ応力や反力増幅は減らない。100/200Nは剛支持の配置比較荷重であり、実機の定格輪荷重・試験荷重ではない。負反力は反対方向の支持を示す。",
        },
        "static_support": {
            "contact_geometry": current_contacts,
            "same_xy_support_as_original_A": support_unchanged,
            "base_mass_cases_kg": [estimated, upper],
            "mass_case_source": "validation_results.json mass.estimated_complete_base_kg and requirements.base_upper_budget_kg",
            "base_cg_assumed_xyz_mm": inputs["stability"]["base_cg_xyz_mm"],
            "component_assumptions_from_original_A": assumptions["inherited_component_assumptions"],
            "caster_orientation_samples_per_case": inputs["stability"]["caster_orientation_samples"],
            "caster_angle_step_deg": assumptions["caster_angle_step_deg"],
            "caster_angle_convention": assumptions["caster_angle_convention"],
            "note_ja": "CG=(0,0,85)mmは台車全体の未測定の仮定。電池を下げた後の実機CGではない。各姿勢で平床・重力・剛体・点接触を仮定しキャスター720方位を標本化。CG高さの低下は平床静止のXY支持余裕には反映されない。負の反力は接地離脱を示す。AとA2を同じ質量・同じCGで評価したときだけ静的結果が一致する。",
            "cases": cases,
        },
        "isolated_cg_relocation_sensitivity": {
            "battery_and_adapter_mass_assumed_kg": battery_mass,
            "battery_cg_old_new_assumed_z_mm": [old_battery_z, new_battery_z],
            "battery_only_mass_moment_change_kg_mm": battery_moment,
            "frame_mass_kg": frame_mass,
            "frame_cg_old_new_z_mm": [old_frame_z, new_frame_z],
            "frame_only_mass_moment_change_kg_mm": frame_moment,
            "cases": relocation_cases,
            "not_the_total_vehicle_cg_change": True,
            "note_ja": "同じ総質量Mの中で指定部品だけを移す感度例。電池/アダプター0.75kgが一体で高さ139.5→67.5mmへ動く仮定の寄与は−54/M mm、フレーム1.672kgを6mm下げる寄与は−10.032/M mm。元の139.5mmはAのトレイ上面107mm＋同じ65mm高さの予約電池の半高で、実選定電池のCGではない。この二項の和はA→A2の真の全体CG差ではない。支持板上昇、軸受反転、モーター位置、部品撤去/交換、質量差、配線・機器位置を全て積み上げていない。静的評価のCG=85mmからこの和を引いた計算もしていない。",
        },
        "self_checks": checks,
        "equilibrium_max_abs_residual": max_equilibrium_residual,
        "operation_approved": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=HERE / "design_parameters.json")
    parser.add_argument("--original", type=Path, default=HERE.parents[1] / "docs/amr-01/design_parameters.json")
    parser.add_argument("--validation", type=Path, default=HERE / "validation_results.json")
    parser.add_argument("--output", type=Path, default=HERE / "calculation_results.json")
    args = parser.parse_args()
    try:
        data = [json.loads(path.read_text(encoding="utf-8"))
                for path in (args.config, args.original, args.validation)]
        result = evaluate(*data)
        sources = {"config": args.config, "original_component_assumptions": args.original,
                   "CAD_mass": args.validation, "reused_numerical_functions": NUMERICAL_SOURCE}
        result["sources"] = {}
        for name, path in sources.items():
            resolved = path.resolve()
            try:
                result["sources"][name] = str(resolved.relative_to(HERE.parents[1]))
            except ValueError:
                result["sources"][name] = str(resolved)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    except (OSError, ValueError, TypeError, KeyError, ImportError) as exc:
        parser.exit(2, f"計算失敗: {exc}\n")
    print(f"A2 台車質量概算 {result['mass_inputs']['estimated_complete_base_kg']:.6f} kg")
    print(f"14kg駆動条件: 余裕込み {result['drive']['wheel_torque_with_margin_Nm']:.6f} N·m/輪")
    print(f"初期外輪 {result['drive']['initial_outer_wheel_rpm']:.6f} rpm; 静的ケース {len(result['static_support']['cases'])}")
    print(f"電池だけのCG感度寄与 {result['isolated_cg_relocation_sensitivity']['cases'][0]['battery_only_contribution_mm']:.6f} mm")


if __name__ == "__main__":
    main()
