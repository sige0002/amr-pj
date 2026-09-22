"""Mobile-readable BOM and cost shares from current purchase-line totals.

No new prices or quotes are inferred. USD uses the recorded reference FX.
Unknown costs stay null and are shown separately from the percentage base.
"""
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
import csv
import hashlib
import json

HERE = Path(__file__).resolve().parent
raw = (HERE/'BOM.csv').read_bytes()
rows = list(csv.DictReader(raw.decode('utf-8-sig').splitlines()))
summary = json.loads((HERE/'cost_summary.json').read_text())
rate = Decimal(str(summary['FX_reference_JPY_per_USD']))
validation=json.loads((HERE/'validation.json').read_text())
revision=summary['revision']
vehicle_mass=validation['mass']['estimated_base_kg']
groups = [
    ('電池・充電器・アダプター', ['POWER_KIT','POWER_KIT_SHIP','POWER_ADAPTER','POWER_ADAPTER_SHIP']),
    ('モーター2個', ['D01']),
    ('専用モーター金具2個', ['Q01','S08']),
    ('タイヤ・キャスター', ['D02','C01','P01','S02','S06']),
    ('フレーム・締結材', ['F01','F02','D6_POSTS','F03','F04','P03','H01','MW','D3_M6','D3_STOP_BOLTS','D3_STOP_NUTS','D3_STOP_WASHERS','D62_FLOOR_SCREWS','D62_BEAM_WASHERS']),
    ('アルミ天板', ['DECK_plate','DECK_CNC_SHIP']),
    ('制御・電源保護', ['E02']+[r['ID'] for r in rows if r['ID'].startswith('ELEC_')]),
    ('PLA・ベルト・保護材', ['P04','H02','DECK_cargo_straps','DECK_edge_protection_and_slack_retention','POWER_PADS','POWER_LOW_STRAPS']),
    ('その他送料', ['S03','D3_STRAP_SHIP','S04','S07']),
]
by_id = {r['ID']: r for r in rows}
ids = [i for _, members in groups for i in members]
assert len(ids) == len(set(ids))
assert set(ids) == {r['ID'] for r in rows if not r['ID'].startswith('U')}


def yen(row):
    if row['明細金額'] == '':
        return None
    assert row['通貨'] in ['JPY', 'USD']
    return Decimal(row['明細金額']) * (rate if row['通貨']=='USD' else 1)


def evidence(row):
    if yen(row) is None: return '未計上'
    if row['価格根拠'] in ['予算枠','ユーザー仮枠']: return '仮予算'
    if row['価格根拠'] == '材料消費参考': return '材料消費'
    if '自動見積' in row['価格根拠']: return '自動見積'
    return '価格記録'


def jpy(value):
    return f'{value:,.0f}円'


total = sum(yen(r) for r in rows if yen(r) is not None)
assert abs(float(total)-summary['full_running_subtotal_JPY_reference']) < 1e-7
category_rows = []
for name, members in groups:
    cost = sum((yen(by_id[i]) for i in members if yen(by_id[i]) is not None), Decimal(0))
    category_rows.append(dict(category=name,JPY_reference=float(cost),
                              percent_of_priced_subtotal=float(cost/total*100),
                              source_ids=members,
                              unpriced_ids=[i for i in members if yen(by_id[i]) is None]))
category_rows.sort(key=lambda r: r['JPY_reference'], reverse=True)
assert abs(sum(r['JPY_reference'] for r in category_rows)-float(total)) < 1e-7
states = defaultdict(Decimal)
for row in rows:
    if yen(row) is not None: states[evidence(row)] += yen(row)
unpriced = [r for r in rows if yen(r) is None]
out = dict(revision=summary['revision'], date='2026-09-22',
           BOM_sha256=hashlib.sha256(raw).hexdigest(),
           denominator_JPY_reference=float(total),denominator_scope='Existing priced lines, provisional budgets and PLA consumption; excludes all unpriced items.',
           FX_reference_JPY_per_USD=float(rate),FX_date=summary['FX_date'],
           categories=category_rows,by_price_basis_JPY={k:float(v) for k,v in states.items()},
           unpriced_rows=[dict(id=r['ID'],name=r['部品名'],status=r['選定状況'],cost=None) for r in unpriced],
           purchase_quantities_not_usage_prorating=True,
           incomplete_vehicle_total=True)
