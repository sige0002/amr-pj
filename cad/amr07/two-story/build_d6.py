"""D6.3 two-storey AMR. Run with FreeCAD Python; no GUI required.

The quoted D3 cargo plate is translated only. All electronics stand ABOVE
the lower rails. Four precut 100mm SF2 posts and two spare 300mm rails carry
the cargo; four independently fastened PLA panels carry electronics only.
"""
from pathlib import Path
from itertools import combinations, product
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import FreeCAD as App
import Part
import MeshPart

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
D3=BASE/'aluminum-direct-deck'
sys.path.insert(0,str(BASE))
from hardware_geometry import profile,slotnut_at
spec=importlib.util.spec_from_file_location('joint_geometry',BASE/'printed-deck-frame/build_p1.py')
j=importlib.util.module_from_spec(spec);spec.loader.exec_module(j)
V=App.Vector
NAME='AMR01_TwoStorey_D6'
SOURCE='099686bacaad0f72e8bc4ce15005cd708a5b2f83'
RHO={'aluminum':2.7e-6,'steel':7.85e-6,'PLA':1.24e-6,'rubber':1.1e-6}
P=dict(revision='D6.3',date='2026-09-22',source_revision=SOURCE,
    architecture='1F battery/computer/power above base rails; 2F independent aluminum cargo deck',
    base_rail_top_z_mm=99,floor_bottom_top_z_mm=[99,101.4],equipment_seat_z_mm=104,
    upright_part='SUS SF2-30・30 BLACK, SF9-322 Amazon pack,100mm',upright_qty=4,
    upright_length_mm=100,upright_centers_xy_mm=[list(p) for p in product([-105,105],[-135,135])],
    upright_bottom_top_z_mm=[99,199],upper_rail_part='MISUMI NFSL6-3030-300',
    upper_rail_qty=2,upper_rail_bottom_top_z_mm=[199,229],
    upper_rail_purchase='reuse the two unused pieces of the already budgeted four-pack',
    new_HBLFSN6_qty=12,new_M6x12_qty=24,new_HNTT6_6_qty=24,
    lower_joint_brackets_per_post=2,upper_joint_brackets_per_post=1,
    reinforcement='opposing X brackets at all four post bases; directional stiffness qualification still pending',
    vehicle_mass_target_kg=10,vehicle_mass_target_is_hard_limit=False,
    floor_fasteners_per_panel=4,floor_direct_M6_per_panel=3,floor_seam_M4_per_panel=1,
    floor_support='PLA ribbed seam beam fixed to BOTH inner rails with two M6 per end; four panels with integral underside seam ribs',
    floor_beam_M6_qty=4,floor_M4_countersunk_qty=4,
    floor_outer_corner_notches=False,corner_flat_gusset_qty=0,
    corner_joint='Four auxiliary flat gussets and their8 fastener sets removed. Eight HBLFSN6 lower-frame joints retained; independent floor corner screws reused from inner rail positions. Frame racking qualification remains open.',
    deck_LWH_mm=[300,300,4],deck_bottom_top_z_mm=[229,233],deck_translation_z_mm=130,
    battery='Makita BL1860B A-60464',charger='Makita DC18RF JPADC18RF',
    adapter='Netkey diy-adapter03',battery_origin_xyz_mm=[-193,-37.5,104],
    battery_installed_XYZ_mm=[113,75,62],adapter_origin_xyz_mm=[-184,-45,166],
    adapter_installed_XYZ_mm=[95,90,30],mating_insertion_depth_credited_mm=0,
    battery_geometry='conservative catalog envelopes, not actual latched-interface CAD',
    computer_origin_LWH_mm=[-60,-50,104,120,100,60],computer_product_selected=False,
    battery_service_waypoints_xyz_mm=[[0,0,0],[0,0,8],[-220,0,8]],
    exchange='OFF, unplug rear connector, release belt, lift8mm then withdraw rearward220mm; cargo and deck stay',
    normal_payload_kg=10,structural_payload_kg=15,static_factor_target=2,
    payload_cg_max_z_mm=330,metal_support_cutting=False,metal_support_drilling=False,
    new_metal_machining=False,loaded_use_released=False)

def box(x,y,z,l,w,h):return Part.makeBox(l,w,h,V(x,y,z))
def fuse(items):
    s=items[0]
    for other in items[1:]:s=s.fuse(other)
    return s.removeSplitter()
