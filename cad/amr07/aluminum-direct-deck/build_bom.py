"""D3 purchasing list, preserving quoted currency and inherited unknown costs."""
from pathlib import Path
import csv
import hashlib
import io
import json
import math
import subprocess
from decimal import Decimal, ROUND_HALF_UP

HERE=Path(__file__).resolve().parent
source=subprocess.check_output(['git','-C',str(HERE),'show','3417383:cad/amr07/BOM.csv']).decode('utf-8-sig')
reader=csv.DictReader(io.StringIO(source));fields=reader.fieldnames
excluded={'F03','F04','P04','DECK_square_bar','DECK_plate','DECK_fasteners_and_extra_slotnuts',
          'FIXTURE_HARDWARE','DECK_CNC_SHIP','DECK_SHIP'}
rows=[r for r in reader if r['ID'] not in excluded]
for r in rows:
    if r['ID']=='F02':r['備考']='下段2本使用、4本パックの残り2本は予備。上段なし。2026-09-22 P1で確認した商品価格を継承。'
    if r['ID']=='S04':
        r.update({'明細金額':'','価格根拠':'住所・同梱条件未確定','選定状況':'送料未確定',
                  '備考':'ミスミAmazon出品の3,000円以上送料無料表示。カート・配送先で確認。'})


def add(id_,name,spec,qty,unit='個',pack=None,price=None,asin=None,note='',basis='購入単価未確定'):
    r={k:'' for k in fields}
    r.update({'ID':id_,'分類':'D3荷台・フレーム','部品名':name,'仕様・型番':spec,'使用数':str(qty),
              '単位':unit,'通貨':'JPY','価格根拠':basis,'選定状況':'寸法選定済・実機検証前','備考':note})
    if pack:
        packs=math.ceil(qty/pack)
        r.update({'購入予定数':str(pack*packs),'購入単位':f'{pack}{unit}/パック','購入口数':str(packs),
                  '余剰数':str(pack*packs-qty),'購入単位単価':str(price),'明細金額':str(packs*price)})
    if asin:r.update({'購入先':'Amazon掲載','URL':'https://www.amazon.co.jp/dp/'+asin})
    rows.append(r);return r


add('F03','純正反転ブラケット本体','HBLFSN6',8,pack=10,price=917,asin='B0DKF1FCD6',
    note='下段8個のみ。上段追加8個を削除。ねじ・ナット別売。',basis='2026-09-22 P1商品確認を継承')
add('F04','車体全体の先入れ溝ナット','HNTT6-6',50,pack=50,price=2556,asin='B0DK9C99YH',
    note='既存基礎44＋天板6＝50個。50個パック1組に削減。H01とは別。',basis='2026-09-22 P1商品確認を継承')
add('D3_M6','ブラケット・天板固定ボルト','M6x12 六角穴付、CBM6-12相当',22,
    note='下段ブラケット16＋天板6。天板は4mmアルミへ頭を直接当てる。実物長さ/溝深さ/締付けを照合。販売パック未確定。')
add('D3_STOP_BOLTS','印刷ストッパ固定ねじ','M4x25 六角穴付',8,note='PLA位置決め部品40x15x15を一個2本で固定。主荷物保持はベルト。')
add('D3_STOP_NUTS','ストッパ用ナット','M4 六角ナット 対辺7 厚3.2',8)
add('D3_STOP_WASHERS','ストッパ用座金','M4 ID4.3 OD9 t0.8',8,unit='枚')
mass=json.loads((HERE/'validation.json').read_text())['mass'];grams=math.ceil(mass['total_solid_PLA_kg']*1000)
r=add('P04','電池受け・電装トレイ・ストッパのPLA','車体全7部品、中実CAD換算',grams,unit='g',
      note='手持ち材料2円/gの消費評価。実スライス、失敗、電力、労務別。天板は含まない。',basis='材料消費参考')
