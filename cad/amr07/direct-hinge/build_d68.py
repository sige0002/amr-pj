"""D6.8: hinges seated directly on 3030; metal lid angles; floor-supported controls.

Run with FreeCAD Python. Purchased parts are drawing-based nominal geometry.
The previous D6.5 unchanged hardware remains the verified source assembly.
"""
from pathlib import Path
from itertools import combinations
import importlib.util, json, math, hashlib, sys
import FreeCAD as App
import Part, MeshPart
HERE=Path(__file__).resolve().parent; BASE=HERE.parent; SOURCE=BASE/'two-story'
spec=importlib.util.spec_from_file_location('old_hatch_helpers',BASE/'hinged-deck/build_hatch.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
d6=h.d6;j=h.j;V=App.Vector;box=h.box;fuse=h.fuse;cyl=h.cyl
NAME='AMR01_DirectHinge_D68';AXIS=V(0,156,230);h.AXIS=AXIS
RHO={'PLA':1.24e-6,'steel':7.85e-6,'aluminum':2.7e-6}
P=dict(revision='D6.8',date='2026-09-23',hinge='Sugatsune HG-TP20',hinge_qty=2,
 hinge_centers_x_mm=[-105,105],hinge_axis_yz_mm=[156,230],opening_deg=[0,90],
 hinge_nominal_each_Nm=2,hinge_initial_tolerance_fraction=.25,
 plate_size_mm=[300,300,4],plate_z_mm=[229,233],new_plate_holes_xy_mm=[[x,109] for c in [-105,105] for x in [c-15,c+15]],
 frame_mount='Fixed metal hinge leaves on outer Y150 face; two M4 slot screws per hinge; no plastic or adapter under hinge.',
 lid_mount='Two identical simple CNC aluminum angles; no opening stops. Review range0..90deg, held by torque hinges. No frame drilling; four D4.5 lid holes.',
 battery_harness_points=[[-160,45,181],[-160,95,181],[-178,95,181],[-178,100,181],[-195,100,181],[-195,100,172],[-195,82,172]],
 operator_side='rear -X',estop=dict(part='IDEC XA1E-BV302R',panel_center_mm=[-197,-103,160.4]),
 arm=dict(part='amon 3212',panel_center_mm=[-201,-69,160.4]),
 main_power=dict(part='amon 3214',panel_center_mm=[-201,64,156.4]),
 unload_before_open=True,production_release=False)

def slot_m4(surface,inward,axis=(1,0,0)):
 # uxcell B07P71JFX7 seller dimensions:16x8x7.6, M4. Seated long axis
 # crosses the slot; nose0.8 and taper are nominal assumptions, not a vendorSTEP.
 yz=[(-4,1.2),(4,1.2),(4,2),(8,2),(4,8.8),(-4,8.8),(-8,2),(-4,2)]
 p=[V(-4,y,z) for y,z in yz]
 s=Part.Face(Part.makePolygon(p+[p[0]])).extrude(V(8,0,0)).cut(cyl(2.1,9,(0,0,0)))
 z=V(*inward);x=V(*axis);y=z.cross(x)
 s.Placement=App.Placement(V(*surface),App.Rotation(x,y,z,'ZXY'))
 return s

def angle_shape(cx):
 # Identical simple L,50x50x22,4mm walls. One R3 inside root.
 s=fuse([box(cx-25,100,233,50,50,4),box(cx-25,146,237,50,4,18)])
 s=s.fuse(box(cx-25,143,237,50,3,3).cut(cyl(3,50,(cx-25,143,240),(1,0,0))))
 holes=[]
 for x in [cx-15,cx+15]:holes.extend([cyl(2.25,7,(x,109,232)),cyl(2.25,8,(x,145,246),(0,1,0))])
 return s.cut(Part.makeCompound(holes)).removeSplitter()

def main():
 old=App.openDocument(str(SOURCE/'AMR01_TwoStorey_D6.FCStd'));bv=json.loads((SOURCE/'validation.json').read_text())
 doc=App.newDocument(NAME);doc.Label='AMR D6.8 | DIRECT FRAME HINGES | FLOOR SUPPORTED E-STOP'
 removed=['Reserved_EmergencyStop','BatteryVehicleHarness']+['DeckBolt'+str(i) for i in range(6)]+['DeckSlotNut'+str(i) for i in [1,2,3,5]]
 changed=['AluminumDeckD3','FloorPLA_0_0','FloorPLA_0_1','BatteryModuleHarness']
 for o in old.Objects:
  if hasattr(o,'MaterialBasis') and o.Name not in removed:doc.copyObject(o,False)
 new=[];printed=[];moving=[];released=[];mounts=[];case_mounts=[]
 def add(name,s,mat,note,move=False,mass=None):
  assert s.isValid() and len(s.Solids)>0,name
  o=doc.addObject('PartDesign::Feature',name);o.Shape=s
  for k,v in [('MaterialBasis',mat),('ModelNote',note)]:o.addProperty('App::PropertyString',k,'Design');setattr(o,k,v)
  if mass is not None:o.addProperty('App::PropertyFloat','CatalogMassKg','Design');o.CatalogMassKg=mass
  new.append(name)
  if mat=='PLA':printed.append(name)
  if move:moving.append(name)
  return o
 def washer(name,p,n=(0,0,1),move=False):
  return add(name,cyl(6,1,p,n).cut(cyl(2.25,1,p,n)),'steel','M4 OD12 t1 steel washer; shared pack.',move)
 def nut(name,p,n=(0,0,1),move=False):
  s=j.hexagon(0,0,0,7,3.2).cut(cyl(2.1,3.2,(0,0,0)))
  s.Placement=App.Placement(V(*p),App.Rotation(V(0,0,1),V(*n)))
  return add(name,s,'steel','M4 metal nut, AF7 h3.2. Thread form omitted.',move)
 def bolt(name,p,n=(0,0,-1),length=16,move=False):
  return add(name,j.screw(p,n,4,length),'steel',f'M4x{length} socket cap. Nominal thread envelope.',move)
 for i,cx in enumerate(P['hinge_centers_x_mm']):
  add(f'LidAngle_{i}',angle_shape(cx),'aluminum','6061-T6 CNC angle50x50x22,4mm walls,one R3 root,4 plain D4.5 holes. No opening stop; identical left/right manufacturing part.',True)
  for k,x in enumerate([cx-15,cx+15]):
   # Fixed leaf:2mm; washer1mm; bolt10mm ->7mm slot projection.
   bolt(f'HingeFrameBolt_{i}_{k}',(x,153,214),(0,-1,0),10)
   washer(f'HingeFrameWasher_{i}_{k}',(x,152,214),(0,1,0))
   add(f'HingeFrameNut_{i}_{k}',slot_m4((x,150,214),(0,-1,0)),'steel','uxcell B07P71JFX7 M4 hammer nut16x8x7.6; nominal nose/taper. Verify fit and seating in NFSL6 slot before manufacture release.')
   mounts.append(dict(bolt=f'HingeFrameBolt_{i}_{k}',xyz=[x,150,214],slot_projection_mm=7,nominal_thread_overlap_mm=5.8,slot_floor_clearance_mm=2))
   # Moving leaf onto metal angle: bolt from outside, nut accessible inboard.
   bolt(f'HingeLidBolt_{i}_{k}',(x,153,246),(0,-1,0),16,True)
   washer(f'HingeLidTopWasher_{i}_{k}',(x,152,246),(0,1,0),True)
   nut(f'HingeLidNut_{i}_{k}',(x,142.8,246),(0,1,0),True)
   # Angle to lid: top access and underside wrench, clear of rail atY120.
   bolt(f'AngleDeckBolt_{i}_{k}',(x,109,237),move=True)
   washer(f'AngleDeckWasher_{i}_{k}',(x,109,228),move=True)
   nut(f'AngleDeckNut_{i}_{k}',(x,109,224.8),move=True)
  # Supplier drawing reconstruction. Fixed and moving barrel sections avoid
  # claiming detailed friction internals.52mm includes max1mm end projections.
  for which,z0,zh,move,segments in [('Fixed',205,214,False,[(-26,6),(20,6)]),('Moving',236,246,True,[(-19.9,39.8)])]:
   leaf=box(cx-25,150,z0,50,2,19)
   leaf=leaf.cut(Part.makeCompound([cyl(2.15,4,(x,149,zh),(0,1,0)) for x in [cx-15,cx+15]]))
   pieces=[leaf]
   for a,L in segments:
    pieces += [cyl(6,L,(cx+a,156,230),(1,0,0)),box(cx+a,150,223 if not move else 230,L,3,7)]
   add(f'HGTP20_{which}_{i}',fuse(pieces),'steel','Nominal50x50, hole30x32, axis6 from mounting plane,t2. Two60g complete hinges. Fixed base against frame; moving bracket onlid. Closed180deg toopen90deg lies within rated180deg torque sector.',move,.03)
 plate=doc.getObject('AluminumDeckD3');plate.Shape=plate.Shape.cut(Part.makeCompound([cyl(2.25,6,(x,y,228)) for x,y in P['new_plate_holes_xy_mm']])).removeSplitter()
 plate.ModelNote+=' D6.8 adds four D4.5 holes atX+-90/120,Y109. Existinggrid and thickness unchanged. New machining quote required.'
 # Keep already quoted M6x15 locks; washer stack remains all metal.
 for i,x in enumerate([-105,105]):
  for k in range(3):
   n=f'HatchLockWasher_{i}_{k}';add(n,cyl(9,1,(x,-135,233+k)).cut(cyl(3.25,1,(x,-135,233+k))),'steel','M6 OD18 t1;3 per M6x15 lock.');released.append(n)
  s=cyl(3,15,(x,-135,236),(0,0,-1)).fuse(cyl(5,3,(x,-135,236))).fuse(box(x-13,-137,239,26,4,10))
  n=f'HatchLockWingBolt_{i}';add(n,s,'steel','TRUSCO B36-0615 M6x15 lock, remove before opening.');released.append(n)
 moving += [o.Name for o in doc.Objects if o.Name.startswith(('AluminumDeck','PrintedStop','StopBolt','StopWasher','StopNut'))]

 # Printed landing pads are integral with the two rear floor panels. The case
 # base bears over the rear aluminum rail. Captive nuts are loaded sideways
 # before cases; all installation screws then run downward from the open case.
 def case(prefix,iy,bounds,center,holes):
  x0,y0,z0,L,W,H=bounds;top=z0+H
  floor=doc.getObject(f'FloorPLA_0_{iy}')
  pad=box(x0,y0,101.4,L,W,8)
  positions=[(x0+9,y0+16),(x0+L-9,y0+16),(x0+9,y0+W-16),(x0+L-9,y0+W-16)]
  cut=[]
  for k,(x,y) in enumerate(positions):
   cut += [j.hexagon(x,y,102.1,7.4,3.8),cyl(2.25,9,(x,y,101.2))]
   # Horizontal entry slot terminates in nut pocket; case mustbe lifted before service.
   cut.append(box(x0 if x<x0+L/2 else x,y-3.7,102.1,(x-x0) if x<x0+L/2 else (x0+L-x),7.4,3.8))
   nut(f'{prefix}FloorNut_{k}',(x,y,102.6))
   bolt(f'{prefix}FloorBolt_{k}',(x,y,117.4))
   washer(f'{prefix}FloorWasher_{k}',(x,y,116.4))
   case_mounts.append(dict(case=prefix,panel=floor.Name,bolt=f'{prefix}FloorBolt_{k}',xy_mm=[x,y],thread_engagement_mm=3.2,tip_z_mm=101.4,roof_above_pocket_mm=3.5))
  floor.Shape=floor.Shape.fuse(pad).cut(Part.makeCompound(cut)).removeSplitter()
  floor.ModelNote+=' D6.8 integral8mm landing,4 side-loaded captiveM4 nuts. Original4 floor/frame fixing points retained.'
  s=box(*bounds).cut(box(x0+2.5,y0+2.5,z0+7,L-5,W-5,H+1))
  s=s.cut(Part.makeCompound([cyl(2.25,9,(x,y,z0-1)) for x,y in positions]))
  lid=box(x0,y0,top,L,W,3); lid_pockets=[]
  for k,(x,y) in enumerate([(x0+6,y0+6),(x0+L-6,y0+6),(x0+6,y0+W-6),(x0+L-6,y0+W-6)]):
   pocket=j.hexagon(x,y,top-9.4,7.4,3.8).fuse(box(x if x<x0+L/2 else x-6,y-3.7,top-9.4,6,7.4,3.8));lid_pockets.append(pocket)
   bore=cyl(2.25,16,(x,y,top-11))
   s=s.fuse(box(x-5,y-5,top-10,10,10,10).cut(pocket).cut(bore));lid=lid.cut(bore)
   bolt(f'{prefix}LidBolt_{k}',(x,y,top+4))
   washer(f'{prefix}LidWasher_{k}',(x,y,top+3))
   nut(f'{prefix}LidNut_{k}',(x,y,top-9.2))
  for rx in [-215,-179]:
   lid=lid.fuse(box(rx-2,y0+2.5,top-12,4,W-5,12))
   for sy in [y0+2.5,y0+W-5.5]:s=s.fuse(box(rx-2,sy,top-16,4,3,4))
  s=s.cut(Part.makeCompound(lid_pockets))
  for x,y,r in holes:lid=lid.cut(cyl(r,5,(x,y,top-1)))
  if prefix=='RearStop':
   lid=lid.fuse(cyl(17,4.4,(-197,-103,top-4.4)).cut(cyl(11.5,4.4,(-197,-103,top-4.4))))
  if prefix=='RearStop':lid=lid.cut(box(-197-.85,-103+7.9,top-1,1.7,1.9,5))
  # Side ports avoid hidden exit holes against the floor.
  s=s.cut(cyl(4.5,6,(x0+L-3,center[1],z0+14),(1,0,0)))
  add(prefix+'CasePLA',s.removeSplitter(),'PLA','7mm base,2.5mm walls,full landing support. Four top-access M4 screws into floor captive nuts. No cantilever legs.')
  add(prefix+'LidPLA',lid.removeSplitter(),'PLA','3mm local switch panel, two12mm-deep underside ribs seated on four case pads. Four M4 screws/side-loaded captive nuts, removed with switches for case fastening access.')
 case('RearStop',0,(-229,-123,109.4,66,76,48),[-207,-86],[(-197,-103,8.1),(-201,-69,6.1)])
 case('RearPower',1,(-229,42,109.4,66,44,44),[-201,64],[(-201,64,6.1)])
 for key,name,bd,depth,hd,hh in [('estop','EStop_XA1E_BV302R',0,0,0,0),('arm','ARM_3212',16,25,16,15),('main_power','MainPower_3214',22,25,22,16)]:
  x,y,z=P[key]['panel_center_mm']
  if key=='estop':s=fuse([box(x-15.2,y-14.7,z-30.4,30.4,29.4,22.4),cyl(10.5,5,(x,y,z-8)),cyl(7.9,11,(x,y,z-3)),cyl(14.5,12.6,(x,y,z+8))])
  else:s=fuse([cyl(bd/2,depth-3,(x,y,z-depth)),cyl(5.9,6,(x,y,z-3)),cyl(hd/2,hh,(x,y,z+3))])
  add(name,s,'reference','Catalogue switch/terminal envelope, not supplier detailedCAD. Switch mass included in existing electrical allowance.')
 doc.getObject('BatteryModuleHarness').Shape=d6.pipe(P['battery_harness_points'])
 doc.getObject('BatteryModuleHarness').ModelNote='D6.8 route moved away from main switch approach; restrain supplied adapter lead. Same moving module/harness allowance.'
 for name,points,r in [('RearStopSignalRoute',[[-163,-86,123.4],[-155,-86,123.4],[-145,-103,110.5],[125,-103,110.5],[125,-95,126],[135,-95,126]],2.5),('MainPowerInputRoute',[[-199,127,172],[-199,135,172],[-155,135,172],[-155,110,141],[-155,64,123.4],[-163,64,123.4]],3),('MainPowerOutputRoute',[[-163,77,120],[-157,77,120],[-145,77,110],[-145,114,114],[220,114,114],[220,-75,126],[205,-75,126]],3)]:
  add(name,d6.pipe(points,r),'reference','Wiring route reservation, grommets/clamps/terminal detail not yet released.')
 # Second main-power port is distinct from input, allowing positive separation.
 o=doc.getObject('RearPowerCasePLA');o.Shape=o.Shape.cut(cyl(4.5,6,(-166,77,120),(1,0,0))).removeSplitter()
 doc.recompute()
 physical=[o for o in doc.Objects if hasattr(o,'MaterialBasis') and o.MaterialBasis!='reference'];refs=[o for o in doc.Objects if hasattr(o,'MaterialBasis') and o.MaterialBasis=='reference']
 def mass(o):return o.CatalogMassKg if hasattr(o,'CatalogMassKg') else o.Shape.Volume*RHO.get(o.MaterialBasis,0)
 ledger=[dict(name=n,mass_kg=mass(doc.getObject(n)),center_mm=d6.center(doc.getObject(n).Shape)) for n in new if doc.getObject(n).MaterialBasis!='reference']
 ledger += [dict(name='remove '+n,mass_kg=-mass(old.getObject(n)),center_mm=d6.center(old.getObject(n).Shape)) for n in removed if old.getObject(n).MaterialBasis!='reference']
 for n in changed:
  for title,o,sgn in [('old ',old.getObject(n),-1),('new ',doc.getObject(n),1)]:ledger.append(dict(name=title+n,mass_kg=sgn*mass(o),center_mm=d6.center(o.Shape)))
 total=bv['mass']['estimated_base_kg']+sum(a['mass_kg'] for a in ledger)
 lm=sum(mass(doc.getObject(n)) for n in moving)
 a=sum(mass(doc.getObject(n))*9.80665*(156-d6.center(doc.getObject(n).Shape)[1])/1000 for n in moving)
 b=sum(mass(doc.getObject(n))*9.80665*(230-d6.center(doc.getObject(n).Shape)[2])/1000 for n in moving)
 angles=[0,math.pi/2]+[t for t in [math.atan2(b,a)] if 0<t<math.pi/2]
 t=max(angles,key=lambda t:abs(a*math.cos(t)+b*math.sin(t)));peak=abs(a*math.cos(t)+b*math.sin(t))
 torque=dict(empty_lid_mass_kg=lm,closed_moment_Nm=a,vertical_CG_component_Nm=b,maximum_gravity_moment_Nm=peak,maximum_angle_deg=math.degrees(t),pair_nominal_Nm=4,pair_initial_min_Nm=3,pair_initial_max_Nm=5,minimum_initial_hold_ratio=3/peak,tangential_open_force_max_N=(5+peak)/.306)
 unchanged=all(h.equivalent_brep(doc.getObject(o.Name).Shape,o.Shape) for o in old.Objects if hasattr(o,'MaterialBasis') and o.Name not in removed+changed)
 out=dict(parameters=P,new_objects=new,changed_objects=changed,removed_objects=removed,moving_parts=moving,released_before_open=released+['StrapRouteX','StrapRouteY','CargoEnvelopeD3'],frame_mounts=mounts,case_mounts=case_mounts,physical_parts=len(physical),retained_shapes_BRep_equal=unchanged,torque=torque,mass=dict(estimated_base_kg=total,source_kg=bv['mass']['estimated_base_kg'],total_solid_PLA_kg=sum(mass(o) for o in physical if o.MaterialBasis=='PLA'),ledger=ledger,actually_weighed=False))
 (HERE/'parameters.json').write_text(json.dumps(P,ensure_ascii=False,indent=2)+'\n');(HERE/'geometry.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 doc.saveAs(str(HERE/(NAME+'.FCStd')))
 # Export the actual modified plate and one identical manufacturing angle.
 for n,filename in [('AluminumDeckD3','AMR_GridDeck_D68'),('LidAngle_1','AMR_LidAngle_D68')]:
  s=doc.getObject(n).Shape.copy();s.translate(V(0,0,-229) if n=='AluminumDeckD3' else V(-105,-100,-233))
  target=HERE/(filename+'.FCStd')
  if target.exists():
   prior=App.openDocument(str(target));same=h.equivalent_brep(s,prior.Objects[0].Shape);App.closeDocument(prior.Name)
   if same and (HERE/(filename+'.step')).exists():continue
  q=App.newDocument(filename);o=q.addObject('PartDesign::Feature','Part');o.Shape=s;q.recompute();q.saveAs(str(HERE/(filename+'.FCStd')));Part.export([o],str(HERE/(filename+'.step')));App.closeDocument(q.Name)
 for n in printed+['FloorPLA_0_0','FloorPLA_0_1']:
  s=doc.getObject(n).Shape.copy();bb=s.BoundBox;s.translate(V(-bb.XMin,-bb.YMin,-bb.ZMin));assert max(bb.XLength,bb.YLength,bb.ZLength)<256
  MeshPart.meshFromShape(Shape=s,LinearDeflection=.06,AngularDeflection=.25,Relative=False).write(str(HERE/(n+'.stl')))
 print(json.dumps(dict(mass=total,torque=torque,unchanged=unchanged,parts=len(physical)),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
