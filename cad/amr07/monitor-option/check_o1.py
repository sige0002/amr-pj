from pathlib import Path
import json,itertools,hashlib,math
import FreeCAD as App
import Part,Mesh
HERE=Path(__file__).resolve().parent;BASE=HERE.parent
r=json.loads((HERE/'requirements.json').read_text());p=HERE/'AMR01_OptionalMonitor_O1.FCStd';d=App.openDocument(str(p))
added=set(r['additional_parts']);ref=['BatteryBL1860B','BatteryAdapter03','Reserved_Computer','Reserved_ComputerSupply','PicoOwned','Pico_RS485_HAT','PicoHeaderEnvelope','EStop_HW1B_V402R','MainPower_3214','OptMonitorEnvelope']
objs=[o for o in d.Objects if hasattr(o,'MaterialBasis') and (o.MaterialBasis!='reference' or o.Name in ref)]
checks=0;hits=[]
for a,b in itertools.combinations(objs,2):
 if not {a.Name,b.Name}&added:continue
 checks+=1
 if a.Shape.BoundBox.intersect(b.Shape.BoundBox):
  vol=a.Shape.common(b.Shape).Volume
  if vol>.001:hits.append([a.Name,b.Name,round(vol,4)])
new=[o for o in objs if o.Name in added]
services={}
# Above and rear approach to red E-stop; main rocker approached from rear.
volumes={'estop_above_hand_r35':Part.makeCylinder(35,100,App.Vector(-196,-85,212.4)),
'estop_rear_hand':Part.makeBox(130,70,65,App.Vector(-326,-120,185)),
'main_rear_hand':Part.makeBox(120,50,45,App.Vector(-321,39,153)),
'cargo':d.getObject('CargoEnvelopeD3').Shape}
for key,s in volumes.items():
 services[key]=[o.Name for o in new if o.Shape.BoundBox.intersect(s.BoundBox) and o.Shape.common(s).Volume>.001]
old=json.loads((BASE/'two-story/validation.json').read_text());bat=[]
for name in old['moving_parts']:
 o=d.getObject(name)
 if not o:continue
 bb=o.Shape.BoundBox
 for start,dims in [([bb.XMin,bb.YMin,bb.ZMin],[bb.XLength,bb.YLength,bb.ZLength+8]),([bb.XMin-220,bb.YMin,bb.ZMin+8],[bb.XLength+220,bb.YLength,bb.ZLength])]:
  s=Part.makeBox(*dims,App.Vector(*start))
  for q in new:
   if q.Shape.BoundBox.intersect(s.BoundBox) and q.Shape.common(s).Volume>.001:bat.append([name,q.Name])
services['battery_service']=bat
# Original36 holes: short fastener/tool reservation; not infinitely tall payload clearance.
grid=[]
for x in [-100,-50,0,50,100]:
 for y in [-100,-50,0,50,100]:
  s=Part.makeCylinder(4,30,App.Vector(x,y,229))
  for q in new:
   if q.Shape.BoundBox.intersect(s.BoundBox) and q.Shape.common(s).Volume>.001:grid.append([x,y,q.Name])
services['25_grid_short_fixing_envelopes']=grid
# Deck upright removal is checked and may require removing the whole option first.
bb=d.getObject('AluminumDeckD3').Shape.BoundBox
s=Part.makeBox(bb.XLength,bb.YLength,204,App.Vector(bb.XMin,bb.YMin,229))
services['deck_lift_with_option_installed']=[o.Name for o in new if o.Shape.BoundBox.intersect(s.BoundBox) and o.Shape.common(s).Volume>.001]
meshes=[]
for f in HERE.glob('*.stl'):
 m=Mesh.Mesh(str(f));bb=m.BoundBox;o=d.getObject(f.stem)
 meshes.append(dict(file=f.name,closed=m.isSolid(),single_CAD_solid=len(o.Shape.Solids)==1,size_mm=[bb.XLength,bb.YLength,bb.ZLength]))
# Preliminary support checks, design loads not validated rating.
# Conservatively sum 3g inertial moment for entire option at100mm and10N push at150mm.
M=r['max_option_mass_kg']*9.81*3*.1+10*.15
# Two web sections, each30mm wide x8 thick; weak-axis rectangular bending.
stress=(M*1000/2)*6/(30*8**2)
# Flat plate conservatively simply supported span270, section60x3,10N central push.
I=60*3**3/12;delta=10*270**3/(48*69000*I);sigma=(10*270/4)*1.5/I
mandatory=[v for k,v in services.items() if k!='deck_lift_with_option_installed']
out=dict(checked_pairs=checks,new_interferences=hits,services=services,meshes=meshes,
 preliminary_strength=dict(option_3g_plus10N_push_moment_Nm=M,PLA_two_webs_stress_MPa=stress,assumed_PLA_allowable_MPa=10,metal_bridge10N_stress_MPa=sigma,metal_bridge10N_deflection_mm=delta,actual_material_and_joint_testing=False),
 optional_mass_budget_kg=r['max_option_mass_kg'],base_plus_option_budget_kg=r['base_mass_kg']+r['max_option_mass_kg'],payload_for_existing21_5kg_gross_kg=21.5-r['base_mass_kg']-r['max_option_mass_kg'],
 passed=not hits and not any(mandatory) and all(m['closed'] and m['single_CAD_solid'] and max(m['size_mm'])<256 for m in meshes) and stress<10,
 native_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),production_release=False)
(HERE/'validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2),flush=True)
