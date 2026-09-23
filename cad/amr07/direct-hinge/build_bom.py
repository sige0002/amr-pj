"""D6.8 purchase quantities and actual machining observations; no usage proration."""
from pathlib import Path
import csv,json,math,hashlib
HERE=Path(__file__).resolve().parent;BASE=HERE.parent
reader=csv.DictReader((BASE/'hinged-deck/BOM.csv').open(encoding='utf-8-sig'));fields=reader.fieldnames;rows=list(reader);by={x['ID']:x for x in rows}
v=json.loads((HERE/'validation.json').read_text());q=json.loads((HERE/'quote-evidence/observed.json').read_text())
def quantity(id,use,**kw):
 x=by[id];x.update(使用数=str(use),余剰数=str(int(x['購入予定数'])-use),CAD形状数=str(use),**kw)
quantity('F04',66,備考='D6.5の70個から不要な天板4個を除く。ロック用2個を残す。ヒンジ固定M4溝ナットは別行。購入100個の内数。')
quantity('D3_M6',44,備考='D6.5の50本から固定天板用6本を除く。共通70本パックを維持。H01別枠4本は従来どおり別予算で、二重配分しない。')
quantity('D62_FLOOR_SCREWS',28,部品名='床・ケース・ヒンジ金具のM4×16',備考='床継ぎ目4＋ケース底8＋ケース蓋8＋ヒンジ可動葉4＋金具天板4＝28本。購入60本の内数。固定葉用M4×10は別行。')
quantity('D3_STOP_NUTS',36,備考='荷物止め8＋床4＋ケース底8＋蓋8＋ヒンジ可動葉4＋金具天板4＝36個。20個273円×2。開き止め用ではない。')
quantity('D64_FLOOR_WASHERS',36,備考='床上下8＋ケース底8＋蓋8＋ヒンジ固定葉4＋可動葉外側4＋金具天板裏4＝36枚。20枚430円×2。',部品名='床・ケース・ヒンジのM4 OD12×t1座金')
quantity('ELEC_CASE_WASHER',6,部品名='天板ロック用M6 OD18×t1座金',備考='M6×15蝶ボルト1本あたり3枚、2か所で6枚。購入30枚パックの内数。開き止めなし。')
quantity('HATCH_HINGES',2,**{'仕様・型番':'スガツネHG-TP20、2.0N·m/個、初期±25%、60g/個'},購入単位='1個×2',購入口数='2',購入単位単価='1309',明細金額='2618',URL='https://www.amazon.co.jp/dp/B08PYP16SL',備考='2026-09-23 Amazon税込1309円/個。30mmフレーム対応をメーカー確認。外側溝へ直接固定。購入品は寸法図再構成、実品の厚さ・溝ナット・保持力は受入確認前。')
for id in ['HATCH_HINGES','HATCH_LOCKS']:by[id]['分類']='D6.8 天板開閉'
grams=math.ceil(v['mass']['total_solid_PLA_kg']*1000)
by['P04'].update(使用数=str(grams),明細金額=str(2*grams),CAD形状数='14',部品名='床・PCカバー・荷物止め・操作ケース',**{'仕様・型番':'D6.8全14個。床4、支持梁1、PCカバー1、荷物止め4、操作ケースと蓋4'},備考='2円/g、中実CADの材料消費参考。非導電PLA。スライス支持材・失敗・電気・工賃別。ヒンジ用PLA部品と開き止めはない。')
by['DECK_plate'].update(部品名='D6.8格子穴アルミ天板',**{'仕様・型番':'300×300×4 / 6061-T6 / D68C / qty1'},明細金額=f"{q['plate_lot_USD']:.2f}",CAD形状数='1',価格根拠='2026-09-23 実STEP/PDFのJLCCNC自動見積',備考='材料、54丸穴、4長穴込み。既存D3形状へD4.5ヒンジ穴4個追加。数量1枚全額。新規L金具2個との共通送料はDECK_CNC_SHIP。担当者審査前、未発注。')
by['DECK_CNC_SHIP'].update(部品名='天板＋ヒンジL金具 日本宛共通送料',**{'仕様・型番':q['shipping_method']},明細金額=f"{q['shipping_USD']:.2f}",備考='天板1枚＋同形L金具2個の1配送。日本・国単位の表示、郵便番号検証なし。既存モーター金具は別見積。税・決済費用は未計上。',価格根拠='2026-09-23 JLCCNC通常配送表示')
def add(id,name,spec,use,buy,unit,total,currency,url,note):
 x={k:'' for k in fields};x.update(ID=id,分類='D6.8 天板開閉',部品名=name,使用数=str(use),単位='個',購入予定数=str(buy),購入単位=unit,購入口数='1',余剰数=str(buy-use),明細金額=str(total),通貨=currency,URL=url,CAD形状数=str(use),備考=note,選定状況='型式・配置選定、未購入・実機検証前',**{'仕様・型番':spec});rows.append(x);by[id]=x
 if currency=='JPY':x.update(購入単位単価=str(total),価格根拠='2026-09-23 Amazon実ページ税込',購入先='Amazon掲載')
 else:x.update(価格根拠='2026-09-23 実STEP/PDFのJLCCNC自動見積',購入先='JLCCNC')
