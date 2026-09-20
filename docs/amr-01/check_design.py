"""AMR-01 v0.2 の概念設計計算。Python 3.10+、標準ライブラリのみ。
入力値は設計仮定。実機、部品強度、動的安定性、停止性能の適合判定ではない。
Run: python3 check_design.py [--config path] [--output path]
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

G = 9.81
Point = tuple[float, float]
Component = tuple[float, float, float, float]  # kg, x_m, y_m, z_m


def validate_finite(value: Any) -> None:
    """Reject non-finite inputs, including JSON's nonstandard NaN/Infinity."""
    if isinstance(value, dict):
        for item in value.values():
            validate_finite(item)
    elif isinstance(value, list):
        for item in value:
            validate_finite(item)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(value):
            raise ValueError("入力値にNaNまたはInfinityがあります。")


def cg(parts: list[Component]) -> tuple[float, float, float, float]:
    if not parts or any(p[0] <= 0 for p in parts):
        raise ValueError("各構成物の質量は正である必要があります。")
    mass = sum(p[0] for p in parts)
    return (mass, *(sum(p[0] * p[i] for p in parts) / mass for i in (1, 2, 3)))


def support_margin(point: Point, polygon: list[Point]) -> float:
    """CCW凸多角形の各支持辺への符号付き距離の最小値。内側が正。"""
    if len(polygon) < 3:
        raise ValueError("支持多角形には3点以上が必要です。")
    area2 = sum(a[0] * b[1] - b[0] * a[1]
                for a, b in zip(polygon, polygon[1:] + polygon[:1]))
    if area2 <= 0:
        raise ValueError("支持多角形は非退化・反時計回りで指定してください。")
    margins = []
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        if length == 0:
            raise ValueError("支持点が重複しています。")
        margins.append((dx * (point[1] - a[1]) - dy * (point[0] - a[0])) / length)
    return min(margins)


def front_tip(parts: list[Component], edge_x: float) -> dict[str, float | None]:
    restoring = sum(m * G * max(edge_x - x, 0.0) for m, x, _, _ in parts)
    overturning = sum(m * G * max(x - edge_x, 0.0) for m, x, _, _ in parts)
    return {"restoring_Nm": restoring, "overturning_Nm": overturning,
            "static_moment_ratio": restoring / overturning if overturning > 0 else None}


def component(mass: float, xyz_mm: list[float]) -> Component:
    if len(xyz_mm) != 3:
        raise ValueError("重心座標はx,y,zの3要素です。")
    return (mass, *(v / 1000 for v in xyz_mm))


