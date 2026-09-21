"""A4 cost scenarios: unknown mandatory costs remain null, never zero.

Run: python3 cad/amr05/calculate_cost.py [--require-cad] [--self-test]
The default BOM CSV is the custom mount, Taobao motor, separate initial tyre case.
No quote request or purchase is sent by this script.
"""
from __future__ import annotations

import argparse
import copy
import csv
import json
import math
from decimal import Decimal, ROUND_CEILING
from pathlib import Path

HERE = Path(__file__).resolve().parent
A3 = HERE.parent / "amr04"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def money(value):
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("Boolean is not a price")
    result = Decimal(str(value))
    if not result.is_finite() or result < 0:
        raise ValueError(f"Invalid price: {value}")
    return result


def json_number(value):
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    raise TypeError(type(value).__name__)


def purchase_amount(item):
    value = money(item["pack_price_jpy"])
    return None if value is None else value * item["packs"]


def aggregate(rows):
    """Rows carry an ID, price provenance and an already quantity-scaled amount."""
    known = Decimal(0)
    kinds, pending = {}, []
    for row in rows:
        value = money(row["amount_jpy"])
        if value is None:
            pending.append({"id": row["id"], "name": row["name"], "reason": row["price_kind"]})
        else:
            known += value
            kinds[row["price_kind"]] = kinds.get(row["price_kind"], Decimal(0)) + value
    return {"priced_and_allowance_subtotal_jpy": known,
            "priced_subtotals_by_kind_jpy": kinds,
            "required_unpriced_entries": pending,
            "planning_total_jpy": None if pending else known}


def validate_bom(bom):
    ids = set()
    for item in bom["items"]:
        if item["id"] in ids:
            raise ValueError("Duplicate purchase ID")
        ids.add(item["id"])
        for key in ("packs", "pieces_per_pack", "used"):
            value = item[key]
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{item['id']}: invalid {key}")
        if item["used"] > item["packs"] * item["pieces_per_pack"]:
            raise ValueError("Insufficient purchase quantity")
        price = money(item["pack_price_jpy"])
        if price is None and item["price_kind"] != "quote_pending":
            raise ValueError("Unknown purchase price must be labelled quote_pending")
    shipping = {row["id"]: row for row in bom["shipping"]}
    if len(shipping) != len(bom["shipping"]):
        raise ValueError("Duplicate shipping ID")
    for row in shipping.values():
        money(row["amount_jpy"])
    scenario_ids = set()
    used_items, used_shipping = set(), set()
    for scenario in bom["scenarios"]:
        if scenario["id"] in scenario_ids:
            raise ValueError("Duplicate scenario ID")
        scenario_ids.add(scenario["id"])
        selected = set(scenario["item_ids"])
        if len(selected) != len(scenario["item_ids"]) or not selected <= ids:
            raise ValueError("Unknown or repeated scenario purchase ID")
        if not set(bom["common_item_ids"]) <= selected:
            raise ValueError("Scenario omits a common item")
        if len(selected & {"D01", "D03"}) != 1:
            raise ValueError("Select exactly one motor source")
        if ("D02" in selected) != (scenario["tyre_condition"] == "bare"):
            raise ValueError("Initial tyres omitted or duplicated")
        if scenario["mount_variant"] == "custom":
            if "Q01" not in selected or selected & {"B01", "Q02"}:
                raise ValueError("Custom/stock mounts must be exclusive")
        elif scenario["mount_variant"] == "stock":
            if not {"B01", "Q02"} <= selected or "Q01" in selected:
                raise ValueError("Stock mount requires its adapter quote")
        else:
            raise ValueError("Unknown mount variant")
        ship_ids = scenario["shipping_ids"]
        if len(ship_ids) != len(set(ship_ids)) or not set(ship_ids) <= set(shipping):
            raise ValueError("Unknown or repeated shipping ID")
        used_items |= selected
        used_shipping |= set(ship_ids)
    if used_items != ids or used_shipping != set(shipping):
        raise ValueError("Catalog contains an unallocated cost row")
    if bom["default_scenario"] not in scenario_ids:
        raise ValueError("Missing default scenario")
    money(bom["contingency_fraction"])


def scenario_rows(bom, scenario):
    catalog = {row["id"]: row for row in bom["items"]}
    shipping = {row["id"]: row for row in bom["shipping"]}
    purchases = [dict(id=key, name=catalog[key]["name"],
                      price_kind=catalog[key]["price_kind"],
                      amount_jpy=purchase_amount(catalog[key])) for key in scenario["item_ids"]]
    delivery = [dict(id=key, name=shipping[key]["name"],
                    price_kind=shipping[key]["kind"],
                    amount_jpy=shipping[key]["amount_jpy"]) for key in scenario["shipping_ids"]]
    return purchases, delivery


