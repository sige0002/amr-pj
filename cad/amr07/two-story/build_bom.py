"""D6 purchase quantities from D5, including pack leftovers and price evidence."""
from pathlib import Path
import csv,json,math,subprocess
HERE=Path(__file__).resolve().parent
D5=HERE.parent/'makita-power'
r=csv.DictReader((D5/'BOM.csv').open(encoding='utf-8-sig'));fields=r.fieldnames;rows=[row for row in r if row['ID']!='P03']
v=json.loads((HERE/'validation.json').read_text())
obs={a['asin']:a for a in json.loads((HERE/'purchase_observations.json').read_text())}
grams=math.ceil(v['mass']['total_solid_PLA_kg']*1000)
for row in rows:
    if row['ID']=='F02':row.update({'使用数':'4','余剰数':'0','CAD形状数':'4',
        '備考':'下段2本＋上段2本。購入予定4本セットを全て使用し、D5から追加購入なし。価格1467円は同日P1/D5の観測を継承。'})
    if row['ID']=='F03':row.update({'使用数':'20','購入予定数':'20','購入口数':'2','余剰数':'0','明細金額':'1834','CAD形状数':'20',
        '備考':'基礎8個＋支柱下端8個＋上端4個。D6.1の根元両側固定は購入予定パックの余り4個で対応。917円/パックは同日P1/D5の観測を継承。SUS支柱との混用は公称断面適合、現物の突起・座面確認が必要。'})
    if row['ID']=='F04':row.update({'使用数':'70','購入予定数':'100','購入口数':'2','余剰数':'30','明細金額':'5112','CAD形状数':'70',
        '価格根拠':'2026-09-22 商品ページ2556円/50個を再確認',
        '備考':'既存50個＋支柱金具24個＋D6.2継ぎ目支持梁4個－D6.3三角板用8個。購入予定100個の内数、30個余り。SUS支柱側12個も公称同寸法のHNTT6-6、混用受入確認前。'})
    if row['ID']=='D3_M6':row.update({'使用数':'50','備考':'下段ブラケット16＋上段支柱金具24＋天板6＋D6.2支持梁4。旧電池受けから移す別枠4本はH01に含み重複計上しない。D5から追加28本、D6.1から追加4本の購入価格未確定。'})
    if row['ID']=='H01':row.update({'仕様・型番':'詳細は締結部品表、基礎部50点','CAD形状数':'50',
        '備考':'従来66点から三角板用M6ねじ8本・座金8枚を削除。溝ナット8個の削除はF04。2300円の一式仮枠は購入パック未確定のため据置き、16点の削減を架空の節約額へ換算しない。モーターねじFC-2512候補を含む。'})
    if row['ID']=='P04':row.update({'分類':'D6 PLA','部品名':'四隅まで覆うリブ付き床4枚・継ぎ目支持梁1個・荷物ストッパ4個','仕様・型番':'D6.3全PLA、中実CAD換算',
        '使用数':str(grams),'明細金額':str(grams*2),'備考':'2円/gの材料消費参考。D5の電池受け・床下電装受け・前トレイを全て廃止。実スライス、失敗、電力、工賃別。荷台構造は金属。'})
    if row['ID']=='POWER_LOW_STRAPS':row.update({'分類':'D6 1階電装','部品名':'1階計算機・監視回路の保持ベルト','単位':'本','購入予定数':'','購入単位':'商品未選定','購入口数':'','余剰数':'','備考':'幅15mm各1本、棚の長手方向に掛ける。受け棚は既存M6で固定。ケース選定後に通気口を避けて調整。'})
    if row['ID']=='POWER_PADS':row.update({'仕様・型番':'1階電池・電装下面2.6mm、上面1mm等の軟質当て材','備考':'保持具の現物合わせ、温度適合確認前。価格未確定。'})
    if row['ID']=='DECK_plate':
        row.update({'単位':'枚','購入予定数':'1','購入単位':'1枚×1','購入口数':'1','余剰数':'0','購入先':'JLCCNC'})
        row['備考']+=' D6では組付け位置のみ130mm上へ変更。加工STEP/PDFはD3と同一。'
