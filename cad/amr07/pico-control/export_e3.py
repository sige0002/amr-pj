"""Export E3 and validate saved geometry and the complete 16-part prototype set."""
from pathlib import Path
import json, hashlib
import FreeCAD as App
import Part, Mesh
HERE=Path(__file__).resolve().parent;BASE=HERE.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
native=HERE/'AMR01_PicoControl_E3.FCStd'
d=App.openDocument(str(native));old=App.openDocument(str(BASE/'fixed-deck/AMR01_FixedDeck_D69.FCStd'))
g=json.loads((HERE/'geometry.json').read_text())
v=json.loads((HERE/'validation.json').read_text())
assert v['passed'] and v['native_sha256']==sha(native)
def equivalent(a,b):
 aa=a.exportBrepToString().split();bb=b.exportBrepToString().split()
 if len(aa)!=len(bb):return False
 for x,y in zip(aa,bb):
  if x==y:continue
  try:
   if abs(float(x)-float(y))>1e-10:return False
  except ValueError:return False
 return True
for name in g['unchanged_BRep_names']:
 a=d.getObject(name).Shape;b=old.getObject(name).Shape
 assert abs(a.Volume-b.Volume)<.001,name
 assert equivalent(a,b),name
phys=[o for o in d.Objects if hasattr(o,'MaterialBasis') and o.MaterialBasis!='reference']
refs=['BatteryBL1860B','BatteryAdapter03','Reserved_Computer','Reserved_ComputerSupply','PicoOwned','Pico_RS485_HAT','PicoHeaderEnvelope','EStop_HW1B_V402R','MainPower_3214']
objs=phys+[d.getObject(n) for n in refs]
step=HERE/'AMR01_PicoControl_E3.step'
Part.export(objs,str(step))
step.write_text('\n'.join(line.rstrip() for line in step.read_text().splitlines())+'\n')
saved=Part.read(str(step));expected=Part.makeCompound([o.Shape for o in objs])
assert saved.isValid() and len(saved.Solids)==len(expected.Solids)
assert abs(saved.Volume-expected.Volume)<.01,(saved.Volume,expected.Volume)
prior={x['part']:x for x in json.loads((BASE/'fixed-deck/print_manifest.json').read_text())}
meshes=[]
for o in phys:
 if o.MaterialBasis!='PLA':continue
 p=HERE/(o.Name+'.stl')
 if not p.exists():p=BASE/prior[o.Name]['file'];assert sha(p)==prior[o.Name]['sha256']
 m=Mesh.Mesh(str(p));b=m.BoundBox
 assert m.isSolid() and max(b.XLength,b.YLength,b.ZLength)<256,p
 assert abs(m.Volume-o.Shape.Volume)/o.Shape.Volume<.01,(o.Name,m.Volume,o.Shape.Volume)
 meshes.append(dict(part=o.Name,file=str(p.relative_to(BASE)),sha256=sha(p),closed=True,size_mm=[b.XLength,b.YLength,b.ZLength],solid_CAD_volume_mm3=o.Shape.Volume))
assert len(phys)==359 and len(meshes)==16
(HERE/'print_manifest.json').write_text(json.dumps(meshes,indent=2)+'\n')
out=dict(native_sha256=sha(native),source_native_sha256=sha(BASE/'fixed-deck/AMR01_FixedDeck_D69.FCStd'),validation_sha256=sha(HERE/'validation.json'),step_sha256=sha(step),step_solids=len(saved.Solids),step_volume_mm3=saved.Volume,physical_parts=len(phys),prototype_meshes=len(meshes),unchanged_shapes_rechecked=len(g['unchanged_BRep_names']),passed=True,production_release=False)
(HERE/'saved_artifact_validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
