"""Record observed CNC quote facts and hashes; no network or ordering actions."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path


def amount(text):
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise argparse.ArgumentTypeError("Use a numeric amount without currency symbols") from exc
    if not value.is_finite() or value < 0:
        raise argparse.ArgumentTypeError("Amount must be finite and non-negative")
    return value


def positive_int(text):
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError("Quantity must be positive")
    return value


def fingerprint(path, output_dir):
    path = path.resolve(strict=True)
    if not path.is_file():
        raise ValueError(f"Not a file: {path.name}")
    try:
        name = path.relative_to(output_dir).as_posix()
    except ValueError:
        name = path.name
    return {"file": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "size_bytes": path.stat().st_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cad', type=Path, required=True)
    parser.add_argument('--drawing', type=Path, action='append', default=[])
    parser.add_argument('--evidence', type=Path, action='append', required=True,
                        help='Actual quote screenshot or vendor response; repeat for multiple files')
    parser.add_argument('--supplier', required=True)
    parser.add_argument('--url', required=True)
    parser.add_argument('--quantity', type=positive_int, required=True)
    parser.add_argument('--material', required=True)
    parser.add_argument('--finish', required=True)
    parser.add_argument('--tolerance-note', required=True)
    parser.add_argument('--currency', required=True)
    parser.add_argument('--parts-lot-price', type=amount, required=True,
                        help='Vendor amount for the ENTIRE stated quantity; never multiplied by quantity')
    delivery = parser.add_mutually_exclusive_group()
    delivery.add_argument('--shipping-price', type=amount)
    delivery.add_argument('--shipping-included', action='store_true',
                          help='Use only when vendor explicitly includes shipping in parts-lot-price')
    parser.add_argument('--shipping-method')
    parser.add_argument('--shipping-country')
    parser.add_argument('--shipping-basis', choices=['country_only','address_specific','unknown'], default='unknown')
    parser.add_argument('--lead-time', help='Vendor text; keep manufacturing and transit periods distinct')
    parser.add_argument('--status', choices=['automatic','manual_preliminary','manual_confirmed'], required=True)
    parser.add_argument('--vendor-quote-id', help='Actual supplier reference only; omit if none issued')
    parser.add_argument('--observed-at', help='ISO 8601 timestamp with timezone; defaults to recording time')
    parser.add_argument('--tax-status', default='unconfirmed')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Z]{3}', args.currency):
        parser.error('currency must be a three-letter uppercase currency code')
    if not args.url.startswith(('https://','http://')):
        parser.error('url must be the actual supplier web page')
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    observed = args.observed_at or now
    try:
        if datetime.fromisoformat(observed.replace('Z','+00:00')).utcoffset() is None:
            raise ValueError('timezone required')
    except ValueError:
        parser.error('observed-at must be an ISO 8601 timestamp including timezone')
    directory = args.output.resolve().parent
    if any(args.output.resolve() == source.resolve() for source in [args.cad, *args.drawing, *args.evidence]):
        parser.error('output must not overwrite an input artifact')
    shipping = Decimal(0) if args.shipping_included else args.shipping_price
    total = None if shipping is None else args.parts_lot_price + shipping
    record = {
        'recorded_at':now, 'observed_at':observed, 'supplier':args.supplier, 'url':args.url,
        'quote_status':args.status, 'vendor_quote_id':args.vendor_quote_id,
        'cad':fingerprint(args.cad,directory),
        'drawings':[fingerprint(p,directory) for p in args.drawing],
        'conditions':{'quantity':args.quantity,'material':args.material,'finish':args.finish,
                      'tolerance_note':args.tolerance_note,'lead_time':args.lead_time},
        'currency':args.currency,'parts_lot_price':str(args.parts_lot_price),
        'additional_shipping_price':None if shipping is None else str(shipping),
        'shipping_included_in_parts_lot':args.shipping_included,
        'sum_of_displayed_parts_and_shipping':None if total is None else str(total),
        'shipping':{'method':args.shipping_method,'country':args.shipping_country,'basis':args.shipping_basis},
        'tax_status':args.tax_status, 'currency_conversion':None,
        'total_scope':'Sum of supplied price lines only; tax, import, address and payment fees may remain unconfirmed.',
        'evidence':[fingerprint(p,directory) for p in args.evidence],
    }
    directory.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'output':args.output.name,'currency':args.currency,
                      'quantity':args.quantity,'sum_of_displayed_parts_and_shipping':record['sum_of_displayed_parts_and_shipping']},ensure_ascii=False))


if __name__ == '__main__':
    main()
