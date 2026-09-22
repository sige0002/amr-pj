"""Reopen delivered native/STEP/STL, match quoted plate, sample service paths."""
from pathlib import Path
import hashlib,json
import FreeCAD as App
import Part,Mesh
HERE=Path(__file__).resolve().parent
D3=HERE.parent/'aluminum-direct-deck'
NAME='AMR01_TwoStorey_D6'
V=App.Vector
doc=App.openDocument(str(HERE/(NAME+'.FCStd')))
r=json.loads((HERE/'validation.json').read_text())
physical=[o for o in doc.Objects if hasattr(o,'MaterialBasis') and o.MaterialBasis!='reference']
refs=[o for o in doc.Objects if hasattr(o,'MaterialBasis') and o.MaterialBasis=='reference']
assert all(o.Shape.isValid() for o in physical+refs)
assert not r['collisions'] and not r['reference_collisions'] and not r['reference_pair_collisions']
for key in ['continuous_battery_service','continuous_computer_service','grid_fastener_envelopes','joint_assembly_tool_access','tire_outward_service']:
    assert not any(a['hits'] for a in r[key]),key
assert not r['computer_ventilation_keepout_hits'] and not r['computer_connector_keepout_hits']
q=json.loads((D3/'quote-evidence/D3-observed.json').read_text());quoted={}
for ext,key in [('.step','step_sha256'),('.pdf','pdf_sha256')]:
    p=D3/(q['name']+ext);sha=hashlib.sha256(p.read_bytes()).hexdigest();assert sha==q[key];quoted[p.name]=sha
plate=Part.read(str(D3/'AMR_GridDeck_C45_D3.step'));plate.translate(V(0,0,229))
installed=doc.getObject('AluminumDeckD3').Shape
assert plate.cut(installed).Volume<.001 and installed.cut(plate).Volume<.001
step=Part.read(str(HERE/(NAME+'.step')));native_volume=sum(o.Shape.Volume for o in physical)
assert step.isValid() and abs((step.Volume-native_volume)/native_volume)<1e-6
assert len(step.Solids)==sum(len(o.Shape.Solids) for o in physical)
with_equipment=Part.read(str(HERE/(NAME+'-with-equipment-envelopes.step')))
envelope_names=['BatteryBL1860B','BatteryAdapter03','Reserved_Computer']
expected=sum(doc.getObject(n).Shape.Volume for n in envelope_names)
assert abs((with_equipment.Volume-native_volume-expected)/(native_volume+expected))<1e-6
assert len(with_equipment.Solids)==len(step.Solids)+3
service_results=[]
for title,moving,released,samples in [
    ('battery',r['moving_parts'],r['released_before_service'],[[0,0,z] for z in [0,2,4,6,8]]+[[-x,0,8] for x in range(0,221,20)]),
    ('computer',['Reserved_Computer','ComputerTopPad'],['ComputerRetentionBelt'],[[0,0,z] for z in [0,2,4,6,8]]+[[0,-y,8] for y in list(range(0,221,20))+[230]])]:
    fixed=[o for o in physical+refs if o.Name not in moving+released];found=[]
    for delta in samples:
        for name in moving:
            s=doc.getObject(name).Shape.copy();s.translate(V(*delta));b=s.BoundBox
            for f in fixed:
                if b.intersect(f.Shape.BoundBox):
                    overlap=s.common(f.Shape).Volume
                    if overlap>.001:found.append(dict(delta_mm=delta,moving=name,fixed=f.Name,overlap_mm3=overlap))
    assert not found,(title,found)
    service_results.append(dict(module=title,samples_mm=samples,hits=found))
meshes=[]
for entry in json.loads((HERE/'print_manifest.json').read_text()):
    m=Mesh.Mesh(str(HERE/entry['file']));b=m.BoundBox;size=[b.XLength,b.YLength,b.ZLength]
    assert m.isSolid() and max(size)<256
    assert all(abs(x-y)<.001 for x,y in zip(size,entry['size_mm']))
    meshes.append(dict(file=entry['file'],closed=True,size_mm=size))
assert r['unchanged_parts_BRep_equal'] and r['quoted_plate_unchanged']
assert doc.getObject('Reserved_Computer').Shape.BoundBox.ZMin==104
assert doc.getObject('BatteryBL1860B').Shape.BoundBox.ZMin==104
assert len([o for o in physical if o.Name.startswith('LevelBracket_')])==12
assert len([o for o in physical if o.Name.startswith('LevelBolt_')])==24
assert len([o for o in physical if o.Name.startswith('LevelNut_')])==24
assert len([o for o in physical if o.Name.startswith('FloorSeamBolt_')])==4
assert len([o for o in physical if o.Name.startswith('SeamBeamBolt_')])==4
assert doc.getObject('SeamBeamPLA').Shape.isValid()
out=dict(revision=r['parameters']['revision'],native_document=NAME,physical_parts=len(physical),
    native_solids=sum(len(o.Shape.Solids) for o in physical),STEP_solids=len(step.Solids),
    native_volume_mm3=native_volume,STEP_delta_mm3=step.Volume-native_volume,
    with_equipment_STEP_solids=len(with_equipment.Solids),
    equipment_STEP_scope='two selected power catalog envelopes and one unselected computer reservation',
    quoted_files_SHA256=quoted,quoted_plate_BRep_matches=True,
    saved_service_checks=service_results,continuous_conservative_service_envelopes_passed=True,
    meshes=meshes,mass=r['mass'],computer_and_battery_above_base_frame=True,
    loaded_use_released=False,electrical_operating_release=False)
(HERE/'saved_artifact_validation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(physical_parts=len(physical),STEP_solids=len(step.Solids),service_modules=2,closed_print_meshes=len(meshes),quoted_plate_matches=True),ensure_ascii=False))
