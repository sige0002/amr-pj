"""Compare opposing-bracket candidates against saved D6, without changing CAD.

Run under FreeCAD Python. Checks candidate geometry, access and budget only;
no joint strength, preload or lateral-stiffness qualification is inferred.
"""
from pathlib import Path
import hashlib
import json
import FreeCAD as App
import Part

HERE = Path(__file__).resolve().parent
native = HERE / 'AMR01_TwoStorey_D6.FCStd'
report = json.loads((HERE / 'validation.json').read_text())
doc = App.openDocument(str(native))
V = App.Vector
rho = {'aluminum': 2.7e-6, 'steel': 7.85e-6}
parts = [(o.Name, o.Shape, o.MaterialBasis) for o in doc.Objects
         if hasattr(o, 'MaterialBasis')]


def hits(shape, objects):
    found = []
    for name, other, _ in objects:
        if shape.BoundBox.intersect(other.BoundBox):
            overlap = shape.common(other).Volume
            if overlap > .001:
                found.append({'part': name, 'overlap_mm3': overlap})
    return found


def sweep(shape, start, end):
    b = shape.BoundBox
    low = [b.XMin, b.YMin, b.ZMin]
    size = [b.XLength, b.YLength, b.ZLength]
    return Part.makeBox(*[size[i] + abs(end[i]-start[i]) for i in range(3)],
                        V(*[low[i] + min(start[i], end[i]) for i in range(3)]))


results = []
for ends in [('Lower',), ('Lower', 'Upper')]:
    added = []
    for i, (cx, cy) in enumerate(report['parameters']['upright_centers_xy_mm']):
        for end in ends:
            names = [f'LevelBracket_{i}_{end}']
            names += [f'Level{kind}_{i}_{end}_{side}'
                      for side in ['Post', 'Rail'] for kind in ['Bolt', 'Nut']]
            for name in names:
                obj = doc.getObject(name)
                shape = obj.Shape.copy()
                shape.rotate(V(cx, cy, 0), V(0, 0, 1), 180)
                added.append(('Opposite_' + name, shape, obj.MaterialBasis))
    collisions = []
    for i, (name, shape, _) in enumerate(added):
        found = hits(shape, parts + added[:i])
        if found:
            collisions.append({'candidate_part': name, 'hits': found})
    access = []
    for key in ['continuous_battery_service', 'continuous_computer_service']:
        for entry in report[key]:
            shape = doc.getObject(entry['part']).Shape
            found = hits(sweep(shape, entry['from_mm'], entry['to_mm']), added)
            if found:
                access.append({'service': key, 'moving_part': entry['part'], 'hits': found})
    tools = []
    # Same frame-first assembly order as D6: floor and cargo plate are absent.
    metal = [p for p in parts + added if p[2] in rho
             and p[0] not in report['translated_parts']]
    for i, (cx, cy) in enumerate(report['parameters']['upright_centers_xy_mm']):
        for end, z, dz in [('Lower', 99, 1), ('Upper', 199, -1)]:
            original_dx = (-1 if cx > 0 else 1) * (1 if end == 'Lower' else -1)
            for opposite in ([False, True] if end in ends else [False]):
                dx = -original_dx if opposite else original_dx
                prefix = 'Opposite_' if opposite else ''
                for side, surface, inward in [
                    ('Post', (cx+dx*15, cy, z+dz*15), (-dx, 0, 0)),
                    ('Rail', (cx+dx*33, cy, z), (0, 0, -dz)),
                ]:
                    name = prefix + f'LevelBolt_{i}_{end}_{side}'
                    n = V(*inward)
                    seat = V(*surface) - n*4.5
                    tool = Part.makeCylinder(2.9, 35, seat-n*6, -n)
                    found = hits(tool, [p for p in metal if p[0] != name])
                    if found:
                        tools.append({'bolt': name, 'hits': found})
    tires = [{'side': side, 'hits': hits(Part.makeCylinder(
        50.35, 123, V(90, side*153, 50.35), V(0, side, 0)), added)}
        for side in [-1, 1]]
    extra = sum(shape.Volume*rho[material] for _, shape, material in added)
    count = 4*len(ends)
    results.append(dict(
        candidate='opposing_' + '_and_'.join(ends).lower(),
        added_brackets=count, added_M6x12=2*count, added_HNTT6_6=2*count,
        added_mass_kg=extra,
        estimated_base_kg=report['mass']['estimated_base_kg'] + extra,
        additional_bracket_pack_cost_JPY=0 if count == 4 else 917,
        cost_basis='D6 planned 20 brackets with4 unused,100 nuts with34 unused;917JPY/10-pack carried from same-day observation. Additional screws/shipping unpriced. Nothing already owned assumed.',
        mass_basis='Same nominal BRep/density ledger as D6; bracket15g catalog mass not substituted into only the candidate.',
        collisions=collisions, service_collisions=access, tool_collisions=tools,
        tire_service=tires,
        nominal_geometry_and_access_passed=not (collisions or access or tools or any(t['hits'] for t in tires)),
        CAD_modified=False, strength_qualified=False,
        limitation='Opposing X brackets address opening in the X-Z plane; Y loading, racking, preload and mixed-brand seating are not qualified by adding parts.'))

out = dict(
    revision='D6 review only', date='2026-09-22',
    native_sha256=hashlib.sha256(native.read_bytes()).hexdigest(),
    original_base_mass_kg=report['mass']['estimated_base_kg'], candidates=results,
    current_design_qualified=False, candidate_adopted=False,
    finding='Member vertical screening does not certify single-sided joints. Need directional moment/slip and assembly-racking validation; CAD clearance is independent of that.')
(HERE / 'joint_review.json').write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n')
print(json.dumps(out, ensure_ascii=False))
