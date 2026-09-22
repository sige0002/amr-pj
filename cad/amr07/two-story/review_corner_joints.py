"""D6.4: unchanged floor corners and retained joints; not a stiffness rating."""
from pathlib import Path
from itertools import product
import hashlib,json,subprocess,tempfile,math
import FreeCAD as App
import Part
HERE=Path(__file__).resolve().parent
BASELINE='ef44e1c';V=App.Vector
path=HERE/'AMR01_TwoStorey_D6.FCStd';doc=App.openDocument(str(path))
tmp=tempfile.TemporaryDirectory(prefix='amr-d62-corners-')
oldpath=Path(tmp.name)/'D62.FCStd'
oldpath.write_bytes(subprocess.check_output(['git','-C',str(HERE),'show',BASELINE+':cad/amr07/two-story/AMR01_TwoStorey_D6.FCStd']))
old=App.openDocument(str(oldpath))
physical=[o for o in doc.Objects if hasattr(o,'MaterialBasis') and o.MaterialBasis!='reference']
rails=[o for o in physical if o.Name.startswith(('Rail400_','Cross300_'))]
prefixes=('Gusset_','GussetBolt_','Washer_Gusset','SlotNut_Gusset_')
deleted=[o for o in old.Objects if o.Name.startswith(prefixes)]
assert len(deleted)==28 and not any(o.Name.startswith(prefixes) for o in physical)
corners=[];old_defects=[]
for sx,sy in product([-1,1],repeat=2):
    tag=('N1' if sx<0 else '1')+('N1' if sy<0 else '1')
    plate=old.getObject('Gusset_'+tag).Shape
    for i in range(2):
        washer=old.getObject('Washer_Gusset'+tag+str(i)).Shape.copy();washer.translate(V(0,0,-.01))
        area=washer.common(plate).Volume/.01;full_area=math.pi*(6.5**2-3.3**2)
        assert abs(area/full_area-.5)<1e-6
        old_defects.append(dict(gusset='Gusset_'+tag,hole=i,washer_bearing_area_mm2=area,
            full_washer_annulus_mm2=full_area,bearing_fraction=area/full_area,
            defect='Hole center lies on triangular diagonal edge; half of washer unsupported.'))
    corner=Part.makeBox(61,61,2.4,V(169 if sx>0 else -230,89 if sy>0 else -150,99))
    corner=corner.cut(Part.makeCylinder(3.3,2.4,V(sx*185,sy*135,99)))
    panel=doc.getObject(f'FloorPLA_{int(sx>0)}_{int(sy>0)}').Shape
    assert corner.cut(panel).Volume<1e-6 and len(panel.Solids)==1
    bracket_tag=('N' if sx<0 else 'P')+('N' if sy<0 else '')+'120'
    corners.append(dict(panel=f'FloorPLA_{int(sx>0)}_{int(sy>0)}',outer_floor_corner_continuous=True,
        frame_bracket='Bracket_'+bracket_tag,floor_corner_fixing_xy_mm=[sx*185,sy*135],
        plastic_in_structural_clamp=False,auxiliary_flat_gusset_removed=True))
joint_results=[];brackets=[o for o in physical if o.Name.startswith('Bracket_')]
assert len(brackets)==8
for bracket in brackets:
    name=bracket.Name;tag=name[len('Bracket_'):];original=old.getObject(name).Shape
    assert bracket.Shape.cut(original).Volume<1e-6 and original.cut(bracket.Shape).Volume<1e-6
    sx=1 if bracket.Shape.BoundBox.XMin>0 else -1
    sy=1 if bracket.Shape.BoundBox.YMin>0 else -1
    contacts=[];bolts=[]
    for letter,n in [('A',V(sx,0,0)),('B',V(0,sy,0))]:
        probe=bracket.Shape.copy();probe.translate(n*.01)
        hit=[dict(rail=o.Name,metal_contact_area_mm2=probe.common(o.Shape).Volume/.01)
             for o in rails if probe.BoundBox.intersect(o.Shape.BoundBox)]
        hit=[h for h in hit if h['metal_contact_area_mm2']>.001]
        assert len(hit)==1 and hit[0]['metal_contact_area_mm2']>100,(name,letter,hit)
        contacts.extend(hit)
        key='Joint'+letter+'_'+tag;bolt=doc.getObject(key).Shape;nut=doc.getObject('SlotNut_'+key).Shape
        axis=0 if letter=='A' else 1
        def limits(s):
            b=s.BoundBox
            return sorted([getattr(b,'XYZ'[axis]+'Min')*n[axis],getattr(b,'XYZ'[axis]+'Max')*n[axis]])
        lo,hi=limits(bolt);a,b=limits(nut);seat=hi-12
        engagement=min(hi,b)-max(seat,a)
        assert engagement>=6,(key,engagement)
        probe=bolt.copy();probe.translate(n*.01);head_area=probe.common(bracket.Shape).Volume/.01
        assert head_area>35,(key,head_area)
        # Short straight approach before floor/equipment; no full handle sweep.
        coords=list(bolt.BoundBox.Center);coords[axis]=lo*n[axis]
        driver=Part.makeCylinder(2.9,25,V(*coords),-n)
        metals=[o for o in physical if o.MaterialBasis in ['aluminum','steel'] and o.Name!=key]
        hits=[o.Name for o in metals if driver.BoundBox.intersect(o.Shape.BoundBox) and driver.common(o.Shape).Volume>.001]
        assert not hits,(key,hits)
        bolts.append(dict(bolt=key,nominal_thread_overlap_mm=engagement,
            head_to_bracket_bearing_area_mm2=head_area,straight_tool_approach_mm=25,hits=hits))
    assert len({c['rail'] for c in contacts})==2
    joint_results.append(dict(bracket=name,unchanged=True,metal_contacts=contacts,bolts=bolts))
