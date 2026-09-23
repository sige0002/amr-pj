"""Reopen delivery files; verify exports, assembly inheritance and service access."""
from pathlib import Path
from types import SimpleNamespace
import hashlib, importlib.util, json, math
import FreeCAD as App
import Part, Mesh

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
spec = importlib.util.spec_from_file_location('hatch', HERE/'build_hatch.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
doc = App.openDocument(str(HERE/'AMR01_HingedDeck_D67.FCStd'))
source = App.openDocument(str(BASE/'control-layout/AMR01_RearControls_D66.FCStd'))
v = json.loads((HERE/'validation.json').read_text())
cv = json.loads((BASE/'control-layout/validation.json').read_text())
dv = json.loads((BASE/'two-story/validation.json').read_text())
all_objects = [o for o in doc.Objects if hasattr(o, 'MaterialBasis')]
physical = [o for o in all_objects if o.MaterialBasis != 'reference']
assert len(physical) == v['physical_parts'] == 383
assert all(o.Shape.isValid() and all(s.isClosed() for s in o.Shape.Solids) for o in all_objects)
assert digest(BASE/'control-layout/AMR01_RearControls_D66.FCStd') == v['source_sha256']
retained = [o for o in source.Objects if hasattr(o, 'MaterialBasis') and o.Name not in v['removed_objects']]
assert all(h.equivalent_brep(o.Shape, doc.getObject(o.Name).Shape) for o in retained)
assert not v['closed_collisions'] and not v['reference_collisions']
assert not v['continuous_opening_bbox_hits'] and not v['internal_hinge_sample_hits']

quote_dir = BASE/'aluminum-direct-deck'
q = json.loads((quote_dir/'quote-evidence/D3-observed.json').read_text())
quoted = {}
for ext, key in [('.step','step_sha256'),('.pdf','pdf_sha256')]:
    p = quote_dir/(q['name']+ext)
    assert digest(p) == q[key]
    quoted[p.name] = digest(p)
quoted_plate = Part.read(str(quote_dir/'AMR_GridDeck_C45_D3.step'))
quoted_plate.translate(App.Vector(0,0,229))
plate = doc.getObject('AluminumDeckD3').Shape
assert plate.cut(quoted_plate).Volume < .001 and quoted_plate.cut(plate).Volume < .001

print('Reopened native CAD, inheritance and quoted plate verified', flush=True)
exports = []
for filename, extra in [('AMR01_HingedDeck_D67-structure.step', []),
        ('AMR01_HingedDeck_D67.step', ['BatteryBL1860B','BatteryAdapter03','Reserved_Computer',
                                    'EStop_XA1E_BV302R','ARM_3212','MainPower_3214'])]:
    expected = physical + [doc.getObject(n) for n in extra]
    s = Part.read(str(HERE/filename))
    volume = sum(o.Shape.Volume for o in expected)
    assert s.isValid() and abs(s.Volume-volume)/volume < 1e-6
    assert len(s.Solids) == sum(len(o.Shape.Solids) for o in expected)
    exports.append(dict(file=filename, sha256=digest(HERE/filename), solids=len(s.Solids),
                        volume_delta_mm3=s.Volume-volume, valid=True))

meshes = []
for folder, manifest in [(BASE/'two-story','print_manifest.json'),
                         (quote_dir,'print_manifest.json'),
                         (BASE/'control-layout','print_manifest.json'),
                         (HERE,'print_manifest.json')]:
    entries = json.loads((folder/manifest).read_text())
    if folder == quote_dir:
        entries = [e for e in entries if e['file'].startswith('PrintedStop')]
    for e in entries:
        p = folder/e['file']; m = Mesh.Mesh(str(p)); b = m.BoundBox
        size = [b.XLength,b.YLength,b.ZLength]
        assert m.isSolid() and max(size) < 256, str(p)
        if 'size_mm' in e:
            assert all(abs(a-b)<.001 for a,b in zip(size,e['size_mm']))
        meshes.append(dict(file=str(p.relative_to(BASE)),sha256=digest(p),closed=True,size_mm=size))
assert len(meshes) == 18
print('STEP and 18 print meshes verified', flush=True)

stops = []
for i in range(2):
    fixed = doc.getObject(f'HatchFixedAdapter_{i}').Shape
    a = h.rotate(doc.getObject(f'HatchMovingAdapter_{i}').Shape,90)
    b = h.rotate(doc.getObject(f'HatchMovingAdapter_{i}').Shape,91)
    contact = a.common(fixed).Volume
    clearance = a.distToShape(fixed)[0]
    blocked = b.common(fixed).Volume
    assert contact < .001 and clearance < 1e-5 and blocked > .1
    stops.append(dict(index=i,angle90_overlap_mm3=contact,angle90_distance_mm=clearance,
                      angle91_interference_mm3=blocked))

# Re-evaluate inherited withdrawal paths and control access with the final lid.
services = []; approach = []
for angle in [0,90]:
    h._shape_cache.clear()
    excluded = v['released_before_open'] if angle else []
    current = [SimpleNamespace(Name=o.Name,Shape=h.rotate(o.Shape,angle)
               if o.Name in v['moving_parts'] else o.Shape) for o in all_objects if o.Name not in excluded]
    for title, moving, release, stages in [
      ('battery',dv['moving_parts'],dv['released_before_service'],
       [([0,0,0],[0,0,8]),([0,0,8],[-220,0,8])]),
      ('computer',['Reserved_Computer','ComputerTopPad'],['ComputerRetentionBelt'],
       [([0,0,0],[0,0,8]),([0,0,8],[0,-230,8])])]:
        fixed = [o for o in current if o.Name not in moving+release]
        for name in moving:
            for start,end in stages:
                found = h.hits(h.d6.swept_bbox(doc.getObject(name).Shape,start,end),fixed)
                assert not found, (title, angle, name, found)
                services.append(dict(module=title,lid_angle_deg=angle,part=name,
                                     from_mm=start,to_mm=end,hits=found))
    for title,key,radius in [('EStop','estop',35),('ARM','arm',16),('MainPower','main_power',18)]:
        p = cv['parameters'][key]['panel_center_mm']
        found = h.hits(h.cyl(radius,200,(p[0],p[1],p[2]+21)),current)
        assert not found, (title,angle,found)
        approach.append(dict(control=title,lid_angle_deg=angle,diameter_mm=2*radius,hits=found))

# A short L-key fits under the positive-stop return (bottom Z276).
h._shape_cache.clear(); tool_access = []
for i,cx in enumerate([-126,126]):
    for side,y in [('Moving',156.5),('Fixed',188.5)]:
        for k,x in enumerate([cx-18,cx+18]):
            name = f'HatchHinge{side}Fix_{i}_{k}Bolt'
            tool = h.cyl(2,18,(x,y,249)).fuse(h.cyl(2,y-145,(x,y,265),(0,-1,0)))
            found = h.hits(tool,[o for o in all_objects if o.Name != name])
            assert not found, (name,found)
            tool_access.append(dict(bolt=name,tool='diameter4 envelope, short L-key',hits=found))

def mass(o): return o.CatalogMassKg if hasattr(o,'CatalogMassKg') else o.Shape.Volume*h.RHO.get(o.MaterialBasis,0)
t = h.hinge_torque_summary(doc,v['moving_parts'],mass)
assert all(abs(t[k]-v['torque'][k])<1e-10 for k in t if isinstance(t[k],float))
samples=[]
centers={name:sum((s.CenterOfMass*s.Volume for s in doc.getObject(name).Shape.Solids),App.Vector())/doc.getObject(name).Shape.Volume
         for name in v['moving_parts']}
for n in range(901):
    a = math.radians(n/10)
    samples.append(abs(sum(mass(doc.getObject(name))*9.80665*((h.AXIS.y-centers[name].y)*math.cos(a)+
                   (h.AXIS.z-centers[name].z)*math.sin(a))/1000 for name in v['moving_parts'])))
assert abs(max(samples)-t['maximum_gravity_moment_Nm'])<1e-6
assert t['minimum_initial_hold_ratio'] >= 1.2

out = dict(revision='D6.7',native_sha256=digest(HERE/'AMR01_HingedDeck_D67.FCStd'),
    source_native_sha256=v['source_sha256'],physical_parts=len(physical),retained_objects=len(retained),
    retained_BRep_equal_numeric_tolerance=1e-10,quoted_plate_BRep_matches=True,quoted_files_SHA256=quoted,
    exports=exports,meshes=meshes,positive_stop_checks=stops,saved_service_checks=services,
    control_access=approach,hinge_short_L_key_access=tool_access,empty_lid_torque=t,
    continuous_motion_report_sha256=digest(HERE/'validation.json'),
    loaded_use_released=False,printed_hinge_adapters_qualified=False,electrical_operating_release=False)
(HERE/'saved_artifact_validation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('D6.7 saved artifacts PASS: 383 parts, 18 STL, 2 STEP, 90-degree stops, service and tool access.',flush=True)
