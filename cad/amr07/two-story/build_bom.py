"""D6 purchase quantities from D5, including pack leftovers and price evidence."""
from pathlib import Path
import csv,json,math
HERE=Path(__file__).resolve().parent
D5=HERE.parent/'makita-power'
r=csv.DictReader((D5/'BOM.csv').open(encoding='utf-8-sig'));fields=r.fieldnames;rows=list(r)
v=json.loads((HERE/'validation.json').read_text())
obs={a['asin']:a for a in json.loads((HERE/'purchase_observations.json').read_text())}
grams=math.ceil(v['mass']['total_solid_PLA_kg']*1000)
for row in rows:
    if row['ID']=='F02':row.update({'使用数':'4','余剰数':'0','CAD形状数':'4',
        '備考':'下段2本＋上段2本。購入予定4本セットを全て使用し、D5から追加購入なし。価格1467円は同日P1/D5の観測を継承。'})
    if row['ID']=='F03':row.update({'使用数':'16','購入予定数':'20','購入口数':'2','余剰数':'4','明細金額':'1834',
        '備考':'基礎8個＋支柱下端4個＋上端4個。10個パックを1組追加。917円/パックは同日P1/D5の観測を継承。SUS支柱との混用は公称断面適合、現物の突起・座面確認が必要。'})
    if row['ID']=='F04':row.update({'使用数':'66','購入予定数':'100','購入口数':'2','余剰数':'34','明細金額':'5112',
        '価格根拠':'2026-09-22 商品ページ2556円/50個を再確認',
        '備考':'既存50個＋新規支柱金具16個。50個パックを1組追加。SUS支柱側8個も公称同寸法のHNTT6-6、混用受入確認前。'})
    if row['ID']=='D3_M6':row.update({'使用数':'38','備考':'下段ブラケット16＋上段支柱金具16＋天板6。旧電池受けから移す別枠4本はH01に含み重複計上しない。追加16本の購入価格未確定。'})
    if row['ID']=='P04':row.update({'分類':'D6 PLA','部品名':'1階の分割電装床4枚・荷物ストッパ4個','仕様・型番':'D6全PLA、中実CAD換算',
        '使用数':str(grams),'明細金額':str(grams*2),'備考':'2円/gの材料消費参考。D5の電池受け・床下電装受け・前トレイを全て廃止。実スライス、失敗、電力、工賃別。荷台構造は金属。'})
    if row['ID']=='POWER_LOW_STRAPS':row.update({'分類':'D6 1階電装','部品名':'1階計算機・監視回路の保持ベルト','備考':'幅15mm各1本、棚の長手方向に掛ける。受け棚は既存M6で固定。ケース選定後に通気口を避けて調整。'})
    if row['ID']=='POWER_PADS':row.update({'仕様・型番':'1階電池・電装下面2.6mm、上面1mm等の軟質当て材','備考':'保持具の現物合わせ、温度適合確認前。価格未確定。'})
    if row['ID']=='DECK_plate':row['備考']+=' D6では組付け位置のみ130mm上へ変更。加工STEP/PDFはD3と同一。'
post=obs['B0CB5N6ZJJ'];assert post['pack_JPY']==495
row={k:'' for k in fields};row.update({'ID':'D6_POSTS','分類':'D6 上段支持','部品名':'100mm溝付き支柱4本',
    '仕様・型番':'SUS SF2-30・30 BLACK／SF9-322、100mm×4本',
    '使用数':'4','単位':'本','購入予定数':'4','購入単位':'4本/パック','購入口数':'1','余剰数':'0',
    '購入単位単価':str(post['pack_JPY']),'明細金額':str(post['pack_JPY']),'通貨':'JPY',
    '価格根拠':'2026-09-22 Amazon商品ページ表示','選定状況':'型式・メーカー断面CAD確認、金具混用の現物確認前',
    '購入先':'Amazon掲載','URL':post['url'],'CAD形状数':'4',
    '備考':'ブラック100mm4本を選択。メーカー単位質量0.84kg/m。切断・端面タップ・追加穴加工なし。通常5～6日以内発送の表示、送料・Prime配送は未確認。'})
rows.append(row)
with (HERE/'BOM.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fields,lineterminator='\n');w.writeheader();w.writerows(rows)
totals={c:round(sum(float(r['明細金額']) for r in rows if r['通貨']==c and r['明細金額']),2) for c in ['JPY','USD']}
prior=json.loads((D5/'cost_summary.json').read_text());rate=prior['FX_reference_JPY_per_USD']
out=dict(revision='D6',date='2026-09-22',subtotal=totals,
    full_running_subtotal_JPY_reference=totals['JPY']+totals['USD']*rate,
    FX_reference_JPY_per_USD=rate,FX_date=prior['FX_date'],
    difference_from_D5_JPY=totals['JPY']-prior['subtotal']['JPY'],
    added_known_purchased_metal_JPY=495+917+2556,
    added_purchase=dict(posts4_JPY=495,brackets_extra10pack_JPY=917,nuts_extra50pack_JPY=2556,
                       upper300mm_rails_JPY=0,extra_M6x12_qty=16,extra_M6x12_JPY=None),
    selected_power_delivered_Tokyo_reference_JPY=23380,
    source_D3_plate_and_mount_quotes_unchanged=True,new_metal_quote_needed=False,
    unpriced_rows=[r['ID'] for r in rows if not r['明細金額']],
    complete_purchase_total=False,
    note='継承予算枠込みの車体小計。今回の支持金物は表示価格で3968円追加、上段300mm2本は購入予定パック内。追加M6ねじ・送料差額・電装未選定品・税/決済料などは別。')
(HERE/'cost_summary.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False))