post=obs['B0CB5N6ZJJ'];assert post['pack_JPY']==495
row={k:'' for k in fields};row.update({'ID':'D6_POSTS','分類':'D6 上段支持','部品名':'100mm溝付き支柱4本',
    '仕様・型番':'SUS SF2-30・30 BLACK／SF9-322、100mm×4本',
    '使用数':'4','単位':'本','購入予定数':'4','購入単位':'4本/パック','購入口数':'1','余剰数':'0',
    '購入単位単価':str(post['pack_JPY']),'明細金額':str(post['pack_JPY']),'通貨':'JPY',
    '価格根拠':'2026-09-22 Amazon商品ページ表示','選定状況':'型式・メーカー断面CAD確認、金具混用の現物確認前',
    '購入先':'Amazon掲載','URL':post['url'],'CAD形状数':'4',
    '備考':'ブラック100mm4本を選択。メーカー単位質量0.84kg/m。切断・端面タップ・追加穴加工なし。通常5～6日以内発送の表示、送料・Prime配送は未確認。'})
rows.append(row)
for row in rows:
    if row['ID'] in ['D3_STOP_NUTS','D3_STOP_WASHERS']:
        row['使用数']='12'
        row['部品名']=row['部品名'].replace('ストッパ用','ストッパ・床継ぎ目用')
        row['備考']='荷物ストッパ8個＋床継ぎ目4個。共通購入へ集約し二重計上しない。'
        if row['ID']=='D3_STOP_WASHERS':row['仕様・型番']='M4 ID4.3～4.4 OD9 t0.8（規格の現物寸法確認）'
for part_id,name,spec in [
    ('D62_FLOOR_SCREWS','床継ぎ目の皿小ねじ','M4x16、90度皿、頭径8mm、公称寸法'),
    ('D62_BEAM_WASHERS','継ぎ目支持梁端の大径平座金','M6 ID6.6 OD18 t1.6')]:
    row={k:'' for k in fields}
    row.update({'ID':part_id,'分類':'D6.2 1階床支持','部品名':name,'仕様・型番':spec,
        '使用数':'4','単位':'個','通貨':'JPY','価格根拠':'購入単価未確定',
        '選定状況':'寸法選定済・購入パック未確定','CAD形状数':'4',
        '備考':'汎用金属締結材。PLAへのタップではなく貫通締結。追加加工見積は不要。コーナン等の小袋を優先し、価格は未計上。'})
    rows.append(row)
# Keep the currently unpriced scope visible in the same BOM. The historical
# battery/charger rows are superseded; only independent battery protection is
# still unselected. Blank amounts remain unknown, never zero-price purchases.
unselected=json.loads((HERE.parent/'procurement_bom.json').read_text())['unselected']
for item in unselected:
    item=dict(item)
    if item['id']=='U02':continue
    if item['id']=='U01':item.update(name='独立した電池低電圧保護回路',
        specification='選定済みBL1860B・接続アダプターとは別のUVLO回路',
        decision_needed='電池・充電器・アダプター代はPOWER各行で計上済み。独立保護回路の部品・基板・実装費は未見積。')
    if item['id']=='U03':item.update(specification='1階120×100×60mm、質量0.50kgの予約。製品未選定。',
        decision_needed='本体・記憶媒体・冷却の選定と購入価格を確定。重量枠があることは代金計上済みを意味しない。')
    if item['id']=='U06':item['decision_needed']='アダプター付属スイッチと重複計上せず、主遮断・着脱コネクタの必要部品を確定。'
    if item['id']=='U13':item['decision_needed']='現行の1階配線経路から線長・端子数を確定。購入品付属線との重複を避ける。'
    if item['id']=='U15':item.update(specification='D6.3の1階機器・ケース・通風・取付の具体化',
        decision_needed='PLA床とベルトの既計上分を除き、ケース・実機器の固定部・スタンドオフを選定。')
    if item['id']=='U17':item['decision_needed']='見積済みモーター金具・アルミ天板を除く。キャスター板の加工工具、工賃などは未見積。基礎の平面三角板はD6.3で廃止、加工も不要。切断済み支柱に追加加工は不要。'
    if item['id']=='U18':item['decision_needed']=f'現行P04の車体用PLA{grams}gとは別のモック材料・失敗分。スライス未完。'
    row={k:'' for k in fields}
    row.update({'ID':item['id'],'分類':'未選定・未計上','部品名':item['name'],
        '仕様・型番':item['specification'],'通貨':'JPY','価格根拠':'未見積',
        '選定状況':item['phase']+'／未選定',
        '備考':'必要数量：'+item['needed_quantity']+'。'+item['decision_needed']})
    rows.append(row)