def calculate_scenario(bom, scenario):
    purchases, delivery = scenario_rows(bom, scenario)
    result = aggregate(purchases + delivery)
    result.update({"id": scenario["id"], "mount_variant": scenario["mount_variant"],
                   "motor_source": scenario["motor_source"], "tyre_condition": scenario["tyre_condition"],
                   "condition_ja": scenario["condition_ja"],
                   "purchase_priced_subtotal_jpy": aggregate(purchases)["priced_and_allowance_subtotal_jpy"],
                   "shipping_priced_subtotal_jpy": aggregate(delivery)["priced_and_allowance_subtotal_jpy"],
                   "active_item_ids": scenario["item_ids"], "active_shipping_ids": scenario["shipping_ids"]})
    total = result["planning_total_jpy"]
    fraction = money(bom["contingency_fraction"])
    result["planning_total_with_contingency_jpy"] = None if total is None else (total * (1 + fraction)).to_integral_value(rounding=ROUND_CEILING)
    residual = bom["fabrication"]["residual_plate_work"]
    all_outsource = aggregate(purchases + delivery + [dict(id=residual["id"], name=residual["name"],
                              amount_jpy=residual["amount_jpy"], price_kind=residual["kind"])])
    other_total = all_outsource["planning_total_jpy"]
    all_outsource["planning_total_with_contingency_jpy"] = None if other_total is None else (other_total * (1 + fraction)).to_integral_value(rounding=ROUND_CEILING)
    result["with_residual_plate_outsourcing"] = all_outsource
    result["note_ja"] = "数値のある参考価格・仮枠の途中小計。必須見積が残る場合、完成額・価格の下限・税込確定額ではない。主条件はブラケット製作のみ外注、残存板は既所有工具で自加工。"
    return result


def compare_with_A3(bom, scenario, current):
    old_bom, old_summary = read_json(A3 / "bom.json"), read_json(A3 / "cost_summary.json")
    old = {row["id"]: row for row in old_bom["items"]}
    new = {row["id"]: row for row in bom["items"] if row["id"] in scenario["item_ids"]}
    groups = [
        ("3030定尺", {"F01", "F02"}, {"F01", "F02"}),
        ("純正接合部・追加溝ナット", {"F03", "F04"}, {"F03", "F04"}),
        ("モーターと初回タイヤ", {"D01"}, set(new) & {"D01", "D02", "D03"}),
        ("USB通信・ケーブル", {"E01", "E02"}, {"E01", "E02"}),
        ("キャスター", {"C01"}, {"C01"}),
        ("駆動取付部", {"P02", "P05", "P06"}, set(new) & {"Q01", "B01", "Q02"}),
        ("共通板素材", {"P01", "P03"}, {"P01", "P03"}),
        ("PLA消費分", {"P04"}, {"P04"}),
        ("一般締結材", {"H01"}, {"H01"}),
        ("ストラップ", {"H02"}, {"H02"}),
    ]
    for catalog, side in ((old, 1), (new, 2)):
        mapped = [key for group in groups for key in group[side]]
        if len(mapped) != len(set(mapped)) or set(mapped) != set(catalog):
            raise ValueError("A3/A4 comparison must cover each selected purchase once")
    rows = []
    for label, old_ids, new_ids in groups:
        before = sum((purchase_amount(old[key]) for key in old_ids), Decimal(0))
        values = [purchase_amount(new[key]) for key in new_ids]
        after = None if any(value is None for value in values) else sum(values, Decimal(0))
        rows.append({"group_ja": label, "A3_ids": sorted(old_ids), "A4_ids": sorted(new_ids),
                     "A3_jpy": before, "A4_jpy": after,
                     "A4_priced_subtotal_jpy": sum((value for value in values if value is not None), Decimal(0)),
                     "difference_jpy": None if after is None else after - before})
    old_total = money(old_summary["self_fabrication_cash_budget_jpy"])
    recomputed = sum((purchase_amount(row) for row in old.values()), Decimal(0)) + sum((money(row["amount_jpy"]) for row in old_bom["shipping"]), Decimal(0))
    if old_total != recomputed:
        raise ValueError("Saved A3 cost is stale")
    current_total = current["planning_total_jpy"]
    return {"source_bom": "../amr04/bom.json", "source_summary": "../amr04/cost_summary.json",
            "A3_self_fabrication_cash_budget_jpy": old_total,
            "A4_planning_total_jpy": current_total,
            "total_difference_jpy": None if current_total is None else current_total - old_total,
            "all_selected_purchase_rows_covered_once": True, "purchase_delta_breakdown": rows,
            "removed_A3_mount_materials_jpy": sum(purchase_amount(old[key]) for key in ("P02", "P05", "P06")),
            "removed_A3_fabrication_allowance_jpy": old_bom["fabrication"]["outsourced_increment_allowance_jpy"],
            "note_ja": "A3固定材2800円と旧加工6000円は撤去。新しい製作/取付板・配送等が未見積の間、途中小計の差を完成台車の節約額と呼ばない。"}


