"""Compact mobile-readable overview and complete Markdown from the same CSV."""
from pathlib import Path
import csv,json,hashlib
HERE=Path(__file__).resolve().parent
rows=list(csv.DictReader((HERE/'BOM.csv').open(encoding='utf-8-sig')));by={r['ID']:r for r in rows};c=json.loads((HERE/'cost_summary.json').read_text());rate=c['FX_reference_JPY_per_USD'];total=c['full_running_subtotal_JPY_reference']
def yen(r):return float(r['明細金額'])*(rate if r['通貨']=='USD' else 1) if r['明細金額'] else None
groups=[('電池・充電器・アダプター',['POWER_KIT','POWER_KIT_SHIP','POWER_ADAPTER','POWER_ADAPTER_SHIP']),('モーター',['D01']),('モーター専用金具',['Q01','S08']),('タイヤ・キャスター',['D02','C01','P01','S02','S06']),('天板（固定ボルトは共通締結材）',['DECK_plate','DECK_CNC_SHIP']),('操作部・USB線（電装主要部は未計上）',['E02','U08','U22','U24','E3_ESTOP_SHIP']+[x['ID'] for x in rows if x['ID'].startswith('ELEC_')]),('PLA・ベルト',['P04','H02','DECK_cargo_straps','DECK_edge_protection_and_slack_retention','POWER_PADS','POWER_LOW_STRAPS'])]
used={x for _,ids in groups for x in ids};groups.append(('フレーム・締結材・共通送料',[r['ID'] for r in rows if r['ID'] not in used and not r['ID'].startswith('U')]))
cat=[dict(category=name,JPY_reference=sum(yen(by[x]) or 0 for x in ids),source_ids=ids) for name,ids in groups];cat.sort(key=lambda x:x['JPY_reference'],reverse=True)
assert abs(sum(x['JPY_reference'] for x in cat)-total)<1e-6
for x in cat:x['percent_of_priced_subtotal']=100*x['JPY_reference']/total
lines=['# E3 BOM（Pico＋RS485基板・直接非常停止）','',
       '**通信は手持ちPico＋ユーザー提示RS485基板。非常停止はHW1B-V402Rの左右別接点。実配線・電源適合は確認待ちです。** [最小構成](../electrical-buildability/README.ja.md)。','',
       f'**途中小計 {total:,.0f}円相当＋未計上分**。原通貨：{c["subtotal"]["JPY"]:,.0f}円＋{c["subtotal"]["USD"]:.2f} USD。','',
       '[全明細Markdown](BOM-details.ja.md) ／ [CSV](BOM.csv) ／ [加工見積の証拠](MACHINING_QUOTE.ja.md)','',
       f'旧専用回路部品とはんだ端子の非常停止、計{c["withdrawn_electrical_reference_JPY"]:,.0f}円を[価格履歴](../electrical-buildability/withdrawn-parts.ja.md)へ移しました。通信基板・最終ハーネス等が未計上なので、この減額は節約ではありません。割合も完成車の費用割合ではありません。','',
       f'E3でARM計{c["deferred_electrical_reference_JPY"]:,.0f}円と、追加監視等を初回必須から外しました。全電源用の主スイッチ621円は復帰しています。[条件付き・後工程の部品](../electrical-buildability/deferred-parts.ja.md)は下の必須未計上品へ混ぜていません。','',
       f'円換算は記録済みの2026-09-21参考値1 USD＝{rate:.4f}円。現在の決済額ではありません。購入パック全額を計上し、余りを按分していません。車載LinuxミニPC・給電部材・Pico用RS485基板・ヒューズ・配線などは未計上、モーター14,000円とUSB線500円は仮予算、PLAは材料消費の参考です。計算機はLinuxミニPCを想定し、機種は固定しません。非常停止は2,387円＋東京向け送料780円を計上、基板のAmazon表示価格は未取得です。','',
       f'機械部分はヒンジ案D6.8から約{-c["mechanical_difference_from_D68_JPY_reference"]:,.0f}円減。ヒンジ・専用L金具・蝶ボルト等の購入を削除。M6固定6点は既計上パックの余りを使い、新規パック購入なし。天板は同一形状のD3実自動見積を再使用。E3のPLA増加を反映し、既存価格は再取得していません。','',
       '| 部位 | 円換算参考 | 計上済み分の割合 |','|---|---:|---:|']
for x in cat:lines.append(f'| {x["category"]} | {x["JPY_reference"]:,.0f}円 | {x["percent_of_priced_subtotal"]:.1f}% |')
lines+=['','Amazonを優先。Prime会員としての最終配送条件は未確認です。既存価格は確認日と仮枠の区別を各明細に残しています。6点固定はM6×12・HNTT6-6を各6個使い、両側から荷台を保持します。','']
for g in cat:
 lines += [f'## {g["category"]}','','| 部品 | 使用／購入 | 原通貨金額 |','|---|---|---:|']
 for id in g['source_ids']:
  r=by[id];amount=r['明細金額']+' '+r['通貨'] if r['明細金額'] else '未計上';name=f'[{r["部品名"]}](BOM-details.ja.md#item-{id.lower()})'
  lines.append(f'| {name} | {r["使用数"] or "未定"}／{r["購入予定数"] or "未定"} {r["単位"]} | {amount} |')
 lines.append('')
lines+=['## 未計上品','','| 部品 | 状態 |','|---|---|']
for r in rows:
 if not r['明細金額']:lines.append(f'| {r["部品名"]} | {r["選定状況"]} |')
lines+=['','[E3設計と組立手順](../pico-control/README.ja.md) ／ [重量・強度の比較計算](PAYLOAD_REVIEW.ja.md)','']
(HERE/'BOM.ja.md').write_text('\n'.join(lines))
lines=['# E3 BOM 全明細（Pico＋RS485基板・直接非常停止）','',
       '**初回の最小構成を対象とし、部品型番と配線は選定中です。** [最小構成と対象外の部品](../electrical-buildability/README.ja.md)。','',
       '[概要・費用割合](BOM.ja.md) ／ [CSV](BOM.csv)','']
for r in rows:
 lines += [f'<a id="item-{r["ID"].lower()}"></a>',f'## {r["ID"]}：{r["部品名"]}','','| 項目 | 内容 |','|---|---|']
 for k,val in r.items():
  if val:
   val=val.replace('|','／').replace('\n','<br>')
   if k=='URL':val=f'[購入先・見積ページ]({val})'
   lines.append(f'| {k} | {val} |')
 lines.append('')
(HERE/'BOM-details.ja.md').write_text('\n'.join(lines))
(HERE/'BOM-costs.json').write_text(json.dumps(dict(revision='D6.9',BOM_sha256=hashlib.sha256((HERE/'BOM.csv').read_bytes()).hexdigest(),denominator_JPY_reference=total,categories=cat,complete_purchase_total=False),ensure_ascii=False,indent=2)+'\n')
with (HERE/'BOM-summary.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f,lineterminator="\n");w.writerow(['部位','円換算参考','途中小計割合%']);w.writerows([[x['category'],round(x['JPY_reference'],2),round(x['percent_of_priced_subtotal'],2)] for x in cat])
print('BOM CSV/Markdown share',len(rows),'rows')
