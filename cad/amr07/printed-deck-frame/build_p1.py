"""P1: precut 3030 deck supports, independent purchased cross brackets.

Run with FreeCAD Python. All shapes are nominal fit envelopes, not supplier CAD.
The immutable D2 source and mass ledger are fetched from git, never overwritten.
"""
from pathlib import Path
from itertools import product, combinations
import hashlib
import json
import math
import subprocess
import sys
import tempfile
import FreeCAD as App
import Part
import MeshPart

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sys.path.insert(0, str(BASE))
from hardware_geometry import profile, slotnut_at

V = App.Vector
NAME = 'AMR01_PrintedDeck_P1'
SOURCE_REVISION = '3417383'
P = dict(revision='P1', date='2026-09-22', status='fit_checked_prototype_not_load_released',
         frame_x_mm=[-110,75], frame_length_mm=300, frame_bottom_top_z_mm=[99,129],
         plate_bottom_top_z_mm=[129,141], grid_axis_mm=[-125,-75,-25,25,75,125],
         grid_hole_diameter_mm=4.5, nut_pocket_AF_depth_mm=[7.3,3.4],
         seam_xy_mm=[37.5,37.5], seam_gap_mm=0.4,
         attachment_y_mm=[-100,-50,50,100], sleeve_OD_ID_L_mm=[12,6.2,5],
         compression_sleeve_ASIN='B0GWMC8ZY9', bracket='HBLFSN6', bracket_qty=8,
         bracket_model='Conservative 30x30x20 envelope, walls4.5, rib edges3; small casting radii/tabs omitted.',
         metal_support_cutting=False, metal_support_drilling=False,
         normal_payload_target_kg=10, structural_payload_target_kg=15, static_factor_target=2,
         PLA_E_comparison_MPa=2750, PLA_density_kg_mm3=1.24e-6,
         PLA_cost_reference_JPY_g=2, loaded_use_released=False)


def cyl(r,z,h,x,y):
    return Part.makeCylinder(r,h,V(x,y,z))


def hexagon(x,y,z,across,depth):
    r=across/math.sqrt(3)
    pts=[V(x+r*math.cos(i*math.pi/3),y+r*math.sin(i*math.pi/3),z) for i in range(6)]
    return Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(V(0,0,depth))


def screw(surface,inward,diameter,length,head_diameter=None,head_height=None):
    p=V(*surface); n=V(*inward)
    return Part.makeCylinder(diameter/2,length,p,n).fuse(
        Part.makeCylinder((head_diameter or {4:7,6:10}[diameter])/2,
                          head_height or diameter,p,-n)).removeSplitter()


def bracket():
    # u: outward from upper rail; v: across bracket; w: vertical.
    s=Part.makeBox(30,20,4.5,V(0,-10,0)).fuse(Part.makeBox(4.5,20,30,V(0,-10,0)))
    for y in (-10,7):
        pts=[V(4.5,y,4.5),V(27,y,4.5),V(4.5,y,27)]
        s=s.fuse(Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(V(0,3,0)))
    holes=[Part.makeCylinder(3.15,7,V(-1,0,15),V(1,0,0)),cyl(3.15,-1,7,18,0)]
    return s.cut(Part.makeCompound(holes)).removeSplitter()


def strip(points):
    pieces=[]
    for a,b in zip(points,points[1:]):
        dx,dz=b[0]-a[0],b[1]-a[1]; length=math.hypot(dx,dz)
        nx,nz=-dz/length*.75,dx/length*.75
        pts=[V(a[0]+nx,-12.5,a[1]+nz),V(b[0]+nx,-12.5,b[1]+nz),
             V(b[0]-nx,-12.5,b[1]-nz),V(a[0]-nx,-12.5,a[1]-nz)]
        pieces.append(Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(V(0,25,0)))
    return pieces[0].multiFuse(pieces[1:]).removeSplitter()


