"""D6.9 purchase-pack BOM; reuse the actual recorded quote for identical D3 plate."""
from pathlib import Path
import csv, json, hashlib, math

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
source = BASE / 'direct-hinge'
reader = csv.DictReader((source / 'BOM.csv').open(encoding='utf-8-sig'))
fields = reader.fieldnames
removed_ids = ['HATCH_HINGES', 'HATCH_METAL_ANGLES', 'HATCH_FRAME_M4_NUT',
               'HATCH_FRAME_M4_BOLT', 'HATCH_LOCKS', 'ELEC_CASE_WASHER']
old_rows = list(reader)
rows = [r for r in old_rows if r['ID'] not in removed_ids]
buildability = BASE / 'electrical-buildability'
policy = json.loads((buildability / 'requirements.json').read_text())
withdrawn_ids = policy['withdrawn_BOM_ids']
withdrawn = [r for r in rows if r['ID'] in withdrawn_ids]
assert len(withdrawn) == len(withdrawn_ids)
withdrawn_JPY = sum(float(r['明細金額']) for r in withdrawn)
assert all(r['通貨'] == 'JPY' for r in withdrawn)
with (buildability / 'withdrawn-parts.csv').open('w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fields, lineterminator='\n')
    writer.writeheader(); writer.writerows(withdrawn)
history = ['# 撤回した電装部品の価格履歴', '',
           '2026-09-23、回路製作設備なしの条件により、以下を現行購入BOMから外した。',
           '表の価格・数量は旧候補の記録であり、購入指示ではない。代替品は未計上で、節約額を示さない。', '',
           '[製作条件と確認した候補](README.ja.md) ／ [履歴CSV](withdrawn-parts.csv) ／ [現行BOM](../fixed-deck/BOM.ja.md)', '',
           '| 旧ID | 旧候補 | 旧明細価格 | 外した理由 |', '|---|---|---:|---|']
for r in withdrawn:
    reason = 'はんだ端子。加工済み品／代替型番を未選定' if r['ID'] == 'ELEC_S1' else '未設計の専用回路への実装が前提'
    history.append(f'| {r["ID"]} | {r["仕様・型番"]} | {float(r["明細金額"]):,.0f}円 | {reason} |')
history += ['', f'旧価格合計：{withdrawn_JPY:,.0f}円。価格確認日・URL・購入パックは履歴CSVに保持。', '']
(buildability / 'withdrawn-parts.ja.md').write_text('\n'.join(history))
rows = [r for r in rows if r['ID'] not in withdrawn_ids]
by = {r['ID']: r for r in rows}
v = json.loads((HERE / 'validation.json').read_text())
e3_geometry = json.loads((BASE / 'pico-control/geometry.json').read_text())
observed_path = BASE / 'aluminum-direct-deck/quote-evidence/D3-observed.json'
q = json.loads(observed_path.read_text())
economic = next(x for x in q['records'] if x['speed'] == 'economic')


def quantity(id, use, **kw):
    row = by[id]
    row.update(使用数=str(use), 余剰数=str(int(row['購入予定数'])-use), CAD形状数=str(use), **kw)


quantity('F04', 70, 備考='天板6点固定のHNTT6-6を含む共通70個。購入100個の内数。新規パック追加なし。')
quantity('D3_M6', 50, 備考='天板M6×12を6本復帰。共通使用50本／購入70本。H01別枠4本は従来どおり別予算で二重配分しない。')
quantity('D62_FLOOR_SCREWS', 20, 部品名='床・ケース用M4×16', 備考='床継ぎ目4＋ケース底8＋ケース蓋8＝20本。購入60本の内数。')
quantity('D3_STOP_NUTS', 28, 備考='荷物止め8＋床4＋ケース底8＋蓋8＝28個。20個273円×2。')
quantity('D64_FLOOR_WASHERS', 24, 部品名='床・ケース用M4 OD12×t1座金', 備考='床上下8＋ケース底8＋ケース蓋8＝24枚。20枚430円×2。')
grams = math.ceil(e3_geometry['mass']['total_solid_PLA_kg']*1000)
by['P04'].update(使用数=str(grams), 明細金額=str(2*grams), CAD形状数=str(e3_geometry['PLA_parts']),
                部品名='床・PCカバー・荷物止め・操作ケース',
                **{'仕様・型番': 'E3全16個。非常停止箱・蓋と前方床1枚を変更、Picoケースと蓋を追加。他はD6.9を継承'},
                備考='2円/g、中実CADの材料消費参考。非導電PLA。スライス支持材・失敗・電気・工賃別。')
by['DECK_plate'].update(部品名='固定式格子穴アルミ天板',
                       **{'仕様・型番': '300×300×4 / 6061-T6 / AMR_GridDeck_C45_D3 / qty1'},
                       明細金額=f"{economic['parts_lot_USD']:.2f}", CAD形状数='1',
                       価格根拠='2026-09-21 UTC取得のJLCCNC実自動見積を同一形状へ再使用（今回の再取得なし）',
                       備考='材料、50丸穴（格子36＋M6固定6＋荷物止め8）、4長穴込み。タップ・ヒンジ穴なし。D3見積STEPと今回の組立形状を照合。数量1枚全額、手動審査前。')
by['DECK_CNC_SHIP'].update(部品名='アルミ天板1枚の日本宛送料',
                          **{'仕様・型番': q['shipping_service']}, 明細金額=f"{economic['shipping_USD']:.2f}",
                          価格根拠='2026-09-21 UTC取得のD3天板単独配送表示を再使用',
                          備考='天板1枚の日本・国単位表示。住所別未検証。モーター金具は別配送。税・決済費用別、今回の送料再取得なし。')
replacements = {
    'U01': ('完成済みの電池保護・全負荷低電圧遮断', 'BL1860Bとの保護適合・復帰条件を確認する', '2線アダプターだけでセル・温度保護が成立するとは扱わない。完成済みユニットと配線を選定する。'),
    'U08': ('Pico用2チャンネルRS485完成基板', 'ユーザー提示Amazon B0GKHKCZV3／Pico-2CH-RS485型', '手持ちPico＋本基板を使用。別のUSB–RS485変換器・裸ICは買わない。価格・ピン実装・現物改訂は未確認。'),
    'U09': ('駆動遮断・コイル保護の完成済みユニット', '非常停止による独立遮断、実DC負荷・突入へ適合', '基板実装用リレーと未設計ドライバの組合せを撤回。完成済み品の端子・保護・定格を確認する。'),
    'U10': ('手動再許可・独立監視の完成済みユニット', '故障・復電後の自動再始動防止と通信／制御停止監視', '旧ラッチIC・外部WD ICの個別実装は撤回。必要動作を完成品構成として確認する。'),
    'U11': ('回生吸収・逆流保護の完成済みユニット', 'M0601C_111・電池・遮断構成に適合', '旧比較器・MOSFET・抵抗等の未設計回路を撤回。電圧・吸収エネルギー・発熱を確認する。'),
    'U12': ('電圧・電流・温度監視の完成済みモジュール', '車載監視用、測定レンジと接続方式未選定', '機能重複は選定後に整理。基板の個別実装をユーザーへ要求しない。'),
    'U13': ('端末加工済み電源・信号ハーネス', '線径・線長・両端の端子番号を配線図で確定', '圧着工具の所有を仮定しない。モーター付属線、スイッチ端子、ヒューズ、RS485終端を含める。'),
}
for id, (name, spec, note) in replacements.items():
    by[id].update(部品名=name, **{'仕様・型番': spec}, 備考=note,
                  選定状況='完成品構成へ再選定・未計上')
for id, name, spec, note in [
    ('U21', '制御系の完成済みDC/DC・給電ケーブル', '搭載モジュール決定後に入出力・端子を確定', '旧M78AR05-1の基板実装前提を撤回。給電の二重計上・USB逆送を避ける。'),
    ('U22', '非常停止スイッチ（配線加工不要品）', '押下保持式、実負荷を切れるDC接点、ねじ／適合コネクタ端子', '直接遮断を優先し、定格が合わなければリレー1個を追加。2NCや安全コントローラーは必須にしない。型番未選定、旧CADは配置参考。'),
    ('U23', '必要なハーネス製作・組立検査費', '既製配線で成立しない部分のみ、実見積で比較', '未見積・未発注。PCB製造一般料金を完成配線ユニットの価格に使わない。U13の材料費と重複しない。'),
]:
    row = {field: '' for field in fields}
    row.update(ID=id, 分類='未選定・未計上', 部品名=name, **{'仕様・型番': spec}, 通貨='JPY',
               価格根拠='未見積', 選定状況='完成品構成へ再選定・未計上', 備考=note)
    rows.append(row); by[id] = row
by['ELEC_U1']['備考'] += ' 製作設備なしの条件により、未実装ヘッダーのはんだ付けをユーザーへ要求しない。'
by['ELEC_ARM']['選定状況'] = '初号機では不採用'
by['ELEC_MAIN']['選定状況'] = '全電源操作用として維持、加工済み配線・負荷適合は要確認'
by['ELEC_MAIN']['備考'] = 'Linux終了後の全電源遮断用。モーターのみを切る非常停止とは別機能。旧価格621円を再使用、今回再取得なし。総電流・突入と250型端子の接続を確認。'
by['U15']['備考'] += ' 完成済みモジュールの寸法・配線確定後にCADを再配置する。'
by['E02'].update(部品名='LinuxミニPC–Pico用USBデータケーブル',
                 URL='',
                 **{'仕様・型番': '手持ちPicoのUSB端子とLinuxミニPCに合わせる'},
                 選定状況='500円は既存仮予算、型番未選定', 価格根拠='旧USB線の仮予算を保持、今回の価格取得なし',
                 備考='USB通信とPico/HAT給電用。手持ち／付属線があれば重複購入しない。')
by['U08']['URL']='https://www.amazon.co.jp/dp/B0GKHKCZV3'
by['ELEC_U1']['備考']='手持ちPicoを通信・周期制御に使用、購入0円。型番・ヘッダー有無は回答待ち。ヘッダー未実装なら、はんだ不要の接続方法を確定してから製作する。'
by['ELEC_U1']['選定状況']='手持ち使用、型番・ピン実装状態は未確認'
by['U22'].update(部品名='非常停止スイッチ HW1B-V402R',
                 **{'仕様・型番': 'IDEC／2NC／M3.5ねじ端子／φ40頭／左右モーターを別接点で遮断'},
                 使用数='1',単位='個',購入予定数='1',購入単位='1個',購入口数='1',余剰数='0',購入単位単価='2387',明細金額='2387',CAD形状数='1',
                 価格根拠='2026-09-23 Yahoo ANGEL HAM SHOP JAPAN表示、税込、送料別',選定状況='配置設計に採用、モーター入力突入・実遮断適合は未検証',
                 URL=policy['estop']['price_source'],備考='1接点に左右の電流を合算しない。メーカーDC24V DC-12 10A/DC-13 5Aは試験負荷別で、モーター入力の適合保証ではない。Amazon同型Prime未確認。')
for id,name,amount,specification,note in [
    ('E3_ESTOP_SHIP','非常停止スイッチ送料（住所未照合）','780','Yahoo表示・東京都向け','実住所への送料・Primeではない。送料込み参考3167円。'),
    ('U24','Picoケース固定用M3締結材','','M3×12 8本、M3ナット8個、OD7座金12枚','床固定4点＋蓋4点。使用数確定、購入パック価格は未計上。'),
]:
    row={field:'' for field in fields}
    row.update(ID=id,分類='電装取付',部品名=name,**{'仕様・型番':specification},通貨='JPY',明細金額=amount,
               価格根拠='2026-09-23販売ページ表示' if amount else '未見積',選定状況='計上・配送先確認待ち' if amount else '必要数確定・価格未計上',備考=note)
    if amount:row.update(使用数='1',単位='式',購入予定数='1',購入単位='1配送',購入口数='1',余剰数='0',購入単位単価=amount,URL=policy['estop']['price_source'])
    rows.append(row);by[id]=row
by['U06'].update(部品名='電源着脱・分岐コネクタ', **{'仕様・型番': '電池アダプターと左右モーターの電源配線用'},
                 備考='主電源スイッチの250型端子を含む。付属端子・配線を確認して不足分だけ計上。ヒューズはU07、ケーブルはU13。')
by['U07'].update(**{'仕様・型番': '電源直近のヒューズとホルダー。DC定格・容量・必要数を配線から決定'},
                 備考='旧5回路の構成・数値を引き継がない。線径、分岐、負荷電流・突入と付属ヒューズを確認して必要分だけ選定。')
by['U15'].update(**{'仕様・型番': '最小の通信変換器・非常停止部品の固定と端子絶縁'},
                 備考='既計上PLA床・操作ケースを活用。機種確定後に取付穴を更新。汎用の大きな電装箱を先に追加しない。')
by['U03'].update(部品名='車載LinuxミニPC・記憶媒体・必要な冷却',
                 **{'仕様・型番': 'Linux機。Raspberry Pi 5は候補の一つ、機種・構成は未選定'},
                 選定状況='車載Linux機を使用、機種と価格は未確定',
                 備考='初回から搭載。所有済みとは仮定しない。1階の既存予約場所へ実部品と配線を配置検証する。')
by['U04'].update(部品名='車載LinuxミニPC用の給電部材',
                 **{'仕様・型番': '電池の電圧範囲とPC入力定格を照合。必要な場合のみ完成済みDC/DCを追加'},
                 選定状況='初回必須、型番・価格未確定',
                 備考='非常停止によるモーター遮断とは別分岐。PCの入力電圧・容量・コネクタに合わせて選定。5V系へ固定しない。U21は別の追加機器用で重複させない。',
                 URL='')

# E2: conditional additions and later features are not mandatory unpriced items.
deferral = {
    'ELEC_ARM': ('初回不採用', '専用ARM回路と追加ボタンを設けない。'),
    'U01': ('条件付き', '電池・アダプターの既存保護を確認し、不足があれば追加。未確認のまま不要とは断定しない。'),
    'U09': ('条件付き', '非常停止ボタンのDC接点で直接切れない場合のみリレー1個とソケット／完成品を選定。'),
    'U10': ('初回不採用', '専用再許可回路・独立監視ユニットは初回必須にしない。'),
    'U11': ('条件付き', '減速・遮断時の電源適合性を確認し、必要な場合だけ対策する。旧自作クランプを採用しない。'),
    'U12': ('後工程', '車載の追加監視センサー一式を先に購入しない。'),
    'U14': ('条件付き', '回生抵抗など発熱部品を実際に採用する場合のみ。端子絶縁はU15に含む。'),
    'U19': ('後工程', '最初は手動走行。自律移動に着手する際に選定。'),
    'U21': ('条件付き', 'USB給電で不足する機器やリレーコイルを採用する場合のみ。'),
    'U23': ('条件付き', '既製配線で接続できない部分が判明した場合のみ加工費を調べる。'),
}
assert set(deferral) == set(policy['deferred_BOM_ids'])
deferred = []
for row in rows:
    if row['ID'] not in deferral:
        continue
    stage, reason = deferral[row['ID']]
    deferred.append(dict(row, 選定状況=stage, 備考=reason))
with (buildability / 'deferred-parts.csv').open('w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fields, lineterminator='\n')
    writer.writeheader(); writer.writerows(deferred)
deferred_JPY = sum(float(r['明細金額']) for r in deferred if r['明細金額'])
lines = ['# E3：初回購入の必須から外した部品', '',
         'この表は購入指示ではない。条件付き項目は必要性を確認してから追加する。旧価格は履歴で、今の見積ではない。', '',
         '[最小構成](README.ja.md) ／ [現行BOM](../fixed-deck/BOM.ja.md) ／ [CSV](deferred-parts.csv)', '',
         '| ID | 部品 | 段階 | 理由 |', '|---|---|---|---|']
for r in deferred:
    lines.append(f'| {r["ID"]} | {r["部品名"]} | {r["選定状況"]} | {r["備考"]} |')
lines += ['', f'このうち旧計上価格は計{deferred_JPY:,.0f}円。代替部品の未計上分があるため完成車の節約額ではない。', '']
(buildability / 'deferred-parts.ja.md').write_text('\n'.join(lines))
rows = [r for r in rows if r['ID'] not in deferral]
with (HERE / 'BOM.csv').open('w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fields, lineterminator='\n')
    writer.writeheader(); writer.writerows(rows)
old = json.loads((source / 'cost_summary.json').read_text())
rate = old['FX_reference_JPY_per_USD']
subtotal = {c: sum(float(r['明細金額']) for r in rows if r['通貨'] == c and r['明細金額']) for c in ['JPY', 'USD']}
total = subtotal['JPY'] + subtotal['USD']*rate
quote = dict(source='../aluminum-direct-deck/quote-evidence/D3-observed.json',
             source_sha256=hashlib.sha256(observed_path.read_bytes()).hexdigest(),
             original_observed_at=q['observed_at'], re_queried_this_revision=False,
             plate_lot_USD=economic['parts_lot_USD'], shipping_USD=economic['shipping_USD'],
             total_USD=economic['total_USD'], quantity=1, step_sha256=q['step_sha256'], pdf_sha256=q['pdf_sha256'],
             geometry_equivalence_check='saved_artifact_validation.json', automatic_not_manual=True,
             manual_review_complete=False, order_placed=False)
summary = dict(revision='E3 on D6.9 chassis', date='2026-09-23', subtotal=subtotal,
               FX_reference_JPY_per_USD=rate, FX_date=old['FX_date'],
               FX_basis='Recorded 2026-09-21 reference, not current settlement rate',
               full_running_subtotal_JPY_reference=total,
               difference_from_D68_JPY_reference=total-old['full_running_subtotal_JPY_reference'],
               mechanical_difference_from_D68_JPY_reference=total+withdrawn_JPY+deferred_JPY-3167-old['full_running_subtotal_JPY_reference'],
               withdrawn_electrical_reference_JPY=withdrawn_JPY,
               deferred_electrical_reference_JPY=deferred_JPY, electrical_scope_revision=policy['revision'],
               electrical_withdrawal_is_cost_saving=False,
               removed_purchase_ids=removed_ids+withdrawn_ids+list(deferral), machining_quote=quote,
               electrical_buildability_requirements='../electrical-buildability/requirements.json',
               electrical_buildability_sha256=hashlib.sha256((buildability / 'requirements.json').read_bytes()).hexdigest(),
               unpriced_rows=[r['ID'] for r in rows if not r['明細金額']], complete_purchase_total=False,
               note='E3途中小計。PC・給電・Pico用RS485基板・ヒューズ・配線等未計上。主電源621円復帰、非常停止2387円＋東京向け送料780円。旧部品の除外は完成車の節約額ではない。モーター・USB線は仮予算。Prime未確認。')
(HERE / 'cost_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
print(json.dumps(dict(subtotal=subtotal, total_JPY_reference=total,
                      difference_from_D68=summary['difference_from_D68_JPY_reference'])))
