"""Tool envelopes for the selected bench-first assembly sequence."""
from pathlib import Path
import json,importlib.util
import FreeCAD as App
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('b',HERE/'build_d68.py');b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
doc=App.openDocument(str(HERE/(b.NAME+'.FCStd')));v=json.loads((HERE/'validation.json').read_text())
objects=[o for o in doc.Objects if hasattr(o,'MaterialBasis') and o.Name not in ['CargoEnvelopeD3','StrapRouteX','StrapRouteY']]
def check(name,stage,shape,omitted):
 hits=[]
 for o in objects:
  if o.Name in omitted:continue
  if shape.BoundBox.intersect(o.Shape.BoundBox) and shape.common(o.Shape).Volume>.001:hits.append(o.Name)
 return dict(name=name,stage=stage,hits=hits)
checks=[]
for i,cx in enumerate([-105,105]):
 for k,x in enumerate([cx-15,cx+15]):
  checks.append(check(f'HingeLidBolt_{i}_{k}','hinge to L angle on bench; screwdriver outside',b.cyl(3,45,(x,159,246),(0,1,0)),[]))
  # Nut tool approach, outside diameter10 with4.6 bore for projecting M4 thread.
  checks.append(check(f'HingeLidNut_{i}_{k}','hold nut inside with7mm wrench',b.cyl(5,12,(x,130,246),(0,1,0)).cut(b.cyl(2.3,12,(x,130,246),(0,1,0))),[]))
  checks.append(check(f'AngleDeckBolt_{i}_{k}','angle to plate on bench; socket from top',b.cyl(3,45,(x,109,243)),[]))
  checks.append(check(f'AngleDeckNut_{i}_{k}','plate on bench; nut socket from underside',b.cyl(5,20,(x,109,204)).cut(b.cyl(2.3,20,(x,109,204))),[]))
assert not any(x['hits'] for x in checks),checks
(HERE/'assembly_access.json').write_text(json.dumps(dict(passed=True,checks=checks,scope='Nominal tool approach envelopes; full human hand movements and actual tool geometry not qualified.'),indent=2)+'\n')
print('Assembly tool paths PASS',len(checks))
