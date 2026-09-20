"""Recalculate DDSM115 drive sizing, static reactions and wear sensitivity.

Run with Python 3; only the standard library is required. Shared static
equilibrium functions are imported from amr02, without its historical design.
"""
from pathlib import Path
import importlib.util
import json
import math

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("amr_statics", HERE.parent / "amr02/calculate_design.py")
numerical = importlib.util.module_from_spec(spec)
spec.loader.exec_module(numerical)


def evaluate(config, original, validation):
    numerical.validate_finite([config, original, validation])
    geo, drive = config["geometry"], config["drive"]
    mass = validation["mass"]
    estimated = mass["estimated_complete_base_kg"]
    assert math.isclose(estimated, mass["mechanical_estimate_kg"] + sum(config["mass_electrical_budget_kg"].values()))
    assert math.isclose(validation["drive_track_mm"], geo["drive_track_mm"])
    radius = geo["wheel_diameter_mm"] / 2000
    track = geo["drive_track_mm"] / 1000
    gross = config["requirements"]["gross_mass_calculation_limit_kg"]
    slope = math.radians(drive["slope_for_sizing_deg"])
    force = gross * (drive["acceleration_m_s2"] + numerical.G * math.sin(slope)
                    + drive["rolling_resistance_assumed"] * numerical.G * math.cos(slope))
    torque = force * radius / 2
    speeds = {}
    for name in ("initial", "later"):
        v, omega = drive[name + "_v_m_s"], drive[name + "_omega_rad_s"]
        speeds[name] = {"v_m_s": v, "omega_rad_s": omega,
                        "inner_wheel_rpm": (v - omega * track / 2) * 60 / (2 * math.pi * radius),
                        "outer_wheel_rpm": (v + omega * track / 2) * 60 / (2 * math.pi * radius)}
        speeds[name]["within_command_cap"] = speeds[name]["outer_wheel_rpm"] <= drive["wheel_command_cap_rpm"]

    assumption = original["stability_example"]
    c = numerical.component
    cargo = c(assumption["cargo_kg_xyz_mm"][0], assumption["cargo_kg_xyz_mm"][1:])
    folded = [c(assumption["arm_system_without_gripper_kg"], assumption["arm_folded_cg_xyz_mm"]),
              c(assumption["gripper_kg"], assumption["gripper_folded_cg_xyz_mm"])]
    forward = [c(assumption["arm_system_without_gripper_kg"], assumption["arm_forward_cg_xyz_mm"]),
               c(assumption["gripper_kg"], assumption["gripper_forward_cg_xyz_mm"])]
    contacts = numerical.contact_samples(geo, config["stability"]["caster_orientation_samples"])
    cases = []
    for base_mass in (estimated, config["requirements"]["base_upper_budget_kg"]):
        base = c(base_mass, config["stability"]["base_cg_xyz_mm"])
        scenarios = {"base_only": [base], "base_plus_cargo": [base, cargo],
                     "future_transport": [base, *folded, cargo]}
        for object_mass in assumption["object_mass_sensitivity_cases_kg"]:
            scenarios[f"forward_object_{object_mass:g}kg_NOT_APPROVED"] = [base, *forward]
            if object_mass:
                scenarios[f"forward_object_{object_mass:g}kg_NOT_APPROVED"].append(c(object_mass, assumption["object_cg_xyz_mm"]))
        for name, parts in scenarios.items():
            total, x, y, z = numerical.cg(parts)
            response = numerical.static_case(parts, contacts)
            cases.append({"base_mass_kg": base_mass, "scenario": name, "gross_mass_kg": total,
                          "assumed_cg_xyz_mm": [x, y, z], "components_kg_xyz_mm": parts, **response})

    # A kinematic sensitivity example, not a permitted wear depth or life estimate.
    nominal_radius_mm = radius * 1000
    radial_wear_mm = 1.0
    command_distance_mm = 1000.0
    equal_wheel_angle = command_distance_mm / nominal_radius_mm
    heading = radial_wear_mm * equal_wheel_angle / geo["drive_track_mm"]
    actual_arc = (nominal_radius_mm - radial_wear_mm / 2) * equal_wheel_angle
    turning_radius = actual_arc / heading
    transport = [x for x in cases if x["scenario"] in ("base_only", "base_plus_cargo", "future_transport")]
    max_transport_wheel_N = max(x["wheel_reaction_ranges_N"][side]["max_signed_N"] for x in transport for side in ("left", "right"))
    residual = max(value for x in cases for value in x["equilibrium_max_abs_residual"].values())
    assert residual < 1e-8
    assert all(x["all_sampled_reactions_nonnegative"] for x in transport)
    return {
        "version": config["version"], "design": config["design"],
        "status": "nominal_drive_and_assumed_static_CG_not_hardware_qualification",
        "sources": ["design_parameters.json", "validation_results.json", "../../docs/amr-01/design_parameters.json", "../amr02/calculate_design.py"],
        "mass_inputs": {"estimated_complete_base_kg": estimated, "base_upper_budget_kg": config["requirements"]["base_upper_budget_kg"]},
        "drive": {"gross_mass_kg": gross, "force_N": force, "wheel_torque_Nm": torque,
                  "wheel_torque_with_margin_Nm": torque * drive["torque_margin"],
                  "margin_factor": drive["torque_margin"], "catalog_rated_torque_Nm": drive["rated_torque_Nm"],
                  "rated_to_margin_requirement_ratio": drive["rated_torque_Nm"] / (torque * drive["torque_margin"]),
                  "sizing_inputs": {k: drive[k] for k in ("acceleration_m_s2", "slope_for_sizing_deg", "rolling_resistance_assumed")},
                  "wheel_diameter_mm": geo["wheel_diameter_mm"], "track_mm": geo["drive_track_mm"],
                  "speed_cases": speeds, "wheel_command_cap_rpm": drive["wheel_command_cap_rpm"],
                  "continuous_operation_verified": False,
                  "note_ja": "定格0.96N·mは18Vの公表値。計算は左右等分の駆動力で、旋回抵抗・段差衝撃・低電圧での発熱を含まない。5度は選定条件、90rpmは指令上限であり運用保証ではない。"},
        "static_support": {"base_cg_assumed_xyz_mm": config["stability"]["base_cg_xyz_mm"],
                           "caster_orientation_samples_per_case": len(contacts), "cases": cases,
                           "max_transport_drive_wheel_reaction_N": max_transport_wheel_N,
                           "max_transport_drive_wheel_equivalent_kg": max_transport_wheel_N / numerical.G,
                           "equilibrium_max_abs_residual": residual,
                           "note_ja": "CGは未実測の仮定。平床の剛体静止・キャスター720方位で算出。公表単輪荷重10kgは衝撃や動的条件の保証ではない。アーム前方展開は感度比較のみ。"},
        "tire_wear_sensitivity": {
            "tracked_point": "midpoint_between_drive_wheel_contacts_at_CAD_x90_y0",
            "assumed_radial_wear_mm_NOT_LIMIT": radial_wear_mm,
            "nominal_encoder_command_distance_mm": command_distance_mm,
            "both_wheels_equal_wear_actual_distance_mm": command_distance_mm * (nominal_radius_mm - radial_wear_mm) / nominal_radius_mm,
            "one_wheel_only_wear_heading_change_abs_deg": math.degrees(heading),
            "one_wheel_only_wear_lateral_offset_abs_mm": turning_radius * (1 - math.cos(heading)),
            "one_wheel_only_wear_forward_distance_mm": turning_radius * math.sin(heading),
            "note_ja": "一方の半径だけ1mm減り、左右同角度を指令した理想無滑りモデル。摩耗寿命・許容摩耗量ではない。弾性変形、キャスター過渡、床滑り、外部位置補正を含まない。"},
        "operation_approved": False,
    }


if __name__ == "__main__":
    result = evaluate(json.loads((HERE / "design_parameters.json").read_text()),
                      json.loads((HERE.parents[1] / "docs/amr-01/design_parameters.json").read_text()),
                      json.loads((HERE / "validation_results.json").read_text()))
    (HERE / "calculation_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: result[k] for k in ("mass_inputs", "drive", "tire_wear_sensitivity")}, ensure_ascii=False, indent=2))
    print("Static cases:", len(result["static_support"]["cases"]), "maximum transport drive-wheel equivalent kg:", result["static_support"]["max_transport_drive_wheel_equivalent_kg"])
