"""D5: selected Makita power module in a rear service bay, low computer tray.

Supplier battery/adapter are catalog envelopes, not mating-interface CAD.
The entire latched battery+adapter module lifts out after unplugging and
releasing its one webbing belt. Thus no guessed adapter screw pattern or
printed electrical contact geometry is used.
"""
from pathlib import Path
from itertools import combinations
import hashlib
import json
import subprocess
import tempfile
import FreeCAD as App
import Part
import MeshPart

HERE=Path(__file__).resolve().parent
D3=HERE.parent/'aluminum-direct-deck'
V=App.Vector
NAME='AMR01_MakitaPower_D5'
SOURCE='099686bacaad0f72e8bc4ce15005cd708a5b2f83'
RHO={'aluminum':2.7e-6,'steel':7.85e-6,'PLA':1.24e-6,'rubber':1.1e-6}
P=dict(revision='D5',date='2026-09-22',battery='Makita BL1860B A-60464',
       battery_selected=True,charger='Makita DC18RF JPADC18RF',
       adapter='Netkey diy-adapter03',source_revision=SOURCE,
       battery_catalog_LWH_mm=[113,75,62],battery_installed_XYZ_mm=[75,113,62],
       battery_origin_xyz_mm=[-240,-56.5,112],battery_catalog_mass_budget_kg=.68,
       adapter_catalog_LWH_mm=[95,90,30],adapter_installed_XYZ_mm=[90,95,30],
       adapter_origin_xyz_mm=[-247.5,-47.5,174],adapter_catalog_mass_kg=.123,
       mating_insertion_depth_credited_mm=0,
       battery_and_adapter_geometry='catalog bounding envelopes; interface offsets must be measured',
       module_retention='one25mm webbing/cam buckle belt through tray; padded body stops',
       exchange='power off, unplug external connector, open belt, lift whole battery+adapter module',
       service_translation_xyz_mm=[0,0,140],deck_LWH_mm=[300,300,4],deck_top_z_mm=103,
       minimum_fixed_ground_mm=25,normal_payload_kg=10,structural_payload_kg=15,
       new_metal_machining=False,box_body=False,charger_on_vehicle=False,
       loaded_use_released=False,electrical_protection_qualification=False)


def box(x,y,z,l,w,h):return Part.makeBox(l,w,h,V(x,y,z))
def fuse(shapes):
    s=shapes[0]
    for other in shapes[1:]:s=s.fuse(other)
    return s.removeSplitter()
def cut(s,tools):return s.cut(Part.makeCompound(tools)).removeSplitter()
def center(s):
    return [sum(getattr(t.CenterOfMass,k)*t.Volume for t in s.Solids)/s.Volume for k in ['x','y','z']]
def hits(s,objects):
    found=[];bb=s.BoundBox
    for o in objects:
        if bb.intersect(o.Shape.BoundBox):
            volume=s.common(o.Shape).Volume
            if volume>.001:found.append(dict(part=o.Name,overlap_mm3=volume))
    return found
def pipe(points,r=3):
    # Conservative polyline harness envelope. Detailed bends are not fabricated.
    p=[V(*a) for a in points];bits=[]
    for a,b in zip(p,p[1:]):
        d=b-a;bits.append(Part.makeCylinder(r,d.Length,a,d))
    for a in p[1:-1]:bits.append(Part.makeSphere(r,a))
    return fuse(bits)


