"""Open saved native/STEP files and check the service state independently."""
from pathlib import Path
import json
import hashlib
import FreeCAD as App
import Part

HERE=Path(__file__).resolve().parent
D3=HERE.parent/'aluminum-direct-deck'
NAME='AMR01_BatteryDrawer_D4'
V=App.Vector
doc=App.openDocument(str(HERE/(NAME+'.FCStd')))
r=json.loads((HERE/'validation.json').read_text())
physical=[o for o in doc.Objects if hasattr(o,'MaterialBasis') and o.MaterialBasis!='reference']
refs=[o for o in doc.Objects if hasattr(o,'MaterialBasis') and o.MaterialBasis=='reference']
assert all(o.Shape.isValid() for o in physical+refs)
assert len(physical)==r['physical_parts']
assert not r['collisions'] and not r['reference_collisions'] and not r['battery_reference_pair_collisions']
q=json.loads((D3/'quote-evidence/D3-observed.json').read_text())
quoted={}
for ext,key in [('.step','step_sha256'),('.pdf','pdf_sha256')]:
    p=D3/(q['name']+ext);sha=hashlib.sha256(p.read_bytes()).hexdigest()
    assert sha==q[key];quoted[p.name]=sha
plate=Part.read(str(D3/'AMR_GridDeck_C45_D3.step'));plate.translate(V(0,0,99))
installed=doc.getObject('AluminumDeckD3').Shape
assert abs(plate.Volume-installed.Volume)<.001
assert plate.cut(installed).Volume<.001 and installed.cut(plate).Volume<.001
step=Part.read(str(HERE/(NAME+'.step')))
native_volume=sum(o.Shape.Volume for o in physical)
delta=step.Volume-native_volume
assert step.isValid() and abs(delta/native_volume)<1e-6
assert len(step.Solids)==sum(len(o.Shape.Solids) for o in physical)
# This sampling cross-check complements, rather than substitutes for, the
# continuous boundary-extrusion envelope in build_d4.py.
moving=[doc.getObject(n) for n in r['moving_parts']]
excluded=set(r['moving_parts']+r['released_before_service'])
fixed=[o for o in physical+refs if o.Name not in excluded]
sample_hits=[]
for distance in range(0,221,10):
    for o in moving:
        s=o.Shape.copy();s.translate(V(0,distance,0));bb=s.BoundBox
        for f in fixed:
            if bb.intersect(f.Shape.BoundBox):
                vol=s.common(f.Shape).Volume
                if vol>.001:sample_hits.append(dict(travel=distance,moving=o.Name,fixed=f.Name,overlap_mm3=vol))
assert not sample_hits
new_zmax=max(doc.getObject(n).Shape.BoundBox.ZMax for n in r['added_parts'])
assert new_zmax<=69.000001
assert r['unchanged_parts_BRep_equal'] and r['deck_BRep_unchanged']
assert doc.getObject('BatteryCandidate').Shape.BoundBox.YMin==-52
# Check actual stored STLs, not just requested mesh settings.
import Mesh
meshes=[]
for entry in json.loads((HERE/'print_manifest.json').read_text()):
    m=Mesh.Mesh(str(HERE/entry['file']));b=m.BoundBox
    size=[b.XLength,b.YLength,b.ZLength]
    assert m.isSolid() and max(size[:2])<256 and size[2]<256
    assert all(abs(a-b)<.001 for a,b in zip(size,entry['size_mm']))
    meshes.append(dict(file=entry['file'],closed=m.isSolid(),size_mm=size))
out=dict(native_document=NAME,all_shapes_valid=True,physical_parts=len(physical),
    native_physical_solids=sum(len(o.Shape.Solids) for o in physical),step_solids=len(step.Solids),
    native_volume_mm3=native_volume,step_volume_mm3=step.Volume,step_delta_mm3=delta,
    step_relative_tolerance=1e-6,step_scope='physical parts; catalog battery, liners, straps and wire references remain in FCStd only',
    quoted_plate_BRep_matches_saved_assembly=True,quoted_files_SHA256=quoted,
    saved_service_samples_mm=list(range(0,221,10)),saved_service_sample_hits=sample_hits,
    continuous_service_check_passed=not any(x['hits'] for x in r['continuous_drawer_service']),
    unchanged_original_parts_BRep_equal=r['unchanged_parts_BRep_equal'],
    inherited36grid_examples_new_parts_max_Z_mm=new_zmax,lowest_inherited_grid_tip_Z_mm=92.8,
    meshes=meshes,mass=r['mass'],battery_selected=False,load_test_completed=False)
(HERE/'saved_artifact_validation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False,indent=2),flush=True)
