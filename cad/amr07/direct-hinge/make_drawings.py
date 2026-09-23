"""Manufacturing quotation drawings; actual STEP controls 3D geometry."""
from pathlib import Path
import hashlib,json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3,landscape
HERE=Path(__file__).resolve().parent
p=json.loads((HERE/'parameters.json').read_text())
def header(c,name,qty):
 c.setFont('Helvetica-Bold',18);c.drawString(35,805,name+' / D6.8 / QUOTATION ONLY')
 c.setFont('Helvetica',10);c.drawString(35,784,f'2026-09-23 | mm | Quantity {qty} | Matching STEP required | Not released for fabrication')
def notes(c,items,x=680,y=750):
 for text in items:
  c.setFont('Helvetica',10);c.drawString(x,y,text);y-=18
def common(name):
 return ['Aluminum 6061-T6; require Rp0.2 >=240MPa.',
 'As machined. No blasting, anodizing or cosmetic finish.',
 'No threads or inserts. All specified holes are THROUGH.',
 'Deburr both sides. Edge break <=0.2mm.',
 'Hole coordinates +/-0.10mm; D4.5 +0.2/0.',
 'Other dimensions ISO2768-m unless specified.',
 'Do not change dimensions, material, R or holes without review.',
 'STEP SHA256:',hashlib.sha256((HERE/(name+'.step')).read_bytes()).hexdigest()[:32],
 hashlib.sha256((HERE/(name+'.step')).read_bytes()).hexdigest()[32:]]
name='AMR_GridDeck_D68';c=canvas.Canvas(str(HERE/(name+'.pdf')),pagesize=landscape(A3));header(c,name,1)
ox,oy,sc=350,440,1.75
xy=lambda x,y:(ox+x*sc,oy+y*sc)
c.rect(*xy(-150,-150),300*sc,300*sc)
for x in [-125,-75,-25,25,75,125]:
 for y in [-115,-65,-15,35,85,135]:c.circle(*xy(x,y),2.25*sc)
for x in [-105,0,105]:
 for y in [-135,135]:c.circle(*xy(x,y),3.3*sc)
for x,y in [(s*109.5,y) for s in [-1,1] for y in [-39,-11]]+[(x,s*109.5) for s in [-1,1] for x in [-14,14]]:c.circle(*xy(x,y),2.25*sc)
for x,y,dx,dy in [(-140,10,6,30),(140,10,6,30),(60,-105,30,6),(60,105,30,6)]:c.roundRect(*xy(x-dx/2,y-dy/2),dx*sc,dy*sc,3*sc)
c.setStrokeColorRGB(.8,.12,.08)
for x,y in p['new_plate_holes_xy_mm']:c.circle(*xy(x,y),2.25*sc);c.circle(*xy(x,y),5*sc)
c.setStrokeColorRGB(0,0,0);c.setFont('Helvetica',11);c.drawString(270,735,'300 x 300; thickness4 +/-0.10')
c.drawString(85,144,'TOP / Origin centre(0,0); red rings mark4 new holes (rings are NOT machined).')
c.rect(85,104,300*sc,4*sc);c.drawString(85,82,'SIDE:4 +/-0.10. Flatness<=0.5 over300. Preserve flatness during shipment.')
notes(c,common(name)+['','36 GRID D4.5: Cartesian product of',
 'X=-125,-75,-25,25,75,125; Y=-115,-65,-15,35,85,135.',
 '6 FRAME D6.6 +0.2/0: X=-105,0,105; Y=+/-135.',
 '8 STOP D4.5: X=+/-109.5,Y=-39,-11;',
 'and X=+/-14,Y=+/-109.5.',
 '4 NEW HINGE D4.5: X=-120,-90,90,120; Y=109.',
 '4 slots30x6 R3: (+/-140,10) alongY;',
 '(60,+/-105) alongX. Length30+/-0.2,width6+0.2/0.',
 'Same D3 plate outline/grid, with ONLY4 new plain holes.',
 'Keep holes separate; no tapping; quantity1.'])
c.showPage();c.save()
name='AMR_LidAngle_D68';c=canvas.Canvas(str(HERE/(name+'.pdf')),pagesize=landscape(A3));header(c,name,2)
# Export local frame: X=-25..25,Y=0..50,Z=0..22.
sc=5;ox,oy=160,475
q=c.beginPath()
for i,(x,y) in enumerate([(0,0),(50,0),(50,22),(46,22),(46,4),(0,4)]):
 if i==0:q.moveTo(ox+x*sc,oy+y*sc)
 else:q.lineTo(ox+x*sc,oy+y*sc)
q.close();c.drawPath(q)
c.setFont('Helvetica',11);c.drawString(125,640,'SIDE Y-Z:50 x22; foot/upright4 +/-0.10; inside root R3.')
ox,oy=335,215
q=c.beginPath()
for i,(x,y) in enumerate([(-25,0),(25,0),(25,50),(-25,50)]):
 if i==0:q.moveTo(ox+x*sc,oy+y*sc)
 else:q.lineTo(ox+x*sc,oy+y*sc)
q.close();c.drawPath(q)
for x in [-15,15]:c.circle(ox+x*sc,oy+9*sc,2.25*sc)
c.drawString(125,184,'TOP X-Y:50x50, width50; two base holes, no threads.')
notes(c,common(name)+['','One identical part; quantity2, not mirrored.',
 'Overall50(X) x50(Y) x22(Z). Main walls4 +/-0.10.',
 'One inside root R3; other outline per STEP.',
 '4x D4.5 +0.2/0 THROUGH:',
 '2 base bores: X=+/-15,Y=9,axisZ.',
 '2 upright bores: X=+/-15,Z=13,axisY.',
 'Hole centre coords +/-0.10 from exported local origin.',
 'Main mounting faces perpendicular0.2/22.',
 'Main foot and upright seating flatness0.15.',
 'No opening stops, ears or additional flanges.',
 '50mm foot preserves existing cargo belt clearance.',
 'Schematic sharp lines atR3; STEP controls actual radii.',
 'Manual review of machining access/R3 is required.'])
c.showPage();c.save()
print('Two quotation PDFs generated for actual exported STEP hashes.')
