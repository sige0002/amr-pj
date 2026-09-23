"""Independent saved-CAD checks of D6.5 floor fixings and load paths.

Run in FreeCAD Python. Beam equations are short-term screening, not printed
material allowables, joint-preload qualification or proof of creep resistance.
"""
from pathlib import Path
from itertools import product
import hashlib,json,math
import FreeCAD as App
import Part

HERE=Path(__file__).resolve().parent
path=HERE/'AMR01_TwoStorey_D6.FCStd'
doc=App.openDocument(str(path));V=App.Vector
report=json.loads((HERE/'validation.json').read_text())
beam=doc.getObject('SeamBeamPLA').Shape
panels=[]
for ix,iy in product(range(2),repeat=2):
    name=f'FloorPLA_{ix}_{iy}';panel=doc.getObject(name).Shape
    expected=[((-1 if ix==0 else 1)*x,(-1 if iy==0 else 1)*y)
              for x,y in [(25,135),(185,135),(215,20),(15,25)]]
    fixings=[f for f in report['floor_fixings'] if f['panel']==name]
    assert len(fixings)==4 and set(tuple(f['xy_mm']) for f in fixings)==set(expected)
    assert sum(f['thread']=='M6' for f in fixings)==3
    checks=[]
    for f in fixings:
        x,y=f['xy_mm'];bolt=doc.getObject(f['bolt']).Shape;b=bolt.BoundBox
        assert abs((b.XMin+b.XMax)/2-x)<1e-6 and abs((b.YMin+b.YMax)/2-y)<1e-6
        assert panel.common(Part.makeCylinder(1.8,2.4,V(x,y,99))).Volume<1e-6
        # Move head/washer seat slightly into the panel to establish actual
        # bearing, independent of the nominal hole list. No extra CAD objects.
        if f['thread']=='M6':
            seat=Part.makeCylinder(9,.01,V(x,y,101.39)).cut(Part.makeCylinder(3.3,.01,V(x,y,101.39)))
            area=panel.common(seat).Volume/.01
            assert area>200,(name,f,area)
            rails=[o for o in doc.Objects if o.Name.startswith(('Cross300_','Rail300_','Rail400_'))]
            ring=Part.makeCylinder(8,.01,V(x,y,98.99)).cut(Part.makeCylinder(4.1,.01,V(x,y,98.99)))
            rail_area=sum(o.Shape.common(ring).Volume/.01 for o in rails)
            assert rail_area>60,(name,f,rail_area)
        else:
            assert abs(b.ZMax-106.4)<1e-6
            shifted=doc.getObject(f['top_washer']).Shape.copy();shifted.translate(V(0,0,-.01))
            area=panel.common(shifted).Volume/.01
            assert area>95,(name,f,area)
            # Prove that the old conical pocket is filled, not merely hidden.
            full_web=Part.makeCylinder(4,2.4,V(x,y,99)).cut(Part.makeCylinder(2.25,2.4,V(x,y,99)))
            assert full_web.cut(panel).Volume<1e-6,(name,'missing plain-hole web')
            key=f'{ix}_{iy}';lower=doc.getObject('FloorSeamWasher_'+key).Shape.copy();lower.translate(V(0,0,.01))
            assert lower.common(beam).Volume/.01>95
            nut=doc.getObject('FloorSeamNut_'+key).Shape.BoundBox
            assert nut.ZLength==3.2 or abs(nut.ZLength-3.2)<1e-6
            assert nut.ZMin-b.ZMin>=2*.7
            rail_area=None
        checks.append(dict(**f,actual_head_or_washer_bearing_projected_area_mm2=area,
                           actual_rail_support_probe_area_mm2=rail_area))
    shifted=beam.copy();shifted.translate(V(0,0,.01))
    contact=panel.common(shifted).Volume/.01
    assert contact>1000,(name,contact)
    panels.append(dict(panel=name,fixing_count=4,fixings=checks,
                       fixing_spread_XY_mm=[200,115],beam_bearing_area_mm2=contact))

anchors=[]
for sign in [-1,1]:
    points=[a for a in report['floor_beam_anchors'] if a['rail_surface_xyz_mm'][1]==sign*50]
    assert len(points)==2
    assert sorted(a['rail_surface_xyz_mm'][0] for a in points)==[-18,18]
    for a in points:
        i=a['bolt'].rsplit('_',1)[1]
        washer=doc.getObject('SeamBeamWasher_'+i).Shape.copy()
        washer.translate(V(0,sign*.01,0))
        contact=washer.common(beam).Volume/.01
        assert contact>200,(a,contact)
        a=dict(a,actual_washer_bearing_area_mm2=contact)
        anchors.append(a)

