from pathlib import Path
import json, hashlib, itertools
import FreeCAD as App
import Part, Mesh
HERE=Path(__file__).resolve().parent;BASE=HERE.parent
p=HERE/'AMR01_PicoControl_E3.FCStd';d=App.openDocument(str(p))
o=App.openDocument(str(BASE/'fixed-deck/AMR01_FixedDeck_D69.FCStd'))
g=json.loads((HERE/'geometry.json').read_text());changed=set(g['changed']+g['added'])
phys=[x for x in d.Objects if hasattr(x,'MaterialBasis') and x.MaterialBasis!='reference']
refs=['BatteryBL1860B','BatteryAdapter03','Reserved_Computer','EStop_HW1B_V402R','MainPower_3214','Reserved_ComputerSupply','Pico_RS485_HAT','PicoOwned','PicoHeaderEnvelope']
objects=phys+[d.getObject(n) for n in refs]
hits=[];inherited=[];thread=[];checks=0
for a,b in itertools.combinations(objects,2):
 if not {a.Name,b.Name}.intersection(changed):continue
 checks+=1
 if not a.Shape.BoundBox.intersect(b.Shape.BoundBox):continue
 vol=a.Shape.common(b.Shape).Volume
 if vol<.001:continue
 # PCB header mating is a reserved mock assembly, not detailed connector geometry.
 if {a.Name,b.Name}<=set(['Pico_RS485_HAT','PicoOwned','PicoHeaderEnvelope']):continue
 if a.MaterialBasis==b.MaterialBasis=='steel' and 'Pico' in a.Name and 'Pico' in b.Name and a.Name[-1]==b.Name[-1] and (('Floor' in a.Name and 'Floor' in b.Name) or ('Lid' in a.Name and 'Lid' in b.Name)) and ('Nut' in a.Name or 'Nut' in b.Name) and ('Bolt' in a.Name or 'Bolt' in b.Name):
  thread.append([a.Name,b.Name,vol]);continue
 aa=o.getObject(a.Name);bb=o.getObject(b.Name)
 prior=aa.Shape.common(bb.Shape).Volume if aa and bb and aa.Shape.BoundBox.intersect(bb.Shape.BoundBox) else 0
 if abs(vol-prior)<.01:inherited.append([a.Name,b.Name,vol]);continue
 hits.append(dict(a=a.Name,b=b.Name,volume_mm3=round(vol,4),old_volume_mm3=round(prior,4)))
# Recheck the original continuous battery-service envelope against changed objects.
# Moving part sweeps along each straight segment conservatively use bounding boxes.
prior=json.loads((BASE/'two-story/validation.json').read_text())
service_hits=[]
for n in prior['moving_parts']:
 moving=d.getObject(n)
 if not moving:continue
 s=moving.Shape;bb=s.BoundBox
 # lift8 then travel rearwards220; bounding envelope of each linear segment.
 for label,lo,hi in [('lift',[bb.XMin,bb.YMin,bb.ZMin],[bb.XMax,bb.YMax,bb.ZMax+8]),('rear',[bb.XMin-220,bb.YMin,bb.ZMin+8],[bb.XMax,bb.YMax,bb.ZMax+8])]:
  sweep=Part.makeBox(*[hi[k]-lo[k] for k in range(3)],App.Vector(*lo))
  for a in objects:
   if a.Name not in changed or a.Name in prior['moving_parts']:continue
   if a.Shape.BoundBox.intersect(sweep.BoundBox) and a.Shape.common(sweep).Volume>.001:service_hits.append([n,label,a.Name])
# Preliminary strip calculation for the E-stop lid, not a printed-part proof.
F=150;L=38;width=71-22.5;t=5;E=1800
stress=3*F*L/(2*width*t*t);deflection=F*L**3/(4*E*width*t**3)
meshes=[]
for f in sorted(HERE.glob('*.stl')):
 m=Mesh.Mesh(str(f));bb=m.BoundBox
 assert m.isSolid() and max(bb.XLength,bb.YLength,bb.ZLength)<256,f
 meshes.append(dict(file=f.name,closed=True,print_bounds_mm=[bb.XLength,bb.YLength,bb.ZLength]))
out=dict(revision='E3',checked_pairs=checks,new_interferences=hits,inherited_contact_pairs=len(inherited),intentional_nominal_thread_pairs=thread,battery_service_hits=service_hits,
 passed=not hits and not service_hits,meshes=meshes,
 lid_review=dict(press_N=F,span_mm=L,effective_width_mm=width,thickness_mm=t,assumed_E_MPa=E,stress_MPa=stress,deflection_mm=deflection,assumed_short_term_allowable_MPa=10,passes_preliminary_strip_model=stress<10,printed_strength_validated=False),
 excludes=['actual cables and connector bends','received PCB keepouts and header stack','electrical ratings and operation','complete new Linux PC dimensions'],
 native_sha256=hashlib.sha256(p.read_bytes()).hexdigest())
(HERE/'validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2),flush=True)
