"""E4 purchase list; retain source prices and invalidate obsolete deck quote."""
from pathlib import Path
import csv,json,math,hashlib
HERE=Path(__file__).resolve().parent;BASE=HERE.parent
with (BASE/'fixed-deck/BOM.csv').open(encoding='utf-8-sig') as f:r=csv.DictReader(f);fields=r.fieldnames;rows=list(r)
removed={'D3_STOP_BOLTS','D3_STOP_WASHERS'};rows=[r for r in rows if r['ID'] not in removed];by={r['ID']:r for r in rows}
g=json.loads((HERE/'geometry.json').read_text());old=json.loads((BASE/'fixed-deck/cost_summary.json').read_text());rate=old['FX_reference_JPY_per_USD']
by['D3_M6'].update(使用数='44',余剰数='26',部品名='フレーム用M6×12キャップボルト',備考='天板6本はE4_LOWHEADへ分離。使用44／購入70。購入パック数を維持。')
by['D3_STOP_NUTS'].update(使用数='20',購入予定数='20',購入口数='1',余剰数='0',明細金額='273',部品名='床・ケース用M4ナット',備考='標準から荷物止め8個分を外す。床4＋ケース底8＋蓋8。20個273円の既存価格。')
grams=math.ceil(g['mass']['total_solid_PLA_kg']*1000)
by['P04'].update(使用数=str(grams),明細金額=str(2*grams),CAD形状数='12',部品名='床・PCカバー・操作部・PicoケースのPLA',**{'仕様・型番':'E4標準12個。荷物止め4個は標準から除外。2円/gの材料消費参考'},備考='中実CAD参考。支持材・失敗・電気代・工賃別。モニター部品は一切含まない。')
for id in ['DECK_plate','DECK_CNC_SHIP']:
 by[id].update(明細金額='',購入単位単価='',価格根拠='E4変更後の実加工見積未取得',選定状況='旧D3見積は現形状に適用不可',備考='新STEP: reviewed-design/E4_Deck_300x300x4.step。旧28.67USD＋送料9.98USDを転記しない。未計上を節約額としない。')
by['DECK_plate']['仕様・型番']='6061-T6 300×300×4、25φ4.5＋6φ6.6＋4長穴30×6R3、タップ/皿加工なし'
by['POWER_LOW_STRAPS'].update(部品名='1階計算機の保持ベルト',使用数='1',**{'仕様・型番':'幅15mm、車載PC用1本'},備考='監視回路用ベルトは撤去済み。Picoケースは4点ボルト固定。')
for id,name,spec,qty,pack,price,note,url in [
 ('E4_LOWHEAD','天板用極低頭M6×12','NBK SSH-M6-12、頭径10／高さ1.5／六角3mm',6,10,528,'メーカー10本入税込参考。6本使用、4本余り。個人購入先・AmazonPrime・送料は未確定。一般M6の締付値を流用しない。','https://www.nbk1560.com/products/specialscrew/nedzicom/socketheadcapscrew/SSH/'),
 ('E4_TERMINAL_RETENTION','ケース内配線の保持・表示用品','結束バンド、縁保護、MOTOR STOP/MAIN POWER表示',1,None,None,'ケースの結束橋を使用。現物ハーネスに合わせて数と寸法を決定。',''),
 ('E4_LOWHEAD_SHIP','極低頭ボルトの送料','購入先確定後',1,None,None,'メーカー表示単価に送料を含むと仮定しない。','')]:
 row={f:'' for f in fields};row.update(ID=id,分類='E4追加',部品名=name,**{'仕様・型番':spec},使用数=str(qty),単位='本' if pack else '式',通貨='JPY',備考=note,URL=url,選定状況='寸法選定・購入先未確定',価格根拠='2026-09-23メーカー掲載税込参考' if price else '未見積')
 if pack:row.update(購入予定数=str(pack),購入単位='10本入',購入口数='1',余剰数=str(pack-qty),購入単位単価=str(price),明細金額=str(price),CAD形状数='6')
 rows.append(row)