def hits(tool,parts):
    return [o.Name for o in parts if tool.BoundBox.intersect(o.Shape.BoundBox)
            and tool.common(o.Shape).Volume>.001]
physical=[o for o in doc.Objects if hasattr(o,'MaterialBasis') and o.MaterialBasis!='reference']
tool_checks=[]
for a in report['floor_beam_anchors']:
    x,y,z=a['rail_surface_xyz_mm'];sign=1 if y>0 else -1
    tool=Part.makeCylinder(2.9,35,V(x,sign*39.2,z),V(0,-sign,0))
    # The beam is fastened before the four panels and their M4 hardware.
    assembly=[o for o in physical if not o.Name.startswith(('FloorPLA_','FloorSeam')) and o.Name!=a['bolt']]
    found=hits(tool,assembly);assert not found,(a,found)
    tool_checks.append(dict(part=a['bolt'],step='before panels and M4 screws',hits=found))
for ix,iy in product(range(2),repeat=2):
    name=f'FloorSeamNut_{ix}_{iy}';x=(-1 if ix==0 else 1)*15;y=(-1 if iy==0 else 1)*25
    # Hollow socket OD11/ID8 from below; excludes the actual screw/nut being
    # worked on, and begins below the plain washer.
    tool=Part.makeCylinder(5.5,35,V(x,y,58)).cut(Part.makeCylinder(4,35,V(x,y,58)))
    found=hits(tool,[o for o in physical if o.Name not in [name,f'FloorSeamBolt_{ix}_{iy}']])
    assert not found,(name,found)
    tool_checks.append(dict(part=name,step='M4 socket access from underside',hits=found))
    driver=Part.makeCylinder(1.7,35,V(x,y,106.4))
    found=hits(driver,[o for o in physical if o.Name not in [f'FloorSeamBolt_{ix}_{iy}','ComputerBarrierPLA']])
    assert not found,(name,'M4 driver with PC and barrier removed',found)
    tool_checks.append(dict(part=f'FloorSeamBolt_{ix}_{iy}',step='M4 top driver with PC and barrier removed',hits=found))

pc=doc.getObject('Reserved_Computer').Shape.BoundBox
pc_supports=[]
for ix,iy in product(range(2),repeat=2):
    x=(-1 if ix==0 else 1)*50;y=(-1 if iy==0 else 1)*40
    panel=doc.getObject(f'FloorPLA_{ix}_{iy}').Shape
    expected=Part.makeBox(10,10,5.6,V(x-5,y-5,101.4))
    assert expected.cut(panel).Volume<1e-6
    head_top=doc.getObject(f'FloorSeamBolt_{ix}_{iy}').Shape.BoundBox.ZMax
    assert pc.ZMin-head_top>=3.59 and 107-head_top>=.59
    pc_supports.append(dict(xy_mm=[x,y],solid_size_mm=[10,10,5.6],solid_top_z_mm=107,
                           liner_t_mm=1,barrier_t_mm=2,barrier_top_z_mm=109,case_to_head_mm=pc.ZMin-head_top,hard_support_to_head_mm=107-head_top))

def distance(a,b):return a.distToShape(b)[0]
pc_belt=doc.getObject('ComputerRetentionBelt').Shape
battery_belt=doc.getObject('BatteryRetentionBelt').Shape
clearance=distance(beam,pc_belt)
assert clearance>=.49
rib_shapes=[]
for ix,iy in product(range(2),repeat=2):
    s=doc.getObject(f'FloorPLA_{ix}_{iy}').Shape
    rib_shapes.append(s.common(Part.makeBox(500,320,15,V(-250,-160,84))))
battery_clearance=min(distance(s,battery_belt) for s in rib_shapes)
assert battery_clearance>=2.29

