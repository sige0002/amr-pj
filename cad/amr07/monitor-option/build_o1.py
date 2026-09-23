"""Optional 7-inch monitor packaging study, independent of standard E3.
Run via FreeCAD Python. Monitor envelope is a design requirement, NOT vendor CAD.
"""
from pathlib import Path
import importlib.util,json,hashlib,math
import FreeCAD as App
import Part,MeshPart
HERE=Path(__file__).resolve().parent;BASE=HERE.parent
spec=importlib.util.spec_from_file_location('base_helpers',BASE/'direct-hinge/build_d68.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
V=App.Vector;box=b.box;cyl=b.cyl;fuse=b.fuse
NAME='AMR01_OptionalMonitor_O1';SOURCE=BASE/'reviewed-design/AMR01_Reviewed_E4.FCStd'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 old=App.openDocument(str(SOURCE));d=App.newDocument(NAME)
 d.Label='OPTION O1 | 7in monitor study | STANDARD E4 UNCHANGED'
 for o in old.Objects:
  if hasattr(o,'MaterialBasis'):d.copyObject(o,False)
 added=[]
 def add(n,s,mat,note):
  assert s.isValid() and s.Solids,n
  o=d.addObject('PartDesign::Feature',n);o.Shape=s
  for k,v in [('MaterialBasis',mat),('ModelNote',note)]:o.addProperty('App::PropertyString',k,'Design');setattr(o,k,v)
  added.append(n);return o
 def bolt(n,p,direction,diam,length):return add(n,b.j.screw(p,direction,diam,length,head_diameter=5.5 if diam==3 else None),'steel','Nominal socket screw, helical thread omitted. Optional hardware; not standard BOM.')
 def washer(n,p,normal,od,id,t):return add(n,cyl(od/2,t,p,normal).cut(cyl(id/2,t,p,normal)),'steel','Metal washer against printed flange; no direct metal contact with display.')
 def nut(n,p,normal,diam,af,h):
  s=b.j.hexagon(0,0,0,af,h).cut(cyl((diam+.2)/2,h,(0,0,0)))
  s.Placement=App.Placement(V(*p),App.Rotation(V(0,0,1),V(*normal)))
  return add(n,s,'steel','Nominal through hex nut; thread omitted.')
 # Thin flat metal bridge is behind deck and ahead of the E-stop hand corridor.
 plate=box(-158,-150,239,3,300,60)
 for y in [-135,135]:
  for z in [250,285]:plate=plate.cut(cyl(3.3,5,(-159,y,z),(1,0,0)))
 for y in [20,110]:
  for z in [260,285]:plate=plate.cut(cyl(2.25,5,(-159,y,z),(1,0,0)))
 add('OptBridgePlate',plate,'aluminum','A5052 flat300x60x3,4 D6.6 +4 D4.5 through holes. Buy cut/drilled/deburred; no user machining assumed. No current manufacturing quote.')
 for side in [-1,1]:
  suffix='L' if side<0 else 'R'
  points=[(-155,199),(-70,199),(-70,229),(-127,265),(-147,299),(-155,299)]
  verts=[V(x,150*side,z) for x,z in points];verts.append(verts[0])
  support=Part.Face(Part.makePolygon(verts)).extrude(V(0,8*side,0))
  support=support.fuse(box(-155,120 if side>0 else -158,239,8,38,60))
  # Two triangular gussets transfer the bridge load into the rail-side web.
  for z in [239,289]:
   verts=[V(-147,142*side,z),V(-117,150*side,z),V(-147,150*side,z)]
   support=support.fuse(Part.Face(Part.makePolygon(verts+[verts[0]])).extrude(V(0,0,8)))
  for k,x in enumerate([-132,-82]):
   support=support.cut(cyl(3.3,12,(x,148*side,214),(0,side,0)))
   washer(f'OptFrameWasher{suffix}{k}',(x,158*side,214),(0,side,0),18,6.6,1.6)
   bolt(f'OptFrameBolt{suffix}{k}',(x,159.6*side,214),(0,-side,0),6,18)
   add(f'OptFrameSlotNut{suffix}{k}',b.h.d6.slotnut_at((x,150*side,214),(0,-side,0)),'steel','HNTT6-6 profile from chassis. Four ADDITIONAL nuts, not taken from standard spare count. End insertion may require unloading/removing deck and opening rail end.')
  for k,z in enumerate([250,285]):
   support=support.cut(cyl(3.3,12,(-157,135*side,z),(1,0,0)))
   washer(f'OptBridgeWasher{suffix}{k}',(-159,135*side,z),(1,0,0),12,6.6,1)
   bolt(f'OptBridgeBolt{suffix}{k}',(-159,135*side,z),(1,0,0),6,20)
   nut(f'OptBridgeNut{suffix}{k}',(-147,135*side,z),(1,0,0),6,10,5)
  add('OptSideSupport'+suffix,support.removeSplitter(),'PLA','Optional two-bolt-per-rail side support with gussets. Solid bearing walls required. Print creep/push/vibration tests pending; not a handle.')
 # Local U=screen width along Y, V=screen up tilted10deg toward front,
 # N=back normal. Monitor faces rear/up. Offset65Y clears E-stop hand approach.
 a=math.radians(10);up=V(math.sin(a),0,math.cos(a));back=V(math.cos(a),0,-math.sin(a))
 tr=App.Placement(V(-218,65,245),App.Rotation(V(0,1,0),up,back,'ZXY'))
 def screen(s):s.Placement=tr;return s
 add('OptMonitorEnvelope',screen(box(-100,0,0,200,135,30)),'reference','DESIGN ENVELOPE only: max200x135x30, max0.60kg. No product selected; ports, bezel, ventilation and delivered dimensions must be checked.')
 # Open-backed capture tray.0.6mm nominal side/end gaps and four removable bezel screws.
 tray=box(-110,-10,30.6,220,155,4)
 tray=tray.cut(box(-75,55,30,150,55,6))
 for u in [-103.6,100.6]:tray=tray.fuse(box(u,-3.6,0,3,142.2,34.6))
 for v in [-3.6,135.6]:tray=tray.fuse(box(-103.6,v,0,207.2,3,34.6))
 for u in [-105,105]:
  for v in [-5,140]:tray=tray.fuse(box(u-4,v-4,0,8,8,34.6))
 # Broad side windows permit cables; final port fit remains product-dependent.
 for u in [-111,100.5]:tray=tray.cut(box(u,15,-1,11,105,25))
 tray=screen(tray)
 bosses=fuse([box(-191,y-8,z-8,33,16,16) for y in [20,110] for z in [260,285]])
 # Trim only adapter bosses; preserve the cradle edge walls.
 bosses=bosses.cut(screen(box(-112,-12,-50,224,160,80.6)))
 tray=tray.fuse(bosses)
 for k,(y,z) in enumerate([(y,z) for y in [20,110] for z in [260,285]]):
  tray=tray.cut(cyl(2.25,40,(-192,y,z),(1,0,0)))
  pock=b.j.hexagon(0,0,0,7.4,3.8);pock.Placement=App.Placement(V(-169.6,y,z),App.Rotation(V(0,0,1),V(1,0,0)))
  tray=tray.cut(pock).cut(box(-170,y-3.7,z+1,4.4,7.4,8))
  washer('OptTrayWasher'+str(k),(-155,y,z),(1,0,0),9,4.5,1)
  bolt('OptTrayBolt'+str(k),(-154,y,z),(-1,0,0),4,16)
  nut('OptTrayNut'+str(k),(-169.2,y,z),(1,0,0),4,7,3.2)
 # Front bezel captures CASE edges only. Real selected bezel/touch area must fit.
 bezel=box(-110,-10,-3,220,155,2.4).cut(box(-97,3,-4,194,129,5))
 # Four end holes use through screws/nuts OUTSIDE monitor footprint.
 for k,(u,v) in enumerate([(u,v) for u in [-105,105] for v in [-5,140]]):
  bezel=bezel.cut(cyl(1.7,4,(u,v,-4)))
  hole=screen(cyl(1.7,40,(u,v,-4)));tray=tray.cut(hole)
  # Bolt38 nominal selected M3x40, head at front n=-3, tip n37; rear nut3mm.
  bp=tr.multVec(V(u,v,-3));normal=back
  bolt('OptBezelBolt'+str(k),tuple(bp),tuple(normal),3,40)
  np=tr.multVec(V(u,v,34.6));nut('OptBezelNut'+str(k),tuple(np),tuple(normal),3,5.5,2.4)
 add('OptMonitorTrayPLA',tray.removeSplitter(),'PLA','Mock capture tray plus bridge bosses. Foam pads and retention on CASE bezel only; aperture must be matched to actual monitor. Rear opening is not thermal validation.')
 add('OptMonitorBezelPLA',screen(bezel),'PLA','Removable front retaining bezel with fourM3x40. Only selected CASE edges may bear load; do not clamp LCD glass. Display not selected, print-for-fit only.')
 # Route is a packaging guide and removable with the optional assembly.
 add('OptCableRoute',b.d6.pipe([[-182,161,298],[-167,168,285],[-142,168,255],[-105,165,214],[-105,164,120],[-65,60,124]],3),'reference','HDMI + USB route guide only. Strain relief at screen/support/rail. Actual plugs, bends, fasteners, supply and detached service loop unverified. No connection to motor18V.')
 d.recompute()
 for o in d.Objects:
  if hasattr(o,'MaterialBasis'):assert o.Shape.isValid() and o.Shape.Solids,o.Name
 for o in old.Objects:
  if hasattr(o,'MaterialBasis'):assert b.h.equivalent_brep(o.Shape,d.getObject(o.Name).Shape),o.Name
 physical=[d.getObject(n) for n in added if d.getObject(n).MaterialBasis!='reference']
 rho={'PLA':1.24e-6,'steel':7.85e-6,'aluminum':2.7e-6}
 mass=sum(o.Shape.Volume*rho[o.MaterialBasis] for o in physical)
 pla=sum(o.Shape.Volume*rho['PLA'] for o in physical if o.MaterialBasis=='PLA')
 req=dict(revision='O1',optional=True,standard_CAD=str(SOURCE.relative_to(BASE)),standard_native_sha256=sha(SOURCE),source_objects_unchanged=True,
  monitor_envelope_mm=[200,135,30],monitor_max_mass_kg=.6,monitor_product_selected=False,tilt_from_vertical_deg=10,monitor_bottom_front_xyz_mm=[-218,65,245],
  frame_mounts_each_side=2,frame_bolt='M6x18',additional_slot_nuts=4,bridge_plate_mm=[300,60,3],bridge_holes=dict(D6_6=4,D4_5=4),
  additional_physical_parts=len(physical),new_PLA_parts=4,mechanical_solid_mass_kg=mass,PLA_solid_mass_kg=pla,cable_padding_allowance_kg=.08,
  max_option_mass_kg=mass+.6+.08,base_mass_kg=json.loads((BASE/'reviewed-design/geometry.json').read_text())['mass']['estimated_base_kg'],additional_parts=added,
  standard_BOM_modified=False,standard_power_budget_modified=False,production_release=False,
  exclusions=['actual monitor ports/mounting/bezel/thermal validation','final cable and connector geometry','printed strength and creep testing','actual manufacturing quote','complete electrical supply qualification'])
 (HERE/'requirements.json').write_text(json.dumps(req,ensure_ascii=False,indent=2)+'\n')
 d.saveAs(str(HERE/(NAME+'.FCStd')))
 for o in physical:
  if o.MaterialBasis=='PLA':
   s=o.Shape.copy()
   if o.Name.startswith('OptMonitor'):s.Placement=tr.inverse().multiply(s.Placement)
   bb=s.BoundBox;s.translate(V(-bb.XMin,-bb.YMin,-bb.ZMin))
   MeshPart.meshFromShape(Shape=s,LinearDeflection=.06,AngularDeflection=.25,Relative=False).write(str(HERE/(o.Name+'.stl')))
 Part.export([d.getObject('OptBridgePlate')],str(HERE/'OptionalMonitorBridge_300x60x3.step'))
 print(json.dumps({k:req[k] for k in ['additional_physical_parts','mechanical_solid_mass_kg','PLA_solid_mass_kg','max_option_mass_kg']},indent=2),flush=True)
if __name__=='__main__':main()
