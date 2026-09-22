"""D4 battery-service prototype; source D3 and its quoted aluminum are immutable.

Run using FreeCAD Python. The battery remains a catalog fit candidate, not an
electrically qualified selection. Every retainer, slide and release fastener is
modeled; continuous service envelopes are checked with the deck left installed.
"""
from pathlib import Path
from itertools import combinations, product
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
D3=BASE/'aluminum-direct-deck'
sys.path.insert(0,str(BASE/'printed-deck-frame'))
from build_p1 import cyl, hexagon, screw
V=App.Vector
NAME='AMR01_BatteryDrawer_D4'
SOURCE='099686bacaad0f72e8bc4ce15005cd708a5b2f83'
P=dict(revision='D4',date='2026-09-22',status='mechanical_fit_prototype_battery_not_selected',
       source_revision=SOURCE,deck_bottom_top_z_mm=[99,103],minimum_ground_mm=25,
       battery_candidate='VANT 5S 18.5V 2200mAh XT60',battery_selected=False,
       catalog_body_LWT_mm=[104,40,34.5],installed_body_XYZ_mm=[40,104,34.5],
       accepted_body_max_XYZ_mm=[50,112,36],battery_seat_z_mm=30,
       battery_center_xy_mm=[-30,0],battery_mass_allowance_kg=.75,
       frame_fasteners_reused=4,battery_straps=2,strap_width_thickness_mm=[15,1.5],
       strap_length_min_mm=250,strap_side_overlap_mm=25,
       drawer_retention='2 M4x16 cap screws + M4 prevailing-torque nuts + washers',
       removal_direction='+Y',full_removal_travel_mm=220,side_clearance_for_motion_mm=251,
       battery_pack_electrical_qualification=False,loaded_use_released=False)


def box(x,y,z,l,w,h): return Part.makeBox(l,w,h,V(x,y,z))
def cut(s,tools): return s.cut(Part.makeCompound(tools)).removeSplitter()
def fuse(shapes):
    s=shapes[0]
    for t in shapes[1:]: s=s.fuse(t)
    return s.removeSplitter()
def ycyl(r,x,y,z,h): return Part.makeCylinder(r,h,V(x,y,z),V(0,1,0))
def yhex(x,y,z,af,depth):
    s=hexagon(0,0,0,af,depth)
    s.rotate(V(),V(1,0,0),-90);s.translate(V(x,y,z));return s