def cut(s,items):return s.cut(Part.makeCompound(items)).removeSplitter()
def center(s):
    return [sum(getattr(a.CenterOfMass,k)*a.Volume for a in s.Solids)/s.Volume for k in ['x','y','z']]
def hits(s,objects):
    result=[];bb=s.BoundBox
    for o in objects:
        if bb.intersect(o.Shape.BoundBox):
            v=s.common(o.Shape).Volume
            if v>.001:result.append(dict(part=o.Name,overlap_mm3=v))
    return result
def pipe(points,r=3):
    p=[V(*v) for v in points];a=[]
    for s,t in zip(p,p[1:]):
        d=t-s;a.append(Part.makeCylinder(r,d.Length,s,d))
    a += [Part.makeSphere(r,t) for t in p[1:-1]]
    return fuse(a)
def swept_bbox(s,a,b):
    bb=s.BoundBox
    mins=[bb.XMin,bb.YMin,bb.ZMin];sizes=[bb.XLength,bb.YLength,bb.ZLength]
    return box(*[mins[i]+min(a[i],b[i]) for i in range(3)],
               *[sizes[i]+abs(a[i]-b[i]) for i in range(3)])

def main():
    temp=tempfile.TemporaryDirectory(prefix='amr-d6-source-')
    src=Path(temp.name)/'D3.FCStd'
    src.write_bytes(subprocess.check_output(['git','-C',str(BASE),'show',SOURCE+':cad/amr07/aluminum-direct-deck/AMR01_AluminumDirect_D3.FCStd']))
    old=App.openDocument(str(src));doc=App.newDocument(NAME)
    doc.Label='AMR D6.3 | full floor corners | HBLFSN6 frame joints | cargo233mm'
    removed=['BatteryCradlePLA','BatteryReservedSpace','BatteryConnectorEnvelope','ElectronicsTrayPLA','FrontElectronicsTrayPLA']
    removed.extend(o.Name for o in old.Objects if o.Name.startswith(('Gusset_','GussetBolt_','Washer_Gusset','SlotNut_Gusset_')))
    for o in old.Objects:
        if o.TypeId=='PartDesign::Feature' and o.Name not in removed:doc.copyObject(o,False)
    added=[];changed=[];translated=[];printed=[];moving=[];mass_override={};driver_checks=[]
    def add(name,s,mat,note,moves=False,mass=None):
        assert s.isValid() and len(s.Solids)==1,(name,len(s.Solids))
        o=doc.addObject('PartDesign::Feature',name);o.Shape=s
        for key,value in [('MaterialBasis',mat),('ModelNote',note)]:
            o.addProperty('App::PropertyString',key,'Design');setattr(o,key,value)
        added.append(name)
        if mat=='PLA':printed.append(name)
        if moves:moving.append(name)
        if mass is not None:mass_override[name]=mass
        return o
    def change(name,s):
        o=doc.getObject(name);o.Shape=s;changed.append(name);return o
    # Six cargo fixing coordinates and all purchased/manufactured cargo parts
    # remain identical in their own coordinates. Only the assembly height moves.
    for o in doc.Objects:
        if o.Name.startswith(('AluminumDeck','DeckBolt','DeckSlotNut','PrintedStop','StopBolt','StopWasher','StopNut','StrapRoute','CargoEnvelope')):
            s=o.Shape.copy();s.translate(V(0,0,130));o.Shape=s;translated.append(o.Name)

    # Actual supplier profile, clipped to the selected precut length. Its mass
    # is the official0.84kg/m, not this STEP's simplified density conversion.
    supplier=Part.read(str(HERE/'SUS-SFF-324-source.step'))
    post=supplier.common(box(-16,-16,-100,32,32,100)).removeSplitter()
    for i,(cx,cy) in enumerate(P['upright_centers_xy_mm']):
        s=post.copy();s.translate(V(cx,cy,199))
        add('Upright3030_'+str(i),s,'aluminum','SUS SF2-30・30 BLACK100mm; official cross-section STEP. No end tapping/drilling.0.84kg/m.',mass=.084)
    for i,cy in enumerate([-135,135]):
        s=profile(300);s.translate(V(-150,cy,214))
        add('UpperRail3030_'+str(i),s,'aluminum','Existing purchased4pack300mm has two spare rails. Reuse unmodified;0.76kg/m.',mass=.228)
    for i,(cx,cy) in enumerate(P['upright_centers_xy_mm']):
        for end,dx,z in [('Lower',-1 if cx>0 else 1,99),
                         ('LowerOpposite',1 if cx>0 else -1,99),
                         ('Upper',1 if cx>0 else -1,199)]:
            inv=end=='Upper';dz=-1 if inv else 1
            # Proper orthogonal rotation: local u points away from post,
            # local w points up at bottom / down at top.
            u=V(dx,0,0);w=V(0,0,dz);v=w.cross(u)
            rot=App.Rotation(u,v,w,'ZXY');s=j.bracket()
            s.Placement=App.Placement(V(cx+dx*15,cy,z),rot)
            key=f'{i}_{end}'
            add('LevelBracket_'+key,s,'aluminum','HBLFSN6 nominal30x30x20 walls4.5. Same8mm mouth/lip2mm interfaces; mixed SUS/MISUMI joint requires received-part tab/seat check.')
            data=[('Post',(cx+dx*15,cy,z+dz*15),(-dx,0,0),(0,0,1)),
                  ('Rail',(cx+dx*33,cy,z),(0,0,-dz),(1,0,0))]
            for side,surface,n,axis in data:
                seat=V(*surface)-V(*n)*4.5;name='LevelBolt_'+key+'_'+side
                add(name,j.screw(tuple(seat),n,6,12),'steel','M6x12 cap, through4.5mm bracket. Thread lead-ins omitted.')
                add('LevelNut_'+key+'_'+side,slotnut_at(surface,n,axis),'steel','HNTT6-6 nominal14x15x6.3 nose7.8x0.8. Nominal supplier slot clearances checked; no mixed-joint certification.')
                driver_checks.append((name,Part.makeCylinder(2.9,35,seat-V(*n)*6,-V(*n))))

    # Retain the existing internal metal brackets as the frame joints.
    # The auxiliary flat gussets had their holes centered on their diagonal
    # edges, giving only half-washer bearing. Do not reuse this flawed shape.
    # The printed floor is not credited as a frame racking brace.
    corner_joints=[]
    for sx,sy in product([-1,1],repeat=2):
        tag=('N' if sx<0 else 'P')+('N' if sy<0 else '')+'120'
        corner_joints.append(dict(frame_bracket='Bracket_'+tag,
            frame_bolts=['JointA_'+tag,'JointB_'+tag],flat_gusset_removed=True,
            floor_corner_fixing_xy_mm=[sx*185,sy*135],plastic_in_frame_clamp=False))

    # Spread three reused M6 fixings across the outer and end rails.
    # A fourth, flush M4 fixing ties each panel to the new anchored seam beam.
    floor_fixings=[]
    for i,(x,y) in enumerate(product([-25,25],[-135,135])):
        change('CradleBolt_'+str(i),j.screw((x,y,103),(0,0,-1),6,12))
        change('LargeWasher_Cradle'+str(i),Part.makeCylinder(9,1.6,V(x,y,101.4)).cut(Part.makeCylinder(3.3,1.6,V(x,y,101.4))))
        change('SlotNut_Cradle_'+str(i),slotnut_at((x,y,99),(0,0,-1)))
        floor_fixings.append(dict(panel=f'FloorPLA_{int(x>0)}_{int(y>0)}',bolt='CradleBolt_'+str(i),xy_mm=[x,y],support='outer 400mm rail',thread='M6'))
    for prefix,sgn,washer,nut in [('Electronics',-1,'Electronics','Electronics'),('FrontDeck',1,'Front','FrontDeck')]:
        for i,(x,y) in enumerate([(sgn*185,-135),(sgn*185,135),(sgn*215,-20),(sgn*215,20)]):
            change(f'{prefix}Bolt_{i}',j.screw((x,y,103),(0,0,-1),6,10))
            change(f'LargeWasher_{washer}{i}',Part.makeCylinder(9,1.6,V(x,y,101.4)).cut(Part.makeCylinder(3.3,1.6,V(x,y,101.4))))
            change(f'SlotNut_{nut}_{i}',slotnut_at((x,y,99),(0,0,-1),(0,1,0) if i>=2 else (1,0,0)))
            floor_fixings.append(dict(panel=f'FloorPLA_{int(x>0)}_{int(y>0)}',bolt=f'{prefix}Bolt_{i}',xy_mm=[x,y],support='300mm end rail' if i>=2 else 'outer 400mm rail, corner',thread='M6'))

    # Top flange rests against panel undersides; two full-height end cheeks
    # transfer load through four M6/large-washer joints into the inner rails.
    beam=fuse([box(-32,-50,94,64,100,5),box(-32,-50,79,3.2,100,15),
               box(28.8,-50,79,3.2,100,15),box(-32,-50,74,64,3.2,20),
               box(-32,46.8,74,64,3.2,20)])
    beam_holes=[box(-33,-8.5,96.5,66,17,3.5)]  # PC belt stays at z97..98.5.
    beam_anchors=[]
    for i,(x,sign) in enumerate(product([-18,18],[-1,1])):
        surface=(x,sign*50,84);n=(0,sign,0);seat=(x,sign*45.2,84)
        beam_holes.append(Part.makeCylinder(3.3,8,V(x,sign*44,84),V(*n)))
        add(f'SeamBeamBolt_{i}',j.screw(seat,n,6,12),'steel','M6x12, two anchors per beam end. Through1.6mm OD18 washer and3.2mm PLA cheek into HNTT6-6. Check PLA creep/preload on prototype.')
        add(f'SeamBeamWasher_{i}',Part.makeCylinder(9,1.6,V(*seat),V(*n)).cut(Part.makeCylinder(3.3,1.6,V(*seat),V(*n))),'steel','M6 large washer OD18/ID6.6/t1.6; spreads load on printed beam end cheek.')
        add(f'SeamBeamNut_{i}',slotnut_at(surface,n),'steel','HNTT6-6 in inward-facing slot of inner3030 rail.')
        beam_anchors.append(dict(bolt=f'SeamBeamBolt_{i}',rail_surface_xyz_mm=list(surface),rail='inner negative Y' if sign<0 else 'inner positive Y'))
    for ix,iy in product(range(2),repeat=2):
        x=(-1 if ix==0 else 1)*15;y=(-1 if iy==0 else 1)*25;key=f'{ix}_{iy}'
        beam_holes.append(Part.makeCylinder(2.25,8,V(x,y,93)))
        shaft=Part.makeCylinder(2,14,V(x,y,85.4))
        head=Part.makeCone(2,4,2,V(x,y,99.4))
        add('FloorSeamBolt_'+key,shaft.fuse(head).removeSplitter(),'steel','M4x16 countersunk90deg, nominal headOD8, flush at101.4. Plain through hole and accessible nut; no tapped PLA.')
        add('FloorSeamWasher_'+key,Part.makeCylinder(4.5,.8,V(x,y,93.2)).cut(Part.makeCylinder(2.2,.8,V(x,y,93.2))),'steel','M4 plain washer OD9/ID4.4/t0.8 under beam flange.')
        add('FloorSeamNut_'+key,j.hexagon(x,y,90,7,3.2).cut(Part.makeCylinder(2.0,3.2,V(x,y,90))),'steel','M4 nut AF7/h3.2. Thread simplified; accessible from underside.')
        floor_fixings.append(dict(panel='FloorPLA_'+key,bolt='FloorSeamBolt_'+key,xy_mm=[x,y],support='seam beam, four M6 rail anchors',thread='M4 countersunk'))
    add('SeamBeamPLA',cut(beam,beam_holes),'PLA','64x100x25 ribbed beam, BOTH ends anchored with2xM6. Recess clears PC belt. Electronics shelf only; printed strength and creep qualification pending.')
    holes=[]
    for fixing in floor_fixings:
        x,y=fixing['xy_mm']
        if fixing['thread']=='M6':holes.append(Part.makeCylinder(3.3,4,V(x,y,98)))
        else:
            holes.append(Part.makeCylinder(2.25,15,V(x,y,88)))
            holes.append(Part.makeCone(2.25,4,1.75,V(x,y,99.65)))
    # Openings clear the bottom bracket feet and leave metal directly on metal.
    for x in [-156,54]:
        for y in [-151,118]:holes.append(box(x,y,98,102,33,5))
    # Outer corners are continuous floor; the auxiliary flat gussets are gone.
    # Vertical belt passages are between frame members, not through the rails.
    for x,y,w in [(-197,0,26),(-73,0,26),(-62.25,0,16),(62.25,0,16),(2.75,90,16),(77.25,90,16)]:
        holes.append(box(x-2,y-w/2,98,4,w,15))
    for x in [-196,-80]:holes.append(box(x-.1,-13,101.4,3.2,26,12))
    # Low locators are part of the individual shelf panels. The battery is
    # lifted8mm to clear their110mm tops before it moves rearward.
    locators=[box(-196,-42,101.4,3,84,8.6),box(-80,-42,101.4,3,84,8.6),
              box(-193,-42,101.4,113,2,8.6),box(-193,40,101.4,113,2,8.6),
              box(-64,-52,101.4,2,104,6.6),box(62,-52,101.4,2,104,6.6),
              box(-60,-54,101.4,120,2,6.6),box(-60,52,101.4,120,2,6.6)]
    # Leave the strap's passages open through locator walls too.
    for ix,(x0,x1) in enumerate([(-230,-.2),(.2,230)]):
        for iy,(y0,y1) in enumerate([(-150,-.2),(.2,150)]):
            boundary=box(x0,y0,98,x1-x0,y1-y0,20)
            s=fuse([box(x0,y0,99,x1-x0,y1-y0,2.4)]+[a.common(boundary) for a in locators if a.common(boundary).Volume>0])
            # 45deg ramp permits edge-up printing and keeps the25mm battery
            # strap unobstructed. Rib span is168mm between beam and end rail.
            sy=-1 if iy==0 else 1;xr=-200 if ix==0 else 32
            points=[V(xr,sy*y,z) for y,z in [(14.8,99),(29.8,84),(32.2,84),(32.2,99),(14.8,99)]]
            rib=Part.Face(Part.makePolygon(points)).extrude(V(168,0,0))
            # Existing lower corner brackets reach z94 near the end rails.
            # Taper the final25mm of rib, leaving0.8mm nominal clearance and
            # a continuous shallow rib all the way to the supporting end rail.
            sx=-1 if ix==0 else 1
            taper=[V(sx*x,-160,z) for x,z in [(175,83),(201,83),(201,94.8),(185,94.8),(175,84),(175,83)]]
            rib=rib.cut(Part.Face(Part.makePolygon(taper)).extrude(V(0,320,0))).removeSplitter()
            s=s.fuse(rib).removeSplitter()
            add(f'FloorPLA_{ix}_{iy}',cut(s,holes),'PLA','1F equipment only; FOUR dispersed fixings:3 reused M6/OD18 washers to outer/end rails +1 flush M4 through anchored seam beam. Full outer corner, integral underside seam rib.230x150mm class; creep/temperature test pending.')
    add('BatteryBL1860B',box(*P['battery_origin_xyz_mm'],*P['battery_installed_XYZ_mm']),'reference','Selected genuine6Ah108Wh battery, manufacturer113x75x62mm;0.68kg.',True)
    add('BatteryAdapter03',box(*P['adapter_origin_xyz_mm'],*P['adapter_installed_XYZ_mm']),'reference','Selected approximate95x90x30mm123g adapter. Full additive height retained; check actual latch/switch/lead offsets.',True)
    add('BatteryBasePad',box(-193,-37.5,101.4,113,75,2.6),'reference','Soft liner on1F floor; not on electrical contacts.')
    add('BatteryBeltTopPad',box(-184,-12.5,196,95,25,1),'reference','Insulating pad over adapter; actual switch and vent clearance to measure.',True)
    route=[(-185,97.25),(-185,108),(-179,108),(-179,166.75),(-170,197.75),(-73,197.75),(-64,166.75),(-64,108),(-58,108),(-58,97.25),(-185,97.25)]
    route=[(-197 if x==-185 else x-15,z) for x,z in route]
    add('BatteryRetentionBelt',j.strip(route),'reference','One BT-2520BK25mm cam belt through printed floor slots. Full125g included even when shortened. Release and park before extraction.')
    add('BatteryBuckleEnvelope',box(-222,-17.5,140,20,35,55),'reference','Rear-access20x35x55 buckle reservation; not mating CAD. Locate clear of latch and floor; exact strap/buckle path to mock-test.')
    add('BatteryModuleHarness',pipe([[-160,45,181],[-160,72,181],[-195,72,181],[-195,78,181],[-195,78,172],[-195,82,172]]),'reference','6mm two-wire route reservation, supplied40cm leads restrained; travels with module.',True)
    add('BatteryServiceConnector',box(-211,82,165,24,24,14),'reference','Unplug accessible rear connector before withdrawing battery; protected battery-side contacts.',True)
    add('BatteryVehicleConnector',box(-211,107,165,24,20,14),'reference','Disconnected vehicle half parked outside extraction route.')
    add('BatteryVehicleHarness',pipe([[-199,127,172],[-199,132,172],[-215,132,150],[-215,114,114],[220,114,114],[220,-75,126],[205,-75,126]]),'reference','Main power follows1F perimeter; clamps and strain relief to select. No conductor count/current rating inferred from geometry.')
    computer=change('Reserved_Computer',box(*P['computer_origin_LWH_mm']))
    computer.Label='1F COMPUTER RESERVATION120x100x60 | above base |0.5kg budget'
    supervisor=change('Reserved_SupervisorRS485',box(5,65,104,70,45,30))
    change('Reserved_Protection',box(135,-110,112,70,70,35))
    change('Reserved_ClampAndPower',box(155,-25,112,50,90,35))
    add('ComputerPad',box(-60,-50,101.4,120,100,2.6),'reference','Insulating equipment pad; case product/mount holes remain unselected.')
    add('SupervisorPad',box(5,65,101.4,70,45,2.6),'reference','Insulating equipment pad; case product/mount holes remain unselected.')
    add('ComputerTopPad',box(-60,-7.5,164,120,15,1),'reference','Strap pad to position away from actual cooling openings.')
    add('SupervisorTopPad',box(5,82.5,134,70,15,1),'reference','Strap pad over supervision case, received hardware fit pending.')
    for name,x0,x1,y,top in [('Computer',-63,63,0,166.5),('Supervisor',2,78,90,136.5)]:
        s=box(x0,y-7.5,97,x1-x0,15,top-97).cut(box(x0+1.5,y-8,98.5,x1-x0-3,16,top-100))
        add(name+'RetentionBelt',s,'reference','15mm strap through1F shelf only; long direction avoids both inner3030rails. Product/creep test pending.')
    # These keep-out volumes are checks, not installed equipment or mass.
    ventilation=box(-60,-50,167,120,100,15)
    pc_cables=box(64,-45,112,30,85,45)

    doc.recompute()
    physical=[o for o in doc.Objects if hasattr(o,'MaterialBasis') and o.MaterialBasis!='reference']
    refs=[o for o in doc.Objects if hasattr(o,'MaterialBasis') and o.MaterialBasis=='reference']
    collisions=[]
    for a,b in combinations(physical,2):
        for h in hits(a.Shape,[b]):collisions.append(dict(a=a.Name,**h))
    ref_hits={o.Name:hits(o.Shape,physical) for o in refs}
    ref_pairs=[]
    for a,b in combinations(refs,2):
        for h in hits(a.Shape,[b]):ref_pairs.append(dict(a=a.Name,**h))
    released=['BatteryRetentionBelt','BatteryBuckleEnvelope']
    fixed=[o for o in physical+refs if o.Name not in moving+released]
    service=[]
    for name in moving:
        for a,b in zip(P['battery_service_waypoints_xyz_mm'],P['battery_service_waypoints_xyz_mm'][1:]):
            service.append(dict(part=name,from_mm=a,to_mm=b,hits=hits(swept_bbox(doc.getObject(name).Shape,a,b),fixed)))
    pc_service=[]
    for n in ['Reserved_Computer','ComputerTopPad']:
        fixed_pc=[o for o in physical+refs if o.Name not in ['Reserved_Computer','ComputerTopPad','ComputerRetentionBelt']]
        for a,b in [([0,0,0],[0,0,8]),([0,0,8],[0,-230,8])]:
            pc_service.append(dict(part=n,from_mm=a,to_mm=b,hits=hits(swept_bbox(doc.getObject(n).Shape,a,b),fixed_pc)))
    caster=hits(Part.makeCylinder(43,65,V(-150,0,0)),[doc.getObject(n) for n in added])
    tires=[dict(side=s,hits=hits(Part.makeCylinder(50.35,123,V(90,s*153,50.35),V(0,s,0)),[doc.getObject(n) for n in added])) for s in [-1,1]]
    # All36 holes remain usable. Only theY=135row now backs onto a rail.
    grid=[]
    for x,y in product([-125,-75,-25,25,75,125],[-115,-65,-15,35,85,135]):
        if y==135:
            nut=slotnut_at((x,y,229),(0,0,-1)).cut(Part.makeCylinder(2.1,10,V(x,y,220)))
            # M4 hole is irrelevant to envelope clearance; this is OD-only check.
            shape=nut
        else:shape=Part.makeCylinder(5,6.2,V(x,y,222.8))
        grid.append(dict(x=x,y=y,fastener='HNTT6-4/M4' if y==135 else 'M4 nut/washer',hits=hits(shape,[doc.getObject(n) for n in added]+[computer,supervisor])))
    tools=[]
    for name,s in driver_checks:
        # Shelf and equipment install after frame assembly; verify actual frame
        # joint access against the metal members/hardware at that assembly step.
        parts=[o for o in physical if o.MaterialBasis!='PLA' and o.Name!=name and o.Name not in translated]
        tools.append(dict(bolt=name,hits=hits(s,parts)))
    invariant_names=[o.Name for o in physical if o.Name not in added+changed+translated]
    invariant=all(doc.getObject(n).Shape.cut(old.getObject(n).Shape).Volume<1e-6 and old.getObject(n).Shape.cut(doc.getObject(n).Shape).Volume<1e-6 for n in invariant_names)
    plate=doc.getObject('AluminumDeckD3').Shape.copy();plate.translate(V(0,0,-130))
    plate_equal=plate.cut(old.getObject('AluminumDeckD3').Shape).Volume<1e-6 and old.getObject('AluminumDeckD3').Shape.cut(plate).Volume<1e-6
    source_mass=json.loads((D3/'validation.json').read_text())['mass']['estimated_base_kg']
    deltas=[]
    def mass(o):return mass_override.get(o.Name,o.Shape.Volume*RHO[o.MaterialBasis])
    def ledger(name,m,c):deltas.append(dict(name=name,mass_kg=m,center_mm=c))
    for n in removed:
        o=old.getObject(n)
        if o.MaterialBasis!='reference':ledger('remove '+n,-mass(o),center(o.Shape))
    for n in added:
        o=doc.getObject(n)
        if o.MaterialBasis!='reference':ledger('add '+n,mass(o),center(o.Shape))
    for n in translated+changed:
        a=old.getObject(n);b=doc.getObject(n)
        if a.MaterialBasis!='reference':
            ledger('old position '+n,-mass(a),center(a.Shape));ledger('new position '+n,mass(b),center(b.Shape))
    ledger('remove old battery budget',-.75,[-30,0,60.5])
    for n,m in [('BatteryBL1860B',.68),('BatteryAdapter03',.123)]:ledger(n,m,center(doc.getObject(n).Shape))
    ledger('battery full125g belt plus25g pads',.15,[-146,0,150]);ledger('PC and supervisor belts/pads',.03,[0,10,130])
    # Existing .28kg cargo belts/pads move with cargo; do not count twice.
    ledger('remove old cargo belts/edge protection',-.28,[0,0,180]);ledger('raise cargo belts/edge protection',.28,[0,0,310])
    for n,m in [('Reserved_Computer',.5),('Reserved_SupervisorRS485',.05),('Reserved_Protection',.2),('Reserved_ClampAndPower',.2)]:
        ledger('old '+n,-m,center(old.getObject(n).Shape));ledger('relocate '+n,m,center(doc.getObject(n).Shape))
    dm=sum(a['mass_kg'] for a in deltas);total=source_mass+dm
    moment=[sum(a['mass_kg']*a['center_mm'][i] for a in deltas) for i in range(3)]
    ranges=[[(source_mass*edge+moment[i])/total for edge in interval] for i,interval in enumerate([[-10,10],[-10,10],[85,110]])]
    report=dict(parameters=P,physical_parts=len(physical),all_shapes_valid=all(o.Shape.isValid() for o in physical+refs),
        checked_physical_pairs=len(physical)*(len(physical)-1)//2,collisions=collisions,
        reference_collisions={k:v for k,v in ref_hits.items() if v},reference_pair_collisions=ref_pairs,
        continuous_battery_service=service,continuous_computer_service=pc_service,caster_sweep_hits=caster,tire_outward_service=tires,
        grid_fastener_envelopes=grid,grid_free_holes=30,grid_slotnut_holes=6,
        joint_assembly_tool_access=tools,computer_ventilation_keepout_hits=hits(ventilation,physical+refs),
        floor_fixings=floor_fixings,floor_beam_anchors=beam_anchors,corner_joints=corner_joints,
        computer_connector_keepout_hits=hits(pc_cables,physical+refs),
        added_parts=added,removed_parts=removed,changed_parts=changed,translated_parts=translated,
        moving_parts=moving,released_before_service=released,
        unchanged_physical_parts=len(invariant_names),unchanged_parts_BRep_equal=invariant,quoted_plate_unchanged=plate_equal,
        clearances_mm=dict(first_floor_open_height_at_sides=97.6,central_floor_to_deck=127.6,
            battery_lift_to_lowest_cargo_grid_fastener=222.8-(198.5+8),
            computer_to_deck=229-166.5,computer_vent_keepout_height=15,
            battery_rearward_withdrawal=220),
        mass=dict(source_D3_kg=source_mass,estimated_base_kg=total,remaining_to_10kg_kg=10-total,
            electrical_total_kg=2.153,battery_kg=.68,adapter_kg=.123,new_straps_and_pads_allowance_kg=.18,
            total_solid_PLA_kg=sum(o.Shape.Volume*RHO['PLA'] for o in physical if o.MaterialBasis=='PLA'),
            added_metal_and_hardware_kg=sum(mass(doc.getObject(n)) for n in added if doc.getObject(n).MaterialBasis in ['aluminum','steel']),
            upper_structure_metal_and_hardware_kg=sum(mass(doc.getObject(n)) for n in added if n.startswith(('Upright3030_','UpperRail3030_','Level'))),
            floor_added_hardware_kg=sum(mass(doc.getObject(n)) for n in added if n.startswith(('SeamBeam','FloorSeam')) and doc.getObject(n).MaterialBasis=='steel'),
            mass_overrides_kg=mass_override,actually_weighed=False),
        cg_difference=dict(ledger=deltas,mass_change_kg=dm,moment_change_kg_mm=moment,
            conditional_base_cg_xyz_ranges_mm=ranges,
            basis='Conditional on historical D3 CGx/y+-10,z85..110mm; equipment envelope centroids and mass budgets, not measured CG. Protection0.4kg split equally between two reserved cases; cable routing moment remains in historical uncertainty.'),
        limitations=['Battery+adapter latched offsets and case/switch/connector details need received-part/dummy check.',
            'New SUS posts and MISUMI brackets/nuts share nominal slot dimensions; verify bracket tabs, seating and torque on one joint before assembly. No manufacturer cross-brand certification claimed.',
            'PLA first-floor panel creep/retention/temperature and frame joint slip/racking require physical tests.',
            'Six plate-support coordinates unchanged; prior shell FEA assumes clamped patches and does not certify new frame/joint stiffness.',
            'Normal10kg/structure15kg SF2 are targets; electrical protection, actual computer mounting and loaded operation remain unqualified.'])
    (HERE/'parameters.json').write_text(json.dumps(P,ensure_ascii=False,indent=2)+'\n')
    (HERE/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    doc.saveAs(str(HERE/(NAME+'.FCStd')))
    print(json.dumps({k:report[k] for k in ['collisions','reference_collisions','reference_pair_collisions','continuous_battery_service','joint_assembly_tool_access','computer_ventilation_keepout_hits','computer_connector_keepout_hits','mass']},ensure_ascii=False),flush=True)
    assert not collisions and not report['reference_collisions'] and not ref_pairs
    assert not any(a['hits'] for a in service+pc_service+tires+grid+tools)
    assert not caster and not report['computer_ventilation_keepout_hits'] and not report['computer_connector_keepout_hits']
    assert invariant and plate_equal
    assert all(sum(f['panel']==f'FloorPLA_{ix}_{iy}' for f in floor_fixings)==4 for ix,iy in product(range(2),repeat=2))
    Part.export(physical,str(HERE/(NAME+'.step')))
    Part.export(physical+[doc.getObject(n) for n in ['BatteryBL1860B','BatteryAdapter03','Reserved_Computer']],str(HERE/(NAME+'-with-equipment-envelopes.step')))
    for file in HERE.glob(NAME+'*.step'):file.write_text('\n'.join(t.rstrip() for t in file.read_text().splitlines())+'\n')
    manifest=[]
    for name in printed:
        s=doc.getObject(name).Shape.copy();b=s.BoundBox;s.translate(V(-b.XMin,-b.YMin,-b.ZMin));b=s.BoundBox
        assert max(b.XLength,b.YLength,b.ZLength)<256
        MeshPart.meshFromShape(Shape=s,LinearDeflection=.06,AngularDeflection=.25,Relative=False).write(str(HERE/(name+'.stl')))
        manifest.append(dict(file=name+'.stl',size_mm=[b.XLength,b.YLength,b.ZLength],solid_mass_g=s.Volume*1.24e-3,
            orientation_note='Floor: ribs downward with slicer supports, or stand on central seam edge with brim and local locator-wall supports. Beam: broad top flange toward bed; check17mm belt-channel bridge. STL axes are assembly axes translated to positive coordinates, NOT pre-oriented for printing.',
            sliced=False,support_and_failed_print_material_included=False))
    (HERE/'print_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('D6 build complete',flush=True)

if __name__=='__main__':main()
