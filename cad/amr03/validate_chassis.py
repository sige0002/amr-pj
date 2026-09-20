"""A2 nominal CAD / inventory / mass checks. Run inside FreeCAD after build.
This is not a component load rating, tolerance study or fabrication release.
"""
from pathlib import Path
from itertools import combinations
from collections import defaultdict
import csv
import json
import math
import FreeCAD as App
import Part
import Mesh

HERE = Path(__file__).resolve().parent
cfg = json.loads((HERE / 'design_parameters.json').read_text())
doc = App.getDocument('AMR01_Revision_A2')
parts = [o for o in doc.Objects if o.TypeId == 'PartDesign::Feature' and o.MaterialBasis != 'reference']
reference = doc.getObject('BatteryReservedSpace')
fasteners = set(doc.getObject('_07_Fasteners').Group)
bounds = {o.Name: o.Shape.optimalBoundingBox(False, False) for o in parts + [reference]}
collisions, boolean_count = [], 0
for a, b in combinations(parts, 2):
    if bounds[a.Name].intersect(bounds[b.Name]):
        boolean_count += 1
        overlap = a.Shape.common(b.Shape).Volume
        if overlap > .001:
            collisions.append({'a': a.Name, 'b': b.Name, 'mm3': overlap})
reference_hits = []
for o in parts:
    if bounds[reference.Name].intersect(bounds[o.Name]):
        overlap = reference.Shape.common(o.Shape).Volume
        if overlap > .001:
            reference_hits.append({'part': o.Name, 'mm3': overlap})
bb = Part.makeCompound([o.Shape for o in parts]).optimalBoundingBox(False, False)
frames = [o for o in parts if o.Name.startswith(('Rail400_', 'Cross300_'))]
fb = Part.makeCompound([o.Shape for o in frames]).optimalBoundingBox(False, False)
ground = {n: bounds[n].ZMin for n in ('TireL', 'TireR', 'CasterTire')}
fixed = [o for o in parts if not o.Name.startswith(('Caster', 'Swivel', 'Tire', 'WheelMetal'))]
lowest = min(fixed, key=lambda o: bounds[o.Name].ZMin)
clearance_pairs = [('MotorAngleL', 'GearboxL'), ('GearboxL', 'Rail400_3'),
                   ('GearboxL', 'BearingPlateL'), ('EncoderL', 'EncoderR'),
                   ('Rail400_4', 'TireL'), ('HubBolt_0L', 'Collar_2L'),
                   ('CouplerL', 'KP08_1L'), ('Collar_2L', 'KP08_2L'),
                   ('MotorFaceBolt_1L', 'MotorAngleL')]
clearances = [{'a': a, 'b': b, 'mm': doc.getObject(a).Shape.distToShape(doc.getObject(b).Shape)[0]}
              for a, b in clearance_pairs]
# Mating faces have zero distance; above pairs also include intended contact.
direct_mount = {}
for name, rails in [('BearingPlateL', ['Rail400_3', 'Rail400_4']),
                    ('BearingPlateR', ['Rail400_1', 'Rail400_2']),
                    ('CasterAdapter', ['Rail400_2', 'Rail400_3']),
                    ('BatteryCradlePLA', ['Rail400_2', 'Rail400_3'])]:
    direct_mount[name] = {r: doc.getObject(name).Shape.distToShape(doc.getObject(r).Shape)[0] for r in rails}
assert all(abs(d) < 1e-6 for matches in direct_mount.values() for d in matches.values())
assert not any(o.Name.startswith(('Post_', 'CasterSpacer', 'Belt', 'ForkBridge', 'ForkOuterWall')) for o in parts)

# Catalog masses replace envelope volumes for purchased assemblies.
mass = [
    {'part': 'NFSL6-3030 2.2 m', 'kg': 1.672, 'basis': 'manufacturer 0.76 kg/m'},
    {'part': 'FIT0185 x2', 'kg': .410, 'basis': 'manufacturer 205 g each'},
    {'part': '100mm wheel+tire x2', 'kg': .600, 'basis': 'seller reference 300 g each; unmeasured'},
    {'part': 'KP08 x4', 'kg': .148, 'basis': '37 g each supplier reference, inherited from A; adopted item unmeasured'},
    {'part': 'HBLFSN6 x8', 'kg': .120, 'basis': 'MISUMI official catalog 15 g each; bolts/nuts counted separately'},
    {'part': '420G-R50', 'kg': .150, 'basis': 'engineering allowance, not measured'},
    {'part': 'couplings x2', 'kg': .040, 'basis': '20 g each allowance'},
    {'part': 'unmodeled grub screws / retaining hardware', 'kg': .030, 'basis': 'allowance; modeled plain nuts counted separately'},
    {'part': 'battery retaining straps x2', 'kg': .040, 'basis': 'allowance; unselected and not modeled'},
]
skip_prefix = ('Rail400_', 'Cross300_', 'Bracket_', 'Gearbox', 'MotorCan', 'Encoder',
               'MotorShaft', 'KP08_', 'Coupler', 'WheelMetal', 'Tire')
