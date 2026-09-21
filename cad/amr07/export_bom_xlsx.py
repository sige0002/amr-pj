"""Readable Excel views of the generated BOM; requires openpyxl==3.1.5."""
from pathlib import Path
import unicodedata

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.workbook.properties import CalcProperties
from openpyxl.utils import get_column_letter

HERE = Path(__file__).resolve().parent
NAVY, TEAL, LIGHT, AMBER = '18364A', '147D92', 'F0F5F8', 'FFF2CC'


def wrap_supplier(text, width=16):
    """Explicit breaks also work in Calc's hyperlink text rendering."""
    lines, line, used = [], '', 0
    for char in text:
        size = 2 if unicodedata.east_asian_width(char) in ('W', 'F') else 1
        if char == '\n' or used + size > width:
            lines.append(line)
            line, used = '', 0
        if char != '\n':
            line += char
            used += size
    return '\n'.join(lines + [line])


def export(data):
    wb = Workbook()
    wb.remove(wb.active)
    wb.properties.title = 'AMR-01 A6 BOM'
    wb.properties.subject = '平地10kg・追加機械ブレーキなし'
    wb.properties.creator = 'amr-pj'
    wb.calculation = CalcProperties(calcMode='auto')
    table_count = 0

    def sheet(name, title, headers, records, widths, subtitle, row_height=54):
        nonlocal table_count
        ws = wb.create_sheet(name)
        ws.sheet_view.showGridLines = False
        ws.sheet_view.zoomScale = 85
        last = get_column_letter(len(headers))
        ws.merge_cells(f'A1:{last}1')
        ws['A1'] = title
        ws['A1'].font = Font(name='Noto Sans CJK JP', size=17, bold=True, color='FFFFFF')
        ws['A1'].fill = PatternFill('solid', fgColor=NAVY)
        ws['A1'].alignment = Alignment(vertical='center')
        ws.row_dimensions[1].height = 34
        ws.merge_cells(f'A2:{last}2')
        ws['A2'] = subtitle
        ws['A2'].font = Font(name='Noto Sans CJK JP', size=10, color='526575')
        ws['A2'].alignment = Alignment(wrap_text=True, vertical='center')
        ws.row_dimensions[2].height = 34
        for col, header in enumerate(headers, 1):
            c = ws.cell(4, col, header)
            c.fill = PatternFill('solid', fgColor=TEAL)
            c.font = Font(name='Noto Sans CJK JP', size=10, bold=True, color='FFFFFF')
            c.alignment = Alignment(wrap_text=True, vertical='center')
        ws.row_dimensions[4].height = 30
        for rownum, record in enumerate(records, 5):
            for col, value in enumerate(record, 1):
                c = ws.cell(rownum, col, value)
                c.font = Font(name='Noto Sans CJK JP', size=10, color='18364A')
                c.alignment = Alignment(wrap_text=True, vertical='top', indent=1)
                if rownum % 2:
                    c.fill = PatternFill('solid', fgColor=LIGHT)
                if isinstance(value, (float, int)):
                    c.number_format = '#,##0.00;[Red]-#,##0.00;0'
            ws.row_dimensions[rownum].height = row_height
        for i, width in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = width
        end = 4 + len(records)
        table_count += 1
        tab = Table(displayName=f'BOMTable{table_count}', ref=f'A4:{last}{end}')
        tab.tableStyleInfo = TableStyleInfo(name='TableStyleMedium2', showRowStripes=True)
        ws.add_table(tab)
        ws.freeze_panes = 'C5' if len(headers) > 3 else 'A5'
        ws.auto_filter.ref = tab.ref
        ws.print_title_rows = '1:4'
        ws.print_options.horizontalCentered = True
        ws.page_setup.orientation = 'landscape'
        ws.page_setup.paperSize = ws.PAPERSIZE_A3 if len(headers) > 6 else ws.PAPERSIZE_A4
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.print_area = f'A1:{last}{end}'
        ws.page_margins.left = ws.page_margins.right = 0.25
        ws.page_margins.top = ws.page_margins.bottom = 0.35
        ws.oddFooter.center.text = 'AMR-01 A6 | &P / &N'
        return ws

    purchase = data['procurement_rows']
    end = len(purchase) + 4
    overview = [
        ['円の途中小計', f'=SUMIF(\'購入品\'!H5:H{end},"JPY",\'購入品\'!G5:G{end})', 'キャスターをAmazon273円＋既存Prime会員条件の送料0円とする条件。会員ログイン後の最終注文額は未確認。販売記録・仮枠・材料消費を含む。'],
        ['USDの途中小計', f'=SUMIF(\'購入品\'!H5:H{end},"USD",\'購入品\'!G5:G{end})', '金具82.25＋D2上板38.65（各送料込み）。自動見積・手動審査前。'],
        ['完成車総額', '未確定', '電池・主計算機・配線・基板・税・送料等が未選定／未見積。通貨未換算。'],
        ['運用の設計条件', '平坦な屋内・通常積載10kg', '追加機械ブレーキなし。構造検証は荷物15kg、SF2目標。'],
        ['車体重量の推計', data['CAD_mass_estimate']['estimated_base_kg'], '電装枠を含むCAD推計、実測ではない。'],
        ['数量照合', data['physical_CAD_objects_reconciled'], 'CAD物理形状を全件、費用行へ対応付け。予約形状は部品として数えない。'],
        ['小径座金の税訂正', 29, '10枚×29円は税別。税込319円へ修正し、以前の途中小計から29円増。'],
        ['価格の確認範囲', 'タイヤ・キャスター・座金・タイヤ送料を再確認', 'フレームのAmazon価格は再取得できず既存価格。キャスターはAmazon販売発送273円を確認。その他は既存記録・仮枠。'],
        ['使用数と購入数', '300mm材：2本使用／4本購入', '溝ナット50個＝SET付属16＋追加34。購入数未確定は空欄。'],
        ['編集方法', '購入品の口数・単価・金額を編集可能', '金額が空欄の行は未見積。一式仮枠は金額セルへ直接入力。継続変更はJSONへ反映。'],
        ['PLA', '手持ち300gの材料消費評価600円', '新規スプール購入額ではない。実スライス量・モック印刷費は未確定。'],
        ['部品表の範囲', '走行台車＋停止回路の部品候補', '自律移動用センサー・上位計算機一式まで価格確定したBOMではない。'],
        ['D2格子穴上板', 'CNC採用、旧板素材代を置換', '300×300×4、50mmピッチ36穴。支持6ブロック＋PLA小物4個。小物締結材800円は予算枠。'],
        ['参考円換算', data['reference_JPY_conversion']['subtotal_JPY_rounded_to_10'], 'ECB2026-09-21参考換算。決済換算・税・未確定品は別。']]
    ws = sheet('概要', 'AMR-01 / A6　調達BOM', ['項目', '値', '説明'], overview,
               [29, 50, 77], '2026-09-22 | 購入一覧・締結内訳・製作品・未選定品・CAD対応を収録', 42)
    ws['B5'].number_format = '#,##0" 円"'
    ws['B6'].number_format = '0.00" USD"'
    ws['B9'].number_format = '0.000" kg"'
    ws['B10'].number_format = '0" 点"'
    ws['B11'].number_format = '0" 円"'
    for row in range(5, len(overview) + 5):
        ws.cell(row, 2).alignment = Alignment(horizontal='left', vertical='top', wrap_text=True, indent=1)
    for row in (5, 6):
        ws.cell(row, 2).font = Font(name='Noto Sans CJK JP', size=17, bold=True, color=TEAL)
    records = []
    for n, r in enumerate(purchase, 5):
        total = f'=E{n}*F{n}' if r['planned_purchase_lots'] and r['amount'] is not None else r['amount']
        records.append([r['id'], r['name_ja'] + '\n' + r['specification'],
                        f"{r['used_quantity']}{r['quantity_unit']}", r['purchase_unit'],
                        r['planned_purchase_lots'], r['purchase_lot_unit_price'], total, r['currency'],
                        r['price_basis_ja'] + '\n' + r['selection_status'],
                        '参照を開く' if r['source'] else wrap_supplier(r['supplier'] or '未確定'),
                        (r['supplier'] + '\n' if r['source'] and r['supplier'] else '') + r['procurement_note']])
    ws = sheet('購入品', '購入品・材料・送料', ['ID', '品名・仕様', '使用数', '購入予定単位', '口数', '購入単位単価', '明細金額', '通貨', '根拠・選定状況', '出典', '備考'],
               records, [27, 48, 11, 30, 7, 13, 14, 8, 29, 18, 74],
               '明細金額だけを集計。製作品・締結詳細の金額を足さない。空欄＝未見積、0＝確認した無料条件など。', 68)
    for n, r in enumerate(purchase, 5):
        if r['source']:
            ws.cell(n, 10).hyperlink = r['source']
            ws.cell(n, 10).font = Font(name='Noto Sans CJK JP', color='0563C1', underline='single', size=10)
        for col in (5, 6, 7):
            ws.cell(n, col).font = Font(name='Noto Sans CJK JP', color='0563C1' if col in (5, 6) else NAVY, size=10)
        ws.cell(n, 5).number_format = '0'
        ws.cell(n, 7).number_format = '#,##0.00' if r['currency'] == 'USD' else '#,##0'
        if r['amount'] is None or '枠' in r['price_basis_ja']:
            ws.cell(n, 7).fill = PatternFill('solid', fgColor=AMBER)
    validator = DataValidation(type='decimal', operator='greaterThanOrEqual', formula1='0', allow_blank=True)
    validator.errorTitle = '0以上の数値'
    validator.error = '未確定なら空欄にしてください。'
    validator.showErrorMessage = True
    ws.add_data_validation(validator)
    validator.add(f'E5:F{end}')
    sheet('締結部品', '締結部品の数量内訳', ['仕様', '使用数', 'セット付属', '別途必要数', '費用計上先', '備考'],
          [[r['specification'], r['installed_quantity'], r['included_in_sets'], r['additional_needed'], r['budget_ids'], r['note']] for r in data['fasteners']],
          [57, 11, 13, 13, 47, 72], '購入品シートのセット・一式予算の内訳。別途必要数は販売パック購入数ではありません。', 48)
    ws = sheet('製作品', '外注・自加工・3Dプリント部品', ['ID', '部品', '数量', '材質・寸法', '製作方法', '費用計上先', '設計資料', '備考'],
               [[r['id'], r['name'], r['quantity'], r['specification'], r['method'], r['budget_id'], '設計資料', r['note']] for r in data['manufactured_parts']],
               [9, 27, 8, 40, 17, 25, 13, 75], '親行の素材費・加工見積に含む。モーター金具・上板はCNC。残る自加工品の工具・工賃は未計上。', 50)
    for n, r in enumerate(data['manufactured_parts'], 5):
        ws.cell(n, 7).hyperlink = 'https://github.com/sige0002/amr-pj/blob/main/cad/amr07/' + r['drawing']
        ws.cell(n, 7).style = 'Hyperlink'
    sheet('未選定', '未選定品・未見積項目', ['ID', '必要なもの', '必要数量', '仕様の出発点', '残る決定', '段階'],
          [[r['id'], r['name'], r['needed_quantity'], r['specification'], r['decision_needed'], r['phase']] for r in data['unselected']],
          [9, 45, 24, 66, 75, 20], '価格未確定のため完成車総額を出していません。機械ブレーキは不採用なので、この未選定一覧にも含めません。', 60)
    sheet('CAD照合', 'CAD物理形状と費用行の対応', ['CADオブジェクト', '費用ID', 'ラベル', '材料区分', '締結仕様'],
          [[r['object_name'], r['budget_id'], r['label'], r['material'], r['hardware_spec']] for r in data['cad_inventory']],
          [40, 38, 83, 16, 55], '全298形状。1購入品＝複数CAD形状の場合があります。タイヤ付属ねじと電装予約を別購入品として数えていません。', 32)
    wb.save(HERE / 'BOM.xlsx')
