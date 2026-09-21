"""Fit the selected mount into A4, preserving the quoted A4 artifacts.

Run in headless FreeCAD after build_mount_candidates.py. Replace two brackets
and adjust their M6 fastener placements. Other geometry stays unchanged.
Collision results concern nominal geometry, not load qualification.
"""
from pathlib import Path
from itertools import combinations
import hashlib
import json

import FreeCAD as App
import Part

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parent / 'amr05'
NAME = 'AMR01_M0601C_A5'
V = App.Vector


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    old_path = PREVIOUS / 'AMR01_M0601C_A4.FCStd'
    selection = json.loads((HERE / 'selection.json').read_text())
    candidate_path = HERE / selection['candidate_step_relative']
    parameters = json.loads(candidate_path.with_suffix('.json').read_text())
    candidate_id = parameters['candidate_id']
    old_hash = digest(old_path)
    if NAME in App.listDocuments():
        raise RuntimeError('A5 is already open; preserve any edits before regenerating')
    old = App.openDocument(str(old_path))
    doc = App.newDocument(NAME)
    doc.Label = 'AMR-01 A5 | ' + candidate_id + ' mount | load qualification pending'
    # A4 consists of independent Part features and display groups, not links
    # into a different document. Copy each feature and rebuild its grouping.
    copied = {}
    for obj in old.Objects:
        if obj.TypeId == 'PartDesign::Feature':
            copied[obj.Name] = doc.copyObject(obj, False)
        elif obj.TypeId == 'App::DocumentObjectGroup':
            group = doc.addObject(obj.TypeId, obj.Name)
            group.Label = obj.Label
            copied[obj.Name] = group
        else:
            raise AssertionError('Review unexpected A4 object: ' + obj.TypeId)
    for obj in old.Objects:
        if obj.TypeId == 'App::DocumentObjectGroup':
            copied[obj.Name].Group = [copied[c.Name] for c in obj.Group]

    local = Part.read(str(candidate_path))
    assert local.isValid() and len(local.Solids) == 1
    left = local.copy()
    left.translate(V(*parameters['quote_origin_world_mm']))
    right = left.copy()
    right.rotate(V(90, 0, 0), V(0, 0, 1), 180)
    for side, shape in [('L', left), ('R', right)]:
        obj = doc.getObject('CustomMotorMount' + side)
        obj.Shape = shape
        obj.Label = candidate_id + ' CNC mount ' + side + ' | 15kg payload target, unqualified'
        obj.ModelNote = f"{candidate_id}: seat R{parameters['seat_small_corner_radius_mm']}, flange t{parameters['flange_thickness_mm']}, seat9, rear8. See amr06 strength review. Quotation candidate, not manufacturing release."
    changed = {'CustomMotorMountL', 'CustomMotorMountR'}
    # Stable A4 object IDs remain, while labels and actual placements change.
    # This keeps the rest of the hardware inventory traceable to A4.
    new_xs = sorted(h['center_world_xy_mm'][0] for h in parameters['holes']['frame'])
    flange_bottom = 69 - parameters['flange_thickness_mm']
    for previous_x, new_x in zip((52.5, 127.5), new_xs):
        tag = str(previous_x).replace('.', 'p')
        for side, sign in [('L', 1), ('R', -1)]:
            for prefix, dz in [('MountFrameBolt_', flange_bottom - 64), ('SlotNut_Mount_', 0)]:
                name = prefix + tag + side
                obj = doc.getObject(name)
                delta = V(sign * (new_x - previous_x), 0, dz)
                if delta.Length > 1e-9:
                    shape = obj.Shape.copy()
                    shape.translate(delta)
                    obj.Shape = shape
                    obj.Label = obj.HardwareSpec + ' | ' + side + f' X={90 + sign*(new_x-90):g}'
                    changed.add(name)
    doc.recompute()

    parts = [o for o in doc.Objects if o.TypeId == 'PartDesign::Feature' and o.MaterialBasis != 'reference']
    references = [o for o in doc.Objects if o.TypeId == 'PartDesign::Feature' and o.MaterialBasis == 'reference']
    assert len(parts) == 161
    assert not [o.Name for o in parts + references if not o.Shape.isValid() or o.Shape.isNull()]
    unchanged = [o for o in parts + references if o.Name not in changed]
    for obj in unchanged:
        previous = old.getObject(obj.Name)
        # OCC isEqual also compares topology identity, which copyObject may
        # replace. Compare serialized geometry, with a volume check fallback.
        if obj.Shape.exportBrepToString() != previous.Shape.exportBrepToString():
            error = obj.Shape.cut(previous.Shape).Volume + previous.Shape.cut(obj.Shape).Volume
            assert error < .001, (obj.Name, error)
    bounds = {o.Name: o.Shape.optimalBoundingBox(False, False) for o in parts + references}
    collisions, boolean_count = [], 0
    for a, b in combinations(parts, 2):
        if bounds[a.Name].intersect(bounds[b.Name]):
            boolean_count += 1
            volume = a.Shape.common(b.Shape).Volume
            if volume > .001:
                collisions.append({'a': a.Name, 'b': b.Name, 'overlap_mm3': volume})
    reference_hits = []
    for reference in references:
        for obj in parts:
            if bounds[reference.Name].intersect(bounds[obj.Name]):
                volume = reference.Shape.common(obj.Shape).Volume
                if volume > .001:
                    reference_hits.append({'reference': reference.Name, 'part': obj.Name, 'overlap_mm3': volume})

    access = []
    def check(name, shape, exclude=()):
        box = shape.optimalBoundingBox(False, False)
        hits = []
        for obj in parts:
            if obj.Name in exclude or not box.intersect(bounds[obj.Name]):
                continue
            volume = shape.common(obj.Shape).Volume
            if volume > .001:
                hits.append({'part': obj.Name, 'overlap_mm3': volume})
        access.append({'name': name, 'hits': hits})

    for side, sign in [('L', 1), ('R', -1)]:
        for i, (x, z) in enumerate([(90, 57.95), (83.41820693, 46.55), (96.58179307, 46.55)]):
            check('M2p5_driver_' + side + str(i), Part.makeCylinder(2, 30, V(x, sign * 127.5, z), V(0, -sign, 0)), ['MotorFaceBolt_' + str(i) + side])
        for x in new_xs:
            check('M6_driver_' + side + str(x), Part.makeCylinder(4, 40, V(x, sign * 135, flange_bottom - 6), V(0, 0, -1)))
        for travel in (1, 5, 10, 20, 40, 80):
            tire = doc.getObject('Tire' + side).Shape.copy()
            tire.translate(V(0, sign * travel, 0))
            check('tire_outboard_' + side + str(travel), tire, ['Tire' + side, 'TireCover' + side])

    electrical_path = PREVIOUS / 'AMR01_ElectricalLayout_A4.FCStd'
    electrical = App.openDocument(str(electrical_path))
    harness_hits = []
    for side in ('L', 'R'):
        wire = electrical.getObject('Route_M0601FixedHarness' + side).Shape
        volume = wire.common(doc.getObject('CustomMotorMount' + side).Shape).Volume
        if volume > .001:
            harness_hits.append({'side': side, 'overlap_mm3': volume})
    same_part = left.copy()
    same_part.rotate(V(90, 0, 0), V(0, 0, 1), 180)
    same_part_error = same_part.cut(right).Volume + right.cut(same_part).Volume
    root_faces = [f for f in left.Faces if isinstance(f.Surface, Part.Cylinder)
                  and abs(f.Surface.Radius-2) < 1e-6 and abs(f.Surface.Axis.x) > .999
                  and f.BoundBox.ZMin >= flange_bottom-2-1e-6
                  and f.BoundBox.ZMax <= flange_bottom+1e-6]
    upper_head_root_gap = (doc.getObject('MotorFaceBolt_0L').Shape.distToShape(Part.makeCompound(root_faces))[0]
                           if root_faces else None)
    contacts = {n: bounds[n].ZMin for n in ('TireL', 'TireR', 'CasterTire')}
    frame_gap = {side: doc.getObject('CustomMotorMount' + side).Shape.distToShape(doc.getObject(rail).Shape)[0]
                 for side, rail in [('L', 'Rail400_4'), ('R', 'Rail400_1')]}
    all_box = Part.makeCompound([o.Shape for o in parts]).optimalBoundingBox(False, False)
    previous_validation = json.loads((PREVIOUS / 'validation_results.json').read_text())
    mass_change = sum((doc.getObject('CustomMotorMount' + side).Shape.Volume - old.getObject('CustomMotorMount' + side).Shape.Volume) * 2.70e-6 for side in ('L', 'R'))
    report = {
        'status': 'nominal_geometry_only_load_and_fit_qualification_pending',
        'source_A4_sha256': old_hash, 'candidate_id': candidate_id, 'candidate_STEP_sha256': digest(candidate_path),
        'changed_feature_ids': sorted(changed),
        'physical_parts': len(parts), 'unchanged_physical_and_reference_features': len(unchanged),
        'physical_pair_count': len(parts) * (len(parts) - 1) // 2,
        'bounding_box_candidate_boolean_count': boolean_count,
        'collisions': collisions, 'reserved_battery_collisions': reference_hits,
        'tool_and_tire_access': access, 'existing_harness_envelope_collisions': harness_hits,
        'same_part_rotation_difference_mm3': same_part_error,
        'wheel_and_caster_floor_contacts_z_mm': contacts,
        'direct_3030_face_gap_mm': frame_gap,
        'assembly_bounds_mm': [all_box.XLength, all_box.YLength, all_box.ZLength],
        'mount_bottom_z_mm': bounds['CustomMotorMountL'].ZMin,
        'mass_change_kg': mass_change,
        'mount_flange_thickness_mm': parameters['flange_thickness_mm'],
        'mount_frame_bolt_pitch_mm': parameters['frame_hole_pitch_mm'],
        'upper_motor_screw_to_long_root_surface_minimum_mm': upper_head_root_gap,
        'M6x12_nominal_tip_z_mm': flange_bottom + 12,
        'slot_nut_nominal_z_mm': [71,75],
        'screw_thread_engagement_caveat': 'Unthreaded envelopes only. Actual lead-in, incomplete threads, nut geometry and tolerance need checking.',
        'estimated_base_mass_kg': previous_validation['mass']['estimated_complete_base_kg'] + mass_change,
        'scope': 'Nominal unsqueezed tires; unchanged assumed tire axial datum and electrical reservations from A4. No tolerance, load, wear, contact/preload, thermal or physical assembly certification. Tool shafts only; tire removal sampled at six distances. New payload deck is not designed by this mount change.',
    }
    (HERE / 'assembly_validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    assert not collisions and not reference_hits and not harness_hits
    assert all(not c['hits'] for c in access)
    assert all(abs(z) < 1e-6 for z in contacts.values())
    assert all(abs(gap) < 1e-6 for gap in frame_gap.values())
    assert same_part_error < .001
    doc.saveAs(str(HERE / (NAME + '.FCStd')))
    Part.export(parts, str(HERE / (NAME + '.step')))
    restored = Part.read(str(HERE / (NAME + '.step')))
    native_volume = sum(o.Shape.Volume for o in parts)
    difference = restored.Volume - native_volume
    assert restored.isValid() and len(restored.Solids) == sum(len(o.Shape.Solids) for o in parts)
    assert abs(difference) < 1 and abs(difference) / native_volume < 1e-6
    report['STEP_roundtrip'] = {'valid': True, 'solids': len(restored.Solids), 'volume_difference_mm3': difference}
    assert digest(old_path) == old_hash
    (HERE / 'assembly_validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'tool_and_tire_access'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