def check_CAD_quantities(bom, require=False):
    paths = [HERE / name for name in ("fasteners.csv", "validation_results.json", "design_parameters.json", "custom_mount_dimensions.json")]
    missing = [path.name for path in paths if not path.exists()]
    if missing:
        if require:
            raise ValueError(f"CAD files not ready: {missing}")
        return {"status": "pending_final_CAD", "missing_sources": missing,
                "note_ja": "設計指定数量を記録した段階。CADとの最終数量照合は未完了。"}
    validation, params = read_json(paths[1]), read_json(paths[2])
    if params["design"] != bom["design"] or params["version"] != bom["version"]:
        raise ValueError("BOM design/version differs from final CAD")
    checks, mount = bom["quantity_checks"], params["mount"]
    dimensions = read_json(paths[3])
    if checks["custom_brackets_count"] != dimensions["quantity"] or checks["custom_bracket_same_part_rotated"] != dimensions["same_part_both_sides"]:
        raise ValueError("Custom quote quantity/handedness differs from CAD")
    if checks["custom_bracket_finished_LWH_mm"] != dimensions["overall_LWH_mm"]:
        raise ValueError("Custom quote envelope is stale")
    for key, param in (("custom_flange_LWH_mm", "flange_LWH_mm"),
                       ("custom_web_LWH_mm", "web_LWH_mm"),
                       ("special_pocket_depth_mm", "motor_pocket_depth_mm"),
                       ("custom_bracket_rear_wall_mm", "motor_rear_wall_mm"),
                       ("custom_bracket_material", "material")):
        if checks[key] != mount[param]:
            raise ValueError(f"Custom quote dimensions/material differ from CAD: {key}")
    expected = {row["specification"]: row for row in bom["quantity_checks"]["fasteners"]}
    actual = {}
    with paths[0].open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            spec = row["specification"]
            if spec in actual:
                raise ValueError("Duplicate CAD fastener specification")
            actual[spec] = {"specification": spec, **{key: int(row[key]) for key in (
                "installed_quantity", "included_in_HBLFSN6_SET", "additional_installed_quantity")}}
            item = actual[spec]
            if item["installed_quantity"] != item["included_in_HBLFSN6_SET"] + item["additional_installed_quantity"]:
                raise ValueError("CAD included/additional fastener mismatch")
            if len(row["model_object_names"].split(";")) != item["installed_quantity"]:
                raise ValueError("CAD fastener object-list mismatch")
    if expected != actual or {key: row["installed_quantity"] for key, row in actual.items()} != validation["hardware_installed"]:
        raise ValueError("BOM/CAD fastener quantity mismatch")
    items = {row["id"]: row for row in bom["items"]}
    nuts = actual["HNTT6-6 slot nut"]
    if items["F04"]["used"] != nuts["additional_installed_quantity"] or items["F03"]["used"] * 2 != nuts["included_in_HBLFSN6_SET"]:
        raise ValueError("Slot-nut purchase allocation mismatch")
    if sum(bom["quantity_checks"]["slot_nuts_by_use"].values()) != nuts["installed_quantity"]:
        raise ValueError("Slot-nut use count mismatch")
    plans, printed = bom["quantity_checks"]["printed_parts_planned_LWH_mm_count"], validation["printed_parts"]
    if len(plans) != len(printed):
        raise ValueError("Printed part count mismatch")
    for plan, part in zip(plans, printed):
        if plan[3] != part["quantity"] or not all(math.isclose(x, y, abs_tol=1e-5) for x, y in zip(plan[:3], part["dimensions_mm"])):
            raise ValueError("Printed dimensions/quantity differ from BOM")
    return {"status": "passed", "sources": [path.name for path in paths],
            "fastener_specifications": len(actual), "slot_nuts_total": nuts["installed_quantity"],
            "general_fasteners_additional_installed": sum(row["additional_installed_quantity"] for key, row in actual.items() if key != "HNTT6-6 slot nut"),
            "printed_parts_count": len(printed),
            "note_ja": "製作主案のCAD数量を照合。購入パック価格・加工性・実部品適合の保証ではない。既製比較案のCAD数量は未確定。"}


