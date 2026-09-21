"""Export the adopted D2 plate; FreeCAD Python, no modification of Q1 files."""
from pathlib import Path
import sys,json,hashlib,zipfile
import FreeCAD as App
import Part

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from cargo_deck import build_deck_specs,parameters
p=parameters();g=p['geometry'];name='AMR_GridDeck_C45_D2'
plate=next(s['shape'] for s in build_deck_specs(include_reference=False) if s['name']=='CargoDeckPlate')
plate.translate(App.Vector(0,0,-g['plate_bottom_top_z_mm'][0]))
assert plate.isValid() and len(plate.Solids)==1
doc=App.newDocument(name);obj=doc.addObject('PartDesign::Feature','GridDeck');obj.Shape=plate
obj.Label='D2 aluminium deck | frame holes x+-105 | 36 M4 grid holes'
doc.recompute();doc.saveAs(str(HERE/(name+'.FCStd')))
step=HERE/(name+'.step');Part.export([obj],str(step));check=Part.read(str(step))
assert check.isValid() and len(check.Solids)==1 and abs(check.Volume-plate.Volume)<.01
data={'tag':'C45','name':name,'revision':'D2','quantity':1,'size_mm':[300,300,4],
      'grid_coordinates_from_center_mm':g['grid_coordinates_from_center_mm'],
      'grid_pitch_mm':50,'grid_hole_count':36,'grid_modeled_bore_mm':4.5,
      'existing_frame_holes':g['frame_holes_xy_mm'],'existing_stop_holes':g['stop_holes_xy_mm'],
      'existing_slots':g['strap_slots'],'volume_mm3':plate.Volume,
      'nominal_mass_kg_at2700':plate.Volume*2.7e-6,'valid_single_solid':True,
      'step_roundtrip_volume_error_mm3':abs(check.Volume-plate.Volume),
      'step_sha256':hashlib.sha256(step.read_bytes()).hexdigest(),
      'material_requested':'6061-T6','minimum_proof_stress_requested_MPa':240,
      'manufacturing_release':False}
(HERE/'geometry.json').write_text(json.dumps([data],ensure_ascii=False,indent=2)+'\n')
print(json.dumps(data,ensure_ascii=False))
