from pathlib import Path
import json,itertools,hashlib
import FreeCAD as App
import Part,Mesh
HERE=Path(__file__).resolve().parent;BASE=HERE.parent
p=HERE/'AMR01_Reviewed_E4.FCStd';d=App.openDocument(str(p));g=json.loads((HERE/'geometry.json').read_text());changed=set(g['changed']+g['added'])
refs=['BatteryBL1860B','BatteryAdapter03','Reserved_Computer','Reserved_ComputerSupply','PicoOwned','Pico_RS485_HAT','PicoHeaderEnvelope','EStop_HW1B_V402R','MainPower_3214']+g['added']
objs=[o for o in d.Objects if hasattr(o,'MaterialBasis') and (o.MaterialBasis!='reference' or o.Name in refs)]
hits=[];checks=0
for a,b in itertools.combinations(objs,2):
 if not {a.Name,b.Name}&changed:continue
 checks+=1
 if a.Shape.BoundBox.intersect(b.Shape.BoundBox):
  vol=a.Shape.common(b.Shape).Volume
  if vol>.001:hits.append([a.Name,b.Name,round(vol,4)])
services={}
def check(name,s,against):
 h=[o.Name for o in against if o.Shape.BoundBox.intersect(s.BoundBox) and o.Shape.common(s).Volume>.001];services[name]=h;return h
battery_names=json.loads((BASE/'two-story/validation.json').read_text())['moving_parts']
installed_grid_constraints={}
# Tools checked with battery module removed; report installed-state restrictions separately.
for x,y in g['grid_xy_mm']:
 shape=Part.makeCylinder(6,40,App.Vector(x,y,189))
 check(f'grid_tool_{x}_{y}',shape,[o for o in objs if o.Name!='AluminumDeckD3' and o.Name not in battery_names])
 installed_grid_constraints[f'{x},{y}']=[o.Name for o in objs if o.Name in battery_names and o.Shape.BoundBox.intersect(shape.BoundBox) and o.Shape.common(shape).Volume>.001]
for i,(x,y) in enumerate(g['frame_fixings_xy_mm']):
 check('deck_top_tool_'+str(i),Part.makeCylinder(6,70,App.Vector(x,y,234.5)),[o for o in objs if o.Name!='DeckBolt'+str(i)])
check('estop_above_hand_r35',Part.makeCylinder(35,100,App.Vector(-196,-85,212.4)),[o for o in objs if not o.Name.startswith(('EStop','RearStop'))])
check('estop_rear_hand',Part.makeBox(130,70,65,App.Vector(-326,-120,185)),[o for o in objs if not o.Name.startswith(('EStop','RearStop'))])
check('main_rear_hand',Part.makeBox(120,50,45,App.Vector(-321,39,153)),[o for o in objs if not o.Name.startswith(('MainPower','RearPower'))])
# Nut tools used with lid on bench, contact blocks/terminals removed.
check('estop_nut_tool_lid_only',Part.makeCylinder(14.5,40,App.Vector(-196,-85,130.4)),[d.getObject('RearStopLidPLA')])
check('main_nut_tool_lid_only',Part.makeCylinder(15,40,App.Vector(-201,64,108.4)),[d.getObject('RearPowerLidPLA')])
# Lid assembly lifts vertically50mm; conservative sweep of lids and controls against fixed housing.
for prefix,names in [('stop',['RearStopLidPLA','EStop_HW1B_V402R','EStopLockNut']+[f'EStopLeadReservation{i}' for i in range(4)]),('power',['RearPowerLidPLA','MainPower_3214','MainPowerNutReservation','MainPowerTerminalReservation0','MainPowerTerminalReservation1'])]:
 moving=[d.getObject(n) for n in names]
 # Sampled5mm steps; intentionally report sampling, not a continuous sweep proof.
 against=[o for o in objs if o.Name not in names and o.Name not in battery_names and not o.Name.startswith('Rear'+('Stop' if prefix=='stop' else 'Power')+'Lid')]
 collisions=set()
 for delta in range(0,51,5):
  for moving_obj in moving:
   s=moving_obj.Shape.copy();s.translate(App.Vector(0,0,delta))
   for q in against:
    if q.Shape.BoundBox.intersect(s.BoundBox) and q.Shape.common(s).Volume>.001:collisions.add(q.Name)
 services[prefix+'_lid_lift50_sampled5mm']=sorted(collisions)
