"""Hinged deck purchase packs, including reuse of four bolts and slot nuts."""
from pathlib import Path
import csv,json,math
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;SRC=BASE/'control-layout'
r=csv.DictReader((SRC/'BOM.csv').open(encoding='utf-8-sig'));fields=r.fieldnames;rows=list(r);by={x['ID']:x for x in rows}
v=json.loads((HERE/'validation.json').read_text());sv=json.loads((SRC/'validation.json').read_text());bv=json.loads((BASE/'two-story/validation.json').read_text())
by['D3_M6'].update(使用数='56',余剰数='14',備考='D6.6の58本−天板固定6本＋ヒンジ固定4本＝56本。外した4本をヒンジへ移し、追加購入なし。旧未計上50本も含め35本1180円×2パックの全額を計上。H01別枠4本は配分し直していない。')
by['F04'].update(使用数='78',余剰数='22',備考='D6.6の78個−不要になった天板4個＋ヒンジフレーム固定4個＝78個。購入予定100個の内数。2個の天板ロック用は残す。')
by['D62_FLOOR_SCREWS'].update(使用数='24',余剰数='36',CAD形状数='24',部品名='床継ぎ目・ケース蓋・天板ヒンジのM4×16',備考='床4＋ケース蓋8＋ヒンジアダプターの天板固定4＋ヒンジ葉8＝24本。購入60本の内数。')
by['D3_STOP_NUTS'].update(使用数='32',購入予定数='40',購入口数='2',余剰数='8',明細金額='546',備考='ストッパ8＋床4＋ケース8＋ヒンジ周辺12＝32個。20個273円×2パック。')
by['D64_FLOOR_WASHERS'].update(使用数='28',購入予定数='40',購入口数='2',余剰数='12',明細金額='860',CAD形状数='28',部品名='床・ケース・ヒンジのM4 OD12平座金',備考='床8＋ケース8＋ヒンジ周辺12＝28枚。20枚430円×2パック。')
by['ELEC_CASE_WASHER'].update(使用数='18',余剰数='12',部品名='操作部・ヒンジ・ロックのM6 OD18×t1平座金',備考='操作ケース8＋ヒンジフレーム固定4＋蝶ボルト3枚×2＝18枚。30枚968円パックの内数。床梁のt1.6とは別。')
old_pla=int(by['P04']['明細金額']);grams=math.ceil((bv['mass']['total_solid_PLA_kg']+sv['mass']['new_PLA_kg']+v['mass']['new_PLA_kg'])*1000)
by['P04'].update(使用数=str(grams),明細金額=str(2*grams),部品名='床・PCカバー・ストッパ・操作ケース・ヒンジアダプター',**{'仕様・型番':'D6.7全PLA。ヒンジ可動アダプター2個＋90°止め付き固定アダプター2個を追加'},備考='2円/g、中実CAD換算の材料消費参考。全て非導電PLA。スライス支持材・失敗・工賃別。ヒンジ取付は空の天板を支持し、積載時の主荷重は金属レールで受ける。')
by['DECK_plate']['備考']+=' D6.7も加工形状を変更しない。ヒンジに格子穴4個、ロックに既存M6穴2個を利用。新規加工見積なし。'
for id,name,spec,use,pack,price,url,note in [
 ('HATCH_HINGES','トルクヒンジ','スガツネHG-TS15、1.5N·m/個、初期−20%〜＋40%',2,2,2344,'https://www.amazon.co.jp/dp/B007628W3W','1172円×2個。空天板約1.302kgの保持用。購入品CADはログインが必要で未取得、メーカー寸法による公称モデル。'),
 ('HATCH_LOCKS','天板ロック用M6蝶ボルト','TRUSCO B36-0615、M6×15、ユニクロ、18個入',2,18,527,'https://www.amazon.co.jp/dp/B002A5PVN4','工具なしのねじ式ロック2か所。各3枚のt1金属座金と板厚4mmで溝への突出8mm。座金は共通パックで計上、樹脂スペーサーを締結経路に入れない。')]:
 row={k:'' for k in fields};row.update({'ID':id,'分類':'D6.7 天板開閉','部品名':name,'仕様・型番':spec,'使用数':str(use),'単位':'個','購入予定数':str(pack),'購入単位':'2個（単品1172円×2）' if id=='HATCH_HINGES' else '18個/パック','購入口数':'1','余剰数':str(pack-use),'購入単位単価':str(price),'明細金額':str(price),'通貨':'JPY','価格根拠':'2026-09-23 Amazon実商品ページ、税込','購入先':'Amazon.co.jp（販売・発送Amazon）','URL':url,'選定状況':'型式・配置選定、未購入・公差/強度受入確認前','CAD形状数':'2','備考':note});rows.append(row)
with (HERE/'BOM.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fields,lineterminator='\n');w.writeheader();w.writerows(rows)
s=json.loads((SRC/'cost_summary.json').read_text());before=s['full_running_subtotal_JPY_reference'];s['revision']='D6.7'
s['subtotal']={c:sum(float(r['明細金額']) for r in rows if r['通貨']==c and r['明細金額']) for c in ['JPY','USD']};s['full_running_subtotal_JPY_reference']=s['subtotal']['JPY']+s['subtotal']['USD']*s['FX_reference_JPY_per_USD']
s['hatch_change']=dict(hinges_JPY=2344,locks_pack_JPY=527,extra_M4_nut_pack_JPY=273,extra_M4_washer_pack_JPY=430,PLA_material_delta_JPY=2*grams-old_pla,reused_M6_bolts=4,reused_slotnuts=4,additional_frame_or_machining_JPY=0,subtotal_increase_JPY=s['full_running_subtotal_JPY_reference']-before)
s['unpriced_rows']=[r['ID'] for r in rows if not r['明細金額']];s['note']='開閉天板・後方操作部・手持ちPicoを反映した途中小計。元の加工天板・金具STEPは変更なし。送料条件、仮予算、未見積は各明細を参照。';(HERE/'cost_summary.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n');print(s['subtotal'],s['full_running_subtotal_JPY_reference'],s['hatch_change'])
