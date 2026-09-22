"""D5 full vehicle subtotal. Exact observed purchase costs vs allowances."""
from pathlib import Path
import csv
import json
import math
HERE=Path(__file__).resolve().parent
D3=HERE.parent/'aluminum-direct-deck'
r=csv.DictReader((D3/'BOM.csv').open(encoding='utf-8-sig'));fields=r.fieldnames;rows=list(r)
v=json.loads((HERE/'validation.json').read_text())
p=json.loads((HERE/'power_selection.json').read_text())
grams=math.ceil(v['mass']['total_solid_PLA_kg']*1000)
for row in rows:
    if row['ID']=='P04':row.update({'部品名':'後端電池受け・低位置電装受け・前電装トレイ・荷物ストッパのPLA',
        '仕様・型番':'D5全PLA、中実CAD換算','使用数':str(grams),'明細金額':str(grams*2),
        '備考':'2円/gの手持ち材料消費参考。旧D3電池受けと後トレイを置換。実スライス・失敗・電力・工賃別。'})
    if row['ID']=='H02':row.update({'部品名':'電池モジュール保持ベルト','仕様・型番':'E-Value BT-2520BK、幅25mm、長さ2mから調整',
        '使用数':'1','購入予定数':'1','購入単位':'1本','購入口数':'1','余剰数':'0','購入単位単価':'393','明細金額':'393',
        '価格根拠':'2026-09-22 表示393円を再確認、同梱前提','選定状況':'品番選定、保持試験前',
        '購入先':'ホームセンターブリコ／Yahoo!','URL':'https://store.shopping.yahoo.co.jp/hcbrico/4977292226752.html',
        '備考':'従来500円仮枠を置換。荷物用2本とは別に1本追加。送料は既存600円枠へ同梱する条件。余長は巻込みを防ぐ長さへ切断・固定。'})

def add(id_,name,spec,price,url,note,qty=1):
    row={key:'' for key in fields}
    row.update({'ID':id_,'分類':'D5選定電源','部品名':name,'仕様・型番':spec,'使用数':str(qty),'単位':'式',
        '購入予定数':str(qty),'購入単位':'1式','購入口数':'1','余剰数':'0','通貨':'JPY','URL':url,
        '価格根拠':'2026-09-22 販売ページ表示' if price is not None else '購入単価未確定',
        '選定状況':'型式選定・現物／電気検証前','備考':note})
    if price is not None:row.update({'購入単位単価':str(price),'明細金額':str(price)})
    rows.append(row)

kit=p['selected']['battery_charger_purchase'];adapter=p['selected']['adapter']
add('POWER_KIT','純正電池＋急速充電器','Makita BL1860B A-60464 x1 + DC18RF JPADC18RF x1',19800,kit['source'],
    'どちらも未所有のため新規購入。新品セットばらし・化粧箱なし。充電器は車外。電池単体を別行で二重計上しない。')
add('POWER_KIT_SHIP','電池・充電器セット送料','東京都表示送料',600,kit['source'],'住所・注文条件により変動。ポイントは値引き計上しない。')
add('POWER_ADAPTER','電池出力アダプター','Netkey diy-adapter03、14AWG、スイッチ・30Aヒューズ付き',2180,adapter['source'],
    '公称約95×90×30mm・123g。全高30mmを加算。低電圧保護には使わない。付属30Aのまま小ハーネス保護を保証しない。')
add('POWER_ADAPTER_SHIP','アダプター送料','東京都表示送料',800,adapter['source'],'発送予定のある商品。ユーザー住所と最終納期は未確認。')
add('POWER_PADS','電池・電装の軟質当て材','電池下面1mm、側面2.5/4mm、電装下面2mm、上面パッド',None,'','寸法調整用。素材価格・温度適合は未確定。')
add('POWER_LOW_STRAPS','低位置電装の保持ベルト','幅15mm、PC用・監視基板用各1本',None,'','電池用1本や荷物用2本とは別。実電装ケースと現物合わせ。',2)
with (HERE/'BOM.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fields,lineterminator='\n');w.writeheader();w.writerows(rows)
totals={c:round(sum(float(r['明細金額']) for r in rows if r['通貨']==c and r['明細金額']),2) for c in ['JPY','USD']}
rate=json.loads((D3/'jpy_conversion.json').read_text())['rate']['JPY_per_USD_calculated']
unknown=json.loads((HERE.parent/'bom_inputs.json').read_text())['unselected']
summary=dict(revision='D5',date='2026-09-22',subtotal=totals,
    selected_power_delivered_Tokyo_reference_JPY=23380,
    new_power_hardware_selected=True,charger_new_purchase=True,
    unpriced_rows=[r['ID'] for r in rows if not r['明細金額']],
    unselected_remaining=unknown,
    full_running_subtotal_JPY_reference=totals['JPY']+totals['USD']*float(rate),
    FX_reference_JPY_per_USD=float(rate),FX_date='2026-09-21',
    source_D3_plate_and_mount_quotes_unchanged=True,new_metal_quote_needed=False,
    complete_purchase_total=False,
    note='既存予算枠込みの走行台車小計。電池・充電器・接続アダプターは選定価格を追加。保護回路、主コネクタ、配線、計算機、送料差額・税・決済料等は未完。')
(HERE/'cost_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:summary[k] for k in ['subtotal','full_running_subtotal_JPY_reference','selected_power_delivered_Tokyo_reference_JPY']},ensure_ascii=False))
