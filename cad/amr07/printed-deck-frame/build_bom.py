"""P1 purchasing list: replace D2 deck rows, keep inherited uncertainty explicit."""
from pathlib import Path
import csv
import hashlib
import io
import json
import math
import re
import subprocess

HERE=Path(__file__).resolve().parent
source=subprocess.check_output(['git','-C',str(HERE),'show','3417383:cad/amr07/BOM.csv']).decode('utf-8-sig')
reader=csv.DictReader(io.StringIO(source)); fields=reader.fieldnames
rows=list(reader)
excluded={'F03','F04','P04','DECK_square_bar','DECK_plate','DECK_fasteners_and_extra_slotnuts',
          'FIXTURE_HARDWARE','DECK_CNC_SHIP','DECK_SHIP'}
rows=[r for r in rows if r['ID'] not in excluded]
observed=[
    ('F02','B0DKDZ8G9G','NFSL6-3030-300',4,1467),
    ('F03','B0DKF1FCD6','HBLFSN6',10,917),
    ('F04','B0DK9C99YH','HNTT6-6',50,2556),
    ('P1_SLEEVE','B0GWMC8ZY9','M6 sleeve ID6.2 OD12 L5mm',10,580),
    ('P1_BUTTON','B0C2CDH79R','M6x16 button cap, YAHATA',10,410),
    ('P1_WASHER','B0G2X4FSQX','uxcell M6 washer ID6.4 OD18 t1.6',50,845),
]
evidence=[]
for id_,asin,spec,pack,price in observed:
    path=Path('/tmp/amr-p1-source-check')/(asin+'.html')
    if asin=='B0DKF1FCD6': path=path.with_name('bracket.html')
    # Evidence extracts can be regenerated without re-fetching a changed price.
    item=dict(id=id_,asin=asin,url='https://www.amazon.co.jp/dp/'+asin,spec=spec,
              pack_qty=pack,observed_pack_JPY=price,date_JST='2026-09-22',
              source='Product title and displayed product price, not a cart/checkout quote',
              delivery='Seller/recipient/cart dependent; Prime availability not asserted')
    if path.exists():
        raw=path.read_bytes(); item['raw_html_sha256']=hashlib.sha256(raw).hexdigest()
        title=re.search(r'<title>(.*?)</title>',raw.decode(errors='replace'),re.S)
        item['observed_title']=title[1] if title else None
    evidence.append(item)
for r in rows:
    if r['ID']=='F02':
        r.update({'使用数':'4','余剰数':'0','CAD形状数':'4','価格根拠':'2026-09-22 Amazon商品表示',
                  '備考':'下段2本＋上段2本。同じ4本パックを使い切る。上段のための追加パック不要。'})
    if r['ID']=='S04':
        r.update({'明細金額':'','価格根拠':'住所・同梱条件未確定','選定状況':'送料未確定',
                  '備考':'ミスミAmazon出品は3,000円以上送料無料の表示。対象品・同一会計・配送先で確認。'})


def add(id_,name,spec,qty,unit='個',pack=None,price=None,asin=None,note='',basis='購入単価未確定'):
    r={k:'' for k in fields}
    r.update({'ID':id_,'分類':'P1荷台・フレーム','部品名':name,'仕様・型番':spec,'使用数':str(qty),
              '単位':unit,'通貨':'JPY','価格根拠':basis,'選定状況':'寸法選定済・試作検証前','備考':note})
    if pack:
        packs=math.ceil(qty/pack)
        r.update({'購入予定数':str(packs*pack),'購入単位':f'{pack}{unit}/パック','購入口数':str(packs),
                  '余剰数':str(packs*pack-qty),'購入単位単価':str(price),'明細金額':str(packs*price)})
    if asin:r.update({'購入先':'Amazon掲載','URL':'https://www.amazon.co.jp/dp/'+asin})
    rows.append(r)


add('F03','純正反転ブラケット本体','HBLFSN6',16,pack=10,price=917,asin='B0DKF1FCD6',
    note='下段既存8＋上段追加8。2パックで4個余り。ボルト・ナット別売。',basis='2026-09-22 商品表示')
add('F04','車体全体の先入れ溝ナット','HNTT6-6',68,pack=50,price=2556,asin='B0DK9C99YH',
    note='既存基礎44＋上段ブラケット16＋PLA板8。全車で2パック。H01とは別。',basis='2026-09-22 商品表示')
add('P1_BRACKET_BOLTS','上下フレームブラケットのボルト','M6x12 六角穴付、CBM6-12相当',32,
    note='下段16＋上段16。旧F03-SET同梱扱いを廃止し全32本別計上。販売パック・強度区分の確認が残る。')
add('P1_SLEEVE','既製圧縮カラー','アルミ ID6.2×OD12×L5mm',8,pack=10,price=580,asin='B0GWMC8ZY9',
    note='板内に収める既製品。自家切断・穴加工なし。',basis='2026-09-22 商品表示')
add('P1_BUTTON','PLA板固定ボルト','M6x16 六角穴付ボタンキャップ',8,pack=10,price=410,asin='B0C2CDH79R',
    note='寸法条件：頭径10.5以下、頭高3.3以下。販売品の規格/座面を受入照合。',basis='2026-09-22 商品表示')
add('P1_WASHER','PLA板大径座金','M6 ID6.4×OD18×t1.6mm',16,unit='枚',pack=50,price=845,asin='B0G2X4FSQX',
    note='1か所2枚、8か所。既存下段用の座金予算と使用数を分ける。',basis='2026-09-22 商品表示')
add('P1_STOP_BOLTS','印刷ストッパ用ボルト','M4x30 六角穴付',8,note='旧M4x25は長さ不足。新規パック未確定。')
add('P1_STOP_NUTS','ストッパ埋込みナット','M4 六角ナット 対辺7 厚3.2',8,note='既存D2を組んでいれば8個再使用。初回購入では必要。')
mass=json.loads((HERE/'validation.json').read_text())['mass']
pla_g=math.ceil(mass['total_solid_PLA_kg']*1000)
add('P04','P1車体の全PLA部品','4分割荷台＋4ストッパ＋前後トレイ＋既存電池受け',pla_g,unit='g',
    note='11部品。中実CAD換算を切上げ、既所有材料2円/gの消費評価。実スライス/失敗/電力/労務別。',basis='材料消費参考・実購入価格ではない')
rows[-1]['明細金額']=str(pla_g*2);rows[-1]['購入予定数']='0'
add('P1_STRAP_SHIP','荷物ベルト送料参考','旧地域表示から継承',1,note='旧角棒送料600円を除去。配送先別未確認。',basis='過去地域表示参考')
rows[-1]['明細金額']='600'
with (HERE/'BOM.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fields);w.writeheader();w.writerows(rows)
totals={c:round(sum(float(r['明細金額']) for r in rows if r['通貨']==c and r['明細金額']),2) for c in ['JPY','USD']}
summary=dict(date='2026-09-22',source_BOM_revision='3417383',scope='P1 full vehicle running subtotal, with inherited budgets; not a completed quotation',
    subtotal=totals,unpriced_rows=[r['ID'] for r in rows if not r['明細金額']],
    additional_unknowns='Inherited electronics/battery/boards/wires, shipping/taxes/labor and print failures remain unresolved. See parent BOM.',
    current_observations=evidence,quoted_CNC_motor_mounts_USD_including_observed_shipping=82.25,
    CNC_deck_order_needed=False,upper_frame_additional_pack_cost_JPY=0,
    complete_purchase_total=False)
(HERE/'cost_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False))
