"""Package observed website quotes and their CAD/evidence fingerprints.

This records UI observations; it does not estimate prices, submit orders or
claim manual supplier review. Browser state and contact data are not included.
"""
from pathlib import Path
from decimal import Decimal
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent


def fingerprint(path):
    return {'path': path.relative_to(HERE).as_posix(),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    records = []
    for observed_path in sorted((HERE / 'quote-evidence').glob('D*-observed.json')):
        observed = json.loads(observed_path.read_text())
        stem, tag = observed['name'], observed['candidate']
        assert observed['quantity'] == 2 and observed['currency'] == 'USD'
        step = HERE / 'candidates' / (stem + '.step')
        drawing = step.with_suffix('.pdf')
        geometry = json.loads(step.with_suffix('.json').read_text())
        assert fingerprint(step)['sha256'] == geometry['step_sha256']
        evidence = []
        prices = []
        for offer in observed['records']:
            basename = tag + '-' + offer['speed']
            transcript = HERE / 'quote-evidence' / (basename + '.txt')
            text = transcript.read_text()
            part_match = re.search(r'合計価格\s*\$([\d,.]+)', text)
            shipping_match = re.search(r'送料見積\s*\$([\d,.]+)\s*OCS Express', text)
            volume_match = re.search(r'体積: ([\d,.]+) mm³', text)
            assert part_match and shipping_match and volume_match
            parts = Decimal(part_match[1].replace(',', ''))
            freight = Decimal(shipping_match[1].replace(',', ''))
            assert parts == Decimal(str(offer['parts_lot_USD']))
            assert freight == Decimal(str(offer['shipping_USD']))
            assert abs(float(volume_match[1].replace(',', '')) - geometry['volume_mm3_each']) < .01
            assert 'Aluminum 6061' in text and '±0.05mm' in text
            prices.append({**offer, 'displayed_parts_plus_shipping_USD': float(parts + freight)})
            evidence.extend([fingerprint(transcript), fingerprint(transcript.with_suffix('.png'))])
        shipping_text = (HERE / 'quote-evidence' / (tag + '-shipping.txt')).read_text()
        assert 'Japan' in shipping_text and 'OCS Express' in shipping_text
        for suffix in ('settings.png', 'settings-notes.png', 'settings.txt', 'shipping.png', 'shipping.txt'):
            evidence.append(fingerprint(HERE / 'quote-evidence' / (tag + '-' + suffix)))
        records.append({
            'candidate': tag, 'observed_at': observed['observed_at'],
            'uploaded_STEP_filename': step.name, 'uploaded_drawing_filename': drawing.name,
            'files': [fingerprint(step), fingerprint(drawing)],
            'CAD_dimensions_xyz_mm': geometry['overall_LWH_mm'],
            'CAD_volume_mm3': geometry['volume_mm3_each'],
            'CAD_mass_each_kg_at_2700kg_m3': geometry['mass_kg_each_estimate'],
            'drawing_revision': geometry['drawing_revision'],
            'website_remarks': observed['remarks'], 'offers': prices, 'evidence': evidence,
        })
    assert {r['candidate'] for r in records} == {'D1','D2','D3','D4','D5'}
    result = {
        'vendor': 'JLCCNC', 'url': 'https://jlccnc.com/jp/cnc-machining-quote',
        'stage': 'observed_website_automatic_quotes_not_manual_confirmations',
        'vendor_formal_quote_number': None, 'orders_submitted': False, 'payments_made': False,
        'conditions': {
            'quantity': 2, 'two_identical_parts': True, 'currency': 'USD',
            'material_UI': 'Aluminum 6061', 'material_tooltip_temper': 'T6',
            'surface_finish': False, 'appearance': 'Standard', 'threads': False, 'subassembly': False,
            'tightest_tolerance_mm': .05,
            'tolerance_scope': 'Seat flat distance 8.25 +/-0.05 only. Other dimensions ISO 2768-m for quotation; final functional tolerance design pending.',
            'matching_PDF_attached_for_each_variant': True,
            'manufacturing_release': False, 'discounts_applied': False,
            'country': 'Japan', 'shipping_method': 'OCS Express',
            'shipping_transit_business_days': [4,6],
            'shipping_basis': 'country_only_before_checkout',
            'postal_code_field_available': False, 'postal_code_entered': False,
            'address_surcharges_taxes_import_fees_and_payment_conversion': 'unconfirmed',
            'JPY_conversion_rate': None,
        },
        'baseline_A4': {
            'original_record': '../amr05/machining_quote.json',
            'parts_lot_economic_USD': 74.50, 'shipping_USD': 7.23, 'displayed_sum_USD': 81.73,
            'same_session_recheck': [fingerprint(HERE/'quote-evidence'/'A4-control-economic.txt'),
                                     fingerprint(HERE/'quote-evidence'/'A4-control-economic.png')],
        },
        'variants': records,
        'interpretation': 'Observed differences are automatic website quotations for the submitted geometry. No toolpath, cutter count, setup count or final manufacturing price was confirmed by a machinist.',
        'manual_review_policy': 'https://jlccnc.com/help/article/cnc-machining-ordering-guidelines',
    }
    (HERE / 'machining_quotes.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({r['candidate']:r['offers'] for r in records},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
