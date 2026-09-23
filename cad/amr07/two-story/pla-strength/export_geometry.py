"""Extract current D6.5 print solids for a reproducible solid-element screen."""
from pathlib import Path
import hashlib,json
import FreeCAD as A
HERE=Path(__file__).resolve().parent;SOURCE=HERE.parent/'AMR01_TwoStorey_D6.FCStd'
d=A.openDocument(str(SOURCE));out={}
v=json.loads((HERE.parent/'validation.json').read_text())
for name in ['FloorPLA_0_0','FloorPLA_0_1','FloorPLA_1_0','FloorPLA_1_1','SeamBeamPLA']:
 s=d.getObject(name).Shape
 assert s.isValid() and len(s.Solids)==1
 p=HERE/(name+'.step');s.exportStep(str(p))
 p.write_text('\n'.join(l.rstrip() for l in p.read_text().splitlines())+'\n')
 b=s.BoundBox
 out[name]=dict(file=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),volume_mm3=s.Volume,
  bounds_mm=[b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax],solid_mass_kg=s.Volume*1.24e-6,
  fixings=[x for x in v['floor_fixings'] if x['panel']==name])
r=dict(revision='D6.5',source_cad_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),parts=out)
barrier=d.getObject('ComputerBarrierPLA').Shape
r['computer_barrier']=dict(volume_mm3=barrier.Volume,solid_mass_kg=barrier.Volume*1.24e-6,
    model='Mass added at PC support patches; this cover is not included in the five-solid floor FEA. No spanning stiffness credit. Separate CAD/compression review.')
(HERE/'geometry.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({n:[round(p['volume_mm3']),round(p['solid_mass_kg']*1000,2)] for n,p in out.items()}))
A.closeDocument(d.Name)
