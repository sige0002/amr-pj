"""Build quotation-only grid deck variants; run with FreeCAD Python."""
from pathlib import Path
import hashlib
import json
import sys

import FreeCAD as App
import Part

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from cargo_deck import build_deck_specs, parameters

p = json.loads((HERE/'deck_parameters_Q1.json').read_text())
plate = next(s['shape'] for s in build_deck_specs(cfg=p, include_reference=False)
             if s['name'] == 'CargoDeckPlate').copy()
plate.translate(App.Vector(0, 0, -p['geometry']['plate_bottom_top_z_mm'][0]))
grid = [-125, -75, -25, 25, 75, 125]
results = []
for tag, bore in [('C45', 4.5), ('T4', 3.3)]:
    name = 'AMR_GridDeck_' + tag + '_Q1'
    holes = [Part.makeCylinder(bore/2, 6, App.Vector(x, y, -1))
             for x in grid for y in grid]
    shape = plate.cut(Part.makeCompound(holes)).removeSplitter()
    assert shape.isValid() and len(shape.Solids) == 1
    doc = App.newDocument(name)
    obj = doc.addObject('PartDesign::Feature', 'GridDeck')
    obj.Label = 'Quote only: 36 clearance holes' if tag == 'C45' else 'Quote only: 36 M4x0.7 threads, pilot geometry'
    obj.Shape = shape
    obj.addProperty('App::PropertyString', 'ManufacturingNote')
    obj.ManufacturingNote = 'See matching PDF. Not released for fabrication or loaded use.'
    doc.recompute()
    doc.saveAs(str(HERE / (name + '.FCStd')))
    step = HERE / (name + '.step')
    Part.export([obj], str(step))
    restored = Part.read(str(step))
    assert restored.isValid() and len(restored.Solids) == 1
    error = abs(shape.Volume - restored.Volume)
    assert error < 0.01
    results.append({
        'tag': tag, 'name': name, 'quantity': 1,
        'size_mm': [300, 300, 4], 'grid_pitch_mm': 50,
        'grid_coordinates_from_center_mm': grid, 'grid_hole_count': 36,
        'grid_modeled_bore_mm': bore,
        'finished_grid_hole': 'D4.5 through' if tag == 'C45' else 'M4x0.7-6H through; D3.3 pilot only in STEP',
        'existing_frame_holes': p['geometry']['frame_holes_xy_mm'],
        'existing_stop_holes': p['geometry']['stop_holes_xy_mm'],
        'existing_slots': p['geometry']['strap_slots'],
        'volume_mm3': shape.Volume, 'nominal_mass_kg_at2700': shape.Volume * 2.7e-6,
        'step_roundtrip_volume_error_mm3': error, 'valid_single_solid': True,
        'step_sha256': hashlib.sha256(step.read_bytes()).hexdigest(),
        'thread_helices_modeled': False,
        'mass_note': 'T4 pilot model excludes thread cutting mass loss.' if tag == 'T4' else 'CAD volume x nominal density.',
        'installation_warning': 'Outer grid rows y=+-125 conflict with nuts/washers below near y=+-135 support bars. Installed accessories need interface review. 4 mm tapped engagement is not load-qualified.',
        'quote_only': True, 'strength_released': False,
    })
    App.closeDocument(doc.Name)
(HERE / 'geometry.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(results, ensure_ascii=False, indent=2))
