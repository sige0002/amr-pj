"""Saved-CAD contact barrier review; not dielectric or PCB product approval."""
from pathlib import Path
from itertools import product
import hashlib,json
import FreeCAD as App
import Part
HERE=Path(__file__).resolve().parent
path=HERE/'AMR01_TwoStorey_D6.FCStd';doc=App.openDocument(str(path));V=App.Vector
cover=doc.getObject('ComputerBarrierPLA').Shape
report=json.loads((HERE/'validation.json').read_text())
assert cover.isValid() and len(cover.Solids)==1
# The complete protected footprint is solid at every height through this2mm
# thickness. This tests a volume, not selected points that might miss holes.
barrier_volume=Part.makeBox(121,101,2,V(-60.5,-50.5,107))
assert barrier_volume.cut(cover).Volume<1e-6
hardware=[]
for ix,iy in product(range(2),repeat=2):
    names=[f'FloorSeamBolt_{ix}_{iy}',f'FloorSeamTopWasher_{ix}_{iy}']
    for name in names:
        s=doc.getObject(name).Shape;b=s.BoundBox
        assert b.ZMax<107 and b.XMin>-60.5 and b.XMax<60.5 and b.YMin>-50.5 and b.YMax<50.5
        assert s.common(cover).Volume<1e-6
        hardware.append(dict(name=name,nominal_gap_below_barrier_mm=107-b.ZMax))
supports=[]
for i,(x,y) in enumerate(product([-50,50],[-40,40])):
    column=Part.makeBox(10,10,2,V(x-5,y-5,107))
    assert column.cut(cover).Volume<1e-6
    floor=doc.getObject(f'FloorPLA_{int(x>0)}_{int(y>0)}').Shape
    boss=Part.makeBox(10,10,5.6,V(x-5,y-5,101.4))
    assert boss.cut(floor).Volume<1e-6
    pad=doc.getObject(f'ComputerPad_{i}').Shape;b=pad.BoundBox
    assert abs(b.ZMin-109)<1e-6 and abs(b.ZMax-110)<1e-6
    assert abs(b.XMin-(x-5))<1e-6 and abs(b.YMin-(y-5))<1e-6
    supports.append(dict(xy_mm=[x,y],area_mm2=100,load_path='case pad ->2mm solid barrier -> aligned hard floor boss'))
protected=Part.makeBox(121,101,60,V(-60.5,-50.5,109))
metal=[o for o in doc.Objects if hasattr(o,'MaterialBasis') and o.MaterialBasis in ['steel','aluminum']]
metal_hits=[o.Name for o in metal if o.Shape.BoundBox.intersect(protected.BoundBox) and o.Shape.common(protected).Volume>.001]
assert not metal_hits
assert all(not x['hits'] for x in report['continuous_barrier_service'])
mass=cover.Volume*1.24e-6
# All equipment contact is deliberately aligned above the four hard supports.
# Only local through-thickness compression is screened; no diaphragm/span
# strength, dielectric value, puncture load or printed allowable is inferred.
screens=[]
for T in [0,10,30]:
    force=(.525+mass)*9.80665+2*T
    screens.append(dict(belt_tension_each_leg_N=T,total_force_N=force,
        mean_compression_MPa=force/400,twice_load_mean_compression_MPa=2*force/400,
        through_thickness_shortening_mm_at_E1000=force/400*2/1000))
out=dict(revision='D6.5',native_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    part='ComputerBarrierPLA',mass_kg=mass,outer_mm=[123.4,103.4,12.4],
    continuous_floor_mm=2,wall_mm=1.2,protected_footprint_mm=[121,101],through_holes=0,
    covered_hardware=hardware,metal_intrusions_above_barrier=metal_hits,
    supports=supports,local_compression_screen=screens,
    material='Nonconductive unfilled PLA; actual filament and finished print not qualified for insulation.',
    retention='Existing floor locator pocket bounds lateral motion with nominal0.3mm per-side clearance. Installed cased computer and its strap hold barrier down; remove case/belt before barrier service.',
    service_checks=report['continuous_barrier_service'],
    bare_PCB_mounting_complete=False,case_product_selected=False,dielectric_strength_verified=False,
    limitations=['Contact separation is not an electrical insulation certification.',
        'No bare PCB or component-side surface is placed directly on case pads or under the case strap. Select insulating enclosure or mounting-hole standoffs after board selection.',
        'Bottom cooling, actual component protrusions, mounting screws, filament conductivity, print holes/cracks, temperature and abrasion require product-specific checks.',
        'Compression-only local screen assumes case forces enter the four marked pads. No arbitrary point-load or cover spanning capacity is certified. Nominal0.6mm screw clearance does not include deflection/tolerance.'])
(HERE/'computer_barrier_review.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(barrier_kg=mass,covered_hardware=len(hardware),through_holes=0,
    metal_intrusions=metal_hits,local_compression_max_MPa=screens[-1]['mean_compression_MPa']),ensure_ascii=False))
