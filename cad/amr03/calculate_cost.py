"""Generate this variant's BOM CSV and cost comparison from purchase quantities.

Run: python3 cad/amr03/calculate_cost.py
No price lookup or purchasing is performed. Unquoted allowances remain allowances.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent


def calculate(bom):
    ids = set()
    subtotals = {}
    for item in bom["items"]:
        if item["id"] in ids:
            raise ValueError(f"Duplicate BOM id: {item['id']}")
        ids.add(item["id"])
        for key in ("packs", "pieces_per_pack", "used"):
            value = item[key]
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{item['id']}: {key} must be a positive integer")
        if item["used"] > item["packs"] * item["pieces_per_pack"]:
            raise ValueError(f"{item['id']}: purchased quantity is insufficient")
        price = item["pack_price_jpy"]
        if isinstance(price, bool) or not math.isfinite(price) or price < 0:
            raise ValueError(f"{item['id']}: invalid price")
        kind = item["price_kind"]
        subtotals[kind] = subtotals.get(kind, 0) + item["packs"] * price
    shipping = sum(entry["amount_jpy"] for entry in bom["shipping"])
    fabrication = bom["fabrication"]["outsourced_increment_allowance_jpy"]
    contingency = bom["contingency_fraction"]
    if any(not math.isfinite(value) or value < 0
           for value in [*(entry["amount_jpy"] for entry in bom["shipping"]),
                         fabrication, contingency]):
        raise ValueError("Shipping, fabrication and contingency must be nonnegative")
    parts = sum(subtotals.values())
    diy = parts + shipping
    outsourced = diy + fabrication
    return {
        "purchase_subtotals_by_price_kind_jpy": subtotals,
        "parts_and_consumables_subtotal_jpy": parts,
        "shipping_budget_jpy": shipping,
        "self_fabrication_cash_budget_jpy": diy,
        "outsourced_fabrication_cash_budget_jpy": outsourced,
        "contingency_fraction": contingency,
        "self_fabrication_with_10pct_contingency_jpy": math.ceil(diy * (1 + contingency)),
        "outsourced_with_10pct_contingency_jpy": math.ceil(outsourced * (1 + contingency)),
    }


def compare_with_first(bom, first_bom, current, first):
    def amount(data, ids):
        return sum(item["packs"] * item["pack_price_jpy"]
                   for item in data["items"] if item["id"] in ids)

    groups = [
        ("3030定尺", {"F01", "F02"}, {"F01", "F02"}),
        ("接合金具・溝ナット", {"F03"}, {"F03", "F04"}),
        ("駆動系", {f"D{i:02d}" for i in range(1, 8)}, {f"D{i:02d}" for i in range(1, 8)}),
        ("キャスター", {"C01"}, {"C01"}),
        ("金属素材", {"P01", "P02", "P03", "P04", "P05"}, {"P01", "P02", "P03"}),
        ("既所有PLAの消費分", set(), {"P04"}),
        ("追加一般締結材", {"H01"}, {"H01"}),
        ("電池固定ストラップ", set(), {"H02"}),
    ]
    rows = []
    for label, old_ids, new_ids in groups:
        old, new = amount(first_bom, old_ids), amount(bom, new_ids)
        rows.append({"group_ja": label, "first_A_jpy": old,
                     "revised_A_jpy": new, "difference_jpy": new - old})
    old, new = first["shipping_budget_jpy"], current["shipping_budget_jpy"]
    rows.append({"group_ja": "部材配送", "first_A_jpy": old,
                 "revised_A_jpy": new, "difference_jpy": new - old})
    delta = current["self_fabrication_cash_budget_jpy"] - first["self_fabrication_cash_budget_jpy"]
    if not math.isclose(sum(row["difference_jpy"] for row in rows), delta):
        raise ValueError("The cost comparison omits a BOM item")
    return {
        "source_bom": "../amr01/bom.json",
        "source_summary": "../amr01/cost_summary.json",
        "first_self_fabrication_jpy": first["self_fabrication_cash_budget_jpy"],
        "first_outsourced_jpy": first["outsourced_fabrication_cash_budget_jpy"],
        "self_difference_jpy": delta,
        "outsourced_difference_jpy": current["outsourced_fabrication_cash_budget_jpy"] - first["outsourced_fabrication_cash_budget_jpy"],
        "delta_breakdown": rows,
        "note_ja": "両案とも未見積の素材・締結材・加工・送料を含む機械骨格予算。スペーサー撤去だけで大幅に安くなるとはしない。第一案も改良案も候補部品の新規購入単位全体を計上する。改良案のPLAだけは既所有材の消費分。ユーザー指定の絶対予算はない。",
    }


def main():
    bom = json.loads((HERE / "bom.json").read_text(encoding="utf-8"))
    first_bom = json.loads((HERE.parent / "amr01/bom.json").read_text(encoding="utf-8"))
    first_saved = json.loads((HERE.parent / "amr01/cost_summary.json").read_text(encoding="utf-8"))
    result, first = calculate(bom), calculate(first_bom)
    for key in ("self_fabrication_cash_budget_jpy", "outsourced_fabrication_cash_budget_jpy"):
        if first[key] != first_saved[key]:
            raise ValueError(f"First-design saved total is stale: {key}")
    result = {
        "version": bom["version"], "design": bom["design"],
        "checked_on": bom["checked_on"], "currency": bom["currency"],
        "all_amounts_include_tax": bom["all_amounts_include_tax"],
        "status": "planning_budget_with_unquoted_items_not_purchase_quote",
        "source_bom": "bom.json", "scope_ja": bom["scope"],
        "price_kinds_ja": bom["price_kinds_ja"], **result,
        "fabrication": bom["fabrication"], "shipping": bom["shipping"],
        "quantity_checks": bom["quantity_checks"],
        "comparison_with_A": compare_with_first(bom, first_bom, result, first),
        "budget_note_ja": bom["budget_note_ja"],
    }
    (HERE / "cost_summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    with (HERE / "BOM.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["ID", "品名", "購入パック数", "1パック入数", "使用数", "余り",
                         "税込パック単価", "購入小計", "価格区分", "URL", "注意", "計上単位", "調達状態"])
        for item in bom["items"]:
            writer.writerow([item["id"], item["name"], item["packs"], item["pieces_per_pack"],
                             item["used"], item["packs"] * item["pieces_per_pack"] - item["used"],
                             item["pack_price_jpy"], item["packs"] * item["pack_price_jpy"],
                             item["price_kind"], item["url"], item["note"], item["quantity_unit"], item["procurement_status"]])
    print(json.dumps({key: value for key, value in result.items()
                      if key in ("parts_and_consumables_subtotal_jpy", "shipping_budget_jpy",
                                 "self_fabrication_cash_budget_jpy", "outsourced_fabrication_cash_budget_jpy",
                                 "self_fabrication_with_10pct_contingency_jpy", "outsourced_with_10pct_contingency_jpy")},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