(HERE/'BOM-costs.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
with (HERE/'BOM-summary.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f,lineterminator='\n');w.writerow(['部位','円換算参考','途中小計に占める割合%'])
    for c in category_rows:w.writerow([c['category'],round(c['JPY_reference'],2),round(c['percent_of_priced_subtotal'],2)])

lines = [f'# {revision} BOM：費用の内訳と購入リスト', '',
    f'**途中小計 約{jpy(total)} ＋ 未計上分**。通常積載目標10kg、車体推計{vehicle_mass:.3f}kg（10kgは目安）の現行構成。', '',
    '**主計算機・その電源・配線／基板／ケース・追加ねじなどは未計上。LiDARやカメラ等の将来センサーも含まない。** 完成車の総額ではない。', '',
    '## どこに費用がかかるか', '',
    '| 部位 | 金額の目安 | 割合 |', '|---|---:|---:|']
for c in category_rows:
    lines.append(f"| {c['category']} | {jpy(c['JPY_reference'])} | {c['percent_of_priced_subtotal']:.1f}% |")
lines += [f'| **途中小計** | **{jpy(total)}** | **100%** |', '',
    f'割合の分母は計上済み小計。未計上品を0円とは扱わない。円換算は記録済みの1 USD＝{rate:.4f}円（{summary["FX_date"]}参考値）で、現在の決済レートではない。元の小計は{summary["subtotal"]["JPY"]:,.0f}円＋{summary["subtotal"]["USD"]:.2f} USD。行ごとの四捨五入で端数差が出る。', '',
    '電池・モーター金具・天板の欄には、それぞれ記録された送料を含む。共通送料は「その他送料」へ置き、二重計上しない。購入パック全額で集計し、使用数による按分はしていない。', '',
    '## 金額の確かさ', '', '| 根拠 | 計上額 |', '|---|---:|']
for label in ['価格記録','自動見積','仮予算','材料消費']:
    lines.append(f'| {label} | {jpy(states[label])} |')
lines += ['', f'価格記録は既存の販売ページ確認・引継価格。自動見積はJLCCNCの実サイト記録で、未発注・担当者審査前。**モーター14,000円は仮予算**。PLA{by_id["P04"]["明細金額"]}円は材料消費参考で、新規スプールの購入額ではない。', '',
    '## 購入リスト', '',
    '部位を開くと内訳を表示。「使用／購入」は使用数と買う数で、購入予定数が未確定の項目は未定と表示する。購入先は品名のリンク。詳しい仕様・送料条件・根拠は[詳細CSV](BOM.csv)に残す。', '']
short_names = {'D01':'M0601C_111 モーター','Q01':'専用モーター金具 A6-R1',
               'DECK_plate':'格子穴天板 300×300×4mm','F01':'3030フレーム 400mm',
               'F02':'3030フレーム 300mm','F03':'接合金具 HBLFSN6',
               'F04':'溝ナット HNTT6-6','D6_POSTS':'3030支柱 100mm',
               'D02':'タイヤキット DDT-M0601C-TIRE','C01':'キャスター TYG-50',
               'POWER_KIT':'BL1860B電池＋DC18RF充電器','POWER_ADAPTER':'電池アダプター diy-adapter03'}
for c in category_rows:
    lines += [f"<details><summary>{c['category']} — {jpy(c['JPY_reference'])}</summary>", '',
              '| 品目 | 使用／購入 | 金額 | 根拠 |','|---|---|---:|---|']
    for i in c['source_ids']:
        r=by_id[i];name=short_names.get(i,r['部品名'])
        if r['URL']:name=f'[{name}]({r["URL"]})'
        if r['分類']=='送料' or '送料' in r['部品名']:qty='送料1式'
        elif i=='P04':qty='消費'+r['使用数']+'g'
        else:
            use=r['使用数']+r['単位'] if r['使用数'] else '未定'
            purchase=r['購入予定数']+r['単位'] if r['購入予定数'] else '未定'
            qty=use+'／'+purchase
        amount=yen(r)
        price='未計上' if amount is None else jpy(amount)
        if amount is not None and r['通貨']=='USD':price+='（$'+r['明細金額']+'）'
        lines.append(f'| {name} | {qty} | {price} | {evidence(r)} |')
    lines += ['', '</details>', '']
lines += ['**今回の床支持：各板4点、計16点。支持梁の溝ナット4個は購入予定パック内。追加M6×12ねじ4本・大径座金4枚・M4皿ねじ/座金/ナット各4個の価格は未計上。材料消費差額は費用JSONに記載。前回の支柱根元両側補強も維持。**', '',
    '## これから金額が増える項目', '',
    '主計算機の0.5kgは重量の予約であり、購入費の計上ではない。未計上品は次のとおり。', '',
    '| 未計上品 | 状態 |','|---|---|']
for r in unpriced:
    lines.append(f"| {r['部品名']} | {r['選定状況']} |")
lines += ['', '## 見直すと効果の大きい費用', '',
    '- 電池・充電器・アダプター：約23,380円。未所有のため充電器も含む。',
    '- 専用モーター金具2個：約12,935円（送料込みの実自動見積）。形状や加工条件を変更する場合は実見積を取り直す。',
    '- タイヤキット2個：9,240円。Taobaoのモーターに同じキットが付くと確認できた場合のみ、別購入を外せる。',
    '- 溝ナット100個：5,112円、使用78個。20個の接合金具本体1,834円より大きい。安価な互換品へ置換する場合は寸法・締結条件を照合する。', '',
    '[CADと設計の説明](README.ja.md)／[重量と積載](PAYLOAD_REVIEW.ja.md)／[費用集計CSV](BOM-summary.csv)／[全明細CSV](BOM.csv)／[計算値JSON](BOM-costs.json)', '']
(HERE/'BOM.ja.md').write_text('\n'.join(lines))
print(json.dumps(dict(total_JPY=float(total),categories=category_rows,price_basis=out['by_price_basis_JPY'],unpriced_count=len(unpriced)),ensure_ascii=False))
