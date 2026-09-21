"""Dimensioned quotation drawings from the same geometry manifest."""
from pathlib import Path
import hashlib
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3, landscape

HERE = Path(__file__).resolve().parent
rows = json.loads((HERE / 'geometry.json').read_text())
for row in rows:
    path = HERE / (row['name'] + '.pdf')
    c = canvas.Canvas(str(path), pagesize=landscape(A3))
    c.setTitle(row['name'] + ' | QUOTATION ONLY')
    c.setFont('Helvetica-Bold', 18)
    c.drawString(35, 805, row['name'] + ' - GRID DECK / QUOTATION ONLY')
    c.setFont('Helvetica', 10)
    c.drawString(35, 785, 'Revision D2 | 2026-09-22 | All dimensions in mm | Quantity 1 | Not released for fabrication or loaded use')
    scale, ox, oy = 1.8, 345, 440

    def xy(x, y):
        return ox + x*scale, oy + y*scale

    def line(x1, y1, x2, y2):
        c.line(*xy(x1, y1), *xy(x2, y2))

    c.setLineWidth(.8)
    c.rect(*xy(-150, -150), 300*scale, 300*scale)
    for x in row['grid_coordinates_from_center_mm']:
        for y in row['grid_coordinates_from_center_mm']:
            c.circle(*xy(x, y), row['grid_modeled_bore_mm']*scale/2)
            if row['tag'] == 'T4':
                c.circle(*xy(x, y), 2*scale)
    for x, y in row['existing_frame_holes']:
        c.circle(*xy(x, y), 3.3*scale)
    for x, y in row['existing_stop_holes']:
        c.circle(*xy(x, y), 2.25*scale)
    for slot in row['existing_slots']:
        x, y = slot['center_xy_mm']
        dx, dy = (30, 6) if slot['long_axis'] == 'x' else (6, 30)
        c.roundRect(*xy(x-dx/2, y-dy/2), dx*scale, dy*scale, 3*scale)
    c.setDash(5, 3)
    line(-158, 0, 158, 0); line(0, -158, 0, 158)
    c.setDash()
    c.setFont('Helvetica', 10)
    c.drawString(*xy(4, 4), '(0,0)')
    c.drawString(*xy(152, 4), '+X')
    c.drawString(*xy(4, 154), '+Y')
    # Overall dimensions, corner-referenced pitch and edge distance.
    line(-150, 154, -150, 173); line(150, 154, 150, 173)
    line(-150, 169, 150, 169)
    for x in (-150, 150): line(x-2, 167, x+2, 171)
    c.drawCentredString(*xy(0, 172), '300')
    line(-154, -150, -173, -150); line(-154, 150, -173, 150)
    line(-169, -150, -169, 150)
    for y in (-150, 150): line(-171, y-2, -167, y+2)
    c.saveState(); c.translate(*xy(-173, 0)); c.rotate(90)
    c.drawCentredString(0, 0, '300'); c.restoreState()
    c.drawString(75, 140, 'TOP VIEW | Origin at plate centre | Grid edge offset 25, pitch 50 (both axes)')
    c.rect(75, 105, 300*scale, 4*scale)
    c.drawString(75, 86, 'SIDE VIEW | Thickness 4 +/-0.10 | All holes/slots through')

    y = 744
    def note(text, bold=False, gap=18):
        global y
        c.setFont('Helvetica-Bold' if bold else 'Helvetica', 10)
        c.drawString(666, y, text)
        y -= gap

    note('MATERIAL / FINISH', True)
    note('Aluminum 6061-T6 (JLCCNC Aluminum 6061 selection).')
    note('Require Rp0.2 >=240 MPa; confirm material lot / temper.')
    note('As machined; no blasting, anodizing or cosmetic finish.')
    note('No assembly or inserts. Remove burrs on both faces.')
    note('Edge break <=0.2; preserve nominal hole/slot sizes.')
    note('Plate flatness <=0.5 over 300. Protect flatness in shipment.')
    y -= 12
    note('HOLE SCHEDULE - ALL CENTRES FROM (0,0)', True)
    note('GRID: 36 locations, full Cartesian product of:')
    note('X = -125, -75, -25, 25, 75, 125')
    note('Y = -125, -75, -25, 25, 75, 125')
    if row['tag'] == 'C45':
        note('36 x D4.5 +0.2/0 THROUGH. NO THREADS.', True)
    else:
        note('36 x M4x0.7-6H THROUGH, full available depth.', True)
        note('STEP shows D3.3 pilot bores; finished threads per PDF.')
        note('Thread all 36 grid bores. Remaining 14 holes unthreaded.')
    y -= 8
    note('FRAME: 6 x D6.6 +0.2/0 THROUGH')
    note('X = -105, 0, 105; Y = -135, 135 (all combinations)')
    y -= 8
    note('STOPS: 8 x D4.5 +0.2/0 THROUGH, unthreaded')
    note('(X,Y) = (+/-109.5, +/-19) and (+/-19, +/-109.5)')
    y -= 8
    note('STRAPS: 4 x obround slots 30 overall x 6 wide, R3')
    note('Centres (+/-120,0), long axis Y; (0,+/-120), long axis X')
    y -= 12
    note('TOLERANCES / MODEL PRIORITY', True)
    note('Hole and slot centre coordinates +/-0.10 from origin.')
    note('Slot width 6 +0.2/0; length 30 +/-0.2.')
    note('Other linear/angular dimensions: ISO 2768-m.')
    note('PDF controls threads and tolerances; STEP controls outline.')
    note('Do not merge holes or alter geometry without review.')
    y -= 12
    note('QUOTE SCOPE', True)
    note('Includes material, all 50 round holes and all 4 strap slots.')
    note('No mounting hardware. Ship quote to Japan separately.')
    note('D2: six discrete metal supports. No support parts included.')
    c.setFont('Helvetica', 8)
    c.drawString(35, 52, 'Matching STEP: ' + row['name'] + '.step')
    c.drawString(35, 38, 'STEP SHA256: ' + row['step_sha256'])
    c.drawRightString(1155, 38, 'Sheet 1 / 1 | Drawing generated from geometry.json')
    c.save()
    row['pdf_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    row['quoted_material'] = '6061-T6'
    row['quoted_surface_finish'] = 'none / as machined'
    row['highest_tolerance_UI'] = '+/-0.10mm'
(HERE / 'drawing_manifest.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n')
print('Wrote matching D2 PDF drawing and drawing_manifest.json')