def evaluate(config: dict[str, Any]) -> dict[str, Any]:
    validate_finite(config)
    req, geo, drive = config["requirements"], config["geometry"], config["drive"]
    frame, stability = config["frame"], config["stability_example"]
    required_positive = [req["base_target_kg"], req["base_upper_budget_kg"],
                         req["gross_mass_calculation_limit_kg"], geo["wheel_diameter_mm"],
                         geo["drive_track_mm"], geo["body_length_mm"], geo["body_width_mm"],
                         frame["elastic_modulus_assumed_N_mm2"], frame["reference_second_moment_mm4"],
                         frame["beam_example_load_sharing_count"], config["stopping_example"]["deceleration_m_s2"]]
    if any(v <= 0 for v in required_positive):
        raise ValueError("寸法、質量、弾性係数、負担梁数、減速度は正である必要があります。")
    for field in ("initial_speed_m_s", "later_speed_limit_m_s", "acceleration_m_s2",
                  "rolling_resistance_coefficient_assumed", "later_yaw_rate_limit_rad_s"):
        if drive[field] < 0:
            raise ValueError(f"drive.{field} は非負にしてください。")
    if not 0 <= drive["slope_for_sizing_deg"] < 90 or drive["torque_margin_factor"] < 1:
        raise ValueError("勾配は0〜90度未満、トルク余裕係数は1以上にしてください。")
    if geo["caster_trail_mm"] < 0:
        raise ValueError("キャスタートレールは非負です。")
    samples = geo["caster_orientation_samples"]
    if not isinstance(samples, int) or isinstance(samples, bool) or samples < 16:
        raise ValueError("キャスター角度サンプル数は16以上の整数です。")
    if req["base_target_kg"] > req["base_upper_budget_kg"]:
        raise ValueError("台車目標質量が上限を超えています。")
    if req["base_upper_budget_kg"] + req["arm_system_upper_budget_kg"] + req["cargo_limit_kg"] > req["gross_mass_calculation_limit_kg"] + 1e-9:
        raise ValueError("最大構成が総質量の計算枠を超えています。")
    if not math.isclose(sum(config["mass_budget_target_kg"].values()), req["base_target_kg"], abs_tol=1e-9):
        raise ValueError("重量配分の合計と台車目標質量が一致しません。")
    if not math.isclose(stability["arm_system_without_gripper_kg"] + stability["gripper_kg"], req["arm_system_upper_budget_kg"], abs_tol=1e-9):
        raise ValueError("参考アーム系の合計とアーム質量予算が一致しません。")

    radius = geo["wheel_diameter_mm"] / 2000
    track, edge = geo["drive_track_mm"] / 1000, geo["drive_axle_x_mm"] / 1000
    mass, angle = req["gross_mass_calculation_limit_kg"], math.radians(drive["slope_for_sizing_deg"])
    force = mass * (drive["acceleration_m_s2"] + G * math.sin(angle)
                    + drive["rolling_resistance_coefficient_assumed"] * G * math.cos(angle))
    torque = force * radius / 2
    speed, omega = drive["later_speed_limit_m_s"], drive["later_yaw_rate_limit_rad_s"]
    rpm = speed / (2 * math.pi * radius) * 60
    outer_rpm = (speed + omega * track / 2) / (2 * math.pi * radius) * 60
    l, w = geo["body_length_mm"], geo["body_width_mm"]
    pivot_x = geo["drive_axle_x_mm"]
    diameter = 2 * max(math.hypot(x - pivot_x, y) for x in (-l / 2, l / 2) for y in (-w / 2, w / 2))
    cx, cy = (v / 1000 for v in geo["caster_swivel_xy_mm"])
    trail = geo["caster_trail_mm"] / 1000
    polygons = [[(cx + trail * math.cos(2 * math.pi * k / samples),
                   cy + trail * math.sin(2 * math.pi * k / samples)),
                 (edge, -track / 2), (edge, track / 2)] for k in range(samples)]
    cases = {}
    for base_mass in stability["base_mass_cases_kg"]:
        base = component(base_mass, stability["base_cg_xyz_mm"])
        cargo = component(stability["cargo_kg_xyz_mm"][0], stability["cargo_kg_xyz_mm"][1:])
        folded = [component(stability["arm_system_without_gripper_kg"], stability["arm_folded_cg_xyz_mm"]),
                  component(stability["gripper_kg"], stability["gripper_folded_cg_xyz_mm"])]
        forward = [component(stability["arm_system_without_gripper_kg"], stability["arm_forward_cg_xyz_mm"]),
                   component(stability["gripper_kg"], stability["gripper_forward_cg_xyz_mm"])]
        scenarios = {"base_only": [base], "base_plus_cargo": [base, cargo],
                     "future_transport": [base, *folded, cargo]}
        for object_mass in stability["object_mass_sensitivity_cases_kg"]:
            if not 0 <= object_mass <= req["cargo_limit_kg"]:
                raise ValueError("参考把持物の質量は0〜運搬上限以内にしてください。")
            scenarios[f"forward_object_{object_mass:g}kg_NOT_APPROVED"] = [base, *forward]
            if object_mass > 0:
                scenarios[f"forward_object_{object_mass:g}kg_NOT_APPROVED"].append(component(object_mass, stability["object_cg_xyz_mm"]))
        for name, parts in scenarios.items():
            m, x, y, z = cg(parts)
            margins = [support_margin((x, y), polygon) for polygon in polygons]
            cases[f"base_{base_mass:g}kg/{name}"] = {
                "components_kg_xyz_m": [list(p) for p in parts], "total_mass_kg": m,
                "cg_xyz_mm": [1000 * v for v in (x, y, z)],
                "front_edge_margin_mm": (edge - x) * 1000,
                "worst_sampled_caster_support_margin_mm": min(margins) * 1000,
                "front_tip": front_tip(parts, edge),
                "sampled_flat_static_cg_inside": min(margins) > 0,
                "operation_approved": False,
                "note_ja": "仮定した一姿勢の静的計算。正の支持余裕でも運転・把持を許可しない。"}
    length = sum(mm * count for mm, count in frame["cuts_mm_count"]) / 1000
    per_beam_force = frame["beam_example_total_force_N"] / frame["beam_example_load_sharing_count"]
    deflection = per_beam_force * frame["beam_example_span_mm"] ** 3 / (48 * frame["elastic_modulus_assumed_N_mm2"] * frame["reference_second_moment_mm4"])
    stop = config["stopping_example"]
    runtime = config["runtime_example"]
    if not 0 < runtime["usable_fraction_assumed"] <= 1 or any(p <= 0 for p in runtime["average_power_examples_W"]):
        raise ValueError("使用可能率は0より大きく1以下、平均電力は正にしてください。")
    if stop["latency_s"] < 0:
        raise ValueError("遅延は非負にしてください。")
    wh = runtime["voltage_V"] * runtime["capacity_Ah"]
    rx, ry = geo["caster_swivel_xy_mm"]
    sr = geo["caster_assembly_sweep_radius_mm"]
    return {
        "version": config["version"], "status": config["status"],
        "note_ja": "数値は設計仮定からの再計算。部品選定・CAD・実機検証・安全認証ではない。",
        "envelope_LW_mm": [l, w], "mass_budget_sum_kg": sum(config["mass_budget_target_kg"].values()),
        "max_config_mass_at_target_kg": req["base_target_kg"] + req["arm_system_upper_budget_kg"] + req["cargo_limit_kg"],
        "max_config_mass_at_upper_budget_kg": req["base_upper_budget_kg"] + req["arm_system_upper_budget_kg"] + req["cargo_limit_kg"],
        "turning": {"body_only_pivot_swept_diameter_mm": diameter,
                    "body_only_pivot_swept_radius_mm": diameter / 2,
                    "area_ratio_to_v0p1": l * w / (520 * 420),
                    "note_ja": "車軸中心で理想的にその場旋回。アームのはみ出し・誤差・安全離隔を含まない。"},
        "envelope_checks_simplified": {
            "wheel_rectangles_inside": abs(pivot_x) + geo["wheel_diameter_mm"] / 2 <= l / 2 and geo["drive_track_mm"] / 2 + geo["wheel_width_mm"] / 2 <= w / 2,
            "caster_assembly_swept_circle_inside": abs(rx) + sr <= l / 2 and abs(ry) + sr <= w / 2,
            "note_ja": "車輪の矩形とキャスター包絡円だけの概算。干渉なしの保証ではない。"},
        "drive": {"gross_mass_kg": mass, "force_N": force,
                  "wheel_torque_Nm": torque, "wheel_torque_with_margin_Nm": torque * drive["torque_margin_factor"],
                  "straight_wheel_rpm": rpm, "outer_wheel_rpm": outer_rpm,
                  "continuous_torque_target_range_Nm": drive["continuous_wheel_torque_target_range_Nm"],
                  "loaded_wheel_speed_target_rpm": drive["loaded_wheel_speed_target_rpm"]},
        "frame": {"extrusion_total_m": length, "extrusion_mass_kg": length * frame["reference_mass_kg_per_m"],
                  "beam_only_deflection_example_mm": deflection,
                  "note_ja": "接合部・取付板・ねじれ・アームモーメントを含まない。"},
        "stopping_examples": {f"{v:g}_m_s": v * stop["latency_s"] + v * v / (2 * stop["deceleration_m_s2"])
                              for v in (drive["initial_speed_m_s"], speed)},
        "runtime_examples": {"nominal_Wh": wh, "hours_by_assumed_W": {str(p): wh * runtime["usable_fraction_assumed"] / p for p in runtime["average_power_examples_W"]}},
        "reach_example_distance_mm": math.dist(config["reach_example"]["shoulder_xyz_mm"], config["reach_example"]["tcp_xyz_mm"]),
        "stability_cases": cases,
        "unverified": ["部品の入手性・実寸・総質量", "部屋の通路・収納場所・旋回空間", "構造・接合部・支持軸の強度",
                       "保持・非常停止・タイヤ摩擦", "アーム全姿勢・把持重量・逆運動学", "電池保護・回生処理", "実機性能・無監督家庭内運用"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parent
    parser.add_argument("--config", type=Path, default=root / "design_parameters.json")
    parser.add_argument("--output", type=Path, default=root / "calculation_results.json")
    args = parser.parse_args()
    try:
        result = evaluate(json.loads(args.config.read_text(encoding="utf-8")))
        text = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"計算失敗: {exc}\n")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