r['明細金額']=str(grams*2);r['購入予定数']='0'
r=add('D3_STRAP_SHIP','荷物固定ベルト送料参考','従来の地域表示を継承',1,basis='過去の地域表示参考',note='旧角棒送料600円を除去。住所別未確認。');r['明細金額']='600'
quote_path=HERE/'quote-evidence/D3-observed.json';q=json.loads(quote_path.read_text())
for ext,key in [('.step','step_sha256'),('.pdf','pdf_sha256')]:
    assert hashlib.sha256((HERE/(q['name']+ext)).read_bytes()).hexdigest()==q[key]
economic=next(x for x in q['records'] if x['speed']=='economic')
for id_,name,value in [('DECK_plate','D3格子穴アルミ天板',economic['parts_lot_USD']),
                       ('DECK_CNC_SHIP','D3天板 日本宛UPS表示送料',economic['shipping_USD'])]:
    r=add(id_,name,'300x300x4 / 6061-T6 / C45_D3 / qty1',1,basis='修正版STEP/PDFのJLCCNC実自動見積',
          note='加工は材料・全50丸穴・4長穴込み。送料は国単位。担当者審査・税・決済手数料別、未発注。')
    r.update({'通貨':'USD','明細金額':str(value),'URL':'https://jlccnc.com/jp/cnc-machining-quote'})
with (HERE/'BOM.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fields,lineterminator='\n');w.writeheader();w.writerows(rows)
rate=json.loads((HERE.parent/'aluminum-grid-deck/jpy_conversion.json').read_text())['rate']
rate=dict(rate,saved_XML='../aluminum-grid-deck/quote-evidence/ecb-2026-09-21.xml')
fx=Decimal(rate['JPY_per_USD_calculated'])
conversion=[]
for r in q['records']:
    yen=Decimal(str(r['total_USD']))*fx
    conversion.append(dict(r,total_JPY_reference=float(yen),
         total_JPY_rounded_to_10=int((yen/10).quantize(Decimal('1'),rounding=ROUND_HALF_UP)*10)))
(HERE/'jpy_conversion.json').write_text(json.dumps(dict(purpose='D3 actual quote, historical ECB2026-09-21 reference, not payment rate',
     quote_source_sha256=hashlib.sha256(quote_path.read_bytes()).hexdigest(),rate=rate,records=conversion,
     fees_import_taxes_included=False,settlement_JPY=None),ensure_ascii=False,indent=2)+'\n')
totals={c:round(sum(float(r['明細金額']) for r in rows if r['通貨']==c and r['明細金額']),2) for c in ['JPY','USD']}
prev=json.loads((HERE.parent/'printed-deck-frame/cost_summary.json').read_text())['subtotal']
summary=dict(date='2026-09-22',scope='D3 full vehicle running subtotal; includes inherited budget allowances, not a complete quote',
    subtotal=totals,unpriced_rows=[r['ID'] for r in rows if not r['明細金額']],
    quoted_deck_USD=economic,quoted_deck_JPY_reference=conversion[-1]['total_JPY_rounded_to_10'],
    full_running_subtotal_JPY_reference=float(Decimal(str(totals['JPY']))+Decimal(str(totals['USD']))*fx),
    known_subtotal_delta_vs_P1_JPY_reference=float(Decimal(str(totals['JPY']-prev['JPY']))+Decimal(str(totals['USD']-prev['USD']))*fx),
    frame300_used=2,frame300_purchased=4,upper_rails=0,deck_spacers=0,
    optional_grid_hardware=dict(slotnut='HNTT6-4',maximum_simultaneous_qty=12,installed_in_base_CAD=False,
        price_verified=False,personal_procurement_route_verified=False,
        note='拡張機器用。フレーム上の2列で使用。先入れはフレーム組立前に準備、又は横材を外して追加。全36穴で同時使用する必要はない。追加時は費用・質量に加算。'),
    inherited_price_evidence='../printed-deck-frame/cost_summary.json',
    additional_unknowns='電池・電装の未選定部品、輸入/決済/送料差額、加工未見積の既存下段板、労務等は親BOMの留保を継承。',
    complete_purchase_total=False)
(HERE/'cost_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False,indent=2))
