"""Add actual rear controls and pack purchases to the preserved D6.5 ledger."""
from pathlib import Path
import csv,json,math
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'two-story'
f=(BASE/'BOM.csv').open(encoding='utf-8-sig');r=csv.DictReader(f);fields=r.fieldnames;rows=list(r)
v=json.loads((HERE/'validation.json').read_text());basev=json.loads((BASE/'validation.json').read_text())
rows=[r for r in rows if r['ID']!='U05']
by={r['ID']:r for r in rows}
by['F04'].update(使用数='78',余剰数='22',CAD形状数='78',備考='D6.5の70個＋後方ケース8個。購入予定100個の内数。手持ちとは扱わない。')
by['D3_M6'].update(使用数='58',購入予定数='70',購入単位='35本/パック',購入口数='2',余剰数='12',購入単位単価='1180',明細金額='2360',価格根拠='2026-09-23 Amazon商品ページ、35本1180円税込',購入先='オノカツ／Amazon発送',URL='https://www.amazon.co.jp/dp/B01N3BIIMO',選定状況='Onokatsu131-00-M6x12、購入パック確定・未購入',備考='D6.5別枠50本＋操作部8本＝58本。旧50本も未計上だったため2360円全てを今回初計上。基礎H01内の別枠4本には割り当てず、パック余剰12本として保持。一式H01は個別買付表へ分解するまで予算枠を据置く。')
by['D3_STOP_NUTS'].update(使用数='20',購入予定数='20',購入単位='20個/パック',購入口数='1',余剰数='0',購入単位単価='273',明細金額='273',価格根拠='2026-09-23 Amazon商品ページ、20個273円税込',購入先='Amazon.co.jp',URL='https://www.amazon.co.jp/dp/B0BVQJS1D2',**{'仕様・型番':'TRUSCO Y810-0004、M4×0.7、三価クロメート、対辺7mmの公称モデル'},選定状況='パック確定・未購入',備考='ストッパ8＋床継ぎ目4＋ケース蓋8＝20。従来12個も未計上だったためパック全額を初計上。')
by['D62_FLOOR_SCREWS'].update(使用数='12',余剰数='48',CAD形状数='12',部品名='床継ぎ目・操作ケース蓋のM4×16',備考='床継ぎ目4本＋操作ケース蓋8本。購入予定60本から流用、買い増しなし。直販770円＋共通送料385円を維持。')
by['D64_FLOOR_WASHERS'].update(使用数='16',余剰数='4',CAD形状数='16',部品名='床継ぎ目・操作ケース蓋のOD12平座金',備考='床上下8枚＋ケース蓋上8枚。Amazon20枚パック430円、従来店舗の送料込み678円から248円減。CAD内径4.1は公称モデル、実寸受入確認前。')
g=math.ceil((basev['mass']['total_solid_PLA_kg']+v['mass']['new_PLA_kg'])*1000)
by['P04'].update(使用数=str(g),明細金額=str(2*g),部品名='床・支持梁・PCカバー・荷物ストッパ・後方操作ケース',**{'仕様・型番':'D6.5 PLA＋D6.6ケース2個・蓋2枚、中実CAD材料量'},備考='2円/gの材料消費参考。スプール新規購入額、失敗・支持材・電力・工賃を含まない。荷台の主支持は金属。')
by['U06'].update(部品名='電源着脱コネクタ・ヒューズ等の配電部品',備考='主電源スイッチ3214本体はELEC_MAINへ計上。既存電池アダプター付属スイッチ・ヒューズの形式確認後に重複を避けてハーネスを確定。')
by['U15']['備考']+=' 後方操作ケース4点はP04へ計上済み、ここへ重複計上しない。'

def add(id,name,spec,qty,pack,price,url,note):
 d={k:'' for k in fields};d.update({'ID':id,'分類':'D6.6 後方操作部','部品名':name,'仕様・型番':spec,'使用数':str(qty),'単位':'個','購入予定数':str(pack),'購入単位':str(pack)+'個/購入単位','購入口数':'1','余剰数':str(pack-qty),'購入単位単価':str(price),'明細金額':str(price),'通貨':'JPY','価格根拠':'2026-09-23 Amazon実商品ページ、税込','購入先':'Amazon掲載・Amazon発送','URL':url,'選定状況':'型式・配置選定、未購入・実寸受入前','備考':note});rows.append(d)
add('ELEC_ARM','手動ARMボタン（黒）','amon3212、自動戻りNO、取付穴φ12、板厚1〜5mm',1,1,835,'https://www.amazon.co.jp/dp/B075SQ41JN','非常停止解除だけで再起動させないための独立操作。押しても走行指令は出さない。赤3211より177円高いが停止との識別を優先。最小接点負荷は未確認、入力回路で検証。')
add('ELEC_MAIN','全電源の主スイッチ','amon3214、ON/OFF、DC24V10A、取付穴φ12、板厚1〜4mm',1,1,621,'https://www.amazon.co.jp/dp/B075SW22KP','F0後の全負荷遮断。モーター電源用の非常停止とは別。250型絶縁平型端子2個は未計上。始動電流・遮断時過渡の実機検証前。')
add('ELEC_CASE_WASHER','ケース固定M6大径平座金','Onokatsu SUS304、M6 OD18×t1（床梁のt1.6とは別）',8,30,968,'https://www.amazon.co.jp/dp/B0DZVCSRXG','ケース2個×4固定点。M6×12、印刷壁4.5mm＋座金1mmで、公称ねじ掛かり5.3mm。')
with (HERE/'BOM.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fields,lineterminator='\n');w.writeheader();w.writerows(rows)
s=json.loads((BASE/'cost_summary.json').read_text());previous=s['full_running_subtotal_JPY_reference'];s['revision']='D6.6'
s['subtotal']={c:sum(float(r['明細金額']) for r in rows if r['通貨']==c and r['明細金額']) for c in ['JPY','USD']}
s['full_running_subtotal_JPY_reference']=s['subtotal']['JPY']+s['subtotal']['USD']*s['FX_reference_JPY_per_USD']
s['controls_change']=dict(new_switches_JPY=1456,new_M6_washer_pack_JPY=968,newly_priced_shared_M6_packs_JPY=2360,newly_priced_shared_M4_nut_pack_JPY=273,PLA_material_delta_JPY=2*g-1280,subtotal_change_from_procurement_updated_D65_JPY=s['full_running_subtotal_JPY_reference']-previous)
s['unpriced_rows']=[r['ID'] for r in rows if not r['明細金額']]
s['note']='購入パック全額で計上した途中小計。Pico所有・同品購入先変更の1313円減と、後方操作部追加および従来未計上ねじの価格確定を区別。電気保護基板・実装費・計算機・端子配線などは未計上。'
(HERE/'cost_summary.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
print(s['subtotal'],s['full_running_subtotal_JPY_reference'])