def main():
    def historical(name):
        return subprocess.check_output(['git','-C',str(BASE),'show',SOURCE_REVISION+':cad/amr07/'+name])
    snapshot=tempfile.TemporaryDirectory(prefix='amr-p1-source-')
    source=Path(snapshot.name)/'AMR01_M0601C_A6.FCStd'
    source.write_bytes(historical(source.name))
    source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    old=App.openDocument(str(source)); doc=App.newDocument(NAME)
    doc.Label='AMR P1 | precut3030 + HBLFSN6 | PLA prototype'
    removed=[]; changed=[]; added=[]; printables=[]
    omit=('Cargo','SlotNut_CargoDeck','Fixture','PrintedAdapter','PrintedGuide')
    for o in old.Objects:
        if o.TypeId!='PartDesign::Feature': continue
        if o.Name.startswith(omit): removed.append(o.Name); continue
        doc.copyObject(o,False)

    def add(name,shape,material,note,hardware=''):
        assert shape.isValid() and len(shape.Solids)==1, (name,len(shape.Solids))
        o=doc.addObject('PartDesign::Feature',name); o.Shape=shape
        for field,value in [('MaterialBasis',material),('ModelNote',note),('HardwareSpec',hardware)]:
            o.addProperty('App::PropertyString',field,'Design'); setattr(o,field,value)
        added.append(o.Name)
        return o

    # Front electronics tray interfered with the right crossrail. Reprint only
    # this tray shorter, keeping a full metal-supported four-bolt pattern.
    front=Part.makeBox(90,170,2.4,V(100,-85,99))
    for x in (100,187): front=front.fuse(Part.makeBox(3,170,2,V(x,-85,101.4)))
    for y in (-85,82): front=front.fuse(Part.makeBox(90,3,2,V(100,y,101.4)))
    front=front.cut(Part.makeCompound([cyl(3.3,98,7,x,y) for x,y in product((115,175),(-65,65))])).removeSplitter()
    doc.getObject('FrontElectronicsTrayPLA').Shape=front
    doc.getObject('FrontElectronicsTrayPLA').ModelNote='P1 reprint90x170, x100..190. Inner bolt row moved75->115 to clear upper3030.'
    changed.append('FrontElectronicsTrayPLA'); printables.append('FrontElectronicsTrayPLA')
    for prefix in ('FrontDeckBolt_','Washer_FrontDeckBolt_','SlotNut_FrontDeck_','LargeWasher_Front'):
        for i in (0,1):
            o=doc.getObject(prefix+str(i))
            if o:
                s=o.Shape.copy(); s.translate(V(40,0,0)); o.Shape=s; changed.append(o.Name)

    rear=Part.makeBox(55,180,2.4,V(-190,-90,99))
    for x in (-190,-138): rear=rear.fuse(Part.makeBox(3,180,2,V(x,-90,101.4)))
    for y in (-90,87): rear=rear.fuse(Part.makeBox(55,3,2,V(-190,y,101.4)))
    rear=rear.cut(Part.makeCompound([cyl(3.3,98,7,x,y) for x,y in product((-178,-147),(-65,65))])).removeSplitter()
    doc.getObject('ElectronicsTrayPLA').Shape=rear
    doc.getObject('ElectronicsTrayPLA').ModelNote='P1 reprint55x180, x-190..-135. Inner bolt row-117->-147; 10mm clear of upper3030.'
    changed.append('ElectronicsTrayPLA'); printables.append('ElectronicsTrayPLA')
    for prefix in ('ElectronicsBolt_','Washer_ElectronicsBolt_','SlotNut_Electronics_','LargeWasher_Electronics'):
        for i in (2,3):
            o=doc.getObject(prefix+str(i))
            if o:
                s=o.Shape.copy(); s.translate(V(-30,0,0)); o.Shape=s; changed.append(o.Name)

    upper=[]; bracket_names=[]; driver_checks=[]
    for i,cx in enumerate(P['frame_x_mm']):
        s=profile(300); s.rotate(V(0,0,0),V(0,0,1),90); s.translate(V(cx,-150,114))
        upper.append(add('Upper3030_'+str(i),s,'aluminum','NFSL6-3030-300, stock unmodified; catalog0.76kg/m, not proxy volume.'))
        for j,(y,dx) in enumerate(product((-135,135),(-1,1))):
            key=f'{i}_{j}'; base=V(cx+dx*15,y,99)
            b=bracket()
            if dx<0: b.rotate(V(0,0,0),V(0,0,1),180)
            b.translate(base)
            bn=add('UpperBracket_'+key,b,'aluminum',P['bracket_model'],'HBLFSN6'); bracket_names.append(bn.Name)
            for orient,surface,n,axis in [('Vertical',(cx+dx*15,y,114),(-dx,0,0),(0,1,0)),
                                           ('Foot',(cx+dx*33,y,99),(0,0,-1),(1,0,0))]:
                seating=V(*surface)-V(*n)*4.5
                name='UpperBolt'+orient+'_'+key
                add(name,screw(tuple(seating),n,6,12),'steel','M6x12 cap; conservative4.5mm bracket seat; thread model omitted.','M6x12')
                add('UpperNut'+orient+'_'+key,slotnut_at(surface,n,axis),'steel','Catalog nominal HNTT6-6. Insert before closing lower-frame ends.','HNTT6-6')
                # Straight wrench shank5AF -> circumcircle2.89; 40mm approach.
                tool=Part.makeCylinder(2.9,40,seating-V(*n)*6,-V(*n))
                driver_checks.append((name,tool))

    z0,z1=P['plate_bottom_top_z_mm']; grid=list(product(P['grid_axis_mm'],repeat=2))
    cfg=json.loads(historical('deck_parameters.json')); stops=cfg['geometry']['stop_holes_xy_mm']
    plate=Part.makeBox(300,300,z1-z0,V(-150,-150,z0)); cuts=[]
    for x,y in stops:
        cuts.extend([cyl(2.25,z0-1,14,x,y),hexagon(x,y,z0-1,7.3,4.4)])
    for x,y in grid:
        cuts.extend([cyl(2.25,z0-1,14,x,y),hexagon(x,y,z0-1,7.3,4.4)])
    for sl in cfg['geometry']['strap_slots']:
        x,y=sl['center_xy_mm']
        if sl['long_axis']=='y': x=math.copysign(140,x)
        s=cyl(3,z0-1,14,-12,0).fuse(cyl(3,z0-1,14,12,0)).fuse(Part.makeBox(24,6,14,V(-12,-3,z0-1)))
        if sl['long_axis']=='y': s.rotate(V(0,0,0),V(0,0,1),90)
        s.translate(V(x,y,0)); cuts.append(s)
    # Printed belt channels pass over the two metal crossrails; no rail notches.
    for cx in P['frame_x_mm']: cuts.append(Part.makeBox(48,26,3,V(cx-24,-13,z0-1)))
    attachments=list(product(P['frame_x_mm'],P['attachment_y_mm']))
    for x,y in attachments:
        cuts.extend([cyl(6.2,z0-1,14,x,y),cyl(10,z0+5,8,x,y)])
    plate=plate.cut(Part.makeCompound(cuts)).removeSplitter()
    intervals=[(-150,37.3),(37.7,150)]; panels=[]
    for i,(xs,ys) in enumerate(product(intervals,repeat=2),1):
        a,b=xs; c,d=ys
        s=plate.common(Part.makeBox(b-a,d-c,z1-z0,V(a,c,z0))).removeSplitter()
        o=add('PrintedDeckPanel'+str(i),s,'PLA','12mm solid fit geometry. Print process/creep/hold-down/load tests pending; no load rating.')
        panels.append(o); printables.append(o.Name)
    for i,(x,y) in enumerate(attachments):
        add('DeckSleeve'+str(i),cyl(6,129,5,x,y).cut(cyl(3.1,129,5,x,y)),
            'aluminum','Purchased OD12 ID6.2 L5; measure length against printed5mm floor. No cutting/drilling.','M6 sleeve 12x6.2x5')
        for k in range(2):
            z=134+k*1.6
            add('DeckWasher'+str(i)+'_'+str(k),cyl(9,z,1.6,x,y).cut(cyl(3.2,z,1.6,x,y)),
                'steel','Large washer18x6.4x1.6; actual thickness must match stack.','M6 large washer18x6.4x1.6')
        add('DeckBolt'+str(i),screw((x,y,137.2),(0,0,-1),6,16,10.5,3.3),
            'steel','M6x16 ISO7380 button-head conservative cylindrical head envelope; head maxZ140.5 below deck141.','M6x16 button head ISO7380-1')
        add('DeckNut'+str(i),slotnut_at((x,y,129),(0,0,-1),(0,1,0)),'steel','HNTT6-6; upper rail axisY.','HNTT6-6')
        driver_checks.append(('DeckBolt'+str(i),cyl(2.4,140.5,40,x,y)))

    for name,radial,axis in [('XP',109.5,'x'),('XN',-109.5,'x'),('YP',109.5,'y'),('YN',-109.5,'y')]:
        if axis=='x':
            s=Part.makeBox(15,50,15,V(radial-7.5,-25,z1)); pts=[(radial,-19),(radial,19)]
        else:
            s=Part.makeBox(50,15,15,V(-25,radial-7.5,z1)); pts=[(-19,radial),(19,radial)]
        s=s.cut(Part.makeCompound([cyl(2.25,z1-1,17,x,y) for x,y in pts])).removeSplitter()
        o=add('PrintedStop'+name,s,'PLA','Replaceable printed locator, no drilled metal bar. Not a lifting/primary retention point; crossed straps required.')
        printables.append(o.Name)
    for i,(x,y) in enumerate(stops):
        add('StopBolt'+str(i),screw((x,y,156),(0,0,-1),4,30),'steel','M4x30; captured nut inside plate, tipZ126. Locator only; polymer clamp creep unqualified.','M4x30 socket screw')
        add('StopNut'+str(i),hexagon(x,y,129.1,7,3.2).cut(cyl(2.1,129.1,3.2,x,y)),'steel','Reused M4 nut captured above plate bottom, avoids supporting3030.','M4 hex nut')

    add('CargoFlatBottomReference',Part.makeBox(200,200,150,V(-100,-100,141)),'reference',
        'Example flat cargo. Uniform example CG216; actual cargo CG<=220 and XY+-30 required. Not a product/load approval.')
    shoulder=157.5
    for axis,bottom,top in [('X',128.25,291.75),('Y',126.5,293.25)]:
        end=140 if axis=='X' else 120
        points=[(-end,bottom),(-end,shoulder),(-100.75,shoulder),(-100.75,top),
                (100.75,top),(100.75,shoulder),(end,shoulder),(end,bottom)]
        if axis=='X':
            for cx in sorted(P['frame_x_mm'],reverse=True):
                points += [(cx+23,bottom),(cx+17,130),(cx-17,130),(cx-23,bottom)]
        points += [(-end,bottom)]
        s=strip(points)
        if axis=='Y': s.rotate(V(0,0,0),V(0,0,1),90)
        add('CargoStrapRoute'+axis,s,'reference','BT2520 route envelope only; buckles/pads/slack omitted. Printed underside grooves at metal crossings.')
    doc.recompute()
    physical=[o for o in doc.Objects if o.MaterialBasis!='reference']
    refs=[o for o in doc.Objects if o.MaterialBasis=='reference']
    boxes={o.Name:o.Shape.BoundBox for o in physical+refs}

    def hits(shape,objs):
        out=[]
        for o in objs:
            if shape.BoundBox.intersect(boxes[o.Name]):
                v=shape.common(o.Shape).Volume
                if v>.001: out.append(dict(part=o.Name,volume_mm3=v))
        return out

    collisions=[]
    for a,b in combinations(physical,2):
        if boxes[a.Name].intersect(boxes[b.Name]):
            v=a.Shape.common(b.Shape).Volume
            if v>.001: collisions.append(dict(a=a.Name,b=b.Name,volume_mm3=v))
    reference_hits={o.Name:hits(o.Shape,physical) for o in refs}
    tool_results=[]
    # Upper bracket feet must be tightened before fitting the PLA panels.
    tool_obstacles=[o for o in physical if not o.Name.startswith(('PrintedDeck','PrintedStop','Deck','Stop'))]
    for name,shape in driver_checks:
        obstacles=physical if name.startswith('Deck') else tool_obstacles
        tool_results.append(dict(bolt=name,hits=hits(shape,[o for o in obstacles if o.Name!=name])))
    access=[]
    for x,y in grid:
        nut=hexagon(x,y,129.1,7,3.2).cut(cyl(2.1,129.1,3.2,x,y))
        bolt=cyl(2,129.1,11.9,x,y).fuse(cyl(3.5,141,4,x,y))
        access.append(dict(xy_mm=[x,y],hits=hits(nut.fuse(bolt),physical)))
    # Continuous battery sweep after removing the deck only. Upper rails and
    # their brackets stay fixed; the left rail clears the reserved pack by5mm.
    battery=Part.makeBox(120,80,65+180,V(-90,-40,35))
    removable=[o.Name for o in physical if o.Name.startswith(('PrintedDeck','PrintedStop','Deck','Stop'))]
    battery_hits=hits(battery,[o for o in physical if o.Name not in removable])
    retained_battery_hits=hits(battery,[o for o in upper])
    # Swept conservative caster envelope inherited dimensions, both extremes.
    caster=Part.makeCylinder(43,65,V(-150,0,0))
    # The unchanged lower assembly retains D2's service report; only changed
    # geometry is tested against its motion here, not re-certified from a disk.
    caster_new_hits=hits(caster,[o for o in physical if o.Name in added+changed])
    deck_sweeps=[]
    retained=[o for o in physical if o.Name not in removable]
    for o in physical:
        if not o.Name.startswith(('PrintedDeck','PrintedStop','Stop')): continue
        b=o.Shape.BoundBox
        sweep=Part.makeBox(b.XLength,b.YLength,b.ZLength+180,V(b.XMin,b.YMin,b.ZMin))
        deck_sweeps.append(dict(part=o.Name,hits=hits(sweep,retained)))
    density={'steel':7.85e-6,'aluminum':2.7e-6,'PLA':1.24e-6,'rubber':1.1e-6}
    removed_mass=sum(old.getObject(n).Shape.Volume*density[old.getObject(n).MaterialBasis] for n in removed if old.getObject(n).MaterialBasis!='reference')
    added_mass=sum(doc.getObject(n).Shape.Volume*density[doc.getObject(n).MaterialBasis] for n in added if doc.getObject(n).MaterialBasis!='reference')
    delta=sum((doc.getObject(n).Shape.Volume-old.getObject(n).Shape.Volume)*density[doc.getObject(n).MaterialBasis] for n in changed)
    correction=.456-sum(o.Shape.Volume*2.7e-6 for o in upper)
    correction+=.120-sum(doc.getObject(n).Shape.Volume*2.7e-6 for n in bracket_names)
    base_mass=json.loads(historical('assembly_validation.json'))['mass']['estimated_base_kg']
    panel_mass=sum(o.Shape.Volume*1.24e-6 for o in panels)
    m=base_mass-removed_mass+added_mass+delta+correction
    report=dict(parameters=P,source_revision=SOURCE_REVISION,source_sha256=source_hash,
        all_shapes_valid=all(o.Shape.isValid() for o in physical),physical_parts=len(physical),
        checked_physical_pairs=len(physical)*(len(physical)-1)//2,collisions=collisions,
        reference_collisions={k:v for k,v in reference_hits.items() if v},driver_access=tool_results,
        grid_stations=access,battery_service=dict(continuous_sweep_mm=180,removed_parts=removable,hits=battery_hits,
        with_upper_beams_retained_hits=retained_battery_hits,procedure='Unload and remove deck screws/panels. Upper rails and all brackets remain fixed. Left rail-to-battery nominal gap5mm.'),
        changed_parts_caster_sweep_hits=caster_new_hits,deck_upward_sweeps=deck_sweeps,
        removed_parts=removed,changed_parts=changed,added_parts=added,
        panel_sizes_mm=[[o.Shape.BoundBox.XLength,o.Shape.BoundBox.YLength,12] for o in panels],
        mass=dict(source_D2_kg=base_mass,removed_kg=removed_mass,added_proxy_kg=added_mass,
        changed_kg=delta,rail_and_bracket_catalog_correction_kg=correction,solid_panels_kg=panel_mass,
        total_solid_PLA_kg=sum(o.Shape.Volume*1.24e-6 for o in physical if o.MaterialBasis=='PLA'),
        estimated_base_kg=m,remaining_to_10kg_kg=10-m,electrical_allowance_included_kg=2.1,
        straps_allowance_carried_once_kg=.28,actually_sliced=False,actually_weighed=False),
        limitations=['Nominal proxy shapes; bracket tabs/radii and actual tolerances not resolved',
        'Compression sleeve and printed floor need fit/preload coupon',
        'PLA creep, temperature, local bolt hold-down and strap loads unqualified; SF2 not established',
        'D2 structural FEA does not apply to P1', 'Electronics are reservations, not selected-part fit validation'])
    (HERE/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (HERE/'parameters.json').write_text(json.dumps(P,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['physical_parts','collisions','reference_collisions','mass']},ensure_ascii=False),flush=True)
    print('Tool hits:',[r for r in tool_results if r['hits']],flush=True)
    print('Grid hits:',[r for r in access if r['hits']],flush=True)
    print('Battery:',battery_hits,'Caster:',caster_new_hits,flush=True)
    doc.saveAs(str(HERE/(NAME+'.FCStd')))
    assert not collisions and not report['reference_collisions']
    assert not any(r['hits'] for r in tool_results+access)
    assert not battery_hits and not caster_new_hits
    assert not any(r['hits'] for r in deck_sweeps)
    assert m<10
    manifest=[]
    for name in printables:
        s=doc.getObject(name).Shape.copy()
        if name.startswith('PrintedDeck'): s.rotate(V(0,0,0),V(1,0,0),180)
        b=s.BoundBox; s.translate(V(-b.XMin,-b.YMin,-b.ZMin))
        b=s.BoundBox; assert max(b.XLength,b.YLength)<256
        MeshPart.meshFromShape(Shape=s,LinearDeflection=.06,AngularDeflection=.25,Relative=False).write(str(HERE/(name+'.stl')))
        manifest.append(dict(file=name+'.stl',size_mm=[b.XLength,b.YLength,b.ZLength],solid_mass_g=s.Volume*1.24e-3))
    (HERE/'print_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    Part.export(physical,str(HERE/(NAME+'.step')))
    print('P1 build complete',flush=True)


if __name__=='__main__': main()