skip_names = {'CasterTop', 'SwivelRace', 'CasterFork', 'CasterTire', 'CasterCore'}
rho = {'aluminum': 2.70e-6, 'steel': 7.85e-6, 'PLA': 1.24e-6}
for o in parts:
    if o.Name.startswith(skip_prefix) or o.Name in skip_names:
        continue
    mass.append({'part': o.Name, 'kg': o.Shape.Volume * rho[o.MaterialBasis],
                 'basis': 'CAD volume x ' + o.MaterialBasis + ' assumed density; threads omitted'})
mechanical = sum(i['kg'] for i in mass)
electrical = sum(cfg['mass_electrical_budget_kg'].values())

inventory = defaultdict(list)
for o in sorted(fasteners, key=lambda o: o.Name):
    if 'HardwareSpec' in o.PropertiesList:
        spec = o.HardwareSpec
    elif o.Name.startswith('LargeWasher_'):
        spec = 'M6 large washer OD18 ID6.6 t1.6'
    elif o.Name.startswith('Washer_'):
        spec = 'M6 washer OD13 ID6.6 t1.6'
    else:
        raise AssertionError('Uncounted hardware: ' + o.Name)
    inventory[spec].append(o.Name)
with (HERE / 'fasteners.csv').open('w', newline='') as f:
    writer = csv.writer(f, lineterminator='\n')
    writer.writerow(['specification', 'installed_quantity', 'included_in_HBLFSN6_SET',
                     'additional_installed_quantity', 'model_object_names'])
    for spec, names in sorted(inventory.items()):
        included = 16 if spec in ('M6x12 socket screw', 'HNTT6-6 slot nut') else 0
        writer.writerow([spec, len(names), included, len(names)-included, ';'.join(names)])

printed = []
for name in ('BatteryCradlePLA', 'ElectronicsTrayPLA'):
    mesh = Mesh.Mesh(str(HERE / (name + '.stl')))
    box = mesh.BoundBox
    dims = [box.XLength, box.YLength, box.ZLength]
    printed.append({'file': name + '.stl', 'dimensions_mm': dims, 'watertight': mesh.isSolid(),
                    'fits_P1S_256_cube': all(d <= 256 for d in dims), 'quantity': 1,
                    'solid_PLA_mass_kg': doc.getObject(name).Shape.Volume * rho['PLA']})

rotating_names = {'SwivelRace', 'CasterFork', 'CasterTire', 'CasterCore'}
caster_shape = Part.makeCompound([doc.getObject(n).Shape for n in rotating_names])
sweep_targets = [o for o in parts if o.Name not in rotating_names and bounds[o.Name].ZMin < 62.5-1e-6
                 and bounds[o.Name].XMin < -105 and bounds[o.Name].XMax > -195
                 and bounds[o.Name].YMin < 45 and bounds[o.Name].YMax > -45]
sweep_hits = []
for angle in range(0, 360, 5):
    rotated = caster_shape.copy()
    rotated.rotate(App.Vector(-150, 0, 0), App.Vector(0, 0, 1), angle)
    rb = rotated.optimalBoundingBox(False, False)
    for o in sweep_targets:
        if rb.intersect(bounds[o.Name]) and rotated.common(o.Shape).Volume > .001:
            sweep_hits.append({'angle_deg': angle, 'part': o.Name})

step = Part.Shape()
step.read(str(HERE / 'AMR01_Revision_A2.step'))
native_volume = sum(o.Shape.Volume for o in parts)
step_check = {'is_valid': step.isValid(), 'solid_count': len(step.Solids),
              'native_solid_count': sum(len(o.Shape.Solids) for o in parts),
              'volume_difference_mm3': step.Volume-native_volume,
              'reference_battery_excluded': True}