for r in rows:
 if r['ID']=='U22':r['分類']='電装候補・価格計上'
with (HERE/'BOM.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fields,lineterminator='\n');w.writeheader();w.writerows(rows)
sub={c:sum(float(r['明細金額']) for r in rows if r['通貨']==c and r['明細金額']) for c in ['JPY','USD']};total=sub['JPY']+sub['USD']*rate
cost=dict(revision='E4',subtotal=sub,FX_reference_JPY_per_USD=rate,FX_date=old['FX_date'],priced_subtotal_JPY_reference=total,complete_purchase_total=False,new_deck_quote_complete=False,optional_monitor_included=False,unpriced_ids=[r['ID'] for r in rows if not r['明細金額']],BOM_sha256=hashlib.sha256((HERE/'BOM.csv').read_bytes()).hexdigest())
(HERE/'cost_summary.json').write_text(json.dumps(cost,ensure_ascii=False,indent=2)+'\n')
def esc(s):return str(s).replace('|','\\|').replace('\n','<br>')
details=['# E4 全明細','', '[概要](BOM.ja.md) ／ [CSV](BOM.csv)','']
for r in rows:
 details += [f'<a id="item-{r["ID"].lower()}"></a>',f'## {r["ID"]}：{r["部品名"]}','','| 項目 | 内容 |','|---|---|']
 details += [f'| {esc(k)} | {esc(v)} |' for k,v in r.items() if v and k!='ID'];details.append('')
(HERE/'BOM-details.ja.md').write_text('\n'.join(details).rstrip()+'\n')
groups={}
for r in rows:
 id=r['ID'];group=('電池・充電器' if id in ['POWER_KIT','POWER_KIT_SHIP','POWER_ADAPTER','POWER_ADAPTER_SHIP'] else 'モーター・タイヤ・キャスター' if id in ['D01','D02','C01','P01','S02','S06'] else 'モーター金具' if id in ['Q01','S08'] else '天板' if id in ['DECK_plate','DECK_CNC_SHIP','E4_LOWHEAD','E4_LOWHEAD_SHIP'] else '電装・配線' if id.startswith(('ELEC','U','E3','E4_TERMINAL')) or id=='E02' else 'フレーム・締結・PLA等')
 groups.setdefault(group,0);groups[group]+=float(r['明細金額'] or 0)*(rate if r['通貨']=='USD' else 1)
md=['# E4 BOM：標準構成のみ','',f'**計上済み小計 {total:,.0f}円相当＋未計上分**（{sub["JPY"]:,.0f}円＋{sub["USD"]:.2f} USD）。モニターは含めません。','', '**天板の穴配置を変更したため、旧天板見積38.65 USDは現行小計から外しました。この減少を節約額とは扱いません。** 新天板・送料は実再見積待ちです。','', '[全明細Markdown](BOM-details.ja.md) ／ [CSV](BOM.csv) ／ [オプション専用BOM](../monitor-option/BOM.ja.md)','',f'為替は既存の2026-09-21参考値{rate:.4f}円/USDで、決済レートではありません。旧価格・仮予算は各明細に残しています。PC・給電・HAT・最終配線等も未計上です。','', '| 部位 | 計上済み円換算 | 小計内割合 |','|---|---:|---:|']
for name,amount in sorted(groups.items(),key=lambda kv:-kv[1]):md.append(f'| {name} | {amount:,.0f}円 | {amount/total*100:.1f}% |')
md+=['','| 部品 | 使用数 | 購入数 | 計上額 |','|---|---:|---:|---:|']
for r in rows:md.append(f'| [{esc(r["部品名"])}](BOM-details.ja.md#item-{r["ID"].lower()}) | {r["使用数"] or "未定"} | {r["購入予定数"] or "未定"} | {(r["明細金額"]+" "+r["通貨"]) if r["明細金額"] else "未計上"} |')
(HERE/'BOM.ja.md').write_text('\n'.join(md)+'\n');print(json.dumps(cost,ensure_ascii=False))