def section_screen(shape,axis,span,force):
    # A1mm extrusion allows exact section properties from volume integrals;
    # subtract the longitudinal1/12 term from the bending inertia.
    assert len(shape.Solids)==1
    shape=shape.Solids[0]
    area=shape.Volume;c=shape.CenterOfMass;b=shape.BoundBox
    I=(shape.MatrixOfInertia.A22 if axis=='X' else shape.MatrixOfInertia.A11)-area/12
    zmax=max(c.z-b.ZMin,b.ZMax-c.z)
    stress=force*span/4*zmax/I
    return dict(span_mm=span,center_point_force_N=force,area_mm2=area,I_mm4=I,
                stress_MPa=stress,deflection_mm_by_E_MPa={str(E):force*span**3/(48*E*I) for E in [1000,2750]},
                model='simply supported beam; one centered point force; joint compliance and creep omitted')

# Only40mm of floor flange is credited with the rib, ignoring the remaining
# panel width. The seam beam uses its weakest belt-recess section everywhere.
rib_section=doc.getObject('FloorPLA_1_1').Shape.common(Part.makeBox(1,39.8,25,V(100,.2,80)))
beam_section=beam.common(Part.makeBox(100,1,40,V(-50,-.5,70)))
screens=dict(panel_rib=section_screen(rib_section,'X',168,50),
             seam_beam=section_screen(beam_section,'Y',100,50))
# Integrate the tapered end25mm in1mm strips; the rib remains attached to the
# end rail through its continuous flange. Unit-load work accounts for the
# reduced end stiffness, which a uniform-section equation would omit.
work=0.;peak_stress=0.;L=168.;F=50
for i in range(168):
    x=i+.5
    s=doc.getObject('FloorPLA_1_1').Shape.common(Part.makeBox(1,39.8,25,V(32+i,.2,80)))
    assert len(s.Solids)==1
    s=s.Solids[0]
    a=s.Volume;c=s.CenterOfMass;b=s.BoundBox;I=s.MatrixOfInertia.A22-a/12
    lever=min(x,L-x)/2
    work+=lever**2/I
    peak_stress=max(peak_stress,F*lever*max(c.z-b.ZMin,b.ZMax-c.z)/I)
screens['panel_rib'].update(stress_MPa=peak_stress,
    deflection_mm_by_E_MPa={str(E):F*work/E for E in [1000,2750]},
    model='simply supported variable-section rib;1mm strip integration includes end25mm taper;40mm floor flange credited')
for result in screens.values():
    assert result['deflection_mm_by_E_MPa']['1000']<2

out=dict(revision='D6.5',native_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
         panels=panels,total_panel_fixings=16,beam_anchors=anchors,
         beam_ends_supported=2,beam_anchors_per_end=2,
         assembly_tool_checks=tool_checks,computer_supports=pc_supports,
         M4_hole_diameter_mm=4.5,M4_minimum_floor_web_mm=2.4,M4_countersink_count=0,
         beam_to_PC_belt_clearance_mm=clearance,ribs_to_battery_belt_clearance_mm=battery_clearance,
         original_unbraced_central_edge_overhang_mm=49.8,new_edge_to_rib_mm=14.6,
         short_term_elastic_screens=screens,
         material_source='https://store.bblcdn.com/s1/default/58b85d0f3db94878854a28fdb8a0006e/Bambu_PLA_Basic_Technical_Data_Sheet.pdf',
         material_basis='Manufacturer bending modulus XY2750±160MPa.1000MPa is an assumed reduced-stiffness sensitivity, NOT a measured printed-direction modulus or long-term allowable.',
         load_basis='50N on one rib, separately50N on seam beam. About twice the entire2.4kg lower-floor equipment budget; does NOT cover arbitrary cam-belt pretension.',
         required_prototype_checks=['Printed dimensions, flat washer seating, nut engagement and driver/wrench access.',
             'With electronics absent, gradually apply50N through a broad pad to each ribbed region and seam beam; inspect residual set and cracked layers.',
             'Install representative equipment and measured belt tension; dwell at expected equipment temperature and inspect panel sag, washer indentation and bolt relaxation. Set allowable belt tension from test.',
             'PLA clamp faces: do not apply a normal metal-joint M6 tightening torque. Qualify retention/preload and inspect periodically.'],
         whole_floor_strength_factor_2_qualified=False,creep_qualified=False,
         scope='Electronics shelf only. Upper cargo15kg/SF2 target belongs to separate metal structure; not a rating for these printed parts.')
(HERE/'floor_support_review.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:out[k] for k in ['total_panel_fixings','beam_ends_supported','beam_anchors_per_end','beam_to_PC_belt_clearance_mm','ribs_to_battery_belt_clearance_mm','short_term_elastic_screens']},ensure_ascii=False))
