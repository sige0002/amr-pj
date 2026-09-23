"""D6.9 purchase-pack BOM; reuse the actual recorded quote for identical D3 plate."""
from pathlib import Path
import csv, json, hashlib, math

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
source = BASE / 'direct-hinge'
reader = csv.DictReader((source / 'BOM.csv').open(encoding='utf-8-sig'))
fields = reader.fieldnames
removed_ids = ['HATCH_HINGES', 'HATCH_METAL_ANGLES', 'HATCH_FRAME_M4_NUT',
               'HATCH_FRAME_M4_BOLT', 'HATCH_LOCKS', 'ELEC_CASE_WASHER']
old_rows = list(reader)
rows = [r for r in old_rows if r['ID'] not in removed_ids]
by = {r['ID']: r for r in rows}
v = json.loads((HERE / 'validation.json').read_text())
observed_path = BASE / 'aluminum-direct-deck/quote-evidence/D3-observed.json'
q = json.loads(observed_path.read_text())
economic = next(x for x in q['records'] if x['speed'] == 'economic')


def quantity(id, use, **kw):
    row = by[id]
    row.update(使用数=str(use), 余剰数=str(int(row['購入予定数'])-use), CAD形状数=str(use), **kw)


quantity('F04', 70, 備考='天板6点固定のHNTT6-6を含む共通70個。購入100個の内数。新規パック追加なし。')
quantity('D3_M6', 50, 備考='天板M6×12を6本復帰。共通使用50本／購入70本。H01別枠4本は従来どおり別予算で二重配分しない。')
quantity('D62_FLOOR_SCREWS', 20, 部品名='床・ケース用M4×16', 備考='床継ぎ目4＋ケース底8＋ケース蓋8＝20本。購入60本の内数。')
quantity('D3_STOP_NUTS', 28, 備考='荷物止め8＋床4＋ケース底8＋蓋8＝28個。20個273円×2。')
quantity('D64_FLOOR_WASHERS', 24, 部品名='床・ケース用M4 OD12×t1座金', 備考='床上下8＋ケース底8＋ケース蓋8＝24枚。20枚430円×2。')
grams = math.ceil(v['mass']['total_solid_PLA_kg']*1000)
by['P04'].update(使用数=str(grams), 明細金額=str(2*grams), CAD形状数='14',
                部品名='床・PCカバー・荷物止め・操作ケース',
                **{'仕様・型番': 'D6.9全14個、D6.8から形状変更なし。床4、支持梁1、PCカバー1、荷物止め4、操作ケースと蓋4'},
                備考='2円/g、中実CADの材料消費参考。非導電PLA。スライス支持材・失敗・電気・工賃別。')
by['DECK_plate'].update(部品名='固定式格子穴アルミ天板',
                       **{'仕様・型番': '300×300×4 / 6061-T6 / AMR_GridDeck_C45_D3 / qty1'},
                       明細金額=f"{economic['parts_lot_USD']:.2f}", CAD形状数='1',
                       価格根拠='2026-09-21 UTC取得のJLCCNC実自動見積を同一形状へ再使用（今回の再取得なし）',
                       備考='材料、50丸穴（格子36＋M6固定6＋荷物止め8）、4長穴込み。タップ・ヒンジ穴なし。D3見積STEPと今回の組立形状を照合。数量1枚全額、手動審査前。')
by['DECK_CNC_SHIP'].update(部品名='アルミ天板1枚の日本宛送料',
                          **{'仕様・型番': q['shipping_service']}, 明細金額=f"{economic['shipping_USD']:.2f}",
                          価格根拠='2026-09-21 UTC取得のD3天板単独配送表示を再使用',
                          備考='天板1枚の日本・国単位表示。住所別未検証。モーター金具は別配送。税・決済費用別、今回の送料再取得なし。')
with (HERE / 'BOM.csv').open('w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fields, lineterminator='\n')
    writer.writeheader(); writer.writerows(rows)
old = json.loads((source / 'cost_summary.json').read_text())
rate = old['FX_reference_JPY_per_USD']
subtotal = {c: sum(float(r['明細金額']) for r in rows if r['通貨'] == c and r['明細金額']) for c in ['JPY', 'USD']}
total = subtotal['JPY'] + subtotal['USD']*rate
quote = dict(source='../aluminum-direct-deck/quote-evidence/D3-observed.json',
             source_sha256=hashlib.sha256(observed_path.read_bytes()).hexdigest(),
             original_observed_at=q['observed_at'], re_queried_this_revision=False,
             plate_lot_USD=economic['parts_lot_USD'], shipping_USD=economic['shipping_USD'],
             total_USD=economic['total_USD'], quantity=1, step_sha256=q['step_sha256'], pdf_sha256=q['pdf_sha256'],
             geometry_equivalence_check='saved_artifact_validation.json', automatic_not_manual=True,
             manual_review_complete=False, order_placed=False)
summary = dict(revision='D6.9', date='2026-09-23', subtotal=subtotal,
               FX_reference_JPY_per_USD=rate, FX_date=old['FX_date'],
               FX_basis='Recorded 2026-09-21 reference, not current settlement rate',
               full_running_subtotal_JPY_reference=total,
               difference_from_D68_JPY_reference=total-old['full_running_subtotal_JPY_reference'],
               removed_purchase_ids=removed_ids, machining_quote=quote,
               unpriced_rows=[r['ID'] for r in rows if not r['明細金額']], complete_purchase_total=False,
               note='途中小計。PC・基板・配線・税等未計上。モーター価格は仮予算。Prime最終カート未確認。購入パック全額、余剰を按分しない。')
(HERE / 'cost_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
print(json.dumps(dict(subtotal=subtotal, total_JPY_reference=total,
                      difference_from_D68=summary['difference_from_D68_JPY_reference'])))
