"""E3 electrical packaging on the unchanged D6.9 chassis. FreeCAD Python."""
from pathlib import Path
import json, hashlib, importlib.util, math
import FreeCAD as App
import Part, MeshPart
HERE=Path(__file__).resolve().parent; BASE=HERE.parent; SOURCE=BASE/'fixed-deck'
spec=importlib.util.spec_from_file_location('d68',BASE/'direct-hinge/build_d68.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
V=App.Vector;box=b.box;cyl=b.cyl;fuse=b.fuse
NAME='AMR01_PicoControl_E3'
REMOVE=['ARM_3212','EStop_XA1E_BV302R','Reserved_Protection','Reserved_ClampAndPower','Reserved_SupervisorRS485','SupervisorPad','SupervisorTopPad','SupervisorRetentionBelt','RearStopSignalRoute','MainPowerOutputRoute']
CHANGED=['RearStopCasePLA','RearStopLidPLA','FloorPLA_1_1']+[f'RearStopLid{kind}_{i}' for kind in ['Bolt','Washer','Nut'] for i in range(4)]

def main():
 old=App.openDocument(str(SOURCE/'AMR01_FixedDeck_D69.FCStd'))
 doc=App.newDocument(NAME);doc.Label='AMR E3 | PICO + RS485 | DIRECT 2-POLE E-STOP | MAIN POWER'
 for o in old.Objects:
  if hasattr(o,'MaterialBasis') and o.Name not in REMOVE:doc.copyObject(o,False)
 new=[]
 def add(n,s,mat,note):
  assert s.isValid() and s.Solids,n
  o=doc.addObject('PartDesign::Feature',n);o.Shape=s
  for k,v in [('MaterialBasis',mat),('ModelNote',note)]:o.addProperty('App::PropertyString',k,'Design');setattr(o,k,v)
  new.append(n);return o
 def screw(n,x,y,z,d,length):
  s=cyl(d/2,length,(x,y,z),(0,0,-1)).fuse(cyl(2.75,3,(x,y,z))).cut(b.j.hexagon(x,y,z+1.5,2.5,1.6))
  return add(n,s,'steel','Nominal M3 socket screw, headD5.5/h3; no helical thread.')
 def washer(n,x,y,z):return add(n,cyl(3.5,.6,(x,y,z)).cut(cyl(1.7,.6,(x,y,z))),'steel','M3 plain washer OD7 ID3.4 t0.6.')
 def nut(n,x,y,z):return add(n,b.j.hexagon(x,y,z,5.5,2.4).cut(cyl(1.4,2.4,(x,y,z))),'steel','M3 nut AF5.5 h2.4; thread omitted.')
 # Same footprint and four floor attachments. Increase internal depth for a
 # drawing-based HW1B-V402R envelope, replacing the obsolete solder switch.
 x0,y0,z0,L,W,H=-229,-123,109.4,66,76,66;top=z0+H
 floor_xy=[(-220,-107),(-172,-107),(-220,-63),(-172,-63)]
 lid_xy=[(-223,-117),(-169,-117),(-223,-53),(-169,-53)]
 case=box(x0,y0,z0,L,W,H).cut(box(x0+2.5,y0+2.5,z0+7,L-5,W-5,H+1))
 for x,y in floor_xy:case=case.cut(cyl(2.25,9,(x,y,z0-1)))
 lid=box(x0,y0,top,L,W,5)
 for i,(x,y) in enumerate(lid_xy):
  pocket=b.j.hexagon(x,y,top-9.4,7.4,3.8).fuse(box(x if x<x0+L/2 else x-6,y-3.7,top-9.4,6,7.4,3.8))
  bore=cyl(2.25,19,(x,y,top-12))
  case=case.fuse(box(x-5,y-5,top-10,10,10,10).cut(pocket).cut(bore)).cut(pocket)
  for kind,dz in [('Bolt',20),('Washer',20),('Nut',18)]:
   o=doc.getObject(f'RearStopLid{kind}_{i}');s=o.Shape.copy();s.translate(V(0,0,dz));o.Shape=s
 for rx in [-215,-177]:
  lid=lid.fuse(box(rx-2,y0+2.5,top-12,4,W-5,12))
  for sy in [y0+2.5,y0+W-5.5]:case=case.fuse(box(rx-2,sy,top-16,4,3,4))
 for x,y in lid_xy:lid=lid.cut(cyl(2.25,20,(x,y,top-13)))
 cx,cy,front=-196,-85,top+5
 lid=lid.cut(cyl(11.25,20,(cx,cy,top-13))).cut(box(cx-1.7,cy+10,top-13,3.4,2.3,20))
 # Side access port: two motor feeds + returns, protected by an edge grommet.
 case=case.cut(box(-166,-96,122,6,22,12))
 doc.getObject('RearStopCasePLA').Shape=case.removeSplitter()
 doc.getObject('RearStopLidPLA').Shape=lid.removeSplitter()
 doc.getObject('RearStopCasePLA').ModelNote='E3 same 66x76 footprint and FOUR existing floor bolts; height66. 7mm base,2.5mm walls. Side cable aperture22x12; edge protection required.'
 doc.getObject('RearStopLidPLA').ModelNote='E3 single HW1B holeD22.5 with3.4 key; NO ARM hole. Panel5mm, two12mm-deep ribs supported by case ledges. Four existingM4x16; no countersink. Prototype press/creep test pending.'
 # Body asymmetry from drawing: X width29.4; Y extent26.5+14.9; rear49.4;
 # headD40 projects32. This is an envelope, not detailed vendor STEP geometry.
 estop=fuse([box(cx-14.7,cy-26.5,front-49.4,29.4,41.4,41.4),cyl(10.9,21,(cx,cy,front-8)),cyl(15,4,(cx,cy,front)),cyl(20,19,(cx,cy,front+13))])
 add('EStop_HW1B_V402R',estop,'reference','IDEC catalogue nominal envelope; 2NC screw terminals. One NC per motor; direct switching qualification pending. Panel front180.4, maximum head212.4. Not a vendor solid.')
 # Delete the custom-protection boxes. Retain only an explicit computer-power
 # reservation until the Linux computer input is selected.
 add('Reserved_ComputerSupply',box(155,-25,112,50,90,35),'reference','Computer supply only, conditional DC/DC within50x90x35. Model not selected. Not a custom brake/monitor board.')
 # Pico + user-proposed HAT mock: measured PCB footprint from manufacturer;
 # assembly height, connector positions and support keepouts are provisional.
 tx,ty,tz=5,65,101.4;TL,TW,TH=70,45,32;t=2.4;tt=tz+TH
 tray=box(tx,ty,tz,TL,TW,TH).cut(box(tx+t,ty+t,tz+3,TL-2*t,TW-2*t,TH))
 mounts=[(11,73),(69,73),(11,102),(69,102)]
 tray_lid=box(tx,ty,tt,TL,TW,2.4)
 for i,(x,y) in enumerate(mounts):
  tray=tray.fuse(box(x-4,y-4,tz,8,8,3)).cut(cyl(1.7,5,(x,y,tz-1)))
  ly=71 if y==73 else 104
  pocket=b.j.hexagon(x,ly,tt-6,5.9,2.8)
  pocket=pocket.fuse(box(x if x<40 else x-5,ly-2.95,tt-6,5,5.9,2.8))
  tray=tray.fuse(box(x-4,ly-4,tt-7,8,8,7).cut(pocket).cut(cyl(1.7,10,(x,ly,tt-8))))
  tray_lid=tray_lid.cut(cyl(1.7,5,(x,ly,tt-1)))
  screw(f'PicoFloorBolt_{i}',x,y,tz+3.6,3,12)
  washer(f'PicoFloorTopWasher_{i}',x,y,tz+3)
  washer(f'PicoFloorBottomWasher_{i}',x,y,98.4)
  nut(f'PicoFloorNut_{i}',x,y,96)
  screw(f'PicoLidBolt_{i}',x,ly,tt+3,3,12)
  washer(f'PicoLidWasher_{i}',x,ly,tt+2.4)
  nut(f'PicoLidNut_{i}',x,ly,tt-5.8)
 # Connector/service windows on both ends; no unsupported assumptions about
 # Amazon board terminal positions. Small windows in sidewalls expose connectors.
 for x in [tx-1,tx+TL-t-1]:tray=tray.cut(box(x,76,110,5,23,22))
 for y in [ty-1,ty+TW-t-1]:tray=tray.cut(box(20,y,112,40,5,16))
 # Board carrier ledges avoid putting a metal fastener through PCB/copper.
 for x in [13.75,62.25]:
  for y in [77,94]:tray=tray.fuse(box(x,y,tz+3,4,4,6))
 # Nominal edge capture:0.3mm lateral gap,0.2mm lid-stop clearance.
 for x in [12.25,66.55]:
  for y in [77,94]:tray=tray.fuse(box(x,y,tz+3,1.2,4,8.6))
 for x in [13.75,62.25]:
  for y in [76.0,98.3]:tray=tray.fuse(box(x,y,tz+3,4,.7,8.6))
 for x in [16.5,63.5]:
  for y in [79,96]:tray_lid=tray_lid.fuse(cyl(1.5,tt-122.2,(x,y,122.2)))
 add('PicoTrayPLA',tray.removeSplitter(),'PLA','FourM3 floor mounts; nonconductivePLA.52.5x21 HAT footprint. Edge ledges/connector windows are mock-only pending received-board keepouts and header height. No bare PCB against metal.')
 add('PicoTrayLidPLA',tray_lid.removeSplitter(),'PLA','FourM3 removable cover. Existing belt slots are not used. Four printed stops limit nominal upward motion to0.2mm; tray guides limit lateral movement to0.3mm. Actual PCB keepouts/header height must be checked; not a production print.')
 fl=doc.getObject('FloorPLA_1_1')
 for x,y in mounts:fl.Shape=fl.Shape.cut(cyl(1.7,25,(x,y+12,85)))
 fl.ModelNote+=' E3 four D3.4 holes for Pico tray. Existing FOUR floor-to-frame fixings retained.'
 add('Pico_RS485_HAT',box(13.75,77,110.4,52.5,21,1.6),'reference','User-proposed Amazon B0GKHKCZV3; photograph reported same as Pico-2CH-RS485. Manufacturer footprint52.5x21; PCB thickness1.6 is a packaging assumption.')
 add('PicoOwned',box(14.5,77,121,51,21,1),'reference','User-owned Pico.51x21 nominal footprint; variant/header height not confirmed. Board position is mock-up only.')
 add('PicoHeaderEnvelope',fuse([box(16,77,112,47,3,9),box(16,95,112,47,3,9)]),'reference','Nominal stacked header supports; actual height must be checked before printing.')
 # Route reservations are visible as routed centerlines in drawings only; no
 # claim of finished bend radius, purchased connectors or dynamic flex proof.
 route_points={
  'Signal_USB':[[40,45,124],[40,60,124],[1,60,124],[1,99.5,124],[14.5,99.5,124]],
  'Signal_RS485_L':[[66,94,117],[82,94,117],[82,-103,113],[5,-103,113],[5,-145,70]],
  'Signal_RS485_R':[[66,106,117],[86,106,117],[86,116,113],[5,116,113],[5,145,70]],
 }
 # Reserve 4mm cable corridors; final end points are not motor connector geometry.
 for n,points in route_points.items():add(n,b.d6.pipe(points,2),'reference','Route guide only; verify connectors, strain relief and physical bend radii. Not a collision-qualified cable.')
 for obj in doc.Objects:
  if obj.Name.startswith('Pico'):
   shape=obj.Shape.copy();shape.translate(V(0,12,0));obj.Shape=shape
 doc.recompute()
 for o in doc.Objects:
  if hasattr(o,'Shape'):assert o.Shape.isValid(),o.Name
 physical=[o for o in doc.Objects if hasattr(o,'MaterialBasis') and o.MaterialBasis!='reference']
 def mass(o):return getattr(o,'CatalogMassKg',o.Shape.Volume*b.RHO.get(o.MaterialBasis,0))
 prior=json.loads((SOURCE/'geometry.json').read_text())
 changed_delta=sum(mass(doc.getObject(n))-mass(old.getObject(n)) for n in CHANGED if old.getObject(n).MaterialBasis!='reference')
 added_mass=sum(mass(doc.getObject(n)) for n in new if doc.getObject(n).MaterialBasis!='reference')
 identical=[]
 for o in old.Objects:
  if hasattr(o,'MaterialBasis') and o.Name not in REMOVE+CHANGED:
   assert b.h.equivalent_brep(o.Shape,doc.getObject(o.Name).Shape),o.Name
   identical.append(o.Name)
 g=dict(revision='E3',source='fixed-deck/AMR01_FixedDeck_D69.FCStd',source_sha256=hashlib.sha256((SOURCE/'AMR01_FixedDeck_D69.FCStd').read_bytes()).hexdigest(),
  removed=REMOVE,changed=CHANGED,added=new,unchanged_BRep_names=identical,
  physical_parts=len(physical),PLA_parts=sum(o.MaterialBasis=='PLA' for o in physical),
  mass=dict(estimated_base_kg=prior['mass']['estimated_base_kg']+changed_delta+added_mass,delta_mechanical_kg=changed_delta+added_mass,
            total_solid_PLA_kg=sum(mass(o) for o in physical if o.MaterialBasis=='PLA'),electrical_allowance_not_reduced=True,actually_weighed=False),
  estop=dict(part='HW1B-V402R',panel_center_mm=[cx,cy,front],head_max_z=front+32,body_depth_mm=49.4,contact_assignment='NC1 left motor; NC2 right motor; never parallel contacts'),
  main_power=dict(part='amon3214',restored_to_BOM=True,center_mm=[-201,64,156.4]),
  pico=dict(case_bounds_mm=[tx,ty+12,tz,TL,TW,TH+2.4],floor_mount_xy_mm=[[x,y+12] for x,y in mounts],mount_count=4,board_footprint_mm=[52.5,21],stack_height_unverified=True,print_release=False),
  checks_pending=['received HAT/Pico support/connector positions','E-stop motor-input inrush qualification','final Linux computer and supply dimensions','finished harness collision check'],
  production_release=False)
 (HERE/'geometry.json').write_text(json.dumps(g,ensure_ascii=False,indent=2)+'\n')
 doc.saveAs(str(HERE/(NAME+'.FCStd')))
 for n in ['RearStopCasePLA','RearStopLidPLA','PicoTrayPLA','PicoTrayLidPLA','FloorPLA_1_1']:
  s=doc.getObject(n).Shape.copy();bb=s.BoundBox;s.translate(V(-bb.XMin,-bb.YMin,-bb.ZMin))
  MeshPart.meshFromShape(Shape=s,LinearDeflection=.06,AngularDeflection=.25,Relative=False).write(str(HERE/(n+'.stl')))
 print(json.dumps({k:g[k] for k in ['physical_parts','PLA_parts','mass']},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
