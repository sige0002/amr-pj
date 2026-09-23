"""E4: changes AFTER independent E3 reviews. FreeCAD Python."""
from pathlib import Path
import importlib.util,json,hashlib
import FreeCAD as App
import Part,MeshPart
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;SOURCE=BASE/'pico-control/AMR01_PicoControl_E3.FCStd'
spec=importlib.util.spec_from_file_location('old',BASE/'direct-hinge/build_d68.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
V=App.Vector;box=b.box;cyl=b.cyl;fuse=b.fuse;NAME='AMR01_Reviewed_E4'
REMOVED=['PrintedStopXN','PrintedStopXP','PrintedStopYN','PrintedStopYP']+[f'{prefix}{i}' for prefix in ['StopBolt','StopWasher','StopNut'] for i in range(8)]
CHANGED=['AluminumDeckD3','MainPower_3214','EStop_HW1B_V402R','RearPowerLidPLA','RearStopCasePLA','RearPowerCasePLA']+[f'{p}{i}' for p in ['DeckBolt','DeckSlotNut'] for i in range(6)]+['StrapRouteX','StrapRouteY']
def main():
 old=App.openDocument(str(SOURCE));d=App.newDocument(NAME);d.Label='AMR E4 | REVIEWED SWITCH PACKAGING | CENTERED25-HOLE DECK'
 for o in old.Objects:
  if hasattr(o,'MaterialBasis') and o.Name not in REMOVED:d.copyObject(o,False)
 added=[]
 def add(n,s,mat,note):
  assert s.isValid() and s.Solids,n
  o=d.addObject('PartDesign::Feature',n);o.Shape=s
  for k,v in [('MaterialBasis',mat),('ModelNote',note)]:o.addProperty('App::PropertyString',k,'Design');setattr(o,k,v)
  added.append(n);return o
 plate=box(-150,-150,229,300,300,4)
 grid=[(x,y) for x in [-100,-50,0,50,100] for y in [-100,-50,0,50,100]]
 fixes=[(x,y) for x in [-125,0,125] for y in [-135,135]]
 tools=[cyl(2.25,6,(x,y,228)) for x,y in grid]+[cyl(3.3,6,(x,y,228)) for x,y in fixes]
 # Four identical30x6 rounded through slots, symmetric about vehicle origin.
 for x,y,axis in [(-140,0,'y'),(140,0,'y'),(0,-110,'x'),(0,110,'x')]:
  if axis=='y':s=fuse([box(x-3,y-12,228,6,24,6),cyl(3,6,(x,y-12,228)),cyl(3,6,(x,y+12,228))])
  else:s=fuse([box(x-12,y-3,228,24,6,6),cyl(3,6,(x-12,y,228)),cyl(3,6,(x+12,y,228))])
  tools.append(s)
 plate=plate.cut(Part.makeCompound(tools)).removeSplitter();d.getObject('AluminumDeckD3').Shape=plate
 d.getObject('AluminumDeckD3').Label='E4 deck 300x300x4 | 25 centeredM4 holes |6 peripheral M6'
 d.getObject('AluminumDeckD3').ModelNote='6061-T6;25 D4.5/50mm grid XY+-100;6 D6.6 atX+-125/0,Y+-135;4 slots30x6R3. No countersink. OldD3 quote INVALID for this revision.'
 for i,(x,y) in enumerate(fixes):
  s=cyl(3,12,(x,y,233),(0,0,-1)).fuse(cyl(5,1.5,(x,y,233))).cut(b.j.hexagon(x,y,233.5,3,2))
  d.getObject('DeckBolt'+str(i)).Shape=s;d.getObject('DeckBolt'+str(i)).ModelNote='NBK SSH-M6-12: D10 head1.5,AF3,length12 under head. Catalog profile, no helical thread; use product torque restrictions.'
  d.getObject('DeckSlotNut'+str(i)).Shape=b.d6.slotnut_at((x,y,229),(0,0,-1))
 # Belt paths are reservations; they are optional to show, required when carrying loose cargo.
 d.getObject('StrapRouteX').Shape=box(-140,-12.5,393,280,25,1.5)
 d.getObject('StrapRouteY').Shape=box(-12.5,-110,393,25,220,1.5)
 # Preserve main switch position/battery harness clearance; locally relieve ribs for nut/tool.
 lid=d.getObject('RearPowerLidPLA')
 lid.Shape=lid.Shape.cut(cyl(15.5,13,(-201,64,140.4))).fuse(cyl(17,3,(-201,64,150.4)).cut(cyl(15.5,3,(-201,64,150.4)))).removeSplitter()
 lid.ModelNote+=' E4 main centerX=-201 retained; D31 rib clearance and D34 reinforcement ring. D26x5 nut and D30 tool are design-space reservations, not measured supplier dimensions.'
 # Separate nominal body/neck from nut and terminal reservations to expose their interfaces.
 d.getObject('MainPower_3214').Shape=fuse([cyl(11,8,(-201,64,140.4)),cyl(5.9,11,(-201,64,148.4)),cyl(11,16,(-201,64,159.4))])
 d.getObject('MainPower_3214').ModelNote='amon3214 nominal layout split into body/neck/head; actual body/nut/tab dimensions unmeasured. Need supplied part to qualify.'
 add('MainPowerNutReservation',cyl(13,5,(-201,64,148.4)).cut(cyl(6.2,5,(-201,64,148.4))),'reference','D26x5 assumed resin-nut space. Supplier confirms resin nut, D12 hole,1-4mm panel only; dimension unverified.')
 for k,x in enumerate([-207,-195]):add('MainPowerTerminalReservation'+str(k),box(x-4.5,61,123.4,9,6,17),'reference','Space for250 insulated female terminal/tab assembly, not selected vendor part. Includes blade mating volume. Actual crimp/insulation/bend fit pending.')
 cx,cy,front=-196,-85,180.4
 d.getObject('EStop_HW1B_V402R').Shape=fuse([box(cx-14.7,cy-26.5,front-49.4,29.4,41.4,36.4),cyl(10.9,26,(cx,cy,front-13)),cyl(15,4,(cx,cy,front)),cyl(20,19,(cx,cy,front+13))])
 d.getObject('EStop_HW1B_V402R').ModelNote+=' E4 neck/contact envelope partitioned to show actual separate locknut. Contact latch/terminal detail remains simplified.'
 add('EStopLockNut',cyl(14.2,5,(cx,cy,170.4)).cut(cyl(11,5,(cx,cy,170.4))),'reference','HW9Z-LN catalogD28.4x5, supplied mounting nut; not additional purchase. Not a detailed groove/thread model.')
 # Four distinct terminal approach pockets below block. Exact screw/lead direction unverified.
 for k,(x,y) in enumerate([(-203,-98),(-189,-98),(-203,-76),(-189,-76)]):add('EStopLeadReservation'+str(k),box(x-4,y-4,121,8,8,10),'reference','Reserved8x8x10 space below contact block; not purchased lug geometry. Verify actual terminal direction, insulation and cable bend.')
 for name,x,y,z in [('RearStopCasePLA',-170,-104,138),('RearPowerCasePLA',-170,54,132)]:
  o=d.getObject(name);bridge=box(x,y,z,7,8,10).cut(box(x-1,y+2,z+4,9,4,2))
  o.Shape=o.Shape.fuse(bridge).removeSplitter();o.ModelNote+=' E4 integral cable-tie bridge adjacent to port; harness service loop and edge protection required.'
 d.recompute()
 for o in d.Objects:
  if hasattr(o,'MaterialBasis'):assert o.Shape.isValid() and o.Shape.Solids,o.Name
 unchanged=[]
 for o in old.Objects:
  if hasattr(o,'MaterialBasis') and o.Name not in REMOVED+CHANGED:
   assert b.h.equivalent_brep(o.Shape,d.getObject(o.Name).Shape),o.Name;unchanged.append(o.Name)
 rho={'PLA':1.24e-6,'steel':7.85e-6,'aluminum':2.7e-6}
 mass=lambda o:getattr(o,'CatalogMassKg',o.Shape.Volume*rho.get(o.MaterialBasis,0))
 phys=[o for o in d.Objects if hasattr(o,'MaterialBasis') and o.MaterialBasis!='reference']
 oldphys=[o for o in old.Objects if hasattr(o,'MaterialBasis') and o.MaterialBasis!='reference']
 delta=sum(map(mass,phys))-sum(map(mass,oldphys))
 r=dict(revision='E4',source='pico-control/AMR01_PicoControl_E3.FCStd',source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),review_reports=['design-review-e3/MECHANICAL_REVIEW.ja.md','design-review-e3/ROBOTICS_REVIEW.ja.md'],
  grid_xy_mm=grid,grid_diameter_mm=4.5,grid_count=25,frame_fixings_xy_mm=fixes,frame_bolt='SSH-M6-12',head_height_mm=1.5,
  unchanged_BRep_names=unchanged,removed=REMOVED,changed=CHANGED,added=added,physical_parts=len(phys),PLA_parts=sum(o.MaterialBasis=='PLA' for o in phys),
  mass=dict(estimated_base_kg=10.456266639892878+delta,delta_from_E3_kg=delta,total_solid_PLA_kg=sum(mass(o) for o in phys if o.MaterialBasis=='PLA'),electrical_allowance_not_reduced=True,actually_weighed=False),
  deck_quote_valid=False,standard_monitor_included=False,optional_cargo_stops_included=False,manufacturing_release=False)
 (HERE/'geometry.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
 d.saveAs(str(HERE/(NAME+'.FCStd')))
 for name in ['RearPowerLidPLA','RearStopCasePLA','RearPowerCasePLA']:
  s=d.getObject(name).Shape.copy();bb=s.BoundBox;s.translate(V(-bb.XMin,-bb.YMin,-bb.ZMin))
  MeshPart.meshFromShape(Shape=s,LinearDeflection=.06,AngularDeflection=.25,Relative=False).write(str(HERE/(name+'.stl')))
 Part.export([d.getObject('AluminumDeckD3')],str(HERE/'E4_Deck_300x300x4.step'))
 print(json.dumps({k:r[k] for k in ['physical_parts','PLA_parts','mass']},indent=2),flush=True)
if __name__=='__main__':main()
