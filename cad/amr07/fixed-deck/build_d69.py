"""D6.9: fixed six-bolt deck, retaining D6.8 floor-supported rear controls.

Run with FreeCAD Python. Restore the already quoted D3 plate and the D6.5
M6 fasteners from saved geometry; do not regenerate nominal interfaces.
"""
from pathlib import Path
import importlib.util, json, hashlib
import FreeCAD as App
import Part

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
SOURCE = BASE / 'direct-hinge'
spec = importlib.util.spec_from_file_location('d68_helpers', SOURCE / 'build_d68.py')
old_helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old_helpers)
h = old_helpers.h
d6 = old_helpers.d6
V = App.Vector
cyl = old_helpers.cyl
RHO = old_helpers.RHO
NAME = 'AMR01_FixedDeck_D69'
REMOVED_PREFIXES = (
    'LidAngle_', 'HGTP20_', 'HingeFrame', 'HingeLid', 'AngleDeck',
    'HatchLockWasher_', 'HatchLockWingBolt_',
)


def mass(obj):
    return obj.CatalogMassKg if hasattr(obj, 'CatalogMassKg') else obj.Shape.Volume * RHO.get(obj.MaterialBasis, 0)


def main():
    source_path = SOURCE / 'AMR01_DirectHinge_D68.FCStd'
    fixed_path = BASE / 'two-story/AMR01_TwoStorey_D6.FCStd'
    old = App.openDocument(str(source_path))
    original_fixed = App.openDocument(str(fixed_path))
    prior = json.loads((SOURCE / 'validation.json').read_text())
    doc = App.newDocument(NAME)
    doc.Label = 'AMR D6.9 | FIXED DECK: 6 x M6 | FLOOR SUPPORTED REAR CONTROLS'
    removed = [o.Name for o in old.Objects if o.Name.startswith(REMOVED_PREFIXES)]
    changed = ['AluminumDeckD3', 'DeckSlotNut0', 'DeckSlotNut4']
    restored = ['AluminumDeckD3'] + ['DeckBolt'+str(i) for i in range(6)] + ['DeckSlotNut'+str(i) for i in range(6)]
    for obj in old.Objects:
        if hasattr(obj, 'MaterialBasis') and obj.Name not in removed + changed:
            doc.copyObject(obj, False)
    for name in restored:
        doc.copyObject(original_fixed.getObject(name), False)
    plate = doc.getObject('AluminumDeckD3')
    plate.ModelNote = ('D6.9 fixed deck: quoted D3 300x300x4 plate, 36 D4.5 grid holes, '
                       '6 D6.6 frame holes, 8 D4.5 cargo-stop holes and 4 slots. '
                       'Bears directly on TWO upper 3030 rails at Z229. '
                       'Three M6x12 socket-cap screws per rail into HNTT6-6 slot nuts. '
                       'No hinge holes, adapters, spacers or countersinks.')
    for i in range(6):
        doc.getObject('DeckBolt'+str(i)).ModelNote = (
            'D6.9 M6x12 socket cap; 5mm hex key from above. Head directly on 4mm aluminum, '
            'no washer. Nominal slot projection8mm; slot floor clearance1mm. '
            'Verify actual screw length, thread engagement and tightening on receipt.')
    p = {k: prior['parameters'][k] for k in ['battery_harness_points', 'operator_side', 'estop', 'arm', 'main_power']}
    p.update(revision='D6.9', date='2026-09-23', attachment='fixed bolted deck',
             plate_size_mm=[300, 300, 4], plate_z_mm=[229, 233],
             fastener='M6x12 socket cap + HNTT6-6 slot nut', fastener_qty=6,
             mounting_xy_mm=[[x, y] for x in [-105, 0, 105] for y in [-135, 135]],
             support='Two existing upper 3030 rails; three fasteners on each rail',
             washers=False, countersinks=False, hinges=False, additional_machined_angles=False,
             battery_service_requires_deck_removal=False, unload_before_deck_removal=True,
             deck_service_waypoints_xyz_mm=[[0, 0, 0], [0, 0, 120]], production_release=False)
    doc.recompute()
    physical = [o for o in doc.Objects if hasattr(o, 'MaterialBasis') and o.MaterialBasis != 'reference']
    new = [n for n in restored if n not in changed]
    ledger = []
    for name in removed + changed:
        o = old.getObject(name)
        ledger.append(dict(name='remove '+name, mass_kg=-mass(o), center_mm=d6.center(o.Shape)))
    for name in restored:
        o = doc.getObject(name)
        ledger.append(dict(name='restore '+name, mass_kg=mass(o), center_mm=d6.center(o.Shape)))
    unchanged = all(h.equivalent_brep(o.Shape, doc.getObject(o.Name).Shape)
                    for o in old.Objects if hasattr(o, 'MaterialBasis') and o.Name not in removed + changed)
    assert unchanged
    assert all(h.equivalent_brep(doc.getObject(n).Shape, original_fixed.getObject(n).Shape) for n in restored)
    mounts = [dict(bolt='DeckBolt'+str(i), nut='DeckSlotNut'+str(i), xy_mm=xy,
                   plate_thickness_mm=4, slot_projection_mm=8, slot_floor_clearance_mm=1)
              for i, xy in enumerate(p['mounting_xy_mm'])]
    moving = [o.Name for o in physical if o.Name.startswith(('AluminumDeck', 'PrintedStop', 'StopBolt', 'StopWasher', 'StopNut'))]
    result = dict(parameters=p, new_objects=new, changed_objects=changed, removed_objects=removed,
                  restored_D65_objects=restored, retained_shapes_BRep_equal=unchanged,
                  source_native_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),
                  restoration_source_sha256=hashlib.sha256(fixed_path.read_bytes()).hexdigest(),
                  physical_parts=len(physical), deck_mounts=mounts, case_mounts=prior['case_mounts'],
                  moving_deck_parts=moving,
                  released_before_deck_removal=['DeckBolt'+str(i) for i in range(6)] + ['StrapRouteX', 'StrapRouteY', 'CargoEnvelopeD3'],
                  mass=dict(estimated_base_kg=prior['mass']['estimated_base_kg'] + sum(e['mass_kg'] for e in ledger),
                            source_kg=prior['mass']['estimated_base_kg'], ledger=ledger,
                            total_solid_PLA_kg=sum(mass(o) for o in physical if o.MaterialBasis == 'PLA'),
                            actually_weighed=False))
    (HERE / 'parameters.json').write_text(json.dumps(p, ensure_ascii=False, indent=2)+'\n')
    (HERE / 'geometry.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    doc.saveAs(str(HERE / (NAME+'.FCStd')))
    print(json.dumps(dict(parts=len(physical), mass_kg=result['mass']['estimated_base_kg'],
                          difference_kg=sum(e['mass_kg'] for e in ledger), removed=len(removed),
                          retained_BRep_equal=unchanged)), flush=True)


if __name__ == '__main__':
    main()
