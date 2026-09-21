"""D3: one aluminum deck directly on the original lower 3030 frame.

Run in FreeCAD Python. Historical D2 parts/quote remain immutable. All new
fabricated geometry and clearance checks use the same parameters below.
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

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
sys.path.insert(0,str(BASE))
sys.path.insert(0,str(BASE/'printed-deck-frame'))
from hardware_geometry import slotnut_at
from build_p1 import cyl, hexagon, screw, strip
V=App.Vector
NAME='AMR01_AluminumDirect_D3'
PART='AMR_GridDeck_C45_D3'
SOURCE='3417383'
P=dict(revision='D3',date='2026-09-22',status='nominal_fit_candidate_not_load_released',
       plate_LWT_mm=[300,300,4],plate_bottom_top_z_mm=[99,103],
       frame_top_z_mm=99,additional_support_rails=0,under_deck_spacers=0,
       grid_x_mm=[-125,-75,-25,25,75,125],grid_y_mm=[-115,-65,-15,35,85,135],
       grid_pitch_mm=50,grid_diameter_mm=4.5,grid_count=36,
       grid_slotnut_rows_y_mm=[-65,135],grid_slotnut='HNTT6-4',
       frame_holes_xy_mm=list(product([-105,0,105],[-135,135])),frame_hole_diameter_mm=6.6,
       stop_holes_xy_mm=[(x,y) for x in [-109.5,109.5] for y in [-39,-11]]+
                        [(x,y) for x in [-14,14] for y in [-109.5,109.5]],
       strap_slots=[dict(center_xy_mm=[x,10],long_axis='y') for x in [-140,140]]+
                   [dict(center_xy_mm=[60,y],long_axis='x') for y in [-105,105]],
       slot_LWR_mm=[30,6,3],frame_bolt='M6x12 cap, direct on aluminum, no washer',
       frame_nut='HNTT6-6',battery_bottom_top_z_mm=[28,93],battery_cradle_floor_z_mm=25,
       normal_payload_target_kg=10,structural_payload_target_kg=15,static_factor_target=2,
       metal_support_cutting=False,metal_support_drilling=False,loaded_use_released=False)


def main():
    def historical(name):
        return subprocess.check_output(['git','-C',str(BASE),'show',SOURCE+':cad/amr07/'+name])
    temp=tempfile.TemporaryDirectory(prefix='amr-d3-source-')
    src=Path(temp.name)/'D2.FCStd';src.write_bytes(historical('AMR01_M0601C_A6.FCStd'))
    old=App.openDocument(str(src));doc=App.newDocument(NAME)
    doc.Label='AMR D3 | single aluminum deck | direct3030 | top103mm'
    removed=[];changed=[];added=[];printables=[]
    for o in old.Objects:
        if o.TypeId!='PartDesign::Feature':continue
        if o.Name.startswith(('Cargo','SlotNut_CargoDeck','Fixture','PrintedAdapter','PrintedGuide')):
            removed.append(o.Name);continue
        doc.copyObject(o,False)

    def add(name,shape,mat,note,hardware=''):
        assert shape.isValid() and len(shape.Solids)==1,(name,len(shape.Solids))
        o=doc.addObject('PartDesign::Feature',name);o.Shape=shape
        for f,v in [('MaterialBasis',mat),('ModelNote',note),('HardwareSpec',hardware)]:
            o.addProperty('App::PropertyString',f,'Design');setattr(o,f,v)
        added.append(o.Name);return o

    def box(x,y,z,l,w,h):return Part.makeBox(l,w,h,V(x,y,z))
    def cut(s,tools):return s.cut(Part.makeCompound(tools)).removeSplitter()
    def move(name,dx=0,dy=0,dz=0):
        o=doc.getObject(name);s=o.Shape.copy();s.translate(V(dx,dy,dz));o.Shape=s;changed.append(name)

    # Preserve battery volume and metal mounting heights. Extend the printed
    # vertical walls, lower only the floor and battery by7mm (ground25mm).
    cradle=box(-95,-53,25,130,106,3)
    for y in [-53,50]:cradle=cradle.fuse(box(-95,y,28,130,3,37))
    for y in [-80,50]:cradle=cradle.fuse(box(-95,y,65,130,30,4))
    for x in [-95,32]:cradle=cradle.fuse(box(x,-50,28,3,100,6))
    for x,y in product([-95,32],[-63,53]):cradle=cradle.fuse(box(x,y,50,3,10,15))
    cradle=cut(cradle,[cyl(3.3,64,6,x,y) for x,y in product([-80,20],[-65,65])])
    doc.getObject('BatteryCradlePLA').Shape=cradle
    doc.getObject('BatteryCradlePLA').Label='D3 battery cradle | floor25..28 | no change to rail fasteners'
    doc.getObject('BatteryCradlePLA').ModelNote='Floor lowered7mm; same120x80x65 pack reservation. Battery retention/temperature/creep and actual connector fit pending.'
    changed.append('BatteryCradlePLA');printables.append('BatteryCradlePLA')
    move('BatteryReservedSpace',dz=-7)
    doc.getObject('BatteryReservedSpace').Label='BATTERY RESERVATION 120x80x65 | Z28..93 | not a selected pack'

    # All tray material and screw heads are outside the aluminum plate outline.
    # Each tray has four bolts, two rows20mm apart, plus crossrail bearing.
    for name,x0,width,half_y,xrows,prefixes,oldrows in [
        ('FrontElectronicsTrayPLA',155,75,85,[168,188],
         ['FrontDeckBolt_','LargeWasher_Front','SlotNut_FrontDeck_'],[75,175]),
        ('ElectronicsTrayPLA',-230,75,90,[-188,-168],
         ['ElectronicsBolt_','LargeWasher_Electronics','SlotNut_Electronics_'],[-178,-117])]:
        s=box(x0,-half_y,99,width,half_y*2,2.4)
        for x in [x0,x0+width-3]:s=s.fuse(box(x,-half_y,101.4,3,half_y*2,2))
        for y in [-half_y,half_y-3]:s=s.fuse(box(x0,y,101.4,width,3,2))
        s=cut(s,[cyl(3.3,98,7,x,y) for x,y in product(xrows,[-65,65])])
        doc.getObject(name).Shape=s;doc.getObject(name).Label='D3 '+name+' | clear of deck by5mm'
        doc.getObject(name).ModelNote='Reprint; four M6 bolts in two X rows20mm apart. Electronic enclosures remain unselected reservations.'
        changed.append(name);printables.append(name)
        for i in range(4):
            for prefix in prefixes:move(prefix+str(i),dx=xrows[i//2]-oldrows[i//2])

    z0,z1=P['plate_bottom_top_z_mm']
    holes=[cyl(2.25,98,6,x,y) for x,y in product(P['grid_x_mm'],P['grid_y_mm'])]
    holes.extend(cyl(3.3,98,6,x,y) for x,y in P['frame_holes_xy_mm'])
    holes.extend(cyl(2.25,98,6,x,y) for x,y in P['stop_holes_xy_mm'])
    for sl in P['strap_slots']:
        s=cyl(3,98,6,-12,0).fuse(cyl(3,98,6,12,0)).fuse(box(-12,-3,98,24,6,6))
        if sl['long_axis']=='y':s.rotate(V(0,0,0),V(0,0,1),90)
        s.translate(V(*sl['center_xy_mm'],0));holes.append(s)
    plate=add('AluminumDeckD3',cut(box(-150,-150,z0,300,300,4),holes),'aluminum',
        '6061-T6 single4mm plate; directly bears on four original3030 rails; 36 M4 clearance grid holes50pitch; NO threads.')
    plate.Label='D3 aluminum grid plate300x300x4 | topZ103 | no riser'
    drivers=[]
    for i,(x,y) in enumerate(P['frame_holes_xy_mm']):
        name='DeckBolt'+str(i)
        add(name,screw((x,y,z1),(0,0,-1),6,12),'steel',
            'Direct cap-head bearing on4mm aluminum. Nominal8mm projection into slot,1mm slot-floor clearance. Measure actual stack; thread/preload qualification pending.', 'M6x12 cap')
        add('DeckSlotNut'+str(i),slotnut_at((x,y,99),(0,0,-1)),'steel','HNTT6-6, nominal reconstructed outer profile.','HNTT6-6')
        drivers.append((name,Part.makeCylinder(2.9,40,V(x,y,109))))
    for axis,radial,name in [('x',-109.5,'XN'),('x',109.5,'XP'),('y',-109.5,'YN'),('y',109.5,'YP')]:
        pts=[(radial,y) for y in [-39,-11]] if axis=='x' else [(x,radial) for x in [-14,14]]
        s=box(radial-7.5,-45,103,15,40,15) if axis=='x' else box(-20,radial-7.5,103,40,15,15)
        o=add('PrintedStop'+name,cut(s,[cyl(2.25,102,17,x,y) for x,y in pts]),'PLA',
              'Locating stop only, not a cargo restraint or lifting point. Metal deck and crossed belts carry load/retention.')
        printables.append(o.Name)
    for i,(x,y) in enumerate(P['stop_holes_xy_mm']):
        add('StopBolt'+str(i),screw((x,y,118),(0,0,-1),4,25),'steel','M4x25 nominal, two threads beyond plain nut.','M4x25')
        add('StopWasher'+str(i),cyl(4.5,98.2,.8,x,y).cut(cyl(2.15,98.2,.8,x,y)),'steel','M4 plain washer9x4.3x0.8.','M4 washer')
        add('StopNut'+str(i),hexagon(x,y,95,7,3.2).cut(cyl(2.1,95,3.2,x,y)),'steel','M4 plain hex nut; anti-loosening method to qualify.','M4 hex nut')

    # BeltY runs outside the battery X envelope and below the inner rails.
    # BeltX stays in the open channel above the lowered battery.
    add('CargoEnvelopeD3',box(-100,-100,103,200,200,160),'reference','Example flat200x200 container; nominal uniform CG183mm. Payload CG still<=220, XYwithin30.')
    for name,offset,bottom,top,rotation,span in [('X',0,97.25,263.75,0,140),('Y',60,66.75,265.25,90,105)]:
        pts=[(-span,bottom),(-span,119.5),(-100.75,119.5),(-100.75,top),
             (100.75,top),(100.75,119.5),(span,119.5),(span,bottom),(-span,bottom)]
        s=strip(pts);s.rotate(V(0,0,0),V(0,0,1),rotation);s.translate(V(offset,10 if name=='X' else 0,0))
        add('StrapRoute'+name,s,'reference','25x1.5 routing envelope; buckle, edge sleeves and actual pretension require trial. Unload/remove belts before lifting deck.')
    add('BatteryConnectorEnvelope',box(30,-20,40,15,40,20),'reference',
        '15mm side connector reservation; battery is unselected. Exit horizontally towards front; do not route on top of pack through grid bolt tips.')

    doc.recompute()
    physical=[o for o in doc.Objects if hasattr(o,'MaterialBasis') and o.MaterialBasis!='reference']
    refs=[o for o in doc.Objects if hasattr(o,'MaterialBasis') and o.MaterialBasis=='reference']
    def hits(shape,objects):
        bb=shape.BoundBox;out=[]
        for o in objects:
            if bb.intersect(o.Shape.BoundBox):
                volume=shape.common(o.Shape).Volume
                if volume>.001:out.append(dict(part=o.Name,overlap_mm3=volume))
        return out
    collisions=[]
    for a,b in combinations(physical,2):
        h=hits(a.Shape,[b])
        if h:collisions.append(dict(a=a.Name,**h[0]))
    reference_hits={r.Name:hits(r.Shape,physical) for r in refs}
    # Model both styles of M4 hardware at every usable expansion position.
    # Generic accessory example:3mm plate +0.8 top washer. Plain nut
    # bears directly on the aluminum; free rows use M4x12, slot rows M4x14.
    grid=[]
    for x,y in product(P['grid_x_mm'],P['grid_y_mm']):
        bolt=screw((x,y,106.8),(0,0,-1),4,14 if y in P['grid_slotnut_rows_y_mm'] else 12)
        top=cyl(4.5,106,.8,x,y).cut(cyl(2.15,106,.8,x,y))
        if y in P['grid_slotnut_rows_y_mm']:
            nut=slotnut_at((x,y,99),(0,0,-1))
            # Outer HNTT6 envelope is common to M4/M6. Bore size only affects
            # mass, not the external-clearance test; generic screw stays clear.
            pieces=[bolt,top,nut];mode='M4 HNTT6-4 in existing frame slot'
        else:
            pieces=[bolt,top,hexagon(x,y,95.8,7,3.2).cut(cyl(2.1,95.8,3.2,x,y))]
            mode='M4 hex nut directly on aluminum; preassemble with deck removed'
        hardware=Part.makeCompound(pieces)
        h=hits(hardware,physical+refs)
        h=[a for a in h if a['part']!='CargoEnvelopeD3']
        grid.append(dict(x=x,y=y,mode=mode,hits=h))
    access=[dict(part=n,hits=hits(s,[o for o in physical if o.Name!=n])) for n,s in drivers]
    deck_names=[n for n in added if n.startswith(('AluminumDeck','DeckBolt','PrintedStop','Stop'))]
    retained=[o for o in physical if o.Name not in deck_names]
    sweeps=[]
    for name in deck_names:
        o=doc.getObject(name);b=o.Shape.BoundBox
        s=box(b.XMin,b.YMin,b.ZMin,b.XLength,b.YLength,b.ZLength+180)
        if name.startswith('DeckBolt'):
            x,y=b.Center.x,b.Center.y
            s=cyl(3,91,192,x,y).fuse(cyl(5,103,186,x,y))
        sweeps.append(dict(part=name,hits=hits(s,[a for a in retained if not a.Name.startswith('DeckSlotNut')])))
    b=doc.getObject('BatteryReservedSpace').Shape.BoundBox
    battery_sweep=hits(box(b.XMin,b.YMin,b.ZMin,b.XLength,b.YLength,b.ZLength+180),retained)
    caster_sweep=Part.makeCylinder(43,65,V(-150,0,0))
    caster_hits=hits(caster_sweep,[doc.getObject(n) for n in added+changed if doc.getObject(n).MaterialBasis!='reference'])
    tire_checks=[]
    for side,sign in [('L',1),('R',-1)]:
        # Continuous conservative outward envelope, including tire circular profile.
        tire=doc.getObject('Tire'+side).Shape
        b=tire.BoundBox
        sweep=Part.makeCylinder(50.35,123,V(90,sign*153,50.35),V(0,sign,0))
        tire_checks.append(dict(side=side,hits=hits(sweep,[o for o in physical if o.Name in added+changed])))
    rho={'steel':7.85e-6,'aluminum':2.7e-6,'PLA':1.24e-6,'rubber':1.1e-6}
    removed_mass=sum(old.getObject(n).Shape.Volume*rho[old.getObject(n).MaterialBasis] for n in removed if old.getObject(n).MaterialBasis!='reference')
    added_mass=sum(doc.getObject(n).Shape.Volume*rho[doc.getObject(n).MaterialBasis] for n in added if doc.getObject(n).MaterialBasis!='reference')
    delta=sum((doc.getObject(n).Shape.Volume-old.getObject(n).Shape.Volume)*rho[doc.getObject(n).MaterialBasis] for n in changed if doc.getObject(n).MaterialBasis!='reference')
    source_mass=json.loads(historical('assembly_validation.json'))['mass']['estimated_base_kg']
    total=source_mass-removed_mass+added_mass+delta
    report=dict(parameters=P,source_revision=SOURCE,source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),
                all_shapes_valid=all(o.Shape.isValid() for o in physical+refs),physical_parts=len(physical),
                checked_physical_pairs=len(physical)*(len(physical)-1)//2,collisions=collisions,
                reference_collisions={k:v for k,v in reference_hits.items() if v},grid_stations=grid,
                driver_access=access,deck_removal_sweeps=sweeps,battery_lift_hits=battery_sweep,
                changed_parts_caster_sweep_hits=caster_hits,tire_outward_service=tire_checks,
                removed_parts=removed,changed_parts=changed,added_parts=added,
                clearances_mm=dict(frame_to_plate=0,plate_to_battery=6,battery_to_X_belt=3.5,
                    Y_belt_to_inner_rail=1.5,plate_to_front_and_rear_trays=5,
                    cradle_ground=25,grid_nut_flat_to_adjacent_frame=1.5,grid_screw_tip_to_battery=1.8),
                mass=dict(source_D2_kg=source_mass,removed_kg=removed_mass,added_kg=added_mass,changed_kg=delta,
                    estimated_base_kg=total,remaining_to_10kg_kg=10-total,deck_kg=plate.Shape.Volume*2.7e-6,
                    total_solid_PLA_kg=sum(o.Shape.Volume*1.24e-6 for o in physical if o.MaterialBasis=='PLA'),
                    electrical_allowance_included_kg=2.1,straps_allowance_carried_once_kg=.28,actually_weighed=False),
                limitations=['Nominal CAD fit, not tolerance or loaded-deflection proof',
                    'Frame profiles, nuts and caster are nominal reconstructed shapes; verify received dimensions',
                    'Free grid nuts have1.5mm nominal side clearance; no underside grid washer in the fit example; verify actual fastener stacks',
                    'M6 direct head seating, actual slot depth and bolt projection7.5..8.0mm need received-part inspection',
                    'M4 accessory bolt length must be chosen for actual accessory thickness; sample is3mm plate+0.8top washer, M4x12 free / M4x14 over frame, no underside washer',
                    'Belt route, battery restraints, buckle/edge guards and actual electrical harness remain physical qualification items',
                    'Vehicle15kg/SF2 and loaded operation are not certified'])
    (HERE/'parameters.json').write_text(json.dumps(P,ensure_ascii=False,indent=2)+'\n')
    (HERE/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    doc.saveAs(str(HERE/(NAME+'.FCStd')))
    print(json.dumps({k:report[k] for k in ['physical_parts','collisions','reference_collisions','mass']},ensure_ascii=False),flush=True)
    print('GRID',[(r['x'],r['y'],r['hits']) for r in grid if r['hits']],flush=True)
    print('SERVICE',battery_sweep,caster_hits,[r for r in access+sweeps+tire_checks if r['hits']],flush=True)
    assert not collisions and not report['reference_collisions']
    assert not any(r['hits'] for r in grid+access+sweeps+tire_checks)
    assert not battery_sweep and not caster_hits and total<10
    Part.export(physical,str(HERE/(NAME+'.step')))
    partdoc=App.newDocument(PART);po=partdoc.addObject('PartDesign::Feature','Plate')
    s=plate.Shape.copy();s.translate(V(0,0,-99));po.Shape=s;partdoc.recompute()
    partdoc.saveAs(str(HERE/(PART+'.FCStd')))
    platepath=HERE/(PART+'.step')
    same=False
    if platepath.exists():
        prior=Part.read(str(platepath))
        same=abs(prior.Volume-s.Volume)<1e-5 and s.cut(prior).Volume<1e-5 and prior.cut(s).Volume<1e-5
    if not same:Part.export([po],str(platepath))
    # Preserve the hash of a previously quoted, geometrically identical plate.
    for file in HERE.glob('*.step'):file.write_text('\n'.join(line.rstrip() for line in file.read_text().splitlines())+'\n')
    (HERE/'geometry.json').write_text(json.dumps(dict(name=PART,volume_mm3=s.Volume,mass_kg=s.Volume*2.7e-6,
        step_sha256=hashlib.sha256((HERE/(PART+'.step')).read_bytes()).hexdigest(),parameters=P),indent=2)+'\n')
    manifest=[]
    for name in printables:
        s=doc.getObject(name).Shape.copy();b=s.BoundBox;s.translate(V(-b.XMin,-b.YMin,-b.ZMin));b=s.BoundBox
        assert max(b.XLength,b.YLength)<256
        MeshPart.meshFromShape(Shape=s,LinearDeflection=.06,AngularDeflection=.25,Relative=False).write(str(HERE/(name+'.stl')))
        manifest.append(dict(file=name+'.stl',size_mm=[b.XLength,b.YLength,b.ZLength],solid_mass_g=s.Volume*1.24e-3))
    (HERE/'print_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('D3 build/export complete',flush=True)


if __name__=='__main__':main()
