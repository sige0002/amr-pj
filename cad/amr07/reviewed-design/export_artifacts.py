"""Export and reopen standard/optional STEP; bind prototype meshes to saved CAD."""
from pathlib import Path
import json,hashlib,zipfile
import FreeCAD as App
import Part,Mesh
BASE=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def same_brep(a,b):
 aa=a.exportBrepToString().split();bb=b.exportBrepToString().split()
 if len(aa)!=len(bb):return False
 for x,y in zip(aa,bb):
  if x==y:continue
  try:
   if abs(float(x)-float(y))>1e-10:return False
  except ValueError:return False
 return True
def same(a,b):
 # Saving may change OCCT bookkeeping flags without changing the solid.
 if same_brep(a,b):return True
 if any(len(getattr(a,k))!=len(getattr(b,k)) for k in ['Solids','Faces','Edges','Vertexes']):return False
 if abs(a.Volume-b.Volume)>.0001 or abs(a.Area-b.Area)>.0001:return False
 return a.cut(b).Volume<.0001 and b.cut(a).Volume<.0001
def export(folder,name,optional=False):
 here=BASE/folder;native=here/(name+'.FCStd');d=App.openDocument(str(native));v=json.loads((here/'validation.json').read_text())
 assert v['passed'] and v['native_sha256']==sha(native)
 req=json.loads((here/('requirements.json' if optional else 'geometry.json')).read_text())
 source=BASE/(req['standard_CAD'] if optional else req['source']);assert sha(source)==req['standard_native_sha256' if optional else 'source_sha256']
 old=App.openDocument(str(source));names=[o.Name for o in old.Objects if hasattr(o,'MaterialBasis')] if optional else req['unchanged_BRep_names']
 for n in names:assert same(old.getObject(n).Shape,d.getObject(n).Shape),n
 physical=[o for o in d.Objects if hasattr(o,'MaterialBasis') and o.MaterialBasis!='reference']
 refs=['BatteryBL1860B','BatteryAdapter03','Reserved_Computer','Reserved_ComputerSupply','PicoOwned','Pico_RS485_HAT','PicoHeaderEnvelope','EStop_HW1B_V402R','MainPower_3214','EStopLockNut','MainPowerNutReservation']+[f'MainPowerTerminalReservation{i}' for i in range(2)]+[f'EStopLeadReservation{i}' for i in range(4)]
 if optional:refs+=['OptMonitorEnvelope']
 objs=physical+[d.getObject(n) for n in refs];step=here/(name+'.step');Part.export(objs,str(step));step.write_text('\n'.join(s.rstrip() for s in step.read_text().splitlines())+'\n')
 expected=Part.makeCompound([o.Shape for o in objs]);s=Part.read(str(step));assert s.isValid() and len(s.Solids)==len(expected.Solids) and abs(s.Volume-expected.Volume)<.01
 prior={m['part']:m for m in json.loads((BASE/'pico-control/print_manifest.json').read_text())};meshes=[]
 for o in physical:
  if o.MaterialBasis!='PLA' or (optional and not o.Name.startswith('Opt')):continue
  p=here/(o.Name+'.stl')
  if not p.exists():p=BASE/prior[o.Name]['file'];assert sha(p)==prior[o.Name]['sha256']
  m=Mesh.Mesh(str(p));bb=m.BoundBox;assert m.isSolid() and max(bb.XLength,bb.YLength,bb.ZLength)<256
  assert abs(m.Volume-o.Shape.Volume)/o.Shape.Volume<.01,o.Name
  meshes.append(dict(part=o.Name,file=str(p.relative_to(BASE)),sha256=sha(p),closed=True,bounds_mm=[bb.XLength,bb.YLength,bb.ZLength]))
 assert len(meshes)==(4 if optional else 12)
 (here/'print_manifest.json').write_text(json.dumps(meshes,indent=2)+'\n')
 with zipfile.ZipFile(here/('O1-print-prototypes.zip' if optional else 'E4-print-prototypes.zip'),'w',zipfile.ZIP_DEFLATED) as z:
  z.writestr('README.txt','Prototype only. Check supplied hardware fit, slicing orientation, strength and creep before use. Nonconductive PLA. All models fit256mm envelope.\nOptional monitor hardware is NOT standard equipment.\n')
  for m in meshes:z.write(BASE/m['file'],m['part']+'.stl')
  for n in ['README.ja.md','print_manifest.json','validation.json']:z.write(here/n,n)
 out=dict(passed=True,native_sha256=sha(native),source_native_sha256=sha(source),validation_sha256=sha(here/'validation.json'),step_sha256=sha(step),step_solids=len(s.Solids),step_volume_mm3=s.Volume,physical_parts=len(physical),prototype_meshes=len(meshes),source_shapes_compared=len(names),production_release=False)
 (here/'saved_artifact_validation.json').write_text(json.dumps(out,indent=2)+'\n')
 for p in here.glob('*.step'):p.write_text('\n'.join(x.rstrip() for x in p.read_text().splitlines())+'\n')
 print(folder,json.dumps(out),flush=True)
 App.closeDocument(old.Name)
 App.closeDocument(d.Name)
if __name__=='__main__':
 export('reviewed-design','AMR01_Reviewed_E4')
 export('monitor-option','AMR01_OptionalMonitor_O1',True)
