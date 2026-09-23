"""D6.6: rear controls on bolt-on printed cases; D6.5 structure is immutable.

Run in FreeCAD Python. Purchased switches are catalogue envelopes, not vendor
BReps. All new metal holes are in printable parts; no frame/deck machining.
"""
from pathlib import Path
from itertools import combinations
import hashlib, importlib.util, json, math, sys
import FreeCAD as App
import Part, MeshPart

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
SOURCE=BASE/'two-story'
NAME='AMR01_RearControls_D66'
V=App.Vector
sys.path.insert(0,str(BASE))
from hardware_geometry import slotnut_at
spec=importlib.util.spec_from_file_location('joint_geometry',BASE/'printed-deck-frame/build_p1.py')
j=importlib.util.module_from_spec(spec);spec.loader.exec_module(j)
spec=importlib.util.spec_from_file_location('d65_geometry',SOURCE/'build_d6.py')
d6=importlib.util.module_from_spec(spec);spec.loader.exec_module(d6)
box,fuse,pipe,hits,swept_bbox=d6.box,d6.fuse,d6.pipe,d6.hits,d6.swept_bbox
RHO={'PLA':1.24e-6,'steel':7.85e-6}

P=dict(revision='D6.6',date='2026-09-23',front_axis='+X',operator_side='rear -X',
    estop=dict(part='IDEC XA1E-BV302R',panel_center_mm=[-213,-119,206],
        axis=[0,0,1],head_diameter_mm=29,head_height_mm=20.6,
        rear_envelope_mm=[30.4,29.4,30.4],mount_hole_mm=16.2,
        key_width_mm=1.7,key_overall_height_mm=17.9,panel_thickness_mm=3,
        note='Manufacturer catalogue p6; conservative rear envelope includes terminal-cover space. Yellow printed lid, no added thick nameplate.'),
    arm=dict(part='amon 3212',panel_center_mm=[-213,-71,206],hole_mm=12.2,
        button_color='black',function='momentary manual re-arm only; never a motion command'),
    main_power=dict(part='amon 3214',panel_center_mm=[-203,120,237],hole_mm=12.2,
        function='manual all-load disconnect after source fuse, before independent UVLO; E-stop cuts motors only',
        catalog_limit='DC24V10A; source10A fuse is an initial coordination value, not a validated inrush rating'),
    source_hash=hashlib.sha256((SOURCE/'AMR01_TwoStorey_D6.FCStd').read_bytes()).hexdigest(),
    source_revision='D6.5',pico_owned=True,pico_variant_known=False,
    nominal_purchased_envelopes=True,production_print_release=False,
    new_frame_holes=0,new_cargo_plate_holes=0)

def cylinder(r,h,p,n=(0,0,1)):
    return Part.makeCylinder(r,h,V(*p),V(*n))