add('HATCH_METAL_ANGLES','天板ヒンジ用金属L金具','50×50×22mm、4mm壁、R3内隅1本、D4.5通し穴4、6061-T6',2,2,'同形2個1ロット',q['angle_lot_USD'],'USD','https://jlccnc.com/jp/cnc-machining-quote','2個一式の加工価格。左右同形。開き止めなし。生地、図面指定公差±0.10、タップなし。共通送料はDECK_CNC_SHIP、担当者審査前。')
add('HATCH_FRAME_M4_NUT','3030用M4溝ナット','uxcell B07P71JFX7、16×8×7.6、M4、10個入',4,10,'10個/パック',906,'JPY','https://www.amazon.co.jp/dp/B07P71JFX7','ヒンジ固定葉1枚2個、計4。鼻形状とテーパーはCAD仮定。NFSL6の溝に対する回転・座り・突出と実締結試験は受入時確認。')
add('HATCH_FRAME_M4_BOLT','固定葉用M4×10ボルト','TRUSCO B44-0410、M4×10ステンレス、52本入',4,52,'52本/パック',661,'JPY','https://www.amazon.co.jp/dp/B002A5RK38','全52本パック額。ヒンジ葉t2＋座金t1で溝突出7mm、モデルで底まで2mm。実品寸法照合前。')
with (HERE/'BOM.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fields,lineterminator='\n');w.writeheader();w.writerows(rows)
old=json.loads((BASE/'hinged-deck/cost_summary.json').read_text());rate=old['FX_reference_JPY_per_USD'];subtotal={c:sum(float(x['明細金額']) for x in rows if x['通貨']==c and x['明細金額']) for c in ['JPY','USD']};total=subtotal['JPY']+subtotal['USD']*rate
s=dict(revision='D6.8',date='2026-09-23',subtotal=subtotal,FX_reference_JPY_per_USD=rate,FX_date=old['FX_date'],FX_basis='Reuse documented2026-09-21 reference, not current settlement rate',full_running_subtotal_JPY_reference=total,difference_from_D67_JPY_reference=total-old['full_running_subtotal_JPY_reference'],machining_quote=q,unpriced_rows=[x['ID'] for x in rows if not x['明細金額']],complete_purchase_total=False,opening_stop_cost_JPY=0,note='途中小計。PC・基板・配線・税等未計上。モーター価格は仮予算。Prime最終カート未確認。余りの按分値ではなく購入パック全額。')
(HERE/'cost_summary.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n');print(subtotal,total,'delta',s['difference_from_D67_JPY_reference'])
