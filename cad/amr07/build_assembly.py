"""A6 assembly with cargo deck, corrected interfaces and explicit reservations."""
from pathlib import Path
from itertools import combinations
import hashlib
import json
import sys
import FreeCAD as App
import Part

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parent/'amr05'
sys.path.insert(0,str(HERE))
from hardware_geometry import profile, slotnut_at, deck_slotnut, screw_axis_and_head
from cargo_deck import build_deck_specs

V=App.Vector
NAME='AMR01_M0601C_A6'


def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    source=PREVIOUS/'AMR01_M0601C_A4.FCStd'; source_hash=digest(source)
    assert NAME not in App.listDocuments()
    old=App.openDocument(str(source)); doc=App.newDocument(NAME)
    doc.Label='AMR-01 A6 | flat-floor cargo10 | no added brake | structure15 SF2 target'
    copied={}
    for obj in old.Objects:
        if obj.TypeId=='PartDesign::Feature': copied[obj.Name]=doc.copyObject(obj,False)
        elif obj.TypeId=='App::DocumentObjectGroup':
            group=doc.addObject(obj.TypeId,obj.Name); group.Label=obj.Label; copied[obj.Name]=group
        else: raise AssertionError(obj.TypeId)
    for obj in old.Objects:
        if obj.TypeId=='App::DocumentObjectGroup': copied[obj.Name].Group=[copied[c.Name] for c in obj.Group]
    changed=set()
    caster=json.loads((HERE/'caster_procurement.json').read_text())
    # Same nominal D50/W20/H65, 46x35 pitch and 16 mm trail. Keep the
    # simplified geometry; it is not the supplier's fork/bearing CAD.
    for name in ('CasterTop','SwivelRace','CasterFork','CasterTire','CasterCore'):
        o=doc.getObject(name)
        o.Label='TRUSCO TYG-50 | '+name+' | nominal proxy'
        o.SourceURL=caster['manufacturer_dimensions_url']
        o.ModelNote='TYG-50 supplier drawing: D50/W20/H65±1.5, plate59x47, pitch46x35, holes6.5, trail16±1.5, R41, mass165g. Existing simplified proxy retained; exact fork/bearing geometry and loaded contact height require received-part check.'
        changed.add(name)
    for i,y in enumerate((-135,-65,65,135),1):
        s=profile(400); s.translate(V(-200,y,84)); o=doc.getObject('Rail400_'+str(i)); o.Shape=s
        o.ModelNote='Published slot8/lip2/depth9/max16.5; nominal reconstructed bevels. Internal webs and small radii simplified. Use catalog mass/inertia, not this solid.'; changed.add(o.Name)
    for i,x in enumerate((-215,215),1):
        s=profile(300); s.rotate(V(0,0,0),V(0,0,1),90); s.translate(V(x,-150,84))
        o=doc.getObject('Cross300_'+str(i)); o.Shape=s; o.ModelNote=doc.getObject('Rail400_1').ModelNote; changed.add(o.Name)
    nut_data=[]
    for obj in list(doc.Objects):
        if not obj.Name.startswith('SlotNut_'): continue
        suffix=obj.Name[len('SlotNut_'):]
        if suffix.startswith('Mount_'): bolt_name='MountFrameBolt_'+suffix[6:]
        elif suffix.startswith('Gusset_'): bolt_name='GussetBolt_'+suffix[7:]
        elif suffix.startswith('Caster_'): bolt_name='CasterFrameBolt_'+suffix[7:]
        elif suffix.startswith('Cradle_'): bolt_name='CradleBolt_'+suffix[7:]
        elif suffix.startswith('Electronics_'): bolt_name='ElectronicsBolt_'+suffix[12:]
        elif suffix.startswith('FrontDeck_'): bolt_name='FrontDeckBolt_'+suffix[10:]
        else: bolt_name=suffix
        bolt=doc.getObject(bolt_name); assert bolt is not None, (obj.Name,bolt_name)
        inward=screw_axis_and_head(bolt.Shape)
        b=obj.Shape.optimalBoundingBox(False,False); center=b.Center
        surface=center-inward*4
        rail_axis=(0,1,0) if abs(surface.x)>=199.999 else (1,0,0)
        before=obj.Shape.Volume
        obj.Shape=slotnut_at(tuple(surface),tuple(inward),rail_axis)
        obj.Label='HNTT6-6 | catalog6.3 thick, tapered nominal profile'
        obj.ModelNote='A7.8/B15/E5.5/T6.3/L14. Rear taper reconstructed from catalog view; thread and corner radii omitted. Received slot/nut measurements required.'
        changed.add(obj.Name)
        nut_data.append({'name':obj.Name,'frame_surface_xyz_mm':list(surface),'inward':list(inward),'mass_delta_kg':(obj.Shape.Volume-before)*7.85e-6})
    mount_path=HERE/'M0601C_mount_A6_R1.step'
    mount=Part.read(str(mount_path)); mount.translate(V(45,120,35))

    def add(spec):
        group=doc.getObject(spec['group'])
        if group is None: group=doc.addObject('App::DocumentObjectGroup',spec['group'])
        o=doc.addObject('PartDesign::Feature',spec['name']); o.Shape=spec['shape']; o.Label=spec['label']
        for field,value in [('MaterialBasis',spec['material']),('ModelNote',spec['note']),('SourceURL',spec.get('source',''))]:
            o.addProperty('App::PropertyString',field,'Design'); setattr(o,field,value)
        if 'hardware_spec' in spec:
            o.addProperty('App::PropertyString','HardwareSpec','Hardware'); o.HardwareSpec=spec['hardware_spec']
        group.addObject(o)
        return o

    for side in ('L','R'):
        s=mount.copy()
        if side=='R': s.rotate(V(90,0,0),V(0,0,1),180)
        o=doc.getObject('CustomMotorMount'+side); o.Shape=s; o.Label='A6-R1 CNC mount '+side+' | seated pocket + washer recesses'
        o.ModelNote='A4 width90/t5 retained; profile +.12, seat axisZ50.18, hole groupZ50.35,3x3.2 holes,6.2x.5 washer recesses,wire6.5. Conditional lot fit and strength still pending.'
        changed.add(o.Name)
        for i,(x,z) in enumerate([(90,57.95),(83.4182069312,46.55),(96.5817930688,46.55)]):
            washer=Part.makeCylinder(2.5,.5,V(x,130,z),V(0,1,0)).cut(Part.makeCylinder(1.35,.5,V(x,130,z),V(0,1,0)))
            if side=='R': washer.rotate(V(90,0,0),V(0,0,1),180)
            add({'name':'MotorSeatWasher_'+str(i)+side,'shape':washer,'group':'07_Fasteners','material':'steel',
                 'label':'FW-2505-05EB | 2.7x5x0.5 | '+side,'note':'Purchased washer nominal geometry; received head/washer seating and hardness require checking.',
                 'source':'https://wilco.jp/products/F/FW-EB.html','hardware_spec':'2.7x5x0.5 steel plain washer'})

    deck_specs=build_deck_specs(include_reference=True,slotnut_factory=deck_slotnut)
    for spec in deck_specs:
        if spec['name'].startswith('SlotNut_CargoDeck'):
            bb=spec['shape'].optimalBoundingBox(False,False)
            spec['shape']=deck_slotnut(bb.Center.x,bb.Center.y,99,(0,0,-1))
            spec['note']='HNTT6-6 catalog dimensions with reconstructed taper; bolt engagement per mount_interface.json.'
        add(spec)
    # Explicit electronic reservations, separated from the real cargo deck.
    reservations={
        'Protection':[155,-120,112,70,70,35],
        'ClampAndPower':[175,-45,106,50,90,35],
        'EmergencyStop':[175,65,112,40,40,60],
        'SupervisorRS485':[-225,40,112,70,45,30],
        'Computer':[-225,-45,106,70,80,40]}
    for name,xyz in reservations.items():
        x,y,z,l,w,h=xyz
        add({'name':'Reserved_'+name,'shape':Part.makeBox(l,w,h,V(x,y,z)), 'group':'10_ElectricalReservations',
             'material':'reference','label':name+' | RESERVED, not selected hardware fit',
             'note':'Unselected enclosure/mounts and harness routing; this occupied volume is not a fabricated component.'})
    doc.recompute()
    parts=[o for o in doc.Objects if o.TypeId=='PartDesign::Feature' and o.MaterialBasis!='reference']
    refs=[o for o in doc.Objects if o.TypeId=='PartDesign::Feature' and o.MaterialBasis=='reference']
    assert all(o.Shape.isValid() and not o.Shape.isNull() for o in parts+refs)
    boxes={o.Name:o.Shape.optimalBoundingBox(False,False) for o in parts+refs}
    collisions=[]; boolean_count=0
    for a,b in combinations(parts,2):
        if boxes[a.Name].intersect(boxes[b.Name]):
            boolean_count+=1; v=a.Shape.common(b.Shape).Volume
            if v>.001: collisions.append({'a':a.Name,'b':b.Name,'overlap_mm3':v})
    reference_hits=[]
    for a in refs:
        for b in parts:
            if boxes[a.Name].intersect(boxes[b.Name]):
                v=a.Shape.common(b.Shape).Volume
                if v>.001: reference_hits.append({'reference':a.Name,'part':b.Name,'overlap_mm3':v})
    access=[]
    def check(name,s,excluded=()):
        bb=s.optimalBoundingBox(False,False); hits=[]
        for o in parts:
            if o.Name in excluded or not bb.intersect(boxes[o.Name]): continue
            v=s.common(o.Shape).Volume
            if v>.001: hits.append({'part':o.Name,'overlap_mm3':v})
        access.append({'name':name,'hits':hits})
    for side,sign in [('L',1),('R',-1)]:
        for i,(x,z) in enumerate([(90,57.95),(83.4182069312,46.55),(96.5817930688,46.55)]):
            check('M2p5_driver_'+side+str(i),Part.makeCylinder(2,30,V(x,sign*127.5,z),V(0,-sign,0)),['MotorFaceBolt_'+str(i)+side])
        for x in (52.5,127.5): check('M6_driver_'+side+str(x),Part.makeCylinder(4,40,V(x,sign*135,58),V(0,0,-1)))
        for travel in (1,5,10,20,40,80):
            tire=doc.getObject('Tire'+side).Shape.copy(); tire.translate(V(0,sign*travel,0))
            check('Tire_outboard_'+side+str(travel),tire,['Tire'+side,'TireCover'+side])
    deck_names=[s['name'] for s in deck_specs]
    for distance in (1,20,80,160):
        b=doc.getObject('BatteryReservedSpace').Shape.copy(); b.translate(V(0,0,distance))
        check('Battery_lift_deck_removed_'+str(distance),b,deck_names)
    electrical=App.openDocument(str(PREVIOUS/'AMR01_ElectricalLayout_A4.FCStd'))
    harness=[]
    for side in ('L','R'):
        wire=electrical.getObject('Route_M0601FixedHarness'+side).Shape
        for name in ['CustomMotorMount'+side]+['MotorSeatWasher_'+str(i)+side for i in range(3)]:
            v=wire.common(doc.getObject(name).Shape).Volume
            if v>.001: harness.append({'part':name,'overlap_mm3':v})
    contacts={n:boxes[n].ZMin for n in ('TireL','TireR','CasterTire')}
    previous_mass=json.loads((PREVIOUS/'validation_results.json').read_text())['mass']['estimated_complete_base_kg']
    mount_delta=sum((doc.getObject('CustomMotorMount'+s).Shape.Volume-old.getObject('CustomMotorMount'+s).Shape.Volume)*2.7e-6 for s in ('L','R'))
    added_mass=sum(o.Shape.Volume*(7.85e-6 if o.MaterialBasis=='steel' else 2.7e-6)
                   for o in parts if old.getObject(o.Name) is None)
    # Strap and edge guard mass is in the deck budget, since they are references.
    deck_cfg=json.loads((HERE/'deck_parameters.json').read_text())
    noncad_deck=2*deck_cfg['procurement']['cargo_straps']['catalog_each_mass_kg']+deck_cfg['mass_budget']['edge_protection_and_slack_retention_kg']
    caster_mass_delta=caster['catalog_mass_kg']-caster['previous_CAD_mass_allowance_kg']
    mass=previous_mass+mount_delta+sum(n['mass_delta_kg'] for n in nut_data)+added_mass+noncad_deck+caster_mass_delta
    report={'status':'nominal_geometry_review_revision_not_manufacturing_or_operating_release',
        'source_A4_sha256':source_hash,'mount_STEP_sha256':digest(mount_path),
        'physical_parts':len(parts),'physical_pair_count':len(parts)*(len(parts)-1)//2,
        'bounding_box_candidate_booleans':boolean_count,'collisions':collisions,
        'reference_collisions':reference_hits,'tool_and_service_access':access,'harness_collisions':harness,
        'wheel_and_caster_floor_contacts_z_mm':contacts,'changed_existing_features':sorted(changed),
        'slot_nut_updates':nut_data,'electrical_reservations_xyz_LWH_mm':reservations,
        'caster_substitution':{'part':caster['part'],'drawing_source':caster['manufacturer_dimensions_url'],
            'nominal_mount_and_contact_dimensions_unchanged':True,'exact_supplier_CAD':False,
            'received_height_and_swivel_clearance_verified':False},
        'mass':{'previous_base_estimate_kg':previous_mass,'mount_change_kg':mount_delta,
                'caster_catalog_mass_correction_kg':caster_mass_delta,
                'slot_nut_change_kg':sum(n['mass_delta_kg'] for n in nut_data),'new_CAD_parts_kg':added_mass,
                'deck_straps_and_edge_guard_allowance_kg':noncad_deck,'electrical_allowance_carried_kg':2.1,
                'estimated_base_kg':mass,'remaining_to_10kg_kg':10-mass,'is_weighed':False},
        'scope':'Reconstructed extrusion/nut interface, nominal tire axial datum, rigid undeformed tires. Reservations are not electronic component fit approval. No local contact/thread/thermal/impact certification.'}
    (HERE/'assembly_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('slot_nut_updates','tool_and_service_access')},ensure_ascii=False))
    assert not collisions and not reference_hits and not harness
    assert all(not a['hits'] for a in access)
    assert all(abs(z)<1e-6 for z in contacts.values())
    assert mass<10
    doc.saveAs(str(HERE/(NAME+'.FCStd')))
    Part.export(parts,str(HERE/(NAME+'.step')))
    restored=Part.read(str(HERE/(NAME+'.step')))
    volume=sum(o.Shape.Volume for o in parts)
    assert restored.isValid() and len(restored.Solids)==sum(len(o.Shape.Solids) for o in parts)
    assert abs(restored.Volume-volume)<1
    report['STEP_roundtrip']={'valid':True,'solids':len(restored.Solids),'volume_difference_mm3':restored.Volume-volume}
    assert digest(source)==source_hash
    (HERE/'assembly_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__': main()