def main():
    old=App.openDocument(str(SOURCE/'AMR01_TwoStorey_D6.FCStd'))
    doc=App.newDocument(NAME)
    doc.Label='AMR D6.6 | REAR E-STOP + ARM | rear power | owned Pico'
    removed=['Reserved_EmergencyStop','BatteryVehicleHarness']
    for o in old.Objects:
        if hasattr(o,'MaterialBasis') and o.Name not in removed:doc.copyObject(o,False)
    new=[];printed=[];mounts=[];lid_fixings=[];exclusions=[]
    def add(name,shape,material,note,color=None):
        assert shape.isValid() and len(shape.Solids)>=1,name
        o=doc.addObject('PartDesign::Feature',name);o.Shape=shape
        for key,value in [('MaterialBasis',material),('ModelNote',note)]:
            o.addProperty('App::PropertyString',key,'Design');setattr(o,key,value)
        if color is not None and App.GuiUp:o.ViewObject.ShapeColor=color
        new.append(name)
        if material=='PLA':printed.append(name)
        return o

    # Cases sit on rear-facing / downward-facing slot fasteners. Two planes
    # of attachment resist the operating moment. No battery-floor support.
    def case(prefix,bounds,anchor_y,switch_holes,color):
        x0,y0,z0,l,w,h=bounds;top=z0+h
        outer=box(*bounds);inner=box(x0+2.5,y0+2.5,z0+2.5,l-5,w-5,h+1)
        s=outer.cut(inner)
        anchor_cutters=[];nut_pockets=[]
        for i,y in enumerate(anchor_y):
            leg=box(-234.5,y-11,64.5,4.5,22,z0+3-64.5)
            foot=box(-234.5,y-11,64.5,34.5,22,4.5)
            # Ribs stay at the back of the frame, outside the battery opening.
            rib_bottom=185 if prefix=='RearPower' else 103
            pts=[V(-230,y-2,rib_bottom),V(-230,y-2,z0+3),V(x0+l-3,y-2,z0+3)]
            rib=Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(V(0,4,0))
            s=s.fuse(leg).fuse(foot).fuse(rib)
            for face,point,normal in [('rear',(-230,y,84),(1,0,0)),('under',(-215,y,69),(0,0,1))]:
                p=V(*point);n=V(*normal)
                anchor_cutters.append(Part.makeCylinder(3.25,12,p-n*7,n))
                shoulder=p-n*5.5
                bolt=add(f'{prefix}FrameBolt_{i}_{face}',j.screw(tuple(shoulder),normal,6,12),'steel','M6x12, nominal thread omitted;4.5mm printed wall +1mm washer.')
                washer=Part.makeCylinder(9,1,p-n*5.5,n).cut(Part.makeCylinder(3.25,1,p-n*5.5,n))
                add(f'{prefix}FrameWasher_{i}_{face}',washer,'steel','M6 OD18 ID6.5 t1; separate purchase pack, not the existing t1.6 floor washers.')
                add(f'{prefix}FrameNut_{i}_{face}',slotnut_at(point,normal,(0,1,0)),'steel','HNTT6-6 from planned100-pack, not owned stock.')
                mounts.append(dict(case=prefix,face=face,surface_mm=point,bolt=bolt.Name,
                    nominal_thread_overlap_mm=5.3,tip_to_nominal_slot_bottom_mm=2.5,
                    tool_shape=Part.makeCylinder(4,30,shoulder-n*6,-n)))
        corners=[(x0+6,y0+6),(x0+l-6,y0+6),(x0+6,y0+w-6),(x0+l-6,y0+w-6)]
        lid=box(x0,y0,top,l,w,3)
        for i,(x,y) in enumerate(corners):
            boss=box(x-5,y-5,top-10,10,10,10)
            # Captive M4 hex nut is inserted from the open underside of boss.
            pocket=j.hexagon(x,y,top-10,7.3,4)
            nut_pockets.append(pocket)
            bore=cylinder(2.25,15,(x,y,top-11))
            s=s.fuse(boss.cut(pocket).cut(bore));lid=lid.cut(bore)
            bolt=add(f'{prefix}LidBolt_{i}',j.screw((x,y,top+4),(0,0,-1),4,16),'steel','M4x16 from planned floor screw pack. Plain hole; no countersink.')
            washer=cylinder(6,1,(x,y,top+3)).cut(cylinder(2.25,1,(x,y,top+3)))
            add(f'{prefix}LidWasher_{i}',washer,'steel','M4 OD12 t1 from planned20-pack; captive M4 nut underneath.')
            nut=j.hexagon(x,y,top-9.2,7,3.2).cut(cylinder(2.1,3.2,(x,y,top-9.2)))
            add(f'{prefix}LidNut_{i}',nut,'steel','M4 nominal hex nut from planned20-pack; no countersink.')
            lid_fixings.append(dict(case=prefix,bolt=bolt.Name,xy_mm=[x,y],thread_overlap_mm=3.2))
        s=s.cut(Part.makeCompound(anchor_cutters+nut_pockets)).removeSplitter()
        for x,y,r in switch_holes:lid=lid.cut(cylinder(r,6,(x,y,top-1)))
        if prefix=='RearStop':
            # Key reaches9.8mm from centre: total height17.9 = 8.1+9.8.
            lid=lid.cut(box(-213-.85,-119+7.9,top-1,1.7,1.9,6))
            # Signal bundle port on bottom, with rounded independent grommet allowance.
            s=s.cut(cylinder(4.5,6,(-195,-92,z0-1)))
        else:
            for x in [-192,-216]:s=s.cut(cylinder(4.5,6,(x,132,z0-1)))
        add(prefix+'CasePLA',s.removeSplitter(),'PLA','2.5mm walls/base; integral ribbed slot mounts on two frame faces. M4 captive nut lid. Prototype, print and operating-force qualification required.',color)
        add(prefix+'LidPLA',lid.removeSplitter(),'PLA','3mm panel; four ordinary M4 cap screws. Switch nuts and terminals enclosed. No structural cargo load.',color)
        return top+3

    case('RearStop',(-240,-147,147,53,96,56),[-100,-65],[(-213,-119,8.1),(-213,-71,6.1)],(.94,.76,.10))
    case('RearPower',(-226,95,193,46,50,41),[119,137],[(-203,120,6.1)],(.24,.31,.36))
    # Conservative published switch envelopes; real nut thread and terminal
    # details are deliberately not claimed as purchased CAD.
    ep=P['estop']['panel_center_mm'];x,y,z=ep
    estop=fuse([box(x-15.2,y-14.7,z-30.4,30.4,29.4,22.4),
        cylinder(10.5,5,(x,y,z-8)),cylinder(7.9,11,(x,y,z-3)),
        cylinder(14.5,12.6,(x,y,z+8))])
    add('EStop_XA1E_BV302R',estop,'reference','Selected2NC switch. Catalogue envelope:29mm head,20.6mm front,30.4mm conservative rear incl cover. Supplied locking ring represented.',(.87,.08,.07))
    # Amon packing drawings and installation specs: intentionally conservative
    # terminal/lead envelopes; small manufacturing details require receiving check.
    for name,p,body_d,depth,head_d,head_h in [
        ('ARM_3212',P['arm']['panel_center_mm'],16,25,16,15),
        ('MainPower_3214',P['main_power']['panel_center_mm'],22,25,22,16)]:
        x,y,z=p
        s=fuse([cylinder(body_d/2,depth-3,(x,y,z-depth)),cylinder(5.9,6,(x,y,z-3)),cylinder(head_d/2,head_h,(x,y,z+3))])
        add(name,s,'reference','Selected product with12mm mounting hole; conservative body/terminal envelope, not supplier CAD.',(.15,.17,.19))
    # Wiring clearances are separate references, not additional parts or masses.
    for name,x,y,z,l,w,h in [('EStopTerminalSpace',-228.2,-133.7,158,30.4,29.4,17.6),
            ('ARMLeadSpace',-223,-81,154,20,20,27),
            ('MainPowerTerminalSpace',-215,108,199,24,24,13)]:
        add(name,box(x,y,z,l,w,h),'reference','Reserved insulated terminals/wire bend area; assembled harness not released.')
    add('RearStopSignalRoute',pipe([[-195,-92,147],[-195,-92,119],[-185,-103,110.5],[125,-103,110.5],[125,-95,126],[135,-95,126]],2.5),'reference','E-stop4 conductors andARM2:6-wire protected route to front protection case. Bundle/ties/connector parts still need electrical harness release.')
    add('MainPowerInputRoute',pipe([[-199,127,172],[-199,132,172],[-192,132,172],[-192,132,193]],3),'reference','Battery vehicle connector to rear main switch; existing connector geometry is still a reserved envelope.')
    add('MainPowerOutputRoute',pipe([[-216,132,193],[-216,132,177],[-215,132,150],[-215,114,114],[220,114,114],[220,-75,126],[205,-75,126]],3),'reference','Rear main switch output follows original1F perimeter to UVLO/distribution; source fuse must be before this wire.')
    # Existing hardpoints/reservations are fixed in layout, not silently treated
    # as fully developed protection PCBs or a selected computer.
    doc.getObject('Reserved_SupervisorRS485').Label='OWNED PICO + RS485 / WATCHDOG | variant & PCB pending'
    doc.recompute()
    print('Geometry built; checking assembly and service paths',flush=True)
    physical=[o for o in doc.Objects if hasattr(o,'MaterialBasis') and o.MaterialBasis!='reference']
    refs=[o for o in doc.Objects if hasattr(o,'MaterialBasis') and o.MaterialBasis=='reference']
    collisions=[]
    for a,b in combinations(physical,2):
        for h in hits(a.Shape,[b]):collisions.append(dict(a=a.Name,**h))
    ref_hits={o.Name:hits(o.Shape,physical) for o in refs}
    ref_pairs=[]
    for a,b in combinations(refs,2):
        for h in hits(a.Shape,[b]):ref_pairs.append(dict(a=a.Name,**h))
    basev=json.loads((SOURCE/'validation.json').read_text())
    moving=basev['moving_parts'];released=basev['released_before_service']
    fixed=[o for o in physical+refs if o.Name not in moving+released]
    service=[]
    for name in moving:
        for a,b in zip(basev['parameters']['battery_service_waypoints_xyz_mm'],basev['parameters']['battery_service_waypoints_xyz_mm'][1:]):
            service.append(dict(part=name,from_mm=a,to_mm=b,hits=hits(swept_bbox(doc.getObject(name).Shape,a,b),fixed)))
    pc_service=[]
    for name in ['Reserved_Computer','ComputerTopPad']:
        fixed_pc=[o for o in physical+refs if o.Name not in ['Reserved_Computer','ComputerTopPad','ComputerRetentionBelt']]
        for a,b in [([0,0,0],[0,0,8]),([0,0,8],[0,-230,8])]:
            pc_service.append(dict(part=name,from_mm=a,to_mm=b,hits=hits(swept_bbox(doc.getObject(name).Shape,a,b),fixed_pc)))
    approach=[]
    for title,p,r in [('EStop',P['estop']['panel_center_mm'],35),('ARM',P['arm']['panel_center_mm'],16),('MainPower',P['main_power']['panel_center_mm'],18)]:
        s=cylinder(r,200,(p[0],p[1],p[2]+21))
        approach.append(dict(control=title,diameter_mm=2*r,hits=hits(s,physical+refs)))
    tool_checks=[]
    for m in mounts:
        s=m.pop('tool_shape');tool_checks.append(dict(bolt=m['bolt'],hits=hits(s,[o for o in physical+refs if o.Name!=m['bolt']])))
    new_objects=[doc.getObject(n) for n in new]
    tire=[dict(side=k,hits=hits(cylinder(50.35,123,(90,k*153,50.35),(0,k,0)),new_objects)) for k in [-1,1]]
    caster=hits(cylinder(43,65,(-150,0,0)),new_objects)
    invariant=[o.Name for o in old.Objects if hasattr(o,'MaterialBasis') and o.Name not in removed]
    unchanged=all(doc.getObject(n).Shape.cut(old.getObject(n).Shape).Volume<1e-5 and old.getObject(n).Shape.cut(doc.getObject(n).Shape).Volume<1e-5 for n in invariant)
    additions=[]
    for n in new:
        o=doc.getObject(n)
        if o.MaterialBasis in RHO:additions.append(dict(name=n,mass_kg=o.Shape.Volume*RHO[o.MaterialBasis],center_mm=d6.center(o.Shape)))
    added_mass=sum(e['mass_kg'] for e in additions)
    total=basev['mass']['estimated_base_kg']+added_mass
    ranges=[[(basev['mass']['estimated_base_kg']*edge+sum(e['mass_kg']*e['center_mm'][i] for e in additions))/total for edge in interval] for i,interval in enumerate(basev['cg_difference']['conditional_base_cg_xyz_ranges_mm'])]
    report=dict(parameters=P,physical_parts=len(physical),physical_pairs=len(physical)*(len(physical)-1)//2,
        collisions=collisions,reference_collisions={k:v for k,v in ref_hits.items() if v},reference_pairs=ref_pairs,
        battery_service=service,computer_service=pc_service,operator_approach=approach,frame_fastener_tools=tool_checks,
        tire_service=tire,caster_sweep=caster,retained_base_objects=len(invariant),retained_shapes_BRep_equal=unchanged,
        removed_references=removed,new_objects=new,frame_mounts=mounts,lid_fixings=lid_fixings,
        mass=dict(source_D65_kg=basev['mass']['estimated_base_kg'],new_prints_and_fasteners_kg=added_mass,
            estimated_base_kg=total,new_PLA_kg=sum(doc.getObject(n).Shape.Volume*RHO['PLA'] for n in printed),
            ledger=additions,actually_weighed=False,
            note='Existing0.4kg electrical protection allowance retained, including switches;0.4kg harness and0.05kg Pico allowance retained. No mass saving for owned parts.'),
        conditional_cg_xyz_ranges_mm=ranges,
        explicit_limits=['PC product, Pico variant/headers, protection PCB and wiring terminals remain unselected/unreleased.',
            'Case strength, printed hole tolerances, switch retention and contact/routing temperature require prototype checks.',
            'D6.5 floor FEM remains a floor-only historical analysis; no new case FEM or electrical protection qualification claimed.',
            'Existing battery adapter latch and connector are catalogue reservations; receiving dimensions still required.'])
    (HERE/'parameters.json').write_text(json.dumps(P,ensure_ascii=False,indent=2)+'\n')
    (HERE/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    doc.saveAs(str(HERE/(NAME+'.FCStd')))
    print(json.dumps({k:report[k] for k in ['collisions','reference_collisions','reference_pairs','operator_approach','frame_fastener_tools','conditional_cg_xyz_ranges_mm']},ensure_ascii=False),flush=True)
    assert not collisions and not report['reference_collisions'] and not ref_pairs
    assert not any(c['hits'] for c in service+pc_service+approach+tool_checks+tire)
    assert not caster and unchanged
    assert total<10.5
    Part.export(physical,str(HERE/(NAME+'-structure.step')))
    Part.export(physical+[o for o in refs if o.Name in ['BatteryBL1860B','BatteryAdapter03','Reserved_Computer','EStop_XA1E_BV302R','ARM_3212','MainPower_3214']],str(HERE/(NAME+'.step')))
    for f in HERE.glob('*.step'):f.write_text('\n'.join(x.rstrip() for x in f.read_text().splitlines())+'\n')
    manifest=[]
    for name in printed:
        s=doc.getObject(name).Shape.copy();bb=s.BoundBox;s.translate(V(-bb.XMin,-bb.YMin,-bb.ZMin))
        assert max(bb.XLength,bb.YLength,bb.ZLength)<256
        MeshPart.meshFromShape(Shape=s,LinearDeflection=.06,AngularDeflection=.25,Relative=False).write(str(HERE/(name+'.stl')))
        manifest.append(dict(file=name+'.stl',size_mm=[bb.XLength,bb.YLength,bb.ZLength],solid_mass_g=s.Volume*1.24e-3,
            prototype_only=True,sliced=False,orientation='Lids flat; case orientation/supports to choose in slicer. Preserve captive nut pockets and slot mounting faces. Unfilled nonconductive PLA.'))
    (HERE/'print_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print('D6.6 build passed',total,flush=True)

if __name__=='__main__':main()