result = {
    'status': 'nominal_geometry_checks_only_not_manufacturing_release',
    'part_objects': len(parts), 'reference_objects': 1, 'fastener_objects': len(fasteners),
    'invalid_shapes': [o.Name for o in parts+[reference] if not o.Shape.isValid() or o.Shape.isNull()],
    'all_part_pair_count': len(parts)*(len(parts)-1)//2,
    'bounding_box_candidate_boolean_count': boolean_count,
    'all_part_collisions': collisions, 'battery_reserved_space_collisions': reference_hits,
    'collision_scope': 'All modeled physical pairs including screws/nuts. >0.001 mm3 threshold. Battery keepout separately checked against all physical parts. Nominal thread-free shapes; not tolerance/tool/deformation/cable verification.',
    'frame_LWH_mm': [fb.XLength, fb.YLength, fb.ZLength],
    'frame_bottom_top_z_mm': [fb.ZMin, fb.ZMax],
    'assembled_mechanical_LWH_mm': [bb.XLength, bb.YLength, bb.ZLength],
    'direct_mount_face_gap_mm': direct_mount, 'drive_mount_spacers': 0, 'caster_mount_spacers': 0,
    'ground_contacts_z_mm': ground,
    'minimum_fixed_nonwheel_clearance_mm': bounds[lowest.Name].ZMin, 'lowest_component': lowest.Name,
    'drive_track_mm': bounds['TireL'].Center.y-bounds['TireR'].Center.y,
    'clearances': clearances, 'caster_sweep_fixed_hits': sweep_hits,
    'caster_sweep_scope': '72 nominal orientations at 5 degree spacing against nearby fixed parts including fasteners; not continuous/tolerance proof.',
    'shaft_interfaces_mm': {'shaft_length': 100, 'motor_shaft_in_coupler': 11,
                            'wheel_shaft_in_coupler': 12, 'shaft_end_gap_in_coupler': 2,
                            'coupler_to_inner_bearing_housing': 1.5, 'bearing_span': 27,
                            'wheel_overhang': 32,
                            'note': 'Same shaft placement as A. Internal clamping/set-screw positions and minimum coupling insertion need received-part confirmation.'},
    'motor_M3_thread_engagement_mm': 2, 'motor_M3_max_engagement_mm': 3,
    'motor_angle_inside_radius_modeled_mm': 3,
    'hardware_installed': {k: len(v) for k, v in sorted(inventory.items())},
    'printed_parts': printed, 'step_roundtrip': step_check,
    'mass': {'mechanical_estimate_kg': mechanical, 'additional_electrical_budget_kg': electrical,
             'estimated_complete_base_kg': mechanical+electrical, 'base_upper_budget_kg': 10,
             'remaining_budget_kg': 10-mechanical-electrical, 'within_upper_budget': mechanical+electrical <= 10,
             'note': 'Estimate, not measured. PLA modeled solid. Equipment/guards budget does not establish fit; battery reference geometry is not counted as a purchased part.',
             'breakdown': mass},
    'unverified': cfg['unverified'] + ['Inverted KP08 retaining capacity, bolt clamping/load path, slot-joint slip and aluminum plate bending',
         'Nominal R3 inside angle fillet is included; actual radius and motor bolt access remain to be checked',
         'Battery straps are a cost/mass allowance; exact routing and product are not modeled',
         'PLA clamped flanges can creep; washer loads, temperature and retention need testing'],
}
assert not result['invalid_shapes'] and not collisions and not reference_hits
assert all(a <= b+1e-6 for a, b in zip(result['assembled_mechanical_LWH_mm'], cfg['requirements']['body_envelope_target_mm']))
assert all(abs(z) < 1e-6 for z in ground.values())
assert bounds[lowest.Name].ZMin >= cfg['requirements']['minimum_ground_clearance_mm']-1e-6
assert not sweep_hits, sweep_hits
assert all(p['watertight'] and p['fits_P1S_256_cube'] for p in printed)
assert sum(p['solid_PLA_mass_kg'] for p in printed) <= .250
assert len(inventory['HNTT6-6 slot nut']) == 44
assert len(inventory['M4x16 countersunk screw (overall length)']) == 8
assert len(inventory['M4x12 countersunk screw (overall length)']) == 4
assert math.isclose(result['drive_track_mm'], cfg['geometry']['drive_track_mm'])
assert math.isclose(fb.XLength, 460) and math.isclose(fb.YLength, 300)
assert math.isclose(fb.ZMin, 69) and math.isclose(fb.ZMax, 99)
assert math.isclose(bounds['WheelShaftL'].YMin, 97) and math.isclose(bounds['WheelShaftL'].YMax, 197)
assert step_check['is_valid'] and step_check['solid_count'] == step_check['native_solid_count']
assert abs(step_check['volume_difference_mm3']) < .01
assert result['mass']['within_upper_budget']
(HERE / 'validation_results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({k: v for k, v in result.items() if k not in ('mass', 'unverified')}, ensure_ascii=False))
print(json.dumps({k: v for k, v in result['mass'].items() if k != 'breakdown'}, ensure_ascii=False))
