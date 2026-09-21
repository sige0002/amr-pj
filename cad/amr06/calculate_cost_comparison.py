"""Compare actual quote variants against A4 without replacing its adopted BOM."""
from pathlib import Path
from decimal import Decimal
import copy
import csv
import hashlib
import importlib.util
import json

HERE = Path(__file__).resolve().parent
A4 = HERE.parent / 'amr05'
spec = importlib.util.spec_from_file_location('a4_cost_reference', A4 / 'calculate_cost.py')
cost = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cost)


def main():
    original = json.loads((A4 / 'bom.json').read_text())
    quotes = json.loads((HERE / 'machining_quotes.json').read_text())
    original_bytes = (A4 / 'bom.json').read_bytes()
    scenario = next(s for s in original['scenarios'] if s['id'] == original['default_scenario'])
    baseline = cost.calculate_scenario(original, scenario)
    rows = [{'candidate': 'A4', 'parts_lot_USD': Decimal('74.50'), 'shipping_USD': Decimal('7.23'),
             'displayed_sum_USD': Decimal('81.73'), 'difference_from_A4_USD': Decimal(0),
             'budget': baseline}]
    for quote in quotes['variants']:
        offer = next(o for o in quote['offers'] if o['speed'] == 'economic')
        parts, freight = Decimal(str(offer['parts_lot_USD'])), Decimal(str(offer['shipping_USD']))
        alternative = copy.deepcopy(original)
        bracket = next(i for i in alternative['items'] if i['id'] == 'Q01')
        shipping = next(i for i in alternative['shipping'] if i['id'] == 'S08')
        assert bracket['packs'] == 1 and bracket['pieces_per_pack'] == 2 and bracket['used'] == 2
        bracket['pack_price_foreign']['amount'] = parts
        shipping['amount_foreign']['amount'] = freight
        cost.validate_bom(alternative)
        result = cost.calculate_scenario(alternative, scenario)
        # Validate quantity scaling and currency separation against the two
        # independently observed UI amounts, not a guessed exchange rate.
        assert result['unconverted_quoted_subtotals_by_currency']['USD'] == parts + freight
        assert result['planning_total_jpy'] is None
        assert result['priced_and_allowance_subtotal_jpy'] == baseline['priced_and_allowance_subtotal_jpy']
        assert result['required_unpriced_entries'] == baseline['required_unpriced_entries']
        rows.append({'candidate': quote['candidate'], 'parts_lot_USD': parts,
                     'shipping_USD': freight, 'displayed_sum_USD': parts + freight,
                     'difference_from_A4_USD': parts + freight - Decimal('81.73'),
                     'budget': result})
    assert (A4 / 'bom.json').read_bytes() == original_bytes
    summary = {
        'scope': 'Comparison only. A4 BOM remains the price reference; D5 CAD/mock is not adopted as a lower-cost production mount.',
        'source_A4_BOM': '../amr05/bom.json', 'source_A4_BOM_sha256': hashlib.sha256(original_bytes).hexdigest(),
        'source_quotes': 'machining_quotes.json', 'lowest_observed_candidate': 'A4',
        'cost_reduction_achieved': False,
        'manufacturing_days': 10, 'shipping_country': 'Japan', 'shipping_method': 'OCS Express',
        'conditions': 'Two identical parts, 6061-T6, no finish, seat flats +/-0.05 mm only, other ISO2768-m; automatic quote, not manual approval.',
        'rows': rows,
        'extra_costs_not_zero': ['tax/import/payment/address-specific changes', 'Taobao charges',
                                 'new payload deck and its attachments', 'unsliced PLA fit mocks',
                                 'unselected battery/computer/electrical items'],
        'checks': {'two_part_lot_and_shipping_counted_once': True,
                   'currency_kept_separate': True, 'missing_costs_remain_unknown': True,
                   'A4_BOM_unchanged': True},
    }
    (HERE/'cost_comparison.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=cost.json_number)+'\n')
    with (HERE/'BOM_cost_comparison.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.writer(f)
        writer.writerow(['案','金具2個一式USD','日本宛OCS送料USD','表示金額の和USD','A4との差USD','共通の円小計','円総額','状態'])
        for row in rows:
            writer.writerow([row['candidate'],row['parts_lot_USD'],row['shipping_USD'],row['displayed_sum_USD'],
                             row['difference_from_A4_USD'],row['budget']['priced_and_allowance_subtotal_jpy'],
                             '未確定','サイト自動見積・製作未承認'])
    print(json.dumps({r['candidate']:float(r['displayed_sum_USD']) for r in rows},ensure_ascii=False))


if __name__ == '__main__':
    main()
