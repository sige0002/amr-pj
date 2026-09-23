"""D6.7 side-opening cargo plate on two rated torque hinges, two metal hand locks.

All quoted metal geometry is unchanged. Empty-lid hinges use bolted PLA adapters;
closed cargo load bears directly on the existing two aluminum support rails.
"""
from pathlib import Path
from itertools import combinations
import importlib.util,json,math,hashlib,sys
import FreeCAD as App
import Part,MeshPart
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;SRC=BASE/'control-layout'
sys.path.insert(0,str(BASE));from hardware_geometry import slotnut_at
spec=importlib.util.spec_from_file_location('controls_geometry',SRC/'build_controls.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
V=App.Vector;box=c.box;fuse=c.fuse;hits=c.hits;j=c.j;d6=c.d6
_shape_cache={}
def hits(s,objects):
 out=[];bb=s.BoundBox
 for o in objects:
  if o.Name not in _shape_cache:
   t=o.Shape;_shape_cache[o.Name]=(t,t.BoundBox)
  t,tbb=_shape_cache[o.Name]
  if bb.intersect(tbb):
   volume=s.common(t).Volume
   if volume>.001:out.append(dict(part=o.Name,overlap_mm3=volume))
 return out
NAME='AMR01_HingedDeck_D67';AXIS=V(0,172.5,249.5)
RHO={'PLA':1.24e-6,'steel':7.85e-6,'aluminum':2.7e-6}
P=dict(revision='D6.7',date='2026-09-23',hinge='Sugatsune HG-TS15',hinge_qty=2,hinge_centers_x_mm=[-126,126],hinge_axis_yz_mm=[172.5,249.5],opening_deg=[0,90],opens_toward='+Y',operator_side='rear -X',hinge_torque_each_Nm=1.5,initial_torque_tolerance=[-.2,.4],hinge_catalog_mass_each_kg=.0641,plate_LWT_mm=[300,300,4],plate_bottom_top_z_mm=[229,233],quoted_plate_unchanged=True,closed_locks='TRUSCO B36-0615 M6x15 butterfly bolts x2, each with3 M6 OD18 t1 steel washers',closed_lock_xy_mm=[[-105,-135],[105,-135]],unload_before_open=True,remove_cargo_straps_before_open=True,production_print_release=False)

def cyl(r,h,p,n=(0,0,1)):return Part.makeCylinder(r,h,V(*p),V(*n))
def rotate(s,deg):
 t=s.copy();t.rotate(AXIS,V(1,0,0),-deg);return t

def hinge_torque_summary(doc,moving,mass):
 """Maximum gravity moment over 0..90, including the CG below the axis."""
 lid_mass=sum(mass(doc.getObject(n)) for n in moving)
 a=sum(mass(doc.getObject(n))*9.80665*(AXIS.y-d6.center(doc.getObject(n).Shape)[1])/1000 for n in moving)
 b=sum(mass(doc.getObject(n))*9.80665*(AXIS.z-d6.center(doc.getObject(n).Shape)[2])/1000 for n in moving)
 angles=[0.,math.pi/2]
 critical=math.atan2(b,a)
 if 0<critical<math.pi/2:angles.append(critical)
 angle=max(angles,key=lambda t:abs(a*math.cos(t)+b*math.sin(t)))
 peak=abs(a*math.cos(angle)+b*math.sin(angle))
 # Additional centered mass is only a diagnostic, not a permitted payload.
 # Its own peak phase differs, so solve the combined vector magnitude.
 ay=9.80665*AXIS.y/1000;az=9.80665*(AXIS.z-231)/1000
 A=ay*ay+az*az;B=2*(a*ay+b*az);C=a*a+b*b-2.4**2
 extra=(-B+math.sqrt(B*B-4*A*C))/(2*A)
 return dict(empty_lid_mass_kg=lid_mass,closed_gravity_moment_Nm=a,
  vertical_CG_gravity_moment_component_Nm=b,maximum_gravity_moment_Nm=peak,
  maximum_gravity_moment_angle_deg=math.degrees(angle),minimum_initial_pair_Nm=2.4,
  maximum_initial_pair_Nm=4.2,minimum_initial_hold_ratio=2.4/peak,
  extra_mass_at_center_limit_kg=extra,extra_mass_reference_center_z_mm=231,
  max_tangential_opening_hand_force_N=(4.2+peak)/(math.hypot(322.5,18.5)/1000),
  hand_force_scope='Tangential force at far plate edge; hand follows lid arc.',
  qualify_hot_worn_condition=True)

def equivalent_brep(a,b):
 # FreeCAD renormalises axes on document copies (signed zero / ~1e-16).
 # Compare all topology and geometry tokens, tolerating only1e-10 absolute
 # numeric roundoff, rather than expensive identical-solid booleans.
 aa=a.exportBrepToString().split();bb=b.exportBrepToString().split()
 if len(aa)!=len(bb):return False
 for x,y in zip(aa,bb):
  if x==y:continue
  try:
   if abs(float(x)-float(y))>1e-10:return False
  except ValueError:return False
 return True

def interval_box(s,start,end):
 """Continuous conservative AABB: exact sinusoid extrema for every source-BB corner."""
 b=s.BoundBox;ys=[];zs=[];a0=math.radians(start);a1=math.radians(end)
 for y in [b.YMin,b.YMax]:
  for z in [b.ZMin,b.ZMax]:
   dy=y-AXIS.y;dz=z-AXIS.z
   # y=dy*cos(a)+dz*sin(a), z=dz*cos(a)-dy*sin(a)
   for A,B,vals,origin in [(dy,dz,ys,AXIS.y),(dz,-dy,zs,AXIS.z)]:
    cand=[a0,a1];t=math.atan2(B,A)
    cand += [t+k*math.pi for k in range(-2,3) if a0<t+k*math.pi<a1]
    vals.extend(origin+A*math.cos(a)+B*math.sin(a) for a in cand)
 return box(b.XMin,min(ys),min(zs),b.XLength,max(ys)-min(ys),max(zs)-min(zs))

def main():
 old=App.openDocument(str(SRC/'AMR01_RearControls_D66.FCStd'));basev=json.loads((SRC/'validation.json').read_text())
 doc=App.newDocument(NAME);doc.Label='AMR D6.7 | side-opening metal deck | rear E-STOP'
 removed=['DeckBolt'+str(i) for i in range(6)]+['DeckSlotNut'+str(i) for i in [1,2,3,5]]
 for o in old.Objects:
  if hasattr(o,'MaterialBasis') and o.Name not in removed:doc.copyObject(o,False)
 new=[];printed=[];moving=[];released=[];mounts=[];hinge_sweep={}
 def add(name,s,mat,note,color=None,move=False,mass=None):
  assert s.isValid() and len(s.Solids)>0,name
  o=doc.addObject('PartDesign::Feature',name);o.Shape=s
  for k,v in [('MaterialBasis',mat),('ModelNote',note)]:o.addProperty('App::PropertyString',k,'Design');setattr(o,k,v)
  if mass is not None:o.addProperty('App::PropertyFloat','CatalogMassKg','Design');o.CatalogMassKg=mass
  if App.GuiUp and color:o.ViewObject.ShapeColor=color
  new.append(name)
  if mat=='PLA':printed.append(name)
  if move:moving.append(name)
  return o
 def m4set(prefix,x,y,z,under,move):
  add(prefix+'Bolt',j.screw((x,y,z),(0,0,-1),4,16),'steel','M4x16 cap from planned60-pack; nominal threads.',move=move)
  add(prefix+'Washer',cyl(6,1,(x,y,under-1)).cut(cyl(2.25,1,(x,y,under-1))),'steel','M4 OD12 t1 from shared purchase pack.',move=move)
  add(prefix+'Nut',j.hexagon(x,y,under-4.2,7,3.2).cut(cyl(2.1,3.2,(x,y,under-4.2))),'steel','M4 hex nut; qualify anti-loosening with witness marks.',move=move)
 for i,cx in enumerate([-126,126]):
  # Lid adapter uses four existing grid locations, away from underlying rails.
  lid=box(cx-25,27,233,50,140,10)
  lid_holes=[(math.copysign(125,cx),35),(math.copysign(125,cx),85),(cx-18,156.5),(cx+18,156.5)]
  lid=lid.cut(Part.makeCompound([cyl(2.25,14,(x,y,232)) for x,y in lid_holes]+[cyl(4.25,5,(x,y,239)) for x,y in lid_holes[:2]]+[cyl(6.5,5,(x,y,232)) for x,y in lid_holes[2:]])).removeSplitter()
  add(f'HatchMovingAdapter_{i}',lid,'PLA','10mm continuousplate; deckbolt counterbores4mm, hingefixing nutpockets4mm. Bolts at existingX+-125,Y35/85; hingeatY156.5. Empty lid support only. Print solid, layers in XY; static/creep validation required.',(.19,.51,.75),move=True)
  for k,(x,y) in enumerate(lid_holes[:2]):m4set(f'HatchDeckFix_{i}_{k}',x,y,239,229,True)
  # Fixed bracket: root below moving hardware, outer flat hinge shelf. No
  # extra extrusion or drilled frame. Four millimetre ribs avoid nut access.
  root=box(cx-32,150,202,64,4.5,22)
  shelf=box(cx-32,179,237,64,31,6)
  webs=[]
  for dx in [-4,0]:
   pts=[V(cx+dx,153.5,207),V(cx+dx,204,237),V(cx+dx,179,237),V(cx+dx,153.5,222)]
   webs.append(Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(V(4,0,0)))
  # Positive90degree stop: empty movingadapter touches Y166 at90deg.
  # The return is above hinge/bolt sweeps; short L-key access remains below.
  stop_post=box(cx-20,198,243,40,12,43)
  stop_return=box(cx-20,166,276,40,44,10)
  fixed=fuse([root,shelf,stop_post,stop_return]+webs)
  cut=[]
  for k,x in enumerate([cx-15,cx+15]):
   cut.append(cyl(3.25,9,(x,149,214),(0,1,0)))
   add(f'HatchFrameBolt_{i}_{k}',j.screw((x,155.5,214),(0,-1,0),6,12),'steel','Reuse four removed deck M6x12 bolts,4.5mm root+1mm washer.')
   add(f'HatchFrameWasher_{i}_{k}',cyl(9,1,(x,154.5,214),(0,1,0)).cut(cyl(3.25,1,(x,154.5,214),(0,1,0))),'steel','M6 OD18 t1, shared30-pack.')
   add(f'HatchFrameNut_{i}_{k}',slotnut_at((x,150,214),(0,-1,0),(1,0,0)),'steel','Reuse four removed deck HNTT6-6 nuts. Do not add purchase twice.')
   mounts.append(dict(xyz=[x,150,214],bolt=f'HatchFrameBolt_{i}_{k}',thread_overlap_mm=5.3,slot_bottom_clearance_mm=2.5))
  for x in [cx-18,cx+18]:cut.append(cyl(2.25,9,(x,188.5,236)))
  fixed=fixed.cut(Part.makeCompound(cut)).removeSplitter()
  add(f'HatchFixedAdapter_{i}',fixed,'PLA','Root bolted to outer3030 slot attwo points; ribbed shelf andpositive90degstop. No frame/deck machining. Empty lid hinge reaction only; no forcingpaststop.',(.19,.51,.75))
  # Manufacturer dimension-based nominal hinge. Leaves are separate so opening
  # is explicit. Mass64.1g per complete hinge is divided equally for CG model.
  for which,y0,hy,move in [('Moving',148.5,156.5,True),('Fixed',179,188.5,False)]:
   leaf=box(cx-25,y0,243,50,17.5,2)
   leaf=leaf.cut(Part.makeCompound([cyl(2.15,4,(x,hy,242)) for x in [cx-18,cx+18]]))
   # Split barrel into alternating axial segments; no fictitious solid overlap.
   segments=[(-25,12),(-.5,12)] if move else [(-12.9,12.3),(11.6,13.4)]
   pieces=[leaf];bridges=[];barrels=[]
   for a,L in segments:
    barrel=cyl(6,L,(cx+a,172.5,249.5),(1,0,0))
    bridge=box(cx+a,165 if move else 175,244,L,5,3)
    pieces += [barrel,bridge]
    barrels.append(barrel);bridges.append(bridge)
   if move:hinge_sweep[f'HGTS15_Moving_{i}']=dict(rotating=[leaf]+bridges,invariant=barrels)
   o=add(f'HGTS15_{which}_{i}',fuse(pieces),'steel','Nominal outline from manufacturer drawing:50x48,t2,hole36x32,axis6.5 aboveleaf. SupplierSTEP requireslogin and was not used; internal friction stack not modeled.',(.65,.67,.69),move=move,mass=.03205)
   for k,x in enumerate([cx-18,cx+18]):m4set(f'HatchHinge{which}Fix_{i}_{k}',x,hy,245,237,move)
 # Positive metal threaded locks opposite the hinge. Three steel washers
 # preserve the original8mm slot projection with readily available M6x15.
 for i,x in enumerate([-105,105]):
  y=-135
  for k in range(3):
   n=f'HatchLockWasher_{i}_{k}';add(n,cyl(9,1,(x,y,233+k)).cut(cyl(3.25,1,(x,y,233+k))),'steel','M6 OD18 t1; three perlock, remove withlock beforeopening.');released.append(n)
  # A conservative wing outline, not a manufacturer's detailed STEP.
  shape=cyl(3,15,(x,y,236),(0,0,-1)).fuse(cyl(5,3,(x,y,236))).fuse(box(x-13,y-2,239,26,4,10))
  n=f'HatchLockWingBolt_{i}';add(n,shape,'steel','SelectedTRUSCO B36-0615 M6x15; conservative26x13 winghead. Measured head/retention toverify. 3mmsteelwashers+4mmdeck=>8mmprojection,1mmslotfloorclearance.');released.append(n)
 # All original moving plate/stopper objects retain their closed geometry.
 moving += [o.Name for o in doc.Objects if o.Name.startswith(('AluminumDeck','PrintedStop','StopBolt','StopWasher','StopNut'))]
 doc.recompute();print('Hatch geometry built; validating closed assembly',flush=True)
 physical=[o for o in doc.Objects if hasattr(o,'MaterialBasis') and o.MaterialBasis!='reference'];refs=[o for o in doc.Objects if hasattr(o,'MaterialBasis') and o.MaterialBasis=='reference']
 collisions=[]
 for a,b in combinations(physical,2):
  if a.Name not in new and b.Name not in new:continue
  for h in hits(a.Shape,[b]):collisions.append(dict(a=a.Name,**h))
 ref_hits={r.Name:hits(r.Shape,[o for o in physical if o.Name in new]) for r in refs};ref_hits={k:v for k,v in ref_hits.items() if v}
 base_moving=basev['battery_service'];battery=[]
 base_released=json.loads((BASE/'two-story/validation.json').read_text())['released_before_service']
 base_battery_names=sorted(set(x['part'] for x in base_moving));fixed_service=[o for o in physical+refs if o.Name not in base_battery_names+base_released]
 for q in base_moving:
  battery.append(dict(part=q['part'],from_mm=q['from_mm'],to_mm=q['to_mm'],hits=hits(d6.swept_bbox(doc.getObject(q['part']).Shape,q['from_mm'],q['to_mm']),fixed_service)))
 # Load and its straps are removed, locks disengaged, before lid movement.
 fixed=[o for o in physical+refs if o.Name not in moving+released and not o.Name.startswith(('CargoEnvelope','StrapRoute'))]
 motion=[];radial_proofs=[]
 for name in moving:
  o=doc.getObject(name)
  bb=o.Shape.BoundBox
  dy=max(bb.YMin-AXIS.y,AXIS.y-bb.YMax,0);dz=max(bb.ZMin-AXIS.z,AXIS.z-bb.ZMax,0)
  radial=math.hypot(dy,dz);maxy=interval_box(o.Shape,0,90).BoundBox.YMax
  proved=radial>6.001 and maxy<174.999
  if proved:radial_proofs.append(dict(part=name,barrel_radial_clearance_mm=radial-6,minimum_fixed_bridge_Y_mm=175,maximum_sweep_Y_mm=maxy))
  for angle in range(0,90,5):
   candidates=[a for a in fixed if not (name.startswith('HGTS15_Moving') and a.Name==name.replace('Moving','Fixed')) and not (proved and a.Name.startswith('HGTS15_Fixed'))]
   if name in hinge_sweep:
    shapes=hinge_sweep[name]['invariant']+[interval_box(s,angle,angle+5) for s in hinge_sweep[name]['rotating']]
    h=[q for s in shapes for q in hits(s,candidates)]
   else:h=hits(interval_box(o.Shape,angle,angle+5),candidates)
   if h:motion.append(dict(part=name,interval_deg=[angle,angle+5],hits=h))
 print('Continuous opening boxes checked',len(motion),flush=True)
 # Internal hinge interface uses exact geometry at1degree, while external
 # interference above uses continuous boxes. Segmented barrel model only.
 internal=[]
 for i in range(2):
  for a in range(91):
   h=hits(rotate(doc.getObject(f'HGTS15_Moving_{i}').Shape,a),[doc.getObject(f'HGTS15_Fixed_{i}')])
   if h:internal.append(dict(index=i,angle_deg=a,hits=h))
 tools=[]
 for m in mounts:
  x,y,z=m['xyz'];tools.append(dict(bolt=m['bolt'],hits=hits(cyl(4,40,(x,162,z),(0,1,0)),[o for o in physical+refs if o.Name!=m['bolt']])))
 hand=[]
 for i,x in enumerate([-105,105]):
  hand.append(dict(lock=i,hits=hits(cyl(20,70,(x,-135,249)),[o for o in physical+refs if o.Name!=f'HatchLockWingBolt_{i}'])))
 invariant=[o.Name for o in old.Objects if hasattr(o,'MaterialBasis') and o.Name not in removed]
 unchanged=all(equivalent_brep(doc.getObject(n).Shape,old.getObject(n).Shape) for n in invariant)
 def mass(o):return o.CatalogMassKg if hasattr(o,'CatalogMassKg') else o.Shape.Volume*RHO.get(o.MaterialBasis,0)
 removed_mass=sum(mass(old.getObject(n)) for n in removed);added_mass=sum(mass(doc.getObject(n)) for n in new)
 mass_total=basev['mass']['estimated_base_kg']+added_mass-removed_mass
 # 1.5Nm *2 *0.8: minimum catalogue initial torque, not a lifetime guarantee.
 torque=hinge_torque_summary(doc,moving,mass)
 ledger=[dict(name=n,mass_kg=mass(doc.getObject(n)),center_mm=d6.center(doc.getObject(n).Shape)) for n in new]+[dict(name='remove '+n,mass_kg=-mass(old.getObject(n)),center_mm=d6.center(old.getObject(n).Shape)) for n in removed]
 report=dict(parameters=P,source_sha256=hashlib.sha256((SRC/'AMR01_RearControls_D66.FCStd').read_bytes()).hexdigest(),physical_parts=len(physical),new_closed_pairs_checked=sum(a.Name in new or b.Name in new for a,b in combinations(physical,2)),closed_collisions=collisions,reference_collisions=ref_hits,battery_service=battery,continuous_opening_bbox_hits=motion,continuous_radial_clearance_proofs=radial_proofs,internal_hinge_sample_hits=internal,frame_tool_checks=tools,lock_hand_checks=hand,retained_shapes_BRep_equal=unchanged,new_objects=new,removed_objects=removed,moving_parts=moving,released_before_open= released+['StrapRouteX','StrapRouteY','CargoEnvelopeD3'],torque=torque,mass=dict(estimated_base_kg=mass_total,source_kg=basev['mass']['estimated_base_kg'],added_kg=added_mass,removed_kg=removed_mass,new_PLA_kg=sum(mass(doc.getObject(n)) for n in printed),ledger=ledger,actually_weighed=False),limits=['Hinges andwingbolts are drawing-based nominal models; receivinginspection remains.','Onlyempty lid mayopen. Closedcargo load bears onunchangedmetalrails; cargo belts remainrequired.','Noformalhinge-adapterFEM or lifetime torquequalification. PLAadapters are prototypeonly.','PreviousclampeddeckFEA is notvalidationofnewtwo-lockboundary. See newconservativehandcalculation.'])
 (HERE/'parameters.json').write_text(json.dumps(P,ensure_ascii=False,indent=2)+'\n');(HERE/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 doc.saveAs(str(HERE/(NAME+'.FCStd')))
 print(json.dumps({k:report[k] for k in ['closed_collisions','reference_collisions','continuous_opening_bbox_hits','internal_hinge_sample_hits','frame_tool_checks','lock_hand_checks','torque']},ensure_ascii=False),flush=True)
 assert not collisions and not ref_hits and not motion and not internal
 assert not any(q['hits'] for q in battery+tools+hand) and unchanged
 assert torque['maximum_gravity_moment_Nm']<2.4
 Part.export(physical,str(HERE/(NAME+'-structure.step')))
 Part.export(physical+[o for o in refs if o.Name in ['BatteryBL1860B','BatteryAdapter03','Reserved_Computer','EStop_XA1E_BV302R','ARM_3212','MainPower_3214']],str(HERE/(NAME+'.step')))
 for f in HERE.glob('*.step'):f.write_text('\n'.join(x.rstrip() for x in f.read_text().splitlines())+'\n')
 manifest=[]
 for n in printed:
  s=doc.getObject(n).Shape.copy();bb=s.BoundBox;s.translate(V(-bb.XMin,-bb.YMin,-bb.ZMin))
  MeshPart.meshFromShape(Shape=s,LinearDeflection=.06,AngularDeflection=.25,Relative=False).write(str(HERE/(n+'.stl')))
  manifest.append(dict(file=n+'.stl',size_mm=[bb.XLength,bb.YLength,bb.ZLength],solid_mass_g=mass(doc.getObject(n))*1000,prototype_only=True,orientation='Moving adapter flatXY; fixedadapter onX side, root/shelf/ribs inlayerplane. Solidloadpaths; slicer/receivedfitqualificationrequired.'))
 (HERE/'print_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 print('D6.7 PASSED',mass_total,flush=True)
if __name__=='__main__':main()