def main():
    temp=tempfile.TemporaryDirectory(prefix='amr-d4-')
    src=Path(temp.name)/'D3.FCStd'
    src.write_bytes(subprocess.check_output(['git','-C',str(BASE),'show',
                   SOURCE+':cad/amr07/aluminum-direct-deck/AMR01_AluminumDirect_D3.FCStd']))
    old=App.openDocument(str(src));doc=App.newDocument(NAME)
    doc.Label='AMR D4 | side battery drawer | deck103mm | pack NOT selected'
    removed=['BatteryCradlePLA','BatteryReservedSpace','BatteryConnectorEnvelope']
    for o in old.Objects:
        if o.TypeId=='PartDesign::Feature' and o.Name not in removed:doc.copyObject(o,False)
    added=[];moving=[];printed=[]
    def add(name,s,mat,note,moves=False):
        assert s.isValid() and len(s.Solids)==1,(name,len(s.Solids))
        o=doc.addObject('PartDesign::Feature',name);o.Shape=s
        for key,value in [('MaterialBasis',mat),('ModelNote',note)]:
            o.addProperty('App::PropertyString',key,'Design');setattr(o,key,value)
        added.append(name)
        if moves:moving.append(name)
        if mat=='PLA':printed.append(name)
        return o

    # Two printed guides attach to the same four M6 bottom-slot fittings. All
    # ledges are at/above the previous25mm ground-clearance plane.
    for suffix,web,ledge,mount,axis,bx in [('XN',-70,-70,-80,-65,-72),
                                         ('XP',7,0,20,6,0)]:
        bits=[box(web,-82,25,3,227,28),box(ledge,-82,25,10,227,3),
              box(ledge,-82,33,10,227,3),box(bx,134,39,13 if suffix=='XN' else 12,11,16)]
        for y in [-65,65]:
            bits.append(box(mount-11,y-17,65,22,34,4))
            post=mount-4 if suffix=='XN' else mount
            bridge=min(post,web)
            for rib_y in [y-17,y+13]:
                bits.append(box(post,rib_y,50,4,4,15))
                bits.append(box(bridge,rib_y,50,max(post+4,web+3)-bridge,4,15))
        # M4 nut is dropped in from above; the pocket stays outside the entire
        # pack passage. Nut's purchased locking feature is not thread-modeled.
        holes=[cyl(3.3,64,6,mount,y) for y in [-65,65]]
        holes.extend([ycyl(2.2,axis,133,47,13),yhex(axis,136.8,47,7.3,5.4),
                      box(axis-4.25,136.8,47,8.5,5.4,9)])
        add('BatteryGuide'+suffix,cut(fuse(bits),holes),'PLA',
            'Fixed guide, nominal1..2mm running gaps. Guide print orientation/support removal requires slicer review;4 walls minimum; qualify load, creep and sliding with dummy pack.')
        add('DrawerNut'+suffix,yhex(axis,137,47,7,5).cut(ycyl(2.1,axis,137,47,5)),
            'steel','M4 prevailing-torque hex nut, AF7 nominal height5. Catalog/received locking torque still to verify.')
        add('DrawerWasher'+suffix,ycyl(4.5,axis,149,47,.8).cut(ycyl(2.15,axis,149,47,.8)),
            'steel','M4 washer OD9 ID4.3 t0.8; removed for battery service.')
        add('DrawerScrew'+suffix,screw((axis,149.8,47),(0,-1,0),4,16),'steel',
            'M4x16 cap screw. 3mm hex key from outside +Y. Two screws positively retain the drawer; remove before pulling.')

    # Stepped flanges run inside the fixed guides. The long floor carries the
    # pack at the original XY center and presents a pull handle outside the rail.
    bits=[box(-59,-62,25,58,243,4),box(-65,-62,28,6,207,3),box(-1,-62,28,6,207,3),
          box(-59,-62,29,3,124,13),box(-4,-62,29,3,124,13),
          box(-56,-62,29,52,3,13),box(-56,59,29,52,3,13),
          box(-59,62,29,3,83,4),box(-4,62,29,3,83,4),
          box(-72,145,25,84,4,42)]
    holes=[ycyl(2.2,x,144,47,6) for x in [-65,6]]
    holes += [ycyl(9,-41,144,53.5,6),ycyl(9,-19,144,53.5,6),box(-41,144,44.5,22,6,18),
              ycyl(3.7,-30,144,32.5,6)]
    for y in [-28,28]:
        # Recess the lower strap run instead of reducing ground clearance.
        holes.append(box(-57.7,y-7.7,24.9,55.4,15.4,2))
        holes += [box(-57.7,y-7.7,25,1.9,15.4,17.2),box(-4.2,y-7.7,25,3.4,15.4,17.2)]
    tray=add('BatteryDrawerPLA',cut(fuse(bits),holes),'PLA',
        'Removable tray243mm long,4mm floor; strap under-runs recessed; no friction-only retention. The two M4 screws carry withdrawal restraint.',True)

    add('BatteryCandidate',box(-50,-52,30,40,104,34.5),'reference',
        'Catalog fit candidate ONLY: VANT5S18.5V2200mAh,295g,104x34.5x40. Battery/charger/cell protection not selected.',True)
    pad_shapes=[box(-55,-56,29,50,112,1),box(-56,-52,30,6,104,10),
                box(-10,-52,30,6,104,10),box(-50,-59,30,40,7,10),box(-50,52,30,40,7,10)]
    for i,s in enumerate(pad_shapes):
        add('BatteryPad'+str(i),s,'reference',
            'Soft replaceable pack-specific liner; no hard screw tip touches pack. Body clearance is tuned by liner thickness, not by crushing the pack.',True)
    for y in [-28,28]:
        outer=box(-57.5,y-7.5,25.2,55,15,40.8)
        inner=box(-56,y-8,26.7,52,16,37.8)
        shape=outer.cut(inner).fuse(box(-2.5,y-7.5,39.5,1.5,15,25)).removeSplitter()
        add('BatteryBelt'+('N' if y<0 else 'P'),shape,'reference',
            '15x250 hook-and-loop strap, nominal1.5mm thick; closure on X side, not above pack. Belt passes THROUGH tray channels. Existing H02 qty2 budget retained.',True)

    # Cable bends and disconnected service position are reserved, not supplier
    # connector CAD. Both battery leads stay on the moving drawer. No cable
    # remains attached across the moving joint during extraction.
    path=[V(-30,52,49),V(-30,66,49),V(-30,80,47),V(-30,94,32.5),V(-30,157,32.5)]
    cables=[]
    for a,b in zip(path,path[1:]):
        d=b-a;cables.append(Part.makeCylinder(3,d.Length,a,d))
    for pt in path[1:-1]:cables.append(Part.makeSphere(3,pt))
    add('BatteryLeadRoute',fuse(cables),'reference',
        '6mm combined cable envelope, route only. Replace polyline elbows with actual harness bend radii; strain-relieve on drawer before the connector. Qualify fuse location near source.',True)
    add('BatteryServiceConnector',box(-42,157,29.5,24,24,14),'reference',
        'Insulated battery-side XT60-class connector/boot envelope, NOT selected supplier geometry. Disconnect vehicle half outside body before removing screws; cap live battery half.',True)
    # Two tie slots beside the connector and two upstream slots provide simple
    # strain relief. Printed tabs bound the boot; they are not electrical latches.
    s=tray.Shape
    for y in [118,164]:
        s=cut(s,[box(x,y-2,24,2.4,4,6) for x in [-46,-16.4]])
    tray.Shape=s
    pocket=box(-51,79,29,17,24,13).cut(box(-49,81,31,13,20,12))
    tray.Shape=tray.Shape.fuse(pocket).removeSplitter()
    # Integral balance-lead pocket with lacing slots, not another unsecured part.
    ph=[box(x,88,24,2.4,6,9) for x in [-48,-39.4]]
    tray.Shape=cut(tray.Shape,ph)

    doc.recompute()
    physical=[o for o in doc.Objects if hasattr(o,'MaterialBasis') and o.MaterialBasis!='reference']
    refs=[o for o in doc.Objects if hasattr(o,'MaterialBasis') and o.MaterialBasis=='reference']
    def hits(s,objects):
        result=[];bb=s.BoundBox
        for o in objects:
            if bb.intersect(o.Shape.BoundBox):
                v=s.common(o.Shape).Volume
                if v>.001:result.append(dict(part=o.Name,overlap_mm3=v))
        return result
    collisions=[]
    for a,b in combinations(physical,2):
        for h in hits(a.Shape,[b]):collisions.append(dict(a=a.Name,**h))
    reference_hits={o.Name:hits(o.Shape,physical) for o in refs}
    # Check battery module references against each other too (pack, padding,
    # straps, cables). Shared contact faces are allowed, overlapping volumes not.
    battery_reference_pairs=[]
    for a,b in combinations([o for o in refs if o.Name in moving],2):
        for h in hits(a.Shape,[b]):battery_reference_pairs.append(dict(a=a.Name,**h))
    moving_set=set(moving)
    released={n for n in added if n.startswith(('DrawerScrew','DrawerWasher'))}
    retained=[o for o in physical+refs if o.Name not in moving_set|released]
    # Planar-faced positive-Y boundary extrusion + original solid is a
    # continuous translation envelope (not a handful of sampled positions).
    # Cylindrical handle/hole faces have axes parallel to Y; their caps already
    # define the outer envelope. Curved cable/connector solids use conservative
    # bounding-box sweeps instead. Holes may be conservatively filled.
    def swept(s,distance,conservative=False):
        if conservative:
            b=s.BoundBox
            return box(b.XMin,b.YMin,b.ZMin,b.XLength,b.YLength+distance,b.ZLength)
        bits=[s]
        for f in s.Faces:
            if isinstance(f.Surface,Part.Plane) and f.normalAt(0,0).y>1e-7:
                bits.append(f.extrude(V(0,distance,0)))
        return Part.makeCompound(bits)
    service=[]
    for name in moving:
        o=doc.getObject(name)
        service.append(dict(part=name,travel_mm=220,hits=hits(swept(o.Shape,220,name=='BatteryLeadRoute'),retained)))
    # Max-body + top belt envelope tests the declared acceptance size, replacing
    # the catalog candidate and its soft, adjustable liners.
    maxpack=box(-55,-56,30,50,112,36)
    maxstraps=Part.makeCompound([box(-57.5,y-7.5,66,55,15,1.5) for y in [-28,28]])
    accept=[o for o in physical if o.Name not in moving_set|released]
    max_hits=hits(swept(maxpack,220),accept)+hits(swept(maxstraps,220),accept)
    tools_access=[]
    for x,suffix in [(-65,'XN'),(6,'XP')]:
        tools_access.append(dict(part='DrawerScrew'+suffix,hits=hits(ycyl(2.5,x,153.8,47,60),
             [o for o in physical+refs if o.Name!='DrawerScrew'+suffix])))
    # Screw withdrawal is coaxial +Y, before drawer translation.
    release_access=[]
    for name in sorted(released):
        release_access.append(dict(part=name,hits=hits(swept(doc.getObject(name).Shape,25),
            [o for o in physical+refs if o.Name not in released and not o.Name.startswith('DrawerNut')])) )
    # Finger-sized access proxy, not an ergonomic certification. It goes through
    # the handle above the separately parked connector with the frame installed.
    hand_hits=hits(box(-40,140,46,20,60,15),physical+refs)
    caster=Part.makeCylinder(43,65,V(-150,0,0))
    caster_hits=hits(caster,[doc.getObject(n) for n in added])
    tire=[]
    for sign in [-1,1]:
        tire.append(dict(side=sign,hits=hits(Part.makeCylinder(50.35,123,V(90,sign*153,50.35),V(0,sign,0)),
                                          [doc.getObject(n) for n in added])))
    rho={'PLA':1.24e-6,'steel':7.85e-6}
    old_cradle=old.getObject('BatteryCradlePLA').Shape.Volume*1.24e-6
    new_mass=sum(o.Shape.Volume*rho[o.MaterialBasis] for o in physical if o.Name in added)
    source_mass=json.loads((D3/'validation.json').read_text())['mass']['estimated_base_kg']
    total=source_mass-old_cradle+new_mass+.01 # extra soft liner allowance
    plate=doc.getObject('AluminumDeckD3').Shape
    prior=old.getObject('AluminumDeckD3').Shape
    same_plate=plate.cut(prior).Volume<1e-6 and prior.cut(plate).Volume<1e-6
    unchanged=[o.Name for o in physical if o.Name not in added]
    invariant=all(doc.getObject(n).Shape.cut(old.getObject(n).Shape).Volume<1e-6 and
                  old.getObject(n).Shape.cut(doc.getObject(n).Shape).Volume<1e-6 for n in unchanged)
    report=dict(parameters=P,all_shapes_valid=all(o.Shape.isValid() for o in physical+refs),
        physical_parts=len(physical),checked_pairs=len(physical)*(len(physical)-1)//2,
        collisions=collisions,reference_collisions={k:v for k,v in reference_hits.items() if v},
        battery_reference_pair_collisions=battery_reference_pairs,handle_access_proxy_hits=hand_hits,
        continuous_drawer_service=service,max_accepted_pack_sweep_hits=max_hits,
        service_hex_key_access=tools_access,fastener_removal=release_access,
        caster_sweep_hits=caster_hits,tire_outward_service=tire,
        unchanged_physical_parts=len(unchanged),unchanged_parts_BRep_equal=invariant,
        deck_BRep_unchanged=same_plate,removed_parts=removed,added_parts=added,moving_parts=moving,
        released_before_service=sorted(released),
        clearances_mm=dict(ground=25,nominal_pack_belt_to_rail=3,max_pack_belt_to_rail=1.5,
             tongue_top_running_gap=2,drawer_sidewall_to_guide=1,pack_front_to_frame_after220mm=14,
             handle_top_to_rail=2),
        mass=dict(source_D3_kg=source_mass,old_cradle_removed_kg=old_cradle,new_prints_and_hardware_kg=new_mass,
             soft_liner_allowance_kg=.01,battery_allowance_carried_kg=.75,electrical_allowance_carried_kg=2.1,
             no_battery_catalog_mass_credit=True,estimated_base_kg=total,remaining_to_10kg_kg=10-total,
             total_solid_PLA_kg=sum(o.Shape.Volume*1.24e-6 for o in physical if o.MaterialBasis=='PLA'),actually_weighed=False),
        inherited_D3_tests='Unchanged deck, cargo belts, grid hardware and frame. Original36-hole/tool checks remain applicable; new parts stay below69mm. See saved validation for independent clearance checks.',
        limitations=['Catalog candidate is not a final battery selection: cost, usable runtime, charger and individual-cell protection unresolved',
            'Guide and tray are PLA prototypes: print orientation, sliding friction, creep, heat and withdrawal restraint require dummy-load testing',
            'All fits nominal; allow only measured pack body<=50x112x36 with leads/boots inside their separate reservations',
            'Unplug externally before withdrawal; this is not a live hot-swap connector or an electrical dock',
            'Vehicle15kg/SF2 qualification remains pending; no claim from battery-retainer CAD alone'])
    (HERE/'parameters.json').write_text(json.dumps(P,ensure_ascii=False,indent=2)+'\n')
    (HERE/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    doc.saveAs(str(HERE/(NAME+'.FCStd')))
    print(json.dumps({k:report[k] for k in ['collisions','reference_collisions','continuous_drawer_service','max_accepted_pack_sweep_hits','service_hex_key_access','fastener_removal','caster_sweep_hits','tire_outward_service','mass']},ensure_ascii=False),flush=True)
    assert not collisions and not report['reference_collisions']
    assert not battery_reference_pairs and not hand_hits
    assert not any(r['hits'] for r in service+tools_access+release_access+tire)
    assert not max_hits and not caster_hits and same_plate and invariant and total<10
    Part.export(physical,str(HERE/(NAME+'.step')))
    step=HERE/(NAME+'.step');step.write_text('\n'.join(x.rstrip() for x in step.read_text().splitlines())+'\n')
    manifest=[]
    for name in printed:
        s=doc.getObject(name).Shape.copy()
        # Orientation candidate only: overhangs/bridges need slicer inspection.
        if name.startswith('BatteryGuide'):s.rotate(V(),V(0,1,0),90 if name.endswith('XN') else -90)
        b=s.BoundBox;s.translate(V(-b.XMin,-b.YMin,-b.ZMin));b=s.BoundBox
        assert max(b.XLength,b.YLength)<256,(name,b)
        MeshPart.meshFromShape(Shape=s,LinearDeflection=.06,AngularDeflection=.25,Relative=False).write(str(HERE/(name+'.stl')))
        manifest.append(dict(file=name+'.stl',size_mm=[b.XLength,b.YLength,b.ZLength],solid_mass_g=s.Volume*1.24e-3))
    (HERE/'print_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('D4 build completed',flush=True)


if __name__=='__main__':main()
