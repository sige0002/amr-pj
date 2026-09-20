"""Generate the A3 purchase BOM, CAD quantity checks and complete A2 comparison.

Run: python3 cad/amr04/calculate_cost.py
Prices are recorded references or allowances; this script performs no purchases.
The existing A2 cost arithmetic is reused without changing the historical BOM.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
A2 = HERE.parent / "amr03"
spec = importlib.util.spec_from_file_location("amr03_cost", A2 / "calculate_cost.py")
assert spec is not None and spec.loader is not None
_a2_cost = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_a2_cost)
calculate = _a2_cost.calculate


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def compare_with_A2(bom, old_bom, current, old):
    """Account for every purchase item on both sides, including new USB costs."""
    groups = [
        ("3030定尺", {"F01", "F02"}, {"F01", "F02"}),
        ("接合金具・溝ナット", {"F03", "F04"}, {"F03", "F04"}),
        ("駆動系（A3はドライバー内蔵）", {f"D{i:02d}" for i in range(1, 8)}, {"D01"}),
        ("キャスター", {"C01"}, {"C01"}),
        ("金属素材", {"P01", "P02", "P03"}, {"P01", "P02", "P03", "P05", "P06"}),
        ("既所有PLA消費分", {"P04"}, {"P04"}),
        ("追加一般締結材", {"H01"}, {"H01"}),
        ("電池固定ストラップ", {"H02"}, {"H02"}),
        ("USB-RS485通信インターフェース", set(), {"E01"}),
        ("USBケーブル", set(), {"E02"}),
    ]
    old_items = {item["id"]: item for item in old_bom["items"]}
    new_items = {item["id"]: item for item in bom["items"]}
    for side, index in ((old_items, 1), (new_items, 2)):
        listed = [item_id for group in groups for item_id in group[index]]
        if len(listed) != len(set(listed)) or set(listed) != set(side):
            raise ValueError("Comparison must cover each BOM item exactly once")

    def amount(items, item_ids):
        return sum(items[key]["packs"] * items[key]["pack_price_jpy"] for key in item_ids)

    rows = []
    for label, old_ids, new_ids in groups:
        before, after = amount(old_items, old_ids), amount(new_items, new_ids)
        rows.append({"group_ja": label, "A2_item_ids": sorted(old_ids),
                     "A3_item_ids": sorted(new_ids), "A2_jpy": before,
                     "A3_jpy": after, "difference_jpy": after - before})
    for row_key, total in (("A2_jpy", old), ("A3_jpy", current)):
        if not math.isclose(sum(row[row_key] for row in rows),
                            total["parts_and_consumables_subtotal_jpy"]):
            raise ValueError("Comparison purchase subtotal mismatch")
    rows.append({"group_ja": "部材配送", "A2_jpy": old["shipping_budget_jpy"],
                 "A3_jpy": current["shipping_budget_jpy"],
                 "difference_jpy": current["shipping_budget_jpy"] - old["shipping_budget_jpy"]})
    difference = current["self_fabrication_cash_budget_jpy"] - old["self_fabrication_cash_budget_jpy"]
    if not math.isclose(sum(row["difference_jpy"] for row in rows), difference):
        raise ValueError("Comparison delta mismatch")
    old_shipping = {item["id"]: item for item in old_bom["shipping"]}
    new_shipping = {item["id"]: item for item in bom["shipping"]}
    shipping_rows = []
    for key in sorted(set(old_shipping) | set(new_shipping)):
        before = old_shipping.get(key, {}).get("amount_jpy", 0)
        after = new_shipping.get(key, {}).get("amount_jpy", 0)
        shipping_rows.append({"id": key, "name": (new_shipping.get(key) or old_shipping[key])["name"],
                              "A2_jpy": before, "A3_jpy": after, "difference_jpy": after - before})
    if not math.isclose(sum(row["difference_jpy"] for row in shipping_rows), rows[-1]["difference_jpy"]):
        raise ValueError("Shipping comparison delta mismatch")
    return {
        "source_bom": "../amr03/bom.json", "source_summary": "../amr03/cost_summary.json",
        "A2_self_fabrication_jpy": old["self_fabrication_cash_budget_jpy"],
        "A2_outsourced_jpy": old["outsourced_fabrication_cash_budget_jpy"],
        "A3_self_fabrication_jpy": current["self_fabrication_cash_budget_jpy"],
        "A3_outsourced_jpy": current["outsourced_fabrication_cash_budget_jpy"],
        "self_difference_jpy": difference,
        "outsourced_difference_jpy": current["outsourced_fabrication_cash_budget_jpy"] - old["outsourced_fabrication_cash_budget_jpy"],
        "all_purchase_items_covered_once": True,
        "A2_purchase_row_count": len(old_items), "A3_purchase_row_count": len(new_items),
        "delta_breakdown": rows, "shipping_delta_breakdown": shipping_rows,
        "note_ja": "A2の全費目を対応付け、新設USB通信/ケーブルとその配送も省かず比較する。両案とも購入単位全体、PLAは既所有材の消費分。A2旧額は外付けドライバー/速度制御MCUなし、A3はドライバー内蔵とUSB通信を含むため、差額は同一完成機能の最終差額ではない。電源・主計算機・電池等は両案とも別の未見積費用。寿命・交換タイヤ等の維持費は初期BOM額に含まない。",
    }


def check_CAD_quantities(bom, params, validation):
    """Cross-check the owned BOM against independent CAD-generated records."""
    if bom["version"] != params["version"] or bom["design"] != params["design"]:
        raise ValueError("BOM version/design differs from CAD parameters")
    items = {item["id"]: item for item in bom["items"]}
    checks = bom["quantity_checks"]
    if items["F03"]["used"] != params["frame_joints"]["count"]:
        raise ValueError("Frame-joint count mismatch")
    with (HERE / checks["fastener_source"]).open(encoding="utf-8-sig", newline="") as stream:
        fasteners = []
        for row in csv.DictReader(stream):
            item = {"specification": row["specification"]}
            for key in ("installed_quantity", "included_in_HBLFSN6_SET", "additional_installed_quantity"):
                item[key] = int(row[key])
            if item["installed_quantity"] != item["included_in_HBLFSN6_SET"] + item["additional_installed_quantity"]:
                raise ValueError("Fastener included/additional count mismatch")
            if len(row["model_object_names"].split(";")) != item["installed_quantity"]:
                raise ValueError("Fastener model-object count mismatch")
            fasteners.append(item)
    if fasteners != checks["fasteners"]:
        raise ValueError("BOM fastener quantities are stale; update from current fasteners.csv")
    by_spec = {row["specification"]: row for row in fasteners}
    if len(by_spec) != len(fasteners):
        raise ValueError("Duplicate fastener specification")
    if {key: value["installed_quantity"] for key, value in by_spec.items()} != validation["hardware_installed"]:
        raise ValueError("Fastener CSV differs from CAD validation")
    nuts = by_spec["HNTT6-6 slot nut"]
    if [nuts["installed_quantity"], nuts["included_in_HBLFSN6_SET"], nuts["additional_installed_quantity"]] != [
        checks["slot_nuts_total"], checks["slot_nuts_included_in_sets"], checks["slot_nuts_additional"]
    ]:
        raise ValueError("Slot-nut quantity mismatch")
    if sum(checks["slot_nuts_by_use"].values()) != nuts["installed_quantity"]:
        raise ValueError("Slot-nut use subtotal mismatch")
    if items["F03"]["used"] * 2 != nuts["included_in_HBLFSN6_SET"] or items["F04"]["used"] != nuts["additional_installed_quantity"]:
        raise ValueError("Slot-nut purchase allocation mismatch")
    if by_spec["M6x12 socket screw"]["included_in_HBLFSN6_SET"] != items["F03"]["used"] * 2:
        raise ValueError("Included M6 screw count mismatch")
    mount = params["mount"]
    for bom_key, param_key in (
        ("upper_angle_stock_mm", "upper_angle_stock_mm"),
        ("upper_angle_finished_mm", "upper_angle_finished_mm"),
        ("lower_angle_stock_mm", "lower_angle_purchase_stock_mm"),
        ("lower_angle_finished_mm", "lower_angle_finished_mm"),
        ("key_plate_blank_mm", "key_plate_blank_mm"),
    ):
        if checks[bom_key] != mount[param_key]:
            raise ValueError(f"Mount stock/finished geometry mismatch: {bom_key}")
    if items["D01"]["used"] != checks["DDSM115_used"] or items["P06"]["used"] != checks["key_plate_count"]:
        raise ValueError("Drive/key purchase quantity mismatch")
    if by_spec["M2.5x10 socket screw"]["installed_quantity"] != mount["motor_mount_holes"] * items["D01"]["used"]:
        raise ValueError("Motor-face screw count mismatch")
    if checks["drive_spacers_used"] != params["geometry"]["drive_mount_spacer_count"] or checks["caster_spacers_used"] != params["geometry"]["caster_mount_spacer_count"]:
        raise ValueError("Spacer quantity mismatch")
    printed = validation["printed_parts"]
    plans = checks["printed_parts_planned_LWH_mm_count"]
    if len(printed) != len(plans):
        raise ValueError("Printed-part count mismatch")
    for part, dimensions in zip(printed, plans):
        if part["quantity"] != dimensions[3] or not all(math.isclose(x, y, abs_tol=1e-5) for x, y in zip(part["dimensions_mm"], dimensions[:3])):
            raise ValueError("Printed-part dimension/quantity mismatch")
    solid_mass = sum(part["solid_PLA_mass_kg"] * part["quantity"] for part in printed)
    if not math.isclose(solid_mass, checks["printed_parts_CAD_solid_PLA_mass_kg"], abs_tol=1e-9):
        raise ValueError("Printed-part mass is stale")
    return {"status": "passed", "sources": ["fasteners.csv", "design_parameters.json", "validation_results.json"],
            "fastener_specifications": len(fasteners),
            "general_fasteners_additional_installed": sum(row["additional_installed_quantity"] for row in fasteners if row["specification"] != "HNTT6-6 slot nut"),
            "printed_parts_count": len(printed), "printed_solid_PLA_mass_kg": solid_mass,
            "note_ja": "CAD数量の整合確認。販売単位、実部品適合、加工性の保証ではない。"}


def main():
    bom, old_bom = read_json(HERE / "bom.json"), read_json(A2 / "bom.json")
    result, old = calculate(bom), calculate(old_bom)
    saved_old = read_json(A2 / "cost_summary.json")
    for key in ("self_fabrication_cash_budget_jpy", "outsourced_fabrication_cash_budget_jpy"):
        if old[key] != saved_old[key]:
            raise ValueError(f"A2 saved cost is stale: {key}")
    for data in (bom, old_bom):
        shipping_ids = [row["id"] for row in data["shipping"]]
        if len(shipping_ids) != len(set(shipping_ids)):
            raise ValueError("Duplicate shipping ID")
    params, validation = read_json(HERE / "design_parameters.json"), read_json(HERE / "validation_results.json")
    quantity_result = check_CAD_quantities(bom, params, validation)
    old_mass, new_mass = read_json(A2 / "validation_results.json")["mass"], validation["mass"]
    mass_keys = ("mechanical_estimate_kg", "additional_electrical_budget_kg", "estimated_complete_base_kg")
    result = {
        "version": bom["version"], "design": bom["design"], "checked_on": bom["checked_on"],
        "currency": bom["currency"], "all_amounts_include_tax": bom["all_amounts_include_tax"],
        "status": "planning_budget_with_unquoted_items_not_purchase_quote",
        "source_bom": "bom.json", "scope_ja": bom["scope"], "price_kinds_ja": bom["price_kinds_ja"],
        **result, "fabrication": bom["fabrication"], "shipping": bom["shipping"],
        "quantity_checks": bom["quantity_checks"], "CAD_quantity_crosscheck": quantity_result,
        "comparison_with_A2": compare_with_A2(bom, old_bom, result, old),
        "mass_estimate_comparison": {
            "sources": ["../amr03/validation_results.json", "validation_results.json"],
            "A2": {key: old_mass[key] for key in mass_keys},
            "A3": {key: new_mass[key] for key in mass_keys},
            "difference": {key: new_mass[key] - old_mass[key] for key in mass_keys},
            "note_ja": "CAD体積・部品公称値・未選定電装の質量枠による推計。実測重量・実重心・搭載適合の保証ではない。電装の質量枠は価格の計上を意味しない。",
        },
        "initial_purchase_only": True, "lifetime_maintenance_cost_included": False,
        "maintenance_note_ja": "適合するDDSM115交換タイヤ単品のSKU・供給・寿命は未確認。初期BOM額に維持費は含まない。必要ならユニット12991円/輪（確認時単価、将来価格保証なし）の交換費を用いて保守費を再比較する。M0601C_111用タイヤ4620円は互換未確認で選定対象外。",
        "excluded_unpriced_items_ja": bom["excluded_unpriced_items_ja"],
        "not_selected_ja": bom["not_selected_ja"], "budget_note_ja": bom["budget_note_ja"],
    }
    (HERE / "cost_summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    with (HERE / "BOM.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["ID", "品名", "購入パック数", "1パック入数", "使用数", "余り", "税込パック単価", "購入小計", "価格区分", "URL", "注意", "計上単位", "調達状態"])
        for item in bom["items"]:
            writer.writerow([item["id"], item["name"], item["packs"], item["pieces_per_pack"], item["used"],
                             item["packs"] * item["pieces_per_pack"] - item["used"], item["pack_price_jpy"],
                             item["packs"] * item["pack_price_jpy"], item["price_kind"], item["url"],
                             item["note"], item["quantity_unit"], item["procurement_status"]])
    print(json.dumps({key: value for key, value in result.items() if key in (
        "parts_and_consumables_subtotal_jpy", "shipping_budget_jpy", "self_fabrication_cash_budget_jpy",
        "outsourced_fabrication_cash_budget_jpy", "self_fabrication_with_10pct_contingency_jpy",
        "outsourced_with_10pct_contingency_jpy", "CAD_quantity_crosscheck")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
