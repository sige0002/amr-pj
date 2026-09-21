#!/usr/bin/env python3
"""Build a procurement BOM from the cost ledger and the native CAD inventory.

Standard library for JSON/CSV/Markdown; --xlsx additionally needs openpyxl 3.1.5.
No price lookup, CAD mutation, purchase or estimate submission is performed here.
"""
import argparse
from collections import Counter, defaultdict
import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

HERE = Path(__file__).resolve().parent
CATEGORIES = ['フレーム', '駆動・支持', '荷台', '電池・PLA', '締結材', '電装候補', '送料']


def read_json(name):
    return json.loads((HERE / name).read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_write(name, rows, fields=None):
    with (HERE / name).open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=fields or list(rows[0]), lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def budget_for(name):
    if name.startswith(('Bracket_', 'JointA_', 'JointB_', 'SlotNut_Joint')):
        return 'F03'
    if name.startswith('SlotNut_CargoDeck'):
        return 'DECK_fasteners_and_extra_slotnuts'
    if name.startswith('SlotNut_'):
        return 'F04'
    if name.startswith('Rail400_'):
        return 'F01'
    if name.startswith('Cross300_'):
        return 'F02'
    if name.startswith('Gusset_'):
        return 'P03'
    if name.startswith('CustomMotorMount'):
        return 'Q01'
    if name.startswith('M0601Motor'):
        return 'D01'
    if name.startswith(('TireL', 'TireR', 'TireCover')):
        return 'D02'
    if name == 'CasterAdapter':
        return 'P01'
    if name in ('CasterTop', 'SwivelRace', 'CasterFork', 'CasterTire', 'CasterCore'):
        return 'C01'
    if name in ('BatteryCradlePLA', 'ElectronicsTrayPLA', 'FrontElectronicsTrayPLA'):
        return 'P04'
    if name.startswith('MotorSeatWasher_'):
        return 'MW'
    if name == 'CargoDeckPlate':
        return 'DECK_plate'
    if name.startswith(('CargoDeckSupport', 'CargoStopX', 'CargoStopY')):
        return 'DECK_square_bar'
    if name.startswith(('CargoDeck', 'CargoStop')):
        return 'DECK_fasteners_and_extra_slotnuts'
    if name.startswith(('MotorFaceBolt_', 'MountFrameBolt_', 'GussetBolt_', 'CasterFrameBolt_',
                        'CasterBolt_', 'Nut_CasterBolt_', 'CradleBolt_', 'ElectronicsBolt_',
                        'FrontDeckBolt_', 'Washer_', 'LargeWasher_')):
        return 'H01'
    raise AssertionError('Unmapped CAD object: ' + name)


def cad_inventory():
    with zipfile.ZipFile(HERE / 'AMR01_M0601C_A6.FCStd') as z:
        root = ET.fromstring(z.read('Document.xml'))
    types = {o.get('name'): o.get('type') for o in root.findall('./Objects/Object')}
    rows = []
    for o in root.findall('./ObjectData/Object'):
        props = {}
        for p in o.findall('./Properties/Property'):
            child = next(iter(p), None)
            if child is not None:
                props[p.get('name')] = child.get('value', '')
        name = o.get('name')
        if types[name] != 'PartDesign::Feature' or props.get('MaterialBasis') == 'reference':
            continue
        assert props.get('MaterialBasis')
        spec = props.get('HardwareSpec', '')
        if not spec and name.startswith('LargeWasher_'):
            spec = 'M6 large washer OD18 ID6.6 t1.6'
        elif not spec and name.startswith('Washer_'):
            spec = 'M6 washer OD13 ID6.6 t1.6'
        rows.append({'object_name': name, 'budget_id': budget_for(name),
                     'label': props.get('Label', ''), 'material': props['MaterialBasis'],
                     'hardware_spec': spec, 'note': props.get('ModelNote', '')})
    assert len(rows) == read_json('assembly_validation.json')['physical_parts'] == 222
    assert len({r['object_name'] for r in rows}) == len(rows)
    expected = {'F01': 4, 'F02': 2, 'F03': 40, 'F04': 28, 'P03': 4, 'Q01': 2,
                'D01': 2, 'D02': 4, 'P01': 1, 'C01': 5, 'P04': 3, 'MW': 6,
                'DECK_plate': 1, 'DECK_square_bar': 6,
                'DECK_fasteners_and_extra_slotnuts': 48, 'H01': 66}
    assert dict(Counter(r['budget_id'] for r in rows)) == expected
    return rows


def fasteners(inventory):
    grouped = defaultdict(list)
    for row in inventory:
        if row['hardware_spec']:
            grouped[row['hardware_spec']].append(row)
    result = []
    for spec, objects in sorted(grouped.items()):
        included = sum(o['budget_id'] == 'F03' for o in objects)
        ids = sorted({o['budget_id'] for o in objects})
        note = '価格は親行に含む。販売パック未確認。'
        if spec == 'HNTT6-6 slot nut':
            note = '50個＝接合SET16＋基礎追加28＋荷台6。追加購入は合計34個。'
        elif spec == 'M2.5x12 socket screw':
            note = 'WILCO FC-2512（12.9）候補。タイヤキットの付属ねじとは別。'
        elif spec == '2.7x5x0.5 steel plain washer':
            note = 'FW-2505-05EBを10枚購入予定・6枚使用・4枚余り。'
        elif spec == 'M6 JIS B1256 grade A washer 12x6.4x1.6':
            note = '荷台M6ボルト1本につき2枚。厚さ選別用の予備は未定。'
        elif spec == 'M6x30 socket screw':
            note = '荷台用。組付け時の突出量7.5〜8.0mmと溝底隙間を実測する。'
        result.append({'specification': spec, 'installed_quantity': len(objects),
                       'included_in_sets': included, 'additional_needed': len(objects) - included,
                       'budget_ids': ', '.join(ids), 'note': note,
                       'cad_object_names': ';'.join(o['object_name'] for o in objects)})
    assert sum(r['installed_quantity'] for r in result) == 180
    result.append({'specification': 'タイヤキット付属ねじ（寸法未公表）',
                   'installed_quantity': 6, 'included_in_sets': 6, 'additional_needed': 0,
                   'budget_ids': 'D02', 'note': '各キット3本×2。CADには個別形状なし。別購入しない。',
                   'cad_object_names': ''})
    return result


def manufacture():
    # Cost references are parents, not additional purchases.
    rows = [
        ('M01', '専用モーター金具', 2, 'A6061-T6／90×30×34mm', 'CNC外注', 'Q01', 'M0601C_mount_A6_R1.step', '左右同形2個、図面PDF同送。75.02USD/2個の自動見積。'),
        ('M02', 'キャスター取付板', 1, 'A5052／80×170×4mm', '自加工', 'P01', 'AMR01_M0601C_A6.FCStd', '材料費のみ。切断・穴加工・面取り。'),
        ('M03', 'コーナーガセット', 4, 'A5052／直角二辺60mm・t3', '自加工', 'P03', 'AMR01_M0601C_A6.FCStd', '150角素材から4枚。加工図はCADから作成が必要。'),
        ('M04', '荷台板', 1, 'A5052／300×300×4mm', '自加工', 'DECK_plate', 'DECK_REVIEW.ja.md', '14丸穴＋30×6長穴4か所。'),
        ('M05', '荷台支持棒', 2, 'アルミ／15×15×300mm', '自加工', 'DECK_square_bar', 'DECK_REVIEW.ja.md', '支持棒2本＋ストッパ4個を同じ995mm材1本から製作。'),
        ('M06', '荷物ストッパ', 4, 'アルミ／15×15×50mm', '自加工', 'DECK_square_bar', 'DECK_REVIEW.ja.md', '支持棒と同じ材料行。素材代を二重計上しない。'),
        ('M07', '電池クレードル', 1, 'PLA／130×160×37mm', 'P1Sで印刷', 'P04', 'AMR01_M0601C_A6.FCStd', '電池型式未定。スライス・印刷条件・実電池の適合未確認。'),
        ('M08', '後部電装トレイ', 1, 'PLA／85×180×4.4mm', 'P1Sで印刷', 'P04', 'AMR01_M0601C_A6.FCStd', '現CADの部品。新電装用ケース・固定具は未選定表で別管理。'),
        ('M09', '前部電装トレイ', 1, 'PLA／145×170×4.4mm', 'P1Sで印刷', 'P04', 'AMR01_M0601C_A6.FCStd', 'PLA消費材料費は3部品まとめてP04。')]
    fields = ['id', 'name', 'quantity', 'specification', 'method', 'budget_id', 'drawing', 'note']
    return [dict(zip(fields, row)) for row in rows]


def price_label(kind):
    if 'allowance' in kind:
        return 'ユーザー仮枠' if kind == 'user_allowance' else '予算枠'
    if kind == 'vendor_automatic_quote':
        return '実サイト自動見積'
    if kind == 'quote_pending':
        return '未見積'
    if kind == 'manufacturer_catalog_reference':
        return 'カタログ参考'
    if 'carried' in kind:
        return '過去価格の引継ぎ'
    return '販売表示・条件付き'


def build():
    ledger, inputs = read_json('bom.json'), read_json('bom_inputs.json')
    assert {r['id'] for r in ledger['items']} == set(inputs['items'])
    inventory = cad_inventory()
    cad_counts = Counter(r['budget_id'] for r in inventory)
    rows = []
    for item in ledger['items']:
        r = dict(item, **inputs['items'][item['id']])
        r['price_basis_ja'] = price_label(r['price_kind'])
        lots, qty = r['planned_purchase_lots'], r['planned_purchase_quantity']
        r['purchase_lot_unit_price'] = float(Decimal(str(r['amount'])) / lots) if lots and r['amount'] is not None else None
        r['surplus_quantity'] = qty - r['used_quantity'] if qty is not None and qty >= r['used_quantity'] else None
        r['cad_physical_object_count'] = cad_counts[r['id']]
        rows.append(r)
    rows.sort(key=lambda r: CATEGORIES.index(r['category']))
    total = lambda currency: sum(Decimal(str(r['amount'])) for r in rows if r['currency'] == currency and r['amount'] is not None)
    assert total('JPY') == Decimal('54189') == Decimal(str(ledger['priced_and_allowance_subtotal_JPY']))
    assert total('USD') == Decimal('82.25') == Decimal(str(ledger['observed_automatic_quote_subtotal_USD']))
    category_totals = {cat: {cur: float(sum(Decimal(str(r['amount'])) for r in rows if r['category'] == cat and r['currency'] == cur and r['amount'] is not None)) for cur in ('JPY', 'USD')} for cat in CATEGORIES}
    data = {'design': ledger['design'], 'date': inputs['date'], 'scope': inputs['scope'],
            'source_hashes': {n: sha(HERE / n) for n in ['bom.json', 'bom_inputs.json', 'bom_price_checks.json', 'AMR01_M0601C_A6.FCStd', 'requirements.json']},
            'procurement_rows': rows, 'fasteners': fasteners(inventory), 'manufactured_parts': manufacture(),
            'unselected': inputs['unselected'], 'cad_inventory': inventory, 'category_totals': category_totals,
            'partial_subtotals': {'JPY': float(total('JPY')), 'USD': float(total('USD'))},
            'completed_vehicle_total': None, 'physical_CAD_objects_reconciled': len(inventory),
            'added_mechanical_brake': 'excluded_by_user', 'ordered': False,
            'price_note': '価格の再確認範囲はbom_price_checks.json。未見積額は0円にせず空欄。PLA消費評価と仮枠を含む途中小計。'}
    (HERE / 'procurement_bom.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    csv_write('BOM.csv', [procurement_display(r) for r in rows])
    csv_write('fasteners.csv', data['fasteners'])
    csv_write('manufactured_parts.csv', data['manufactured_parts'])
    csv_write('BOM_CAD_MAP.csv', inventory)
    write_markdown(data)
    return data


def procurement_display(r):
    return {'ID': r['id'], '分類': r['category'], '部品名': r['name_ja'], '仕様・型番': r['specification'],
            '使用数': r['used_quantity'], '単位': r['quantity_unit'], '購入予定数': r['planned_purchase_quantity'],
            '購入単位': r['purchase_unit'], '購入口数': r['planned_purchase_lots'], '余剰数': r['surplus_quantity'],
            '購入単位単価': r['purchase_lot_unit_price'], '明細金額': r['amount'], '通貨': r['currency'],
            '価格根拠': r['price_basis_ja'], '選定状況': r['selection_status'], '購入先': r['supplier'],
            'URL': r['source'], 'CAD形状数': r['cad_physical_object_count'], '備考': r['procurement_note']}


def amount(value, currency='JPY'):
    return '未見積' if value is None else (f'{value:,.0f}円' if currency == 'JPY' else f'{value:,.2f} USD')


def cell(value):
    return str(value if value is not None else '未確定').replace('|', '\\|').replace('\n', '<br>')


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---'] * len(headers)) + ' |'] + ['| ' + ' | '.join(cell(x) for x in row) + ' |' for row in rows])


def write_markdown(d):
    lines = ['# A6 BOM — 平地10kg・追加機械ブレーキなし', '',
             '2026-09-21更新。**途中小計54,189円＋82.25 USD＋未確定分**。キャスターをAmazon273円＋既存Prime会員条件の送料0円で計上した条件付き金額です。車体の完成価格ではありません。購入・材料消費・仮枠を含み、通貨を換算せず集計しています。', '',
             '[Excel](BOM.xlsx) / [購入一覧CSV](BOM.csv) / [締結部品CSV](fasteners.csv) / [製作品CSV](manufactured_parts.csv)', '',
             'CADの物理形状222点を各費用行へ照合しました。完成キャスターやタイヤキットは、CAD形状数ではなく完成品の購入数で計上します。電装の半透明予約形状は購入品に数えていません。', '',
             'フレーム300mmは2本使用・4本組1セット購入。溝ナットは合計50個＝接合セット付属16個＋別購入34個です。未確定の販売パックを架空の「1セット」として確定していません。', '',
             '小径座金は10枚以上の単価29円が**税別**だったため、10枚税込319円へ訂正しました。旧小計との差は29円です。10枚は数量割引の選択で、最小注文数ではありません。[WILCOの価格表](https://wilco.jp/products/F/FW-EB.html)', '',
             'タイヤ・キャスター・座金・タイヤ送料条件を今回再確認しました。フレームのAmazon価格は再取得できず、既存価格を参考値として引き継いでいます。その他の価格も全行再調査ではなく、既存調査・見積・仮枠です。[確認記録](bom_price_checks.json)', '',
             'キャスターは取付寸法を照合したTRUSCO TYG-50に変更し、Amazon.co.jp販売・発送273円＋既存Prime会員条件の送料0円を第一候補とします。直前の498円から225円減。会員ログイン後の最終注文額は未確認。コーナン店舗受取283円＋送料0円も代替経路として確認しました。[購入経路と条件](CASTER_PROCUREMENT.ja.md)。[格子穴アルミ板のCNC比較見積](aluminum-grid-quote/README.ja.md)は代替案として別記し、現行の板素材代へ重複加算していません。', '',
             '## 分類別小計', '', table(['分類', '円', 'USD'], [[cat, amount(v['JPY']), amount(v['USD'], 'USD')] for cat, v in d['category_totals'].items()]), '',
             '金額空欄・未見積の項目は小計に含みません。未選定品は末尾にまとめています。各行の購入予定は実発注・在庫確保を意味しません。']
    for cat in CATEGORIES:
        lines += ['', '## ' + cat, '']
        records = []
        for r in d['procurement_rows']:
            if r['category'] != cat:
                continue
            source = f"[参照]({r['source']})" if r['source'] else '未確定'
            records.append([r['id'], r['name_ja'] + ('<br>' + r['specification'] if r['specification'] else ''),
                            f"{r['used_quantity']}{r['quantity_unit']}", r['purchase_unit'],
                            amount(r['amount'], r['currency']), r['price_basis_ja'], source])
        lines.append(table(['ID', '品名・仕様', '使用数', '購入予定単位', '明細金額', '価格根拠', '購入先・仕様'], records))
        if cat == 'フレーム':
            lines += ['', 'HBLFSN6-SET/HNTT6-6のリンクは仕様参照です。個人購入できる販売経路・販売単位・着荷額はまだ確定していません。']
        if cat == '電池・PLA':
            lines += ['', 'PLAは手持ち材料300gを使う仮定で、600円は消費材料の評価額です。新規スプール代ではありません。電池本体・充電器は未選定表にあります。']
    lines += ['', '## 締結部品の数量明細', '', '以下は上のセット・一式予算の内訳です。金額を追加加算しません。荷台用M6平座金と基礎部用の座金は寸法が異なるため別行です。', '',
              table(['仕様', '使用数', 'セット付属', '別途必要数', '計上先'], [[r['specification'], r['installed_quantity'], r['included_in_sets'], r['additional_needed'], r['budget_ids']] for r in d['fasteners']]), '',
              'M6×12は36本のうち16本が接合SET付属、追加20本です。タイヤ付属ねじ6本は寸法未公表・CAD個別形状なしで、モーター固定用M2.5×12の6本とは別です。締結材の販売パック・強度区分・厚さ選別は未確定部分が残ります。', '',
              '## 製作品', '', '素材の購入費は親の費用行に含みます。専用モーター金具以外は自加工前提で、工具・工賃や外注完成価格は未計上です。', '',
              table(['部品', '数量', '材質・寸法', '製作', '材料・費用行', '設計資料'], [[r['name'], r['quantity'], r['specification'], r['method'], r['budget_id'], f"[資料]({r['drawing']})"] for r in d['manufactured_parts']]), '',
              '角棒は995mmを1本購入し、300mm×2本と50mm×4個へ切断します。必要完成長800mm、切りしろ18mmの想定です。PLA3部品はP1Sの造形範囲内ですが、実スライスは未実施です。', '',
              '## 未選定・未見積', '',
              table(['ID', '必要なもの', '数量', '残る決定', '段階'], [[r['id'], r['name'], r['needed_quantity'], r['decision_needed'], r['phase']] for r in d['unselected']]), '',
              '追加機械ブレーキ、旧USB-RS485B、既製の背の高いモーターブラケットは現行購入対象に含みません。通常の減速・停止用のモーター制御と回生対策は電装候補へ含めています。', '',
              '## データと更新', '',
              '[数量・購入条件の入力](bom_inputs.json)、[費用台帳](bom.json)、[生成BOM JSON](procurement_bom.json)、[CAD対応表](BOM_CAD_MAP.csv)。CAD形状・金具見積STEP/PDFはこのBOM作成では変更していません。', '',
              '```sh', 'python3 cad/amr07/record_cost.py', 'python3 cad/amr07/build_bom.py', '# Excelも更新する場合（openpyxl 3.1.5）', 'python3 cad/amr07/build_bom.py --xlsx', '```', '',
              'Excel・CSVは生成物です。数量・購入条件はbom_inputs.json、費用はrecord_cost.pyとその参照元へ変更を反映してから再生成してください。bom.jsonはrecord_cost.pyで上書きされます。Excelの金額空欄は未見積で、概要の合計は既知金額だけの途中小計です。', '']
    (HERE / 'BOM.ja.md').write_text('\n'.join(lines))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--xlsx', action='store_true')
    args = parser.parse_args()
    data = build()
    if args.xlsx:
        from export_bom_xlsx import export
        export(data)
    print(json.dumps({'procurement_rows': len(data['procurement_rows']), 'fastener_rows': len(data['fasteners']),
                      'manufactured_rows': len(data['manufactured_parts']), 'unselected_rows': len(data['unselected']),
                      'CAD_objects': len(data['cad_inventory']), 'partial_subtotals': data['partial_subtotals']}, ensure_ascii=False))
