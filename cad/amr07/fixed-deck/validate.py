"""Saved-CAD collisions and continuous straight service/tool envelopes."""
from pathlib import Path
from itertools import combinations
import importlib.util, json
import FreeCAD as App
import Part

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('d69', HERE / 'build_d69.py')
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
doc = App.openDocument(str(HERE / (b.NAME+'.FCStd')))
g = json.loads((HERE / 'geometry.json').read_text())
physical = [o for o in doc.Objects if hasattr(o, 'MaterialBasis') and o.MaterialBasis != 'reference']
refs = [o for o in doc.Objects if hasattr(o, 'MaterialBasis') and o.MaterialBasis == 'reference']
cache = {o.Name: (o.Shape, o.Shape.BoundBox) for o in physical + refs}


def hits(shape, objects):
    bb = shape.BoundBox
    out = []
    for obj in objects:
        other, otherbb = cache[obj.Name]
        if bb.intersect(otherbb):
            volume = shape.common(other).Volume
            if volume > .001:
                out.append(dict(part=obj.Name, overlap_mm3=volume))
    return out


collisions = []
changed = set(g['new_objects'] + g['changed_objects'])
checked = 0
for a, c in combinations(physical, 2):
    if a.Name in changed or c.Name in changed:
        checked += 1
        collisions += [dict(a=a.Name, **v) for v in hits(a.Shape, [c])]
rh = {o.Name: hits(o.Shape, physical) for o in refs}
rh = {k: v for k, v in rh.items() if v}
print('STATIC', json.dumps(dict(collisions=collisions, references=rh)), flush=True)

bv = json.loads((HERE.parent / 'two-story/validation.json').read_text())
service = []
for name in bv['moving_parts']:
    fixed = [o for o in physical + refs if o.Name not in bv['moving_parts'] + bv['released_before_service']]
    for start, end in zip(bv['parameters']['battery_service_waypoints_xyz_mm'], bv['parameters']['battery_service_waypoints_xyz_mm'][1:]):
        pieces = [doc.getObject(name).Shape]
        if name == 'BatteryModuleHarness':
            points = [b.V(*p) for p in g['parameters']['battery_harness_points']]
            pieces = [Part.makeCylinder(3, (t-s).Length, s, t-s) for s, t in zip(points, points[1:])]
            pieces += [Part.makeSphere(3, t) for t in points[1:-1]]
        service.append(dict(part=name, from_mm=start, to_mm=end, deck_installed=True,
                            hits=[q for piece in pieces for q in hits(b.d6.swept_bbox(piece, start, end), fixed)]))
pc = []
for name in ['Reserved_Computer', 'ComputerTopPad']:
    fixed = [o for o in physical + refs if o.Name not in ['Reserved_Computer', 'ComputerTopPad', 'ComputerRetentionBelt']]
    for start, end in [([0, 0, 0], [0, 0, 8]), ([0, 0, 8], [0, -230, 8])]:
        pc.append(dict(part=name, from_mm=start, to_mm=end, hits=hits(b.d6.swept_bbox(doc.getObject(name).Shape, start, end), fixed)))
tool_paths = []
for m in g['deck_mounts']:
    x, y = m['xy_mm']
    omitted = g['released_before_deck_removal']
    tool_paths.append(dict(bolt=m['bolt'], stage='cargo and straps removed; top access, 5mm hex key',
                           envelope_diameter_mm=12, vertical_clearance_mm=70,
                           hits=hits(b.cyl(6, 70, (x, y, 239)), [o for o in physical + refs if o.Name not in omitted])))
for m in g['case_mounts']:
    x, y = m['xy_mm']
    omitted = [m['bolt']] + bv['moving_parts'] + bv['released_before_service']
    omitted += [o.Name for o in physical + refs if o.Name.startswith(m['case']+'Lid') or o.Name in ['EStop_XA1E_BV302R', 'ARM_3212', 'MainPower_3214']]
    tool_paths.append(dict(bolt=m['bolt'], stage='cases before battery; case lid and switches removed',
                           hits=hits(b.cyl(3, 70, (x, y, 122)), [o for o in physical + refs if o.Name not in omitted])))
approach = []
for key, radius in [('estop', 35), ('arm', 16), ('main_power', 18)]:
    x, y, z = g['parameters'][key]['panel_center_mm']
    approach.append(dict(control=key, hits=hits(b.cyl(radius, 180, (x, y, z+21)), physical + refs)))
deck = []
fixed = [o for o in physical + refs if o.Name not in g['moving_deck_parts'] + g['released_before_deck_removal']]
for name in g['moving_deck_parts']:
    deck.append(dict(part=name, from_mm=[0, 0, 0], to_mm=[0, 0, 120],
                     hits=hits(b.d6.swept_bbox(doc.getObject(name).Shape, [0, 0, 0], [0, 0, 120]), fixed)))
print('SERVICE', json.dumps([s for s in service + pc + tool_paths + approach + deck if s['hits']]), flush=True)
out = dict(g, static_changed_pair_count=checked, closed_collisions=collisions,
           reference_collisions=rh, battery_service=service, computer_service=pc,
           assembly_tools=tool_paths, operator_approach=approach, deck_removal=deck,
           continuous_piecewise_bbox=True, opening_stops_present=False, hinges_present=False,
           static_unchanged_pair_basis='../direct-hinge/validation.json; retained BReps identical')
out['passed'] = not (collisions or rh or any(s['hits'] for s in service + pc + tool_paths + approach + deck)) and g['retained_shapes_BRep_equal']
(HERE / 'validation.json').write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n')
print('D6.9 PASS', out['passed'], flush=True)
assert out['passed']