def main():
    temp=tempfile.TemporaryDirectory(prefix='amr-d5-source-')
    src=Path(temp.name)/'D3.FCStd'
    src.write_bytes(subprocess.check_output(['git','-C',str(HERE),'show',
                   SOURCE+':cad/amr07/aluminum-direct-deck/AMR01_AluminumDirect_D3.FCStd']))
    old=App.openDocument(str(src));doc=App.newDocument(NAME)
    doc.Label='AMR D5 | BL1860B6Ah rear lift-out | deck103mm'
    removed=['BatteryCradlePLA','BatteryReservedSpace','BatteryConnectorEnvelope','ElectronicsTrayPLA']
    for o in old.Objects:
        if o.TypeId=='PartDesign::Feature' and o.Name not in removed:doc.copyObject(o,False)
    added=[];printed=[];moving=[];changed=[]
    def add(name,s,mat,note,moves=False):
        assert s.isValid() and len(s.Solids)==1,(name,len(s.Solids))
        o=doc.addObject('PartDesign::Feature',name);o.Shape=s
        for key,value in [('MaterialBasis',mat),('ModelNote',note)]:
            o.addProperty('App::PropertyString',key,'Design');setattr(o,key,value)
        added.append(name)
        if mat=='PLA':printed.append(name)
        if moves:moving.append(name)
        return o

    # New rear tray uses exactly the old four top-slot M6 fittings. Its short
    # rear overhang is supported by the existing X=-215 crossrail, not a riser.
    bits=[box(-254,-80,99,99,160,2.4),box(-244,-59,108.6,83,118,2.4)]
    for y in [-47,-1.5,44]:bits.append(box(-244,y,101.4,83,3,7.2))
    for x in [-247,-161]:bits.append(box(x,-62,101.4,3,124,33.6))
    for y in [-62,59]:bits.append(box(-244,y,108.6,83,3,22.4))
    holes=[Part.makeCylinder(3.3,8,V(x,y,98)) for x in [-188,-168] for y in [-65,65]]
    # Existing screw heads and OD18 washers sit beside the locating walls.
    holes += [Part.makeCylinder(5.6,34,V(x,y,103)) for x in [-188,-168] for y in [-65,65]]
    holes += [Part.makeCylinder(9.3,1.8,V(x,y,101.4)) for x in [-188,-168] for y in [-65,65]]
    # A captive belt passes below the raised seat, through both side walls.
    holes.append(box(-255,-13,104.8,103,26,2.0))
    tray=add('RearBatteryTrayPLA',cut(fuse(bits),holes),'PLA',
        'Rear service tray: same four M6x10/large washers/slot nuts as D3. Seat111mm plus1mm pad. Belt tunnel below seat. Structural payload stays on metal deck. Print/creep/load test pending.')
    add('BatteryBL1860B',box(-240,-56.5,112,75,113,62),'reference',
        'SELECTED Makita genuine BL1860B6Ah108Wh. Official catalog113x75x62. Bounding envelope, not supplier mating CAD. Use0.68kg conservative regional catalog allowance.',True)
    add('BatteryAdapter03',box(-247.5,-47.5,174,90,95,30),'reference',
        'SELECTED Netkey diy-adapter03, approximate95x90x30mm123g. Full height stacked without subtracting mating overlap. Switch, latch, lead orientation and assembled footprint require received-part check.',True)
    # Pads stay in the tray; they never cover the electrical contacts or latch.
    pads=[box(-240,-56.5,111,75,113,1),box(-244,-56.5,112,4,113,18),
          box(-165,-56.5,112,4,113,18),box(-240,-59,112,75,2.5,18),
          box(-240,56.5,112,75,2.5,18)]
    for i,s in enumerate(pads):add('BatteryPad'+str(i),s,'reference','Replaceable soft locating pad; tune to received casing, no screw presses on the battery.')
    add('BatteryBeltTopPad',box(-247.5,-12.5,204,90,25,1),'reference',
        'Removable insulating load spreader/pad under belt; position must clear adapter switch/fuse and vents. Not a support attached to battery.',True)
    belt=box(-252,-12.5,105,98.5,25,101.5).cut(box(-250.5,-13,106.5,95.5,26,98.5))
    add('BatteryRetentionBelt',belt,'reference',
        'One25mm E-Value BT-2520BK cam-buckle belt (same selected family as cargo straps). Routes through tray tunnel. Cut/secure excess; buckle envelope is a reservation. Release before lifting.')
    add('BatteryBuckleEnvelope',box(-272,-17.5,145,20,35,55),'reference',
        'Cam buckle20x35x55 reservation, not supplier CAD. Manufacturer complete strap width30/depth18mm;2mm depth allowance. Cut and secure excess. Fully release and park clear of extraction path.')
    # Whole adapter and pack travel together. The factory battery latch is
    # operated only after removing the assembly from the AMR for charging.
    add('BatteryModuleHarness',pipe([[-210,47.5,189],[-210,69,189],[-210,84,171],[-210,96,171]]),
        'reference','Two14AWG wires in6mm route envelope; strain relief on module. Supplied40cm wires shortened or secured outside extraction path; connector is disconnected before lift.',True)
    add('BatteryServiceConnector',box(-222,96,164,24,24,14),'reference',
        'XT60-class insulated connector/boot allowance, female protected live battery side. Exact connector/boot selection and bend radius remain electrical implementation work.',True)
    add('BatteryVehicleConnector',box(-222,121,164,24,20,14),'reference',
        'Disconnected vehicle-side connector parked1mm clear; rejoin only with main switch OFF. Flexible lead parked clear of lift volume.')
    add('BatteryVehicleHarness',pipe([[-210,141,171],[-210,152,171],[-210,152,158],[-185,148,155],
                                    [-165,144,133],[-159,127,125],[-159,111,88],[-145,111,84],
                                    [165,111,84],[185,102,105]]),
        'reference','Main harness route; outside cargo plate and belts, inside side rail channel. A6 cable-routing acceptance remains open; not detailed conductor geometry.')

    # Former battery cradle is reused as a low computer+supervisor carrier.
    # The same four M6 bottom-slot fasteners remain atX=-80/20,Y=+-65.
    low=old.getObject('BatteryCradlePLA').Shape.copy()
    for x in [-10,-75]:
        low=cut(low,[box(x-7.7,-46,24.9,15.4,92,2.0),
                     box(x-7.7,-45.2,25,15.4,1.9,4),box(x-7.7,43.3,25,15.4,1.9,4)])
    add('LowElectronicsCradlePLA',low,'PLA',
        'Old D3 mounting interface and floor25mm, now computer+supervisor. Two15mm strap channels added. Electronics body mounting remains provisional until actual computer/cases are chosen.')
    computer=doc.getObject('Reserved_Computer');computer.Shape=box(-45,-40,30,70,80,40);changed.append(computer.Name)
    computer.Label='COMPUTER RESERVATION70x80x40 | low Z30..70 |0.5kg allowance'
    supervisor=doc.getObject('Reserved_SupervisorRS485');supervisor.Shape=box(-90,-35,30,30,70,45);changed.append(supervisor.Name)
    supervisor.Label='SUPERVISOR RESERVATION30x70x45 | Z30..75'
    add('LowElectronicsPad',box(-90,-42,28,115,84,2),'reference','2mm soft insulating electronics base liner; module temperatures need ventilation testing.')
    for i,(x,top) in enumerate([(-10,72.5),(-75,77.5)]):
        outer=box(x-7.5,-45,25.2,15,90,top-25.2)
        inner=box(x-8,-43.5,26.7,16,87,top-28.2)
        add('LowElectronicsBelt'+str(i),outer.cut(inner),'reference',
            '15mm retaining strap through floor slots. Computer/supervisor only; does not carry cargo. Product and received case fit to finalize.')

    doc.recompute()
    physical=[o for o in doc.Objects if hasattr(o,'MaterialBasis') and o.MaterialBasis!='reference']
    refs=[o for o in doc.Objects if hasattr(o,'MaterialBasis') and o.MaterialBasis=='reference']
    collisions=[]
    for a,b in combinations(physical,2):
        for h in hits(a.Shape,[b]):collisions.append(dict(a=a.Name,**h))
    reference_hits={o.Name:hits(o.Shape,physical) for o in refs}
    reference_pairs=[]
    for a,b in combinations(refs,2):
        for h in hits(a.Shape,[b]):reference_pairs.append(dict(a=a.Name,**h))
    released=['BatteryRetentionBelt','BatteryBuckleEnvelope']
    fixed=[o for o in physical+refs if o.Name not in moving+released]
    service=[]
    for name in moving:
        b=doc.getObject(name).Shape.BoundBox
        # Conservative full bounding-box sweep proves the entire upward path.
        s=box(b.XMin,b.YMin,b.ZMin,b.XLength,b.YLength,b.ZLength+140)
        service.append(dict(part=name,hits=hits(s,fixed)))
    fingers=hits(box(-231,-86,136,60,28,30),physical+refs)
    caster=hits(Part.makeCylinder(43,65,V(-150,0,0)),[doc.getObject(n) for n in added])
    tires=[dict(side=s,hits=hits(Part.makeCylinder(50.35,123,V(90,s*153,50.35),V(0,s,0)),
                                [doc.getObject(n) for n in added])) for s in [-1,1]]
    # Unchanged grid fastener stacks bottom out no lower than92.8mm. New
    # under-deck computer/straps stay below77.5, rear module stays outsideX=-150.
    grid=[]
    for x in [-125,-75,-25,25,75,125]:
        for y in [-115,-65,-15,35,85,135]:
            grid.append(dict(x=x,y=y,hits=hits(Part.makeCylinder(5,30,V(x,y,92.8)),
                [doc.getObject(n) for n in added]+[computer,supervisor])))
    # Preserve quoted plate and all original metal/hardware geometries.
    invariant_names=[o.Name for o in physical if o.Name not in added+changed]
    invariant=all(doc.getObject(n).Shape.cut(old.getObject(n).Shape).Volume<1e-6 and
                  old.getObject(n).Shape.cut(doc.getObject(n).Shape).Volume<1e-6 for n in invariant_names)
    removed_mass=sum(old.getObject(n).Shape.Volume*RHO[old.getObject(n).MaterialBasis]
                     for n in removed if old.getObject(n).MaterialBasis!='reference')
    added_mass=sum(doc.getObject(n).Shape.Volume*RHO[doc.getObject(n).MaterialBasis]
                   for n in added if doc.getObject(n).MaterialBasis!='reference')
    source_mass=json.loads((D3/'validation.json').read_text())['mass']['estimated_base_kg']
    # Charge the entire manufacturer's125g belt even if its2m web is shortened.
    accessory_allowance=.18 # battery belt .125 + pads .025; electronics .03
    total=source_mass-removed_mass+added_mass-.75+.68+.123+accessory_allowance
    # Difference in moments: original rest-of-vehicle CG is uncertain. Report
    # a range, not an invented measured absolute CG. Parts use solid centroid;
    # battery/computer use their envelope centers and explicit mass allowances.
    deltas=[]
    def ledger(name,m,c):deltas.append(dict(name=name,mass_kg=m,center_mm=c))
    for n in removed:
        o=old.getObject(n)
        if o.MaterialBasis!='reference':ledger('remove '+n,-o.Shape.Volume*RHO[o.MaterialBasis],center(o.Shape))
    for n in added:
        o=doc.getObject(n)
        if o.MaterialBasis!='reference':ledger('add '+n,o.Shape.Volume*RHO[o.MaterialBasis],center(o.Shape))
    ledger('remove old battery allocation',-.75,[-30,0,60.5])
    ledger('BL1860B',.68,[-202.5,0,143]);ledger('adapter03',.123,[-202.5,0,189])
    ledger('battery full catalog strap plus pads',.15,[-205,0,145]);ledger('low electronics pads/straps',.03,[-30,0,50])
    for n,m in [('Reserved_Computer',.5),('Reserved_SupervisorRS485',.05)]:
        ledger('remove old '+n,-m,center(old.getObject(n).Shape));ledger('relocate '+n,m,center(doc.getObject(n).Shape))
    dm=sum(a['mass_kg'] for a in deltas);moment=[sum(a['mass_kg']*a['center_mm'][i] for a in deltas) for i in range(3)]
    assert abs(source_mass+dm-total)<1e-8
    ranges=[[(source_mass*edge+moment[i])/total for edge in interval]
            for i,interval in enumerate([[-10,10],[-10,10],[85,110]])]
    report=dict(parameters=P,physical_parts=len(physical),all_shapes_valid=all(o.Shape.isValid() for o in physical+refs),
        checked_physical_pairs=len(physical)*(len(physical)-1)//2,collisions=collisions,
        reference_collisions={k:v for k,v in reference_hits.items() if v},reference_pair_collisions=reference_pairs,
        continuous_module_lift=service,finger_access_proxy_hits=fingers,caster_sweep_hits=caster,
        tire_outward_service=tires,grid_fastener_envelopes=grid,added_parts=added,removed_parts=removed,
        changed_parts=changed,moving_parts=moving,released_before_service=released,
        unchanged_physical_parts=len(invariant_names),unchanged_parts_BRep_equal=invariant,
        clearances_mm=dict(deck_to_adapter=7.5,deck_to_belt=3.5,deck_to_tray=5,
            ground=25,computer_to_deck=29,highest_underdeck_electronics_strap_to_grid_tip=15.3,
            buckle_body_extension_behind_frame=42,module_height_conservative=92),
        mass=dict(source_D3_kg=source_mass,removed_prints_kg=removed_mass,new_prints_kg=added_mass,
            old_battery_allocation_removed_kg=.75,battery_kg=.68,adapter_kg=.123,
            new_straps_and_pads_allowance_kg=accessory_allowance,
            electrical_total_kg=2.1-.75+.68+.123,estimated_base_kg=total,remaining_to_10kg_kg=10-total,
            total_solid_PLA_kg=sum(o.Shape.Volume*1.24e-6 for o in physical if o.MaterialBasis=='PLA'),actually_weighed=False),
        cg_difference=dict(ledger=deltas,mass_change_kg=dm,moment_change_kg_mm=moment,
            conditional_base_cg_xyz_ranges_mm=ranges,
            basis='conditional on D3 CGx/y+-10,z85..110mm assumptions; envelope-centered electrical mass; not an absolute measured CG',
            requires_updated_stability_envelope=True),
        limitations=['Pack and adapter CAD are conservative catalog envelopes, not manufacturer interface STEP.',
            'Check actual latched module offsets, buckle/switch/fuse access, casing tolerances and harness bend radius with a dummy module before final printing.',
            'PLA tray, belt and four rail joints require dummy-load, temperature/creep and repeated service tests.',
            'Two-wire adapter does not establish individual-cell, temperature or undervoltage protection. Complete and qualify vehicle power protection before operation.',
            'Normal10kg/structural15kg SF2 are design targets; loaded operation has not been released.'])
    (HERE/'parameters.json').write_text(json.dumps(P,ensure_ascii=False,indent=2)+'\n')
    (HERE/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    doc.saveAs(str(HERE/(NAME+'.FCStd')))
    print(json.dumps({k:report[k] for k in ['collisions','reference_collisions','reference_pair_collisions','continuous_module_lift','finger_access_proxy_hits','caster_sweep_hits','tire_outward_service','mass','cg_difference']},ensure_ascii=False),flush=True)
    assert not collisions and not report['reference_collisions'] and not reference_pairs
    assert not any(r['hits'] for r in service+tires+grid) and not fingers and not caster
    assert invariant and total<10
    Part.export(physical,str(HERE/(NAME+'.step')))
    # A second export explicitly includes catalog envelopes for other CAD apps.
    Part.export(physical+[doc.getObject(n) for n in ['BatteryBL1860B','BatteryAdapter03']],
                str(HERE/(NAME+'-with-power-envelopes.step')))
    for file in HERE.glob('*.step'):file.write_text('\n'.join(t.rstrip() for t in file.read_text().splitlines())+'\n')
    manifest=[]
    for name in printed:
        s=doc.getObject(name).Shape.copy();b=s.BoundBox;s.translate(V(-b.XMin,-b.YMin,-b.ZMin));b=s.BoundBox
        assert max(b.XLength,b.YLength,b.ZLength)<256
        MeshPart.meshFromShape(Shape=s,LinearDeflection=.06,AngularDeflection=.25,Relative=False).write(str(HERE/(name+'.stl')))
        manifest.append(dict(file=name+'.stl',size_mm=[b.XLength,b.YLength,b.ZLength],solid_mass_g=s.Volume*1.24e-3))
    (HERE/'print_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('D5 build complete',flush=True)


if __name__=='__main__':main()
