"""Export final native geometry; verify quote files and prototype print meshes."""
from pathlib import Path
import json,hashlib,importlib.util
import FreeCAD as App
import Part,Mesh
HERE=Path(__file__).resolve().parent;BASE=HERE.parent
spec=importlib.util.spec_from_file_location('d69',HERE/'build_d69.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
v=json.loads((HERE/'validation.json').read_text());assert v['passed']
doc=App.openDocument(str(HERE/(b.NAME+'.FCStd')))
obs=[o for o in doc.Objects if hasattr(o,'MaterialBasis')];phys=[o for o in obs if o.MaterialBasis!='reference']
assert len(phys)==v['physical_parts']==329
assert all(o.Shape.isValid() and all(s.isClosed() for s in o.Shape.Solids) for o in obs)
assert not any(o.Name.startswith(b.REMOVED_PREFIXES+('OpenStop','HatchFixedAdapter','HatchMovingAdapter')) for o in obs)
old=App.openDocument(str(BASE/'direct-hinge/AMR01_DirectHinge_D68.FCStd'))
assert all(b.h.equivalent_brep(o.Shape,doc.getObject(o.Name).Shape) for o in old.Objects if hasattr(o,'MaterialBasis') and o.Name not in v['removed_objects']+v['changed_objects'])
exports=[]
for filename,extras in [(b.NAME+'-structure.step',[]),(b.NAME+'.step',['BatteryBL1860B','BatteryAdapter03','Reserved_Computer','EStop_XA1E_BV302R','ARM_3212','MainPower_3214'])]:
 expected=phys+[doc.getObject(n) for n in extras];Part.export(expected,str(HERE/filename))
 # OCCT emits trailing whitespace. Normalize only these new assembly exports,
 # then reopen the exact delivered bytes for geometric verification.
 p=HERE/filename;p.write_text('\n'.join(line.rstrip() for line in p.read_text().splitlines())+'\n')
 s=Part.read(str(p));volume=sum(o.Shape.Volume for o in expected)
 assert s.isValid() and abs(s.Volume-volume)/volume<1e-6
 assert len(s.Solids)==sum(len(o.Shape.Solids) for o in expected)
 exports.append(dict(file=filename,sha256=digest(HERE/filename),valid=True,solids=len(s.Solids),volume_delta_mm3=s.Volume-volume))
quotes=[]
file='AMR_GridDeck_C45_D3'
p=BASE/'aluminum-direct-deck'/(file+'.step')
s=Part.read(str(p));s.translate(App.Vector(0,0,229));t=doc.getObject('AluminumDeckD3').Shape
assert s.cut(t).Volume<.001 and t.cut(s).Volume<.001
quote_record=json.loads((BASE/'aluminum-direct-deck/quote-evidence/D3-observed.json').read_text())
assert digest(p)==quote_record['step_sha256']
assert digest(p.with_suffix('.pdf'))==quote_record['pdf_sha256']
quotes.append(dict(file='../aluminum-direct-deck/'+p.name,sha256=digest(p),matches_native_part='AluminumDeckD3',both_difference_volumes_below_mm3=.001,volume_mm3=s.Volume,size_mm=[s.BoundBox.XLength,s.BoundBox.YLength,s.BoundBox.ZLength],historical_quote_reused=True))
meshes=[]
for o in phys:
 if o.MaterialBasis!='PLA':continue
 file=o.Name+'.stl';folder=BASE/'direct-hinge' if (BASE/'direct-hinge'/file).exists() else BASE/'two-story' if (BASE/'two-story'/file).exists() else BASE/'aluminum-direct-deck'
 p=folder/file;m=Mesh.Mesh(str(p));bb=m.BoundBox;size=[bb.XLength,bb.YLength,bb.ZLength]
 assert m.isSolid() and max(size)<256,str(p)
 assert abs(m.Volume-o.Shape.Volume)/o.Shape.Volume<.003,(o.Name,m.Volume,o.Shape.Volume)
 meshes.append(dict(file=str(p.relative_to(BASE)),sha256=digest(p),part=o.Name,closed=True,size_mm=size,solid_CAD_volume_mm3=o.Shape.Volume))
assert len(meshes)==14
(HERE/'print_manifest.json').write_text(json.dumps(meshes,indent=2)+'\n')
# Current fastener-approach availability at all36 grid positions: an ordinary
# M4 envelope fromZ224..243 includes space for head/nut; this is a placement guide.
grid=[]
for x in [-125,-75,-25,25,75,125]:
 for y in [-115,-65,-15,35,85,135]:
  s=b.cyl(4,19,(x,y,224));found=[]
  for o in phys:
   if o.Name=='AluminumDeckD3':continue
   if s.BoundBox.intersect(o.Shape.BoundBox) and s.common(o.Shape).Volume>.001:found.append(o.Name)
  grid.append(dict(x=x,y=y,clear=not found,hits=found))
out=dict(revision='D6.9',native_sha256=digest(HERE/(b.NAME+'.FCStd')),source_native_sha256=digest(BASE/'direct-hinge/AMR01_DirectHinge_D68.FCStd'),physical_parts=len(phys),retained_BRep_equal=True,exports=exports,quote_geometry=quotes,meshes=meshes,grid_fastener_envelopes=grid,grid_clear_count=sum(x['clear'] for x in grid),validation_sha256=digest(HERE/'validation.json'),opening_stops=False,operation_released=False)
assert out['grid_clear_count']==36
(HERE/'saved_artifact_validation.json').write_text(json.dumps(out,indent=2)+'\n')
print('D6.9 exports PASS',len(phys),'parts',len(meshes),'STL; grid clear',out['grid_clear_count'],flush=True)
