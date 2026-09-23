"""Saved CAD collision, service, assembly access and sampled motion checks."""
from pathlib import Path
from itertools import combinations
import importlib.util,json,math
import FreeCAD as App
import Part
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('d68',HERE/'build_d68.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
doc=App.openDocument(str(HERE/(b.NAME+'.FCStd')));g=json.loads((HERE/'geometry.json').read_text())
physical=[o for o in doc.Objects if hasattr(o,'MaterialBasis') and o.MaterialBasis!='reference'];refs=[o for o in doc.Objects if hasattr(o,'MaterialBasis') and o.MaterialBasis=='reference']
cache={o.Name:(o.Shape,o.Shape.BoundBox) for o in physical+refs}
def hits(s,objs):
 bb=s.BoundBox;out=[]
 for o in objs:
  t,tbb=cache[o.Name]
  if bb.intersect(tbb):
   vol=s.common(t).Volume
   if vol>.001:out.append(dict(part=o.Name,overlap_mm3=vol))
 return out
collisions=[]
for a,c in combinations(physical,2):
 if a.Name in g['new_objects']+g['changed_objects'] or c.Name in g['new_objects']+g['changed_objects']:
  collisions += [dict(a=a.Name,**v) for v in hits(a.Shape,[c])]
rh={o.Name:hits(o.Shape,physical) for o in refs};rh={k:v for k,v in rh.items() if v}
rp=[]
for a,c in combinations(refs,2):
 if a.Name in g['new_objects'] or c.Name in g['new_objects']:rp += [dict(a=a.Name,**v) for v in hits(a.Shape,[c])]
print('CLOSED',json.dumps(dict(collisions=collisions,refs=rh,reference_pairs=rp)),flush=True)
bv=json.loads((HERE.parent/'two-story/validation.json').read_text())
service=[]
for name in bv['moving_parts']:
 fixed=[o for o in physical+refs if o.Name not in bv['moving_parts']+bv['released_before_service']]
 for a,c in zip(bv['parameters']['battery_service_waypoints_xyz_mm'],bv['parameters']['battery_service_waypoints_xyz_mm'][1:]):
  pieces=[doc.getObject(name).Shape]
  if name=='BatteryModuleHarness':
   points=[b.V(*p) for p in g['parameters']['battery_harness_points']]
   pieces=[Part.makeCylinder(3,(t-s).Length,s,t-s) for s,t in zip(points,points[1:])]+[Part.makeSphere(3,t) for t in points[1:-1]]
  service.append(dict(part=name,from_mm=a,to_mm=c,continuous_piecewise_bbox=True,hits=[q for piece in pieces for q in hits(b.d6.swept_bbox(piece,a,c),fixed)]))
pc=[]
for name in ['Reserved_Computer','ComputerTopPad']:
 fixed=[o for o in physical+refs if o.Name not in ['Reserved_Computer','ComputerTopPad','ComputerRetentionBelt']]
 for a,c in [([0,0,0],[0,0,8]),([0,0,8],[0,-230,8])]:pc.append(dict(part=name,from_mm=a,to_mm=c,hits=hits(b.d6.swept_bbox(doc.getObject(name).Shape,a,c),fixed)))
tools=[]
for m in g['frame_mounts']:
 x,y,z=m['xyz'];tools.append(dict(bolt=m['bolt'],stage='closed or open, outside frame',hits=hits(b.cyl(3,45,(x,158,z),(0,1,0)),[o for o in physical+refs if o.Name!=m['bolt']])))
for m in g['case_mounts']:
 x,y=m['xy_mm'];omitted=[m['bolt']]+bv['moving_parts']+bv['released_before_service']+[o.Name for o in physical+refs if o.Name.startswith(m['case']+'Lid') or o.Name in ['EStop_XA1E_BV302R','ARM_3212','MainPower_3214']]
 tools.append(dict(bolt=m['bolt'],stage='install cases before battery; remove case lid with switches',hits=hits(b.cyl(3,70,(x,y,122)),[o for o in physical+refs if o.Name not in omitted])))
approach=[]
for k,r in [('estop',35),('arm',16),('main_power',18)]:
 x,y,z=g['parameters'][k]['panel_center_mm'];approach.append(dict(control=k,hits=hits(b.cyl(r,180,(x,y,z+21)),physical+refs)))
print('SERVICE',json.dumps(dict(battery=[s for s in service if s['hits']],pc=[s for s in pc if s['hits']],tools=[s for s in tools if s['hits']],approach=approach)),flush=True)
# Continuous AABBs cull most pairs. Remaining close-contact pairs use an
# explicit1deg sweep, not a claim of full tolerance-qualified kinematics.
motion=[];candidates=0;cleared=0
fixed=[o for o in physical+refs if o.Name not in g['moving_parts']+g['released_before_open']]
for name in g['moving_parts']:
 shape=doc.getObject(name).Shape
 for angle in range(0,90,5):
  bb=b.h.interval_box(shape,angle,angle+5)
  possible=[o for o in fixed if bb.BoundBox.intersect(cache[o.Name][1])]
  candidates+=len(possible)
  if not possible:cleared+=1;continue
  possible=[o for o in possible if bb.common(cache[o.Name][0]).Volume>.001]
  if not possible:cleared+=1;continue
  for a in range(angle,angle+6):
   hs=hits(b.h.rotate(shape,a),possible)
   if hs:motion.append(dict(part=name,angle_deg=a,hits=hs))
print('MOTION',json.dumps(motion[:30]),'count',len(motion),flush=True)
out=dict(g,closed_collisions=collisions,reference_collisions=rh,reference_pairs=rp,battery_service=service,computer_service=pc,assembly_tools=tools,operator_approach=approach,motion_sample_step_deg=1,motion_hits=motion,continuous_boxes_cleared=cleared,motion_candidate_pairs=candidates,opening_stops_present=False,motion_range_deg=[0,90])
out['passed']=not (collisions or rh or rp or motion or any(s['hits'] for s in service+pc+tools+approach)) and g['retained_shapes_BRep_equal']
(HERE/'validation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('PASS',out['passed'],flush=True)
