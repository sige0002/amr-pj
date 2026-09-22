"""Independent reopening of D5 native/STEP/STL and battery service positions."""
from pathlib import Path
from itertools import combinations
import json
import hashlib
import FreeCAD as App
import Part
import Mesh
HERE=Path(__file__).resolve().parent
D3=HERE.parent/'aluminum-direct-deck'
NAME='AMR01_MakitaPower_D5'
V=App.Vector
doc=App.openDocument(str(HERE/(NAME+'.FCStd')))
r=json.loads((HERE/'validation.json').read_text())
physical=[o for o in doc.Objects if hasattr(o,'MaterialBasis') and o.MaterialBasis!='reference']
refs=[o for o in doc.Objects if hasattr(o,'MaterialBasis') and o.MaterialBasis=='reference']
assert all(o.Shape.isValid() for o in physical+refs)
assert not r['collisions'] and not r['reference_collisions'] and not r['reference_pair_collisions']
assert not any(t['hits'] for t in r['continuous_module_lift']+r['grid_fastener_envelopes'])
q=json.loads((D3/'quote-evidence/D3-observed.json').read_text());quoted={}
for ext,key in [('.step','step_sha256'),('.pdf','pdf_sha256')]:
    p=D3/(q['name']+ext);sha=hashlib.sha256(p.read_bytes()).hexdigest();assert sha==q[key];quoted[p.name]=sha
plate=Part.read(str(D3/'AMR_GridDeck_C45_D3.step'));plate.translate(V(0,0,99))
installed=doc.getObject('AluminumDeckD3').Shape
assert plate.cut(installed).Volume<.001 and installed.cut(plate).Volume<.001
step=Part.read(str(HERE/(NAME+'.step')))
native_volume=sum(o.Shape.Volume for o in physical);delta=step.Volume-native_volume
assert step.isValid() and abs(delta/native_volume)<1e-6
assert len(step.Solids)==sum(len(o.Shape.Solids) for o in physical)
with_power=Part.read(str(HERE/(NAME+'-with-power-envelopes.step')))
expected_power=sum(doc.getObject(n).Shape.Volume for n in ['BatteryBL1860B','BatteryAdapter03'])
assert abs((with_power.Volume-native_volume-expected_power)/(native_volume+expected_power))<1e-6
assert len(with_power.Solids)==len(step.Solids)+2
moving=[doc.getObject(n) for n in r['moving_parts']]
excluded=set(r['moving_parts']+r['released_before_service'])
fixed=[o for o in physical+refs if o.Name not in excluded]
sample_hits=[]
for travel in range(0,141,10):
    for o in moving:
        s=o.Shape.copy();s.translate(V(0,0,travel));b=s.BoundBox
        for f in fixed:
            if b.intersect(f.Shape.BoundBox):
                overlap=s.common(f.Shape).Volume
                if overlap>.001:sample_hits.append(dict(travel_mm=travel,moving=o.Name,fixed=f.Name,volume_mm3=overlap))
assert not sample_hits
meshes=[]
for entry in json.loads((HERE/'print_manifest.json').read_text()):
    m=Mesh.Mesh(str(HERE/entry['file']));b=m.BoundBox;size=[b.XLength,b.YLength,b.ZLength]
    assert m.isSolid() and max(size)<256
    assert all(abs(x-y)<.001 for x,y in zip(size,entry['size_mm']))
    meshes.append(dict(file=entry['file'],closed=True,size_mm=size))
assert r['unchanged_parts_BRep_equal']
out=dict(revision='D5',native_document=NAME,physical_parts=len(physical),
    native_solids=sum(len(o.Shape.Solids) for o in physical),STEP_solids=len(step.Solids),
    native_volume_mm3=native_volume,STEP_delta_mm3=delta,STEP_relative_tolerance=1e-6,
    with_power_STEP_solids=len(with_power.Solids),power_STEP_scope='two catalog envelopes added, not mating-interface CAD',
    quoted_files_SHA256=quoted,quoted_plate_BRep_matches=True,
    saved_service_samples_mm=list(range(0,141,10)),saved_service_sample_hits=sample_hits,
    continuous_conservative_lift_envelopes_passed=True,meshes=meshes,
    battery_part_selected='Makita BL1860B',charger_part_selected='Makita DC18RF',
    adapter_part_selected='Netkey diy-adapter03',actual_latched_module_measured=False,
    mass=r['mass'],electrical_operating_release=False,loaded_use_released=False)
(HERE/'saved_artifact_validation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False,indent=2))
