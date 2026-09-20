"""AMR-01 B の軸・駆動・静的支持計算。Python 3.10+、標準ライブラリのみ。

Run: python3 calculate_design.py [--config JSON] [--baseline JSON] [--output JSON]
第一案の重心仮定を読み、同じ質量・姿勢で支持配置だけを比較する。
部品定格、動的転倒、実機の可搬能力、運転・把持の承認は判定しない。
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

G = 9.81
Point = tuple[float, float]  # mm
Component = tuple[float, float, float, float]  # kg, x_mm, y_mm, z_mm


def validate_finite(value: Any) -> None:
    if isinstance(value, dict):
        for item in value.values():
            validate_finite(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            validate_finite(item)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(value):
            raise ValueError("NaN/Infinityは計算入力に使用できません。")


def positive(value: Any, name: str, allow_zero: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name}は数値で指定してください。")
    if not math.isfinite(value) or value < 0 or (value == 0 and not allow_zero):
        raise ValueError(f"{name}は有限の{'非負' if allow_zero else '正'}の数値が必要です。")
    return float(value)


def component(mass: float, xyz_mm: list[float]) -> Component:
    positive(mass, "component mass")
    if len(xyz_mm) != 3:
        raise ValueError("重心座標はx,y,zの3要素が必要です。")
    validate_finite(xyz_mm)
    return (mass, *xyz_mm)


def cg(parts: list[Component]) -> Component:
    if not parts or any(part[0] <= 0 for part in parts):
        raise ValueError("重心計算には正の質量の構成物が必要です。")
    mass = sum(part[0] for part in parts)
    return (mass, *(sum(part[0] * part[i] for part in parts) / mass for i in (1, 2, 3)))


def support_margin(point: Point, polygon: list[Point]) -> float:
    """CCW凸支持多角形の各辺への符号付き距離の最小値、mm。"""
    if len(polygon) < 3:
        raise ValueError("支持多角形には3点以上が必要です。")
    edges = list(zip(polygon, polygon[1:] + polygon[:1]))
    area2 = sum(a[0] * b[1] - b[0] * a[1] for a, b in edges)
    if area2 <= 0:
        raise ValueError("支持多角形は非退化・反時計回りにしてください。")
    distances = []
    for a, b in edges:
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        if length == 0:
            raise ValueError("支持点が重複しています。")
        distances.append((dx * (point[1] - a[1]) - dy * (point[0] - a[0])) / length)
    return min(distances)


def front_tip(parts: list[Component], edge_x_mm: float) -> dict[str, float | None]:
    restoring = sum(m * G * max(edge_x_mm - x, 0) / 1000 for m, x, _, _ in parts)
    overturning = sum(m * G * max(x - edge_x_mm, 0) / 1000 for m, x, _, _ in parts)
    return {"restoring_Nm": restoring, "overturning_Nm": overturning,
            "static_moment_ratio": restoring / overturning if overturning > 0 else None}


def shaft_response(load_N: float, support_y_mm: list[float], load_y_mm: float,
                   diameter_mm: float, elastic_modulus_N_mm2: float) -> dict[str, Any]:
    """二点単純支持軸の荷重点たわみ。支持間内と左右張出しに対応する。"""
    positive(load_N, "wheel load", allow_zero=True)
    positive(diameter_mm, "shaft diameter")
    positive(elastic_modulus_N_mm2, "elastic modulus")
    if len(support_y_mm) != 2 or support_y_mm[1] <= support_y_mm[0]:
        raise ValueError("軸受位置は小さい方から異なる2点を指定してください。")
    validate_finite([support_y_mm, load_y_mm])
    length = support_y_mm[1] - support_y_mm[0]
    a = load_y_mm - support_y_mm[0]
    inertia = math.pi * diameter_mm ** 4 / 64
    reactions = [load_N * (length - a) / length, load_N * a / length]
    if 0 <= a <= length:
        b = length - a
        moment = load_N * a * b / length
        deflection = load_N * a * a * b * b / (3 * elastic_modulus_N_mm2 * inertia * length)
        arrangement = "between_bearings"
    else:
        overhang = -a if a < 0 else a - length
        moment = load_N * overhang
        deflection = load_N * overhang ** 2 * (length + overhang) / (3 * elastic_modulus_N_mm2 * inertia)
        arrangement = "overhung"
    return {
        "load_N": load_N, "bearing_support_y_mm": support_y_mm,
        "load_y_mm": load_y_mm, "bearing_span_mm": length, "arrangement": arrangement,
        "inner_outer_signed_reaction_N": reactions,
        "max_abs_bearing_reaction_N": max(abs(force) for force in reactions),
        "max_bending_moment_Nm": moment / 1000,
        "max_bending_stress_MPa": 32 * moment / (math.pi * diameter_mm ** 3),
        "load_point_deflection_mm": deflection,
    }


def wheel_reactions(mass_kg: float, cg_xy_mm: Point, contacts: dict[str, Point]) -> dict[str, float]:
    """ΣFz=mg, ΣxFz=mg*xCG, ΣyFz=mg*yCGから鉛直三点反力を求める。"""
    positive(mass_kg, "supported mass")
    left, right, caster = (contacts[key] for key in ("left", "right", "caster"))
    if not math.isclose(left[0], right[0], abs_tol=1e-12) or not left[1] > right[1]:
        raise ValueError("左右駆動輪は同じx座標、左輪のyは右輪より大きくしてください。")
    if left[0] <= caster[0]:
        raise ValueError("キャスター接地点は駆動車軸より後ろに必要です。")
    weight = mass_kg * G
    caster_force = weight * (left[0] - cg_xy_mm[0]) / (left[0] - caster[0])
    drive_total = weight - caster_force
    left_force = (weight * cg_xy_mm[1] - caster_force * caster[1] - drive_total * right[1]) / (left[1] - right[1])
    return {"left": left_force, "right": drive_total - left_force, "caster": caster_force}


def contact_samples(geometry: dict[str, Any], count: int) -> list[dict[str, Point]]:
    track = positive(geometry["drive_track_mm"], "drive track")
    positive(geometry["caster_trail_mm"], "caster trail", allow_zero=True)
    if isinstance(count, bool) or not isinstance(count, int) or count < 16:
        raise ValueError("キャスター角度サンプル数は16以上の整数が必要です。")
    edge = geometry["drive_axle_x_mm"]
    cx, cy = geometry["caster_pivot_xy_mm"]
    trail = geometry["caster_trail_mm"]
    if edge <= cx + trail:
        raise ValueError("全旋回範囲でキャスター接地点を駆動車軸より後ろにしてください。")
    return [{"left": (edge, track / 2), "right": (edge, -track / 2),
             "caster": (cx + trail * math.cos(2 * math.pi * k / count),
                        cy + trail * math.sin(2 * math.pi * k / count))} for k in range(count)]


def static_case(parts: list[Component], contacts_by_angle: list[dict[str, Point]]) -> dict[str, Any]:
    mass, x, y, _ = cg(parts)
    evaluations = []
    force_error = x_moment_error = y_moment_error = 0.0
    for contacts in contacts_by_angle:
        polygon = [contacts[key] for key in ("caster", "right", "left")]
        reactions = wheel_reactions(mass, (x, y), contacts)
        evaluations.append((support_margin((x, y), polygon), reactions))
        force_error = max(force_error, abs(sum(reactions.values()) - mass * G))
        x_moment_error = max(x_moment_error, abs(sum(reactions[k] * contacts[k][0] for k in reactions) - mass * G * x))
        y_moment_error = max(y_moment_error, abs(sum(reactions[k] * contacts[k][1] for k in reactions) - mass * G * y))
    worst = min(range(len(evaluations)), key=lambda index: evaluations[index][0])
    minimum = evaluations[worst][0]
    ranges = {}
    for key in ("left", "right", "caster"):
        min_index = min(range(len(evaluations)), key=lambda index: evaluations[index][1][key])
        max_index = max(range(len(evaluations)), key=lambda index: evaluations[index][1][key])
        ranges[key] = {
            "min_signed_N": evaluations[min_index][1][key],
            "max_signed_N": evaluations[max_index][1][key],
            "min_at_caster_angle_deg": min_index * 360 / len(evaluations),
            "max_at_caster_angle_deg": max_index * 360 / len(evaluations),
        }
    edge = contacts_by_angle[0]["left"][0]
    return {
        "front_edge_margin_mm": edge - x,
        "worst_sampled_caster_support_margin_mm": minimum,
        "worst_margin_caster_angle_deg": worst * 360 / len(evaluations),
        "contacts_at_worst_margin_xy_mm": contacts_by_angle[worst],
        "signed_reactions_at_worst_margin_N": evaluations[worst][1],
        "wheel_reaction_ranges_N": ranges,
        "all_sampled_reactions_nonnegative": all(item["min_signed_N"] >= -1e-9 for item in ranges.values()),
        "sampled_flat_static_cg_inside": minimum > 0,
        "front_tip": front_tip(parts, edge),
        "equilibrium_max_abs_residual": {
            "vertical_force_N": force_error, "x_weight_moment_Nmm": x_moment_error,
            "y_weight_moment_Nmm": y_moment_error,
        },
        "operation_approved": False,
    }


def evaluate(config: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    validate_finite(config)
    validate_finite(baseline)
    req, geo, drive = (config[key] for key in ("requirements", "geometry", "drive"))
    shaft, stability = config["shaft_comparison"], config["stability"]
    original = baseline["stability_example"]
    base_limit = positive(req["base_upper_budget_kg"], "base mass limit")
    cargo_limit = positive(req["cargo_limit_kg"], "cargo limit", allow_zero=True)
    arm_limit = positive(req["arm_system_upper_budget_kg"], "arm limit", allow_zero=True)
    gross_mass = positive(req["gross_mass_calculation_limit_kg"], "gross mass")
    if base_limit + cargo_limit + arm_limit > gross_mass + 1e-9:
        raise ValueError("台車＋運搬物＋アームの合計が総質量計算枠を超えています。")
    if not math.isclose(original["arm_system_without_gripper_kg"] + original["gripper_kg"], arm_limit, abs_tol=1e-9):
        raise ValueError("比較に使うアーム系質量が第二案の予算と一致しません。")
    if original["cargo_kg_xyz_mm"][0] > cargo_limit:
        raise ValueError("比較に使う荷物が第二案の運搬物上限を超えています。")
    if not math.isclose(geo["drive_track_mm"] / 2, shaft["new_load_y_mm"], abs_tol=1e-9):
        raise ValueError("輪距と新車輪軸の荷重点が一致しません。")
    if geo["bearing_support_y_mm"] != shaft["new_bearing_y_mm"]:
        raise ValueError("配置と軸計算の軸受支持位置が一致しません。")

    shaft_cases = {}
    for label in ("old", "new"):
        shaft_cases[label] = [shaft_response(load, shaft[f"{label}_bearing_y_mm"],
                                            shaft[f"{label}_load_y_mm"], shaft["diameter_mm"],
                                            shaft["elastic_modulus_assumed_N_mm2"])
                              for load in shaft["comparison_wheel_loads_N"]]

    radius = positive(geo["wheel_diameter_mm"], "wheel diameter") / 2000
    track = positive(geo["drive_track_mm"], "track") / 1000
    cap = positive(drive["wheel_command_cap_rpm"], "wheel command cap")
    acceleration = positive(drive["acceleration_m_s2"], "acceleration", allow_zero=True)
    rolling = positive(drive["rolling_resistance_assumed"], "rolling coefficient", allow_zero=True)
    angle_deg = positive(drive["slope_for_sizing_deg"], "slope", allow_zero=True)
    margin = positive(drive["torque_margin"], "torque margin")
    if angle_deg >= 90 or margin < 1:
        raise ValueError("計算勾配は90度未満、トルク余裕係数は1以上にしてください。")
    angle = math.radians(angle_deg)
    force = gross_mass * (acceleration + G * math.sin(angle) + rolling * G * math.cos(angle))
    torque = force * radius / 2
    rim_cap = cap * 2 * math.pi * radius / 60
    speeds = {}
    for label in ("initial", "later"):
        v = positive(drive[f"{label}_v_m_s"], "translation speed", allow_zero=True)
        omega = positive(drive[f"{label}_omega_rad_s"], "yaw rate", allow_zero=True)
        speeds[label] = {
            "v_m_s": v, "omega_rad_s": omega,
            "inner_wheel_rpm": (v - omega * track / 2) / (2 * math.pi * radius) * 60,
            "outer_wheel_rpm": (v + omega * track / 2) / (2 * math.pi * radius) * 60,
            "straight_wheel_rpm": v / (2 * math.pi * radius) * 60,
            "combined_command_fits_cap": v + omega * track / 2 <= rim_cap,
            "max_abs_omega_at_this_v_rad_s": max(0.0, 2 * (rim_cap - v) / track),
            "v_alone_fits_cap": v <= rim_cap,
        }

    sample_count = stability["caster_orientation_samples"]
    new_contacts = contact_samples(geo, sample_count)
    old_geo = baseline["geometry"]
    old_contact_geometry = {
        "drive_axle_x_mm": old_geo["drive_axle_x_mm"], "drive_track_mm": old_geo["drive_track_mm"],
        "caster_pivot_xy_mm": old_geo["caster_swivel_xy_mm"], "caster_trail_mm": old_geo["caster_trail_mm"],
    }
    old_contacts = contact_samples(old_contact_geometry, sample_count)
    cargo = component(original["cargo_kg_xyz_mm"][0], original["cargo_kg_xyz_mm"][1:])
    folded = [component(original["arm_system_without_gripper_kg"], original["arm_folded_cg_xyz_mm"]),
              component(original["gripper_kg"], original["gripper_folded_cg_xyz_mm"])]
    forward = [component(original["arm_system_without_gripper_kg"], original["arm_forward_cg_xyz_mm"]),
               component(original["gripper_kg"], original["gripper_forward_cg_xyz_mm"])]
    cases = {}
    for base_mass in stability["base_mass_cases_kg"]:
        positive(base_mass, "base mass case")
        if base_mass > base_limit:
            raise ValueError("台車質量の感度ケースが第二案の上限を超えています。")
        base = component(base_mass, stability["base_cg_xyz_mm"])
        scenarios = {"base_only": [base], "base_plus_cargo": [base, cargo],
                     "future_transport": [base, *folded, cargo]}
        for object_mass in original["object_mass_sensitivity_cases_kg"]:
            positive(object_mass, "object mass case", allow_zero=True)
            if object_mass > cargo_limit:
                raise ValueError("把持物感度ケースが運搬物上限を超えています。")
            parts = [base, *forward]
            if object_mass > 0:
                parts.append(component(object_mass, original["object_cg_xyz_mm"]))
            scenarios[f"forward_object_{object_mass:g}kg_NOT_APPROVED"] = parts
        for name, parts in scenarios.items():
            mass, x, y, z = cg(parts)
            first, second = static_case(parts, old_contacts), static_case(parts, new_contacts)
            cases[f"base_{base_mass:g}kg/{name}"] = {
                "components_kg_xyz_mm": parts, "total_mass_kg": mass, "cg_xyz_mm": [x, y, z],
                "first_design_A": first, "second_design_B": second,
                "support_margin_B_minus_A_mm": second["worst_sampled_caster_support_margin_mm"] - first["worst_sampled_caster_support_margin_mm"],
                "operation_approved": False,
            }

    return {
        "version": config["version"], "design": config["design"], "status": config["status"],
        "baseline_version": baseline["version"], "gravity_assumed_m_s2": G,
        "note_ja": "仮の重心と一姿勢ごとの剛体静的計算。軸・軸受・継手の定格、動的転倒、実機可搬能力、運転・把持を承認する結果ではない。",
        "shaft_comparison": {
            "diameter_mm": shaft["diameter_mm"],
            "elastic_modulus_assumed_N_mm2": shaft["elastic_modulus_assumed_N_mm2"],
            **shaft_cases,
            "note_ja": shaft["note_ja"] + " 反力の負号は逆向き支持を表す。100/200Nは配置比較用で総質量から得た一輪荷重ではない。",
        },
        "drive": {
            "gross_mass_kg": gross_mass, "force_N": force,
            "wheel_torque_Nm": torque, "wheel_torque_with_margin_Nm": torque * margin,
            "torque_margin": margin, "selected_motor": drive["selected_motor"],
            "motor_no_load_rpm_NOT_LOADED_RATING": drive["no_load_rpm"],
            "motor_stall_torque_Nm_NOT_CONTINUOUS_RATING": drive["stall_torque_kgfcm"] * 0.0980665,
            "continuous_torque_verified": drive["continuous_torque_verified"],
            "wheel_command_cap_rpm_NOT_RATING": cap,
            "initial_outer_wheel_rpm": speeds["initial"]["outer_wheel_rpm"],
            "later_outer_wheel_rpm": speeds["later"]["outer_wheel_rpm"],
            "speed_cases": speeds,
            "coupled_command_limit": {
                "formula": "abs(v_m_s) + half_track_m * abs(omega_rad_s) <= wheel_rim_speed_cap_m_s",
                "half_track_m": track / 2, "wheel_rim_speed_cap_m_s": rim_cap,
            },
            "note_ja": "必要駆動力を左右へ均等配分したトルク計算。輪荷重の均等配分を意味しない。5度は選定計算条件、65rpmは指令上限であり負荷時性能・連続定格・坂道走行許可ではない。",
        },
        "stability_assumptions": {
            "base_mass_cases_kg": stability["base_mass_cases_kg"],
            "base_cg_xyz_mm": stability["base_cg_xyz_mm"],
            "inherited_component_assumptions": {key: value for key, value in original.items()
                                                if key not in ("base_mass_cases_kg", "base_cg_xyz_mm", "note_ja")},
            "first_design_A_contact_geometry": old_contact_geometry,
            "second_design_B_contact_geometry": {key: geo[key] for key in old_contact_geometry},
            "caster_orientation_samples_each_design": sample_count,
            "caster_angle_step_deg": 360 / sample_count,
            "caster_angle_convention": "contact = pivot + trail*(cos(theta), sin(theta)); theta in [0, 360) deg",
            "note_ja": "全旋回360度を有限個でサンプルした最小余裕。A/Bとも同じ角度分割・質量・重心を使用。接地点は点、平床、重力のみ。CG高さは記録するが静的平床の支持余裕には影響しない。",
            "reaction_note_ja": "鉛直力とx/y方向一次モーメントの釣合いで左右輪・キャスターの反力を計算。負の計算反力は接地離脱を示し、実接触が負荷を引張支持できる意味ではない。各輪の最小・最大は別のキャスター角度で起こる。",
        },
        "stability_cases": cases,
        "operation_approved": False,
    }


def main() -> int:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=root / "design_parameters.json")
    parser.add_argument("--baseline", type=Path, default=root.parents[1] / "docs/amr-01/design_parameters.json")
    parser.add_argument("--output", type=Path, default=root / "calculation_results.json")
    args = parser.parse_args()
    try:
        result = evaluate(json.loads(args.config.read_text(encoding="utf-8")),
                          json.loads(args.baseline.read_text(encoding="utf-8")))
        input_files = {}
        for name, path in (("config", args.config), ("baseline", args.baseline)):
            resolved = path.resolve()
            try:
                input_files[name] = str(resolved.relative_to(root.parents[1]))
            except ValueError:
                input_files[name] = str(resolved)
        result["input_files"] = input_files
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, f"計算失敗: {exc}\n")
    print(f"計算出力: {args.output}")
    print(f"最大{result['drive']['gross_mass_kg']:g}kg、余裕込み一輪トルク {result['drive']['wheel_torque_with_margin_Nm']:.6f} N·m")
    print(f"外輪回転数: 初期 {result['drive']['initial_outer_wheel_rpm']:.3f} / 後期 {result['drive']['later_outer_wheel_rpm']:.3f} rpm")
    print(f"静的ケース {len(result['stability_cases'])}、各案キャスター {result['stability_assumptions']['caster_orientation_samples_each_design']} 方位。運転承認なし。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