# Battery service against changed parts only; base E3 check inherited.
old=json.loads((BASE/'two-story/validation.json').read_text());bat=[]
for name in old['moving_parts']:
 o=d.getObject(name)
 if not o:continue
 bb=o.Shape.BoundBox
 if name=='BatteryModuleHarness':
  # Curved route AABB falsely fills empty space; use2mm translation samples for guide only.
  for dx,dz in [(0,z) for z in range(0,9,2)]+[(-x,8) for x in range(0,221,2)]:
   ss=o.Shape.copy();ss.translate(App.Vector(dx,0,dz))
   for q in objs:
    if q.Name in changed and q.Shape.BoundBox.intersect(ss.BoundBox) and q.Shape.common(ss).Volume>.001:bat.append([name,q.Name,dx,dz])
  continue
 for xyz,size in [([bb.XMin,bb.YMin,bb.ZMin],[bb.XLength,bb.YLength,bb.ZLength+8]),([bb.XMin-220,bb.YMin,bb.ZMin+8],[bb.XLength+220,bb.YLength,bb.ZLength])]:
  s=Part.makeBox(*size,App.Vector(*xyz))
  for q in objs:
   if q.Name in changed and q.Shape.BoundBox.intersect(s.BoundBox) and q.Shape.common(s).Volume>.001:bat.append([name,q.Name])
services['battery']=bat
# Empty deck vertically lifted with fixings removed and optional straps detached.
moving=['AluminumDeckD3'];s=Part.makeBox(300,300,204,App.Vector(-150,-150,229))
check('deck_lift',s,[o for o in objs if o.Name not in moving and not o.Name.startswith(('DeckBolt','DeckSlotNut'))])
# 250-square box representative; check footprint at deck surface, excluding deck support.
check('250square_cargo_example',Part.makeBox(250,250,100,App.Vector(-125,-125,233)),[o for o in objs if o.Name!='AluminumDeckD3'])
meshes=[]
for f in HERE.glob('*.stl'):
 m=Mesh.Mesh(str(f));bb=m.BoundBox;meshes.append(dict(file=f.name,closed=m.isSolid(),size_mm=[bb.XLength,bb.YLength,bb.ZLength]))
# Independent checks against the manufacturer dimension audit, not mesh appearance.
audit=json.loads((HERE/'switch-dimensions.json').read_text())
a=audit['main_switch'];front_z=a['mounting_face_Z_mm'];main=d.getObject('MainPower_3214').Shape
front_shape=main.common(Part.makeBox(100,100,50,App.Vector(-250,14,front_z)))
bb=front_shape.BoundBox
assert abs(bb.XLength-a['front_width_mm'])<1e-6 and abs(bb.YLength-a['front_length_mm'])<1e-6
assert abs(bb.ZLength-a['front_projection_from_mounting_face_mm'])<1e-6
lid=d.getObject('RearStopLidPLA').Shape
# Manufacturer key tip lies13.05 from center with the chosen22.5/24.3 cut.
assert lid.common(Part.makeBox(3.28,.15,5,App.Vector(-197.64,-72.1,175.4))).Volume<1e-6
catalog_checks={'main_front_dimensions':True,'estop_key_tip_clear':True,'rear_tab_limit_Z_mm':a['rear_tab_limit_Z_mm']}
out=dict(catalog_dimension_checks=catalog_checks,revision='E4',checked_pairs=checks,new_interferences=hits,services=services,meshes=meshes,passed=not hits and not any(services.values()) and all(x['closed'] and max(x['size_mm'])<256 for x in meshes),
 installed_grid_constraints={k:v for k,v in installed_grid_constraints.items() if v},maintenance_condition='Remove battery module before grid underside tool work and switch-lid servicing',
 native_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),actual_hardware_wiring_and_PLA_tests_complete=False,
 limitations=['Main nut dimensions unpublished in consulted source; mating terminal/finished lead SKU not selected. Published3214 front dimensions are applied; hidden body remains allocated.','Harness route service check is sampled2mm, not continuous or cable-flex qualification; service loop100mm initial allowance','Electrical transients and restart software untested','No physical strength/creep tests'])
(HERE/'validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2),flush=True)
