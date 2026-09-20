"""Build a readable BOM and comparable totals from pack costs, not used fraction."""
from pathlib import Path
import csv
import json
import math

HERE = Path(__file__).resolve().parent


def calculate(bom):
    ids = set()
    sums = {'observed': 0, 'allowance': 0}
    for item in bom['items']:
        assert item['id'] not in ids, 'Duplicate BOM id'
        ids.add(item['id'])
        assert 0 < item['used'] <= item['packs'] * item['pieces_per_pack'], item['id']
        assert item['packs'] > 0 and item['pack_price_jpy'] >= 0
        sums[item['price_kind']] += item['packs'] * item['pack_price_jpy']
    shipping = sum(i['amount_jpy'] for i in bom['shipping'])
    diy = sums['observed'] + sums['allowance'] + shipping
    outsourced = diy + bom['fabrication']['outsourced_increment_allowance_jpy']
    return {
        'observed_purchase_subtotal_jpy': sums['observed'],
        'materials_and_additional_hardware_allowance_jpy': sums['allowance'],
        'shipping_budget_jpy': shipping,
        'self_fabrication_cash_budget_jpy': diy,
        'outsourced_fabrication_cash_budget_jpy': outsourced,
        'self_fabrication_with_10pct_contingency_jpy': math.ceil(diy * (1 + bom['contingency_fraction'])),
        'outsourced_with_10pct_contingency_jpy': math.ceil(outsourced * (1 + bom['contingency_fraction'])),
        'note_ja': bom['scope'] + ' 合計は見積枠を含む試算で、支払確定額ではない。'
    }


if __name__ == '__main__':
    bom = json.loads((HERE / 'bom.json').read_text())
    result = calculate(bom)
    (HERE / 'cost_summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    with (HERE / 'BOM.csv').open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['ID', '品名', '購入パック数', '1パック入数', '使用数', '余り', '税込パック単価', '購入小計', '価格区分', 'URL', '注意'])
        for i in bom['items']:
            w.writerow([i['id'], i['name'], i['packs'], i['pieces_per_pack'], i['used'], i['packs']*i['pieces_per_pack']-i['used'], i['pack_price_jpy'], i['pack_price_jpy']*i['packs'], i['price_kind'], i['url'], i['note']])
    print(json.dumps(result, ensure_ascii=False, indent=2))