with (HERE/'BOM.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fields,lineterminator='\n');w.writeheader();w.writerows(rows)
totals={c:round(sum(float(r['明細金額']) for r in rows if r['通貨']==c and r['明細金額']),2) for c in ['JPY','USD']}
prior=json.loads((D5/'cost_summary.json').read_text());rate=prior['FX_reference_JPY_per_USD']
before62=json.loads(subprocess.check_output(['git','-C',str(HERE),'show','ef44e1c:cad/amr07/two-story/cost_summary.json']))
out=dict(revision=v['parameters']['revision'],date='2026-09-22',subtotal=totals,
    full_running_subtotal_JPY_reference=totals['JPY']+totals['USD']*rate,
    FX_reference_JPY_per_USD=rate,FX_date=prior['FX_date'],
    difference_from_D5_JPY=totals['JPY']-prior['subtotal']['JPY'],
    added_known_purchased_metal_JPY=495+917+2556,
    added_purchase=dict(posts4_JPY=495,brackets_extra10pack_JPY=917,nuts_extra50pack_JPY=2556,
                       upper300mm_rails_JPY=0,extra_M6x12_qty=28,extra_M6x12_JPY=None),
    reinforcement_from_D6=dict(added_brackets=4,added_M6x12=8,added_HNTT6_6=8,
        additional_bracket_and_nut_pack_cost_JPY=0,additional_screws_JPY=None,
        basis='Use4 brackets and8 nuts from purchase-planned D6 packs; no ownership assumed.'),
    floor_reinforcement_from_D61=dict(added_M6x12=4,added_M6_large_washers=4,added_M4_countersunk=4,added_M4_plain_washers=4,added_M4_nuts=4,slotnuts_from_planned_pack=4,additional_slotnut_pack_JPY=0,additional_fastener_price_JPY=None,PLA_material_reference_increase_JPY=grams*2-764),
    corner_rework_from_D62=dict(removed_gussets=4,removed_gusset_fastener_sets=8,relocated_existing_floor_fastener_sets=4,
        additional_purchased_parts=0,additional_metal_machining=False,additional_hardware_purchase_JPY=0,
        removed_gusset_material_budget_JPY=500,hardware_budget_reduction_JPY=0,
        PLA_material_reference_increase_JPY=grams*2-1108,
        priced_and_budgeted_subtotal_change_JPY=totals['JPY']-before62['subtotal']['JPY']),
    selected_power_delivered_Tokyo_reference_JPY=23380,
    source_D3_plate_and_mount_quotes_unchanged=True,new_metal_quote_needed=False,
    unpriced_rows=[r['ID'] for r in rows if not r['明細金額']],
    complete_purchase_total=False,
    note='継承予算枠込みの車体小計。今回の支持金物は表示価格で3968円追加、上段300mm2本は購入予定パック内。追加M6ねじ・送料差額・電装未選定品・税/決済料などは別。')
(HERE/'cost_summary.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False))
