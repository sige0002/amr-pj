#!/usr/bin/env python3
"""Reconcile actual quote evidence and incremental parts without currency mixing."""
from pathlib import Path
from decimal import Decimal
import csv
import hashlib
import json
import re

HERE=Path(__file__).resolve().parent


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    old=json.loads((HERE.parent/'amr05'/'bom.json').read_text())
    previous=json.loads((HERE.parent/'amr05'/'cost_summary.json').read_text())['default_result']
    deck=json.loads((HERE/'deck_parameters.json').read_text())['procurement']
    electrical=json.loads((HERE/'electrical_plan.json').read_text())
    raw=json.loads((HERE/'quote-evidence'/'A6-R1-observed.json').read_text())
    drawing=json.loads((HERE/'M0601C_mount_A6_R1_drawing.json').read_text())
    model=json.loads((HERE/'M0601C_mount_A6_R1.json').read_text())
    assert sha(HERE/'M0601C_mount_A6_R1.step')==drawing['step_sha256']==model['step_sha256']
    assert sha(HERE/'M0601C_mount_A6_R1.pdf')==drawing['pdf_sha256']
    quote=dict(raw,step_sha256=drawing['step_sha256'],pdf_sha256=drawing['pdf_sha256'],
               material='A6061-T6',finish='none',threads=False,shipping_country='Japan',
               shipping_service='OCS Express',highest_tolerance_UI='±0.05mm',
               functional_tolerance_scope='A6-R1 two-sheet PDF, not the old A4 flat-only tolerance',
               final_manual_review=False,ordered=False,paid=False)
    for record in quote['records']:
        contents=(HERE/'quote-evidence'/('A6-R1-'+record['speed']+'.txt')).read_text()
        price=re.search(r'合計価格\s*\$([0-9,.]+)',contents)
        shipping=re.search(r'送料見積\s*\$([0-9,.]+)\s*OCS Express',contents)
        assert float(price[1].replace(',',''))==record['parts_lot_USD']
        assert float(shipping[1].replace(',',''))==record['shipping_USD']
        assert f"{model['volume_mm3_each']:.2f} mm³" in contents
        record['displayed_total_USD']=float(Decimal(str(record['parts_lot_USD']))+Decimal(str(record['shipping_USD'])))
    settings=(HERE/'quote-evidence'/'A6-R1-settings.txt').read_text()
    assert 'M0601C_mount_A6_R1.pdf' in settings
    assert len(quote['remarks'])<=500 and quote['quantity']==2
    quote['evidence_hashes']={p.name:sha(p) for p in sorted((HERE/'quote-evidence').iterdir()) if p.is_file()}
    (HERE/'machining_quote.json').write_text(json.dumps(quote,ensure_ascii=False,indent=2)+'\n')
    economic=next(x for x in quote['records'] if x['speed']=='economic')
    rows=[]
    def row(id,name,quantity,amount,kind,url='',note='',currency='JPY'):
        rows.append(dict(id=id,name=name,quantity=quantity,currency=currency,amount=amount,price_kind=kind,source=url,note=note))
    for item in old['items']:
        if item['id'] not in previous['active_item_ids'] or item['id'] in ('E01','Q01'): continue
        row(item['id'],item['name'],item['used'],item['pack_price_jpy']*item['packs'],item['price_kind'],item.get('url',''),item.get('note',''))
        if item['id']=='E02':
            rows[-1].update(name='主計算機／外部PCとPico Hを接続するUSBデータケーブル予算',
                            note='Pico H側はmicro-B。ホスト側端子と長さを確定してデータ通信対応品を選ぶ。旧USB-RS485Bは搭載しない。500円は仮枠。')
        elif item['id']=='F04':
            rows[-1]['note']='A6全50個のうち接合SET付属16個、基礎部の別購入28個、荷台用6個。ここは28個分の1200円仮枠。荷台6個はDECK_fasteners_and_extra_slotnutsに含み、重複加算しない。販売単位・個人購入経路は未確定。'
        elif item['id']=='H01':
            rows[-1]['note']='基礎部の別購入：M2.5×12を6本、M6×10を8本、M6×12を20本、M6×16を4本、M6六角ナット4個、M6平座金OD13×12枚、大径OD18×12枚。SET付属M6×12の16本、溝ナット、MW座金、荷台締結材、タイヤ付属ねじを重複計上しない。購入パック未確定。'
    for item in old['shipping']:
        if item['id'] not in previous['active_shipping_ids'] or item['id'] in ('S05','S08'): continue
        row(item['id'],item['name'],1,item['amount_jpy'],item['kind'],item.get('url',''),item.get('note',''))
    assert round(sum(x['amount'] or 0 for x in rows))==previous['priced_and_allowance_subtotal_jpy']-4400-660
    for key in ('plate','square_bar','cargo_straps'):
        p=deck[key]
        row('DECK_'+key,p['item'],p['quantity'],p['unit_jpy_incl_tax']*p['quantity'],'observed_2026_09_21',p['url'],p['basis'])
    row('DECK_SHIP','荷台材料の表示送料参考',1,deck['reference_shipping_subtotal_jpy'],'displayed_regional_reference',note='地域・同梱条件は注文時確定')
    for key in ('fasteners_and_extra_slotnuts','edge_protection_and_slack_retention'):
        p=deck[key]; row('DECK_'+key,key,1,p['planning_allowance_jpy'],'allowance',note=p['basis'])
    washer_purchase=Decimal('29')*10*Decimal('1.10')
    row('MW','WILCO FW-2505-05EB 2.7x5x0.5',6,float(washer_purchase),'observed_quantity_break_tax_added','https://wilco.jp/products/F/FW-EB.html','10個購入予定・6個使用。29円/個は10個以上の税別単価：290円＋消費税29円＝319円。1個から購入可だが数量割引を選択。未発注、送料別。H01と別計上。')
    for p in electrical['candidate_parts']:
        row('ELEC_'+p['id'],p['part_number'],p['used_quantity'],p['purchase_price_jpy_incl_tax'],'observed_candidate_2026_09_21',p['source'],p['note'])
    row('Q01','A6-R1専用金具、同形2個',2,economic['parts_lot_USD'],'vendor_automatic_quote','https://jlccnc.com/jp/cnc-machining-quote','STEP/PDF一致、手動審査前',currency='USD')
    row('S08','日本宛OCS Express表示送料',1,economic['shipping_USD'],'vendor_automatic_quote','https://jlccnc.com/jp/cnc-machining-quote','国単位。住所別・税・換算額未確認',currency='USD')
    subtotal=sum(Decimal(str(r['amount'])) for r in rows if r['currency']=='JPY' and r['amount'] is not None)
    expected=Decimal(str(previous['priced_and_allowance_subtotal_jpy']))-5060+Decimal(str(deck['self_work_budget_before_contingency_jpy']))+Decimal(str(electrical['cost']['priced_purchase_subtotal_jpy_incl_tax']))+washer_purchase
    assert subtotal==expected
    result={'design':'AMR01_M0601C_A6','date':'2026-09-21','items':rows,
        'priced_and_allowance_subtotal_JPY':float(subtotal),
        'observed_automatic_quote_subtotal_USD':economic['displayed_total_USD'],
        'planning_total_JPY':None,'ordered':False,
        'previous_partial_subtotal_JPY':previous['priced_and_allowance_subtotal_jpy'],
        'removed_old_USB_RS485B_and_its_shipping_JPY':5060,
        'deck_material_shipping_allowance_addition_JPY':deck['self_work_budget_before_contingency_jpy'],
        'electrical_selected_price_subtotal_JPY':electrical['cost']['priced_purchase_subtotal_jpy_incl_tax'],
        'washer_purchase_addition_JPY':float(washer_purchase),
        'CAD_mass_estimate':json.loads((HERE/'assembly_validation.json').read_text())['mass'],
        'unpriced':['Taobao送料/輸入費','CNC図面審査による差額・税・住所別送料・決済換算',
                    '荷台等を自加工しない場合の切断/穴加工/バリ取り','自加工の工具/作業費',
                    'WILCOと追加電装各店の送料',*electrical['cost']['unpriced']],
        'excluded_by_design':electrical['cost']['excluded_by_design'],
        'note':'材料小売価格、既存仮枠、部品候補、自動加工見積を通貨別計上。完成車確定総額ではない。電装は実装・試験未完。'}
    (HERE/'bom.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    with (HERE/'cost_ledger.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n'); writer.writeheader(); writer.writerows(rows)
    print(json.dumps({k:result[k] for k in ['priced_and_allowance_subtotal_JPY','observed_automatic_quote_subtotal_USD','planning_total_JPY']},ensure_ascii=False))
    print('Run build_bom.py next to refresh the purchasing BOM and optional Excel workbook.')


if __name__=='__main__':main()
