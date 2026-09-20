"""Compare purchase and two tire replacement events; this is not a life forecast."""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
ddsm_unit = 12991
ddt_bare_motor = 14410
ddt_tire_kit = 4620

result = {
    "checked_on": "2026-09-20",
    "currency": "JPY",
    "tax_included": True,
    "scope_ja": "左右モーターと初回タイヤ、および左右タイヤを一斉に0/1/2回交換する場合の該当部品代。フレーム、取付、通信、電池、工賃は含まない。寿命が同じ、1年で何回交換、と仮定した比較ではない。",
    "shipping_ja": "各行の左右2輪分を同時購入すれば現行Switch Scienceの8,000円以上通常送料無料条件に達する。特殊配送条件、将来の値上げ、別注文は未反映。",
    "sources": {
        "DDSM115": "https://www.switch-science.com/products/9628",
        "DDT_M0601C_111": "https://www.switch-science.com/products/7646",
        "DDT_M0601C_TIRE": "https://www.switch-science.com/products/9203",
        "shipping": "https://www.switch-science.com/policies/shipping-policy",
    },
    "catalog_inputs": {"ddsm_unit_jpy": ddsm_unit, "ddt_bare_motor_jpy": ddt_bare_motor,
                       "ddt_compatible_tire_kit_jpy": ddt_tire_kit,
                       "ddsm_available": True, "ddt_bare_motor_available": False,
                       "ddt_tire_kit_available": True,
                       "availability_note": "Product page and current Shopify product JSON observed; no inventory reservation."},
    "scenarios": [
        {"name": "DDSM115_unit_replacement_fallback",
         "status_ja": "タイヤ単体の調達ができずユニット全体を交換する仮定。唯一の交換方法だと断定するものではない。",
         "initial_motor_and_tire_pair_jpy": 2 * ddsm_unit,
         "replacement_pair_each_event_jpy": 2 * ddsm_unit,
         "total_after_pair_replacement_events_jpy": {str(n): 2 * ddsm_unit * (1 + n) for n in (0, 1, 2)}},
        {"name": "DDT_M0601C_111_with_explicitly_compatible_tire_kit",
         "status_ja": "タイヤキットは販売元が適合を明示。ただしモーター本体は売切れで即購入案にはできない。取付形状と実輪荷重条件は別確認。",
         "initial_motor_and_tire_pair_jpy": 2 * (ddt_bare_motor + ddt_tire_kit),
         "replacement_pair_each_event_jpy": 2 * ddt_tire_kit,
         "total_after_pair_replacement_events_jpy": {str(n): 2 * (ddt_bare_motor + ddt_tire_kit * (1 + n)) for n in (0, 1, 2)}},
        {"name": "DDSM115_tire_only_replacement",
         "status_ja": "脱着可能だが適合新品の販売SKU/価格未確認。DDTキットとの互換性を推測して金額を入れない。",
         "initial_motor_and_tire_pair_jpy": 2 * ddsm_unit,
         "replacement_pair_each_event_jpy": None,
         "total_after_pair_replacement_events_jpy": {"0": 2 * ddsm_unit, "1": None, "2": None}},
    ],
    "selection_ja": "消耗するゴム部分だけを交換でき、個人で適合補修品を調達できることを優先要件に追加。DDSM115 CADは比較案として保存し、補修部品確認前に購入仕様を確定しない。",
}

if __name__ == "__main__":
    (HERE / "maintenance_costs.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    for scenario in result["scenarios"]:
        print(scenario["name"], scenario["total_after_pair_replacement_events_jpy"])