def self_test(bom):
    """Check the two important accounting failure modes without extra test files."""
    sample = copy.deepcopy(bom)
    for row in sample["items"]:
        if row["id"] == "Q01":
            row["pack_price_jpy"] = None
        elif row["pack_price_jpy"] is None:
            row["pack_price_jpy"] = 0
    for row in sample["shipping"]:
        if row["amount_jpy"] is None:
            row["amount_jpy"] = 0
    scenarios = {row["id"]: row for row in sample["scenarios"]}
    bare = calculate_scenario(sample, scenarios["custom_taobao_bare"])
    included = calculate_scenario(sample, scenarios["custom_taobao_included"])
    assert bare["planning_total_jpy"] is None
    assert bare["planning_total_with_contingency_jpy"] is None
    assert [row["id"] for row in bare["required_unpriced_entries"]] == ["Q01"]
    assert bare["priced_and_allowance_subtotal_jpy"] - included["priced_and_allowance_subtotal_jpy"] == Decimal(9240)
    return {"unknown_required_quote_keeps_total_null": "passed", "initial_tyre_case_difference_9240_jpy": "passed"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-cad", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    bom = read_json(HERE / "bom.json")
    validate_bom(bom)
    scenarios = {row["id"]: row for row in bom["scenarios"]}
    results = [calculate_scenario(bom, row) for row in bom["scenarios"]]
    default = next(row for row in results if row["id"] == bom["default_scenario"])
    cad = check_CAD_quantities(bom, require=args.require_cad)
    summary = {"version": bom["version"], "design": bom["design"], "checked_on": bom["checked_on"],
               "currency": bom["currency"], "all_amounts_include_tax": bom["all_amounts_include_tax"],
               "amount_basis_note_ja": bom["amount_basis_note_ja"], "scope_ja": bom["scope"],
               "status": "partial_planning_costs_required_quotes_pending" if default["required_unpriced_entries"] else "planning_references_and_allowances_not_purchase_quote",
               "source_bom": "bom.json", "default_scenario": bom["default_scenario"],
               "default_result": default, "scenarios": results,
               "comparison_with_A3": compare_with_A3(bom, scenarios[bom["default_scenario"]], default),
               "contingency_fraction": bom["contingency_fraction"],
               "quantity_checks": bom["quantity_checks"], "CAD_quantity_crosscheck": cad,
               "fabrication": bom["fabrication"], "price_kinds_ja": bom["price_kinds_ja"],
               "initial_purchase_only": True, "lifetime_maintenance_cost_included": False,
               "maintenance": bom["maintenance"],
               "excluded_unpriced_items_ja": bom["excluded_unpriced_items_ja"],
               "procurement_note_ja": bom["procurement_note_ja"], "budget_note_ja": bom["budget_note_ja"]}
    if args.self_test:
        summary["self_tests"] = self_test(bom)
    (HERE / "cost_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False, default=json_number) + "\n", encoding="utf-8")
    catalog = {row["id"]: row for row in bom["items"]}
    with (HERE / "BOM.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["ID", "品名", "購入パック数", "1パック入数", "使用数", "余り", "パック価格円", "購入小計円", "価格区分", "税の扱い", "URL", "注意", "計上単位", "調達状態", "シナリオ"])
        for key in default["active_item_ids"]:
            row = catalog[key]
            amount = purchase_amount(row)
            writer.writerow([key, row["name"], row["packs"], row["pieces_per_pack"], row["used"],
                             row["packs"] * row["pieces_per_pack"] - row["used"],
                             "見積待ち" if row["pack_price_jpy"] is None else row["pack_price_jpy"],
                             "見積待ち" if amount is None else amount, row["price_kind"], row["tax_status"], row["url"],
                             row["note"], row["quantity_unit"], row["procurement_status"], default["id"]])
    print(json.dumps({"default_scenario": default["id"],
                      "priced_and_allowance_subtotal_jpy": default["priced_and_allowance_subtotal_jpy"],
                      "planning_total_jpy": default["planning_total_jpy"],
                      "required_unpriced_entries": default["required_unpriced_entries"],
                      "CAD_quantity_crosscheck": cad, "self_tests": summary.get("self_tests")},
                     ensure_ascii=False, indent=2, default=json_number))


if __name__ == "__main__":
    main()
