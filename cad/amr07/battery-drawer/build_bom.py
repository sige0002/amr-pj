"""D4 full vehicle BOM; unknown costs are not converted into invented quotes."""
from pathlib import Path
import csv
import json
import math

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'aluminum-direct-deck'
reader=csv.DictReader((OLD/'BOM.csv').open(encoding='utf-8-sig'))
fields=reader.fieldnames;rows=list(reader)
v=json.loads((HERE/'validation.json').read_text())
grams=math.ceil(v['mass']['total_solid_PLA_kg']*1000)
for r in rows:
    if r['ID']=='P04':
        r.update({'部品名':'電池引出し・ガイド・電装トレイ・ストッパのPLA',
                  '仕様・型番':'D4全PLA部品、中実CAD換算','使用数':str(grams),
                  '明細金額':str(grams*2),'備考':'旧D3電池受けを除外し、D4印刷部品へ置換。2円/gの材料消費参考。実スライス・失敗・電力・労務別。'})
    if r['ID']=='H02':
        r.update({'仕様・型番':'幅15mm、長さ250mm以上、厚さ1.5mm以下の面ファスナーベルト2本',
                  '選定状況':'必要寸法指定、製品と保持力未確定','CAD形状数':'2',
                  '備考':'受け皿へ通す2本。重なり部分は電池側面。従来500円枠を1回だけ計上。実電池・保持試験で確定。'})

def add(id_,name,spec,qty,note):
    r={f:'' for f in fields}
    r.update({'ID':id_,'分類':'D4電池交換','部品名':name,'仕様・型番':spec,'使用数':str(qty),
              '単位':'個','通貨':'JPY','価格根拠':'購入単価・販売パック未確定',
              '選定状況':'形状候補・実機検証前','備考':note})
    rows.append(r)

add('D4_BOLT','引出し抜け止めボルト','M4x16 六角穴付',2,'3mm六角レンチで側面から脱着。既存4本のM6取付ねじは再使用。')
add('D4_NUT','抜け止め用ゆるみ止めナット','M4 AF7 高さ5mm、DIN985相当',2,'固定ガイドのポケットへ先に挿入。緩み止め抵抗・繰返し脱着は購入品と実機で検証。')
add('D4_WASHER','抜け止め用座金','M4 ID4.3 OD9 t0.8',2,'PLA当て面の保護。')
add('D4_LINER','電池底・四辺の保護パッド','底1mm、四辺は実電池に合わせて調整',1,'印刷当て面と電池の間を軟質材で保護。材料・接着・温度特性と費用は未確定。')
add('D4_LACING','配線・コネクタ固定材','細幅結束材、コネクタ絶縁キャップ',1,'電線外被側で張力を受ける。電池本体へ締め込まない。数量・価格は実ハーネス確定後。')
# Explicitly list the previously omitted unselected battery/charger, rather
# than reporting a subtotal that looks like a complete drivable vehicle.
add('U01','電池とセル保護','18V級、満充電21V以下、実測本体50x112x36mm以内',1,
    '未選定。機械仮合わせ候補VANT5S2200mAhは通常税込9020円、会員6765円＋送料。保護回路等は別。候補価格を確定購入額として小計へ加えない。')
add('U02','適合充電器','採用電池と同時選定、車体外充電',1,'未選定・価格未確定。')
with (HERE/'BOM.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fields,lineterminator='\n');w.writeheader();w.writerows(rows)
totals={c:round(sum(float(r['明細金額']) for r in rows if r['通貨']==c and r['明細金額']),2) for c in ['JPY','USD']}
previous=json.loads((OLD/'cost_summary.json').read_text())
rate=json.loads((OLD/'jpy_conversion.json').read_text())['rate']['JPY_per_USD_calculated']
summary=dict(date='2026-09-22',scope='D4 full running subtotal, unfinished purchase list',
    subtotal=totals,unpriced_rows=[r['ID'] for r in rows if not r['明細金額']],
    known_delta_vs_D3_JPY=totals['JPY']-previous['subtotal']['JPY'],
    PLA_solid_g_rounded=grams,PLA_material_reference_JPY=grams*2,
    new_metal_machining_required=False,quoted_D3_plate_unchanged=True,
    existing_four_M6_mount_sets_reused=True,H02_two_battery_straps_budget_carried_once_JPY=500,
    battery_candidate=dict(part='VANT5S2200mAh XT60',selected=False,ordinary_display_JPY=9020,
        member_display_JPY=6765,shipping_verified=False,stock_verified=False,
        source='https://www.radicon1.com/item/VANT2200-45c-5sG/',included_in_subtotal=False),
    full_running_subtotal_JPY_reference=totals['JPY']+totals['USD']*float(rate),
    complete_purchase_total=False,
    note='候補電池の価格は比較情報。電池・保護・充電器・追加小ねじ・パッド等が未価格のため完成総額ではない。従来の未選定品・輸入費・税・労務等の留保も継承。')
(HERE/'cost_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False,indent=2))