v=json.loads((HERE/'validation.json').read_text())
before=json.loads(subprocess.check_output(['git','-C',str(HERE),'show',BASELINE+':cad/amr07/two-story/validation.json']))
rho={'steel':7.85e-6,'aluminum':2.7e-6}
removed_mass=sum(o.Shape.Volume*rho[o.MaterialBasis] for o in deleted)
before63=json.loads(subprocess.check_output(['git','-C',str(HERE),'show','b38b90b:cad/amr07/two-story/validation.json']))
delta=before63['mass']['estimated_base_kg']-before['mass']['estimated_base_kg']
assert abs(delta-(.044294784-removed_mass))<1e-8
out=dict(revision='D6.4',baseline_D62_commit=subprocess.check_output(['git','-C',str(HERE),'rev-parse',BASELINE],text=True).strip(),
    native_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),corners=corners,
    retained_lower_frame_joints=joint_results,removed_parts=28,additional_parts=0,
    removed_metal_mass_kg=removed_mass,added_PLA_mass_kg=.044294784,mass_change_from_D62_kg=delta,
    mass_comparison_scope='D6.2 to D6.3 corner change only; D6.4 adds separate seam hardware and PC supports.',
    D64_seam_and_PC_change_kg=v['mass']['estimated_base_kg']-before63['mass']['estimated_base_kg'],
    baseline_gusset_defects=old_defects,
    selected='Remove four auxiliary flat plates and eight bolt/washer/nut sets. Keep eight existing HBLFSN6 frame joints. Extend and separately fasten floor corners.',
    options=[dict(option='metal plate above PLA',assessment='Not selected: shared clamp includes PLA creep in frame preload; compression stops and corrected plate holes required.'),
             dict(option='move existing metal plates below frame',assessment='Rejected after bearing review: eight holes centered on diagonal edge give half-washer support. Relocation alone does not fix this.'),
             dict(option='remove flat plates and fasten floor corners',assessment='Selected for prototype. Eight independent metal HBLFSN6 joints retain frame. Removes28 pieces and plate fabrication; all-axis stiffness remains unqualified.')],
    catalog_reference=dict(url='https://jp.misumi-ec.com/vona2/detail/110300442340/?HissuCode=HBLFSN6',checked_date='2026-09-22',
        allowable_N_per_bracket=1176,bolts='2xM6x12',nuts='2xHNTT6-6',
        scope='Two-upright/one-crossmember test with two supporting brackets and all holes bolted. Not an allowable moment or all-axis chassis rating.'),
    assembly='Assemble eight metal joints with both bolts tightened, then beam, floors and equipment. Floor screws remain independent.',
    qualification_scope='Geometric contact, nominal thread overlap,25mm straight tool approach, unchanged metal joints, continuous corners. PLA carries equipment only; no frame bracing credit.',
    whole_frame_strength_qualified=False,static_payload_15kg_SF2_achieved=False,
    remaining='Check joint seating/preload and chassis racking/twist for planned load cases before loaded use. Add properly designed metal reinforcement if measured stiffness requires it.')
(HERE/'corner_joint_review.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(corners=4,retained_metal_joints=8,retained_frame_bolts=16,removed_parts=28,
    mass_change_g=delta*1000,baseline_washer_bearing_fraction=.5),ensure_ascii=False))
