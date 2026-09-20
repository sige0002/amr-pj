"""Run in FreeCAD after build_chassis.py; exports checks, not a safety rating."""
from pathlib import Path
from itertools import combinations
import json
import math
import FreeCAD as App
import Part

HERE = Path(__file__).resolve().parent
root = HERE.parents[1]
cfg = json.loads((root / 'docs/amr-01/design_parameters.json').read_text())
mech = json.loads((HERE / 'mechanical_parameters.json').read_text())
doc = App.getDocument('AMR01_FirstDesign_A')
parts = [o for o in doc.Objects if o.TypeId == 'PartDesign::Feature']
fasteners = set(doc.getObject('_06_Fasteners').Group)
primary = [o for o in parts if o not in fasteners]
collisions = []
tested = 0
for a, b in combinations(primary, 2):
    tested += 1
    if a.Shape.optimalBoundingBox(False, False).intersect(b.Shape.optimalBoundingBox(False, False)):
        vol = a.Shape.common(b.Shape).Volume
        if vol > .001:
            collisions.append({'a': a.Name, 'b': b.Name, 'overlap_mm3': vol})
ground_names = ['TireL', 'TireR', 'CasterTire']
ground = {name: doc.getObject(name).Shape.optimalBoundingBox(False, False).ZMin for name in ground_names}
fixed = [o for o in parts if not o.Name.startswith(('Caster', 'Swivel', 'Tire', 'WheelMetal'))]
lowest = min(fixed, key=lambda o: o.Shape.optimalBoundingBox(False, False).ZMin)
bb = Part.makeCompound([o.Shape for o in parts]).optimalBoundingBox(False, False)
frames = [o for o in parts if o.Name.startswith(('Rail400_', 'Cross300_'))]
fb = Part.makeCompound([o.Shape for o in frames]).optimalBoundingBox(False, False)
initial_rpm = (cfg['drive']['initial_speed_m_s'] + cfg['drive']['initial_yaw_rate_rad_s'] * cfg['geometry']['drive_track_mm']/2000) / (math.pi * .1) * 60
later_rpm = (cfg['drive']['later_speed_limit_m_s'] + cfg['drive']['later_yaw_rate_limit_rad_s'] * cfg['geometry']['drive_track_mm']/2000) / (math.pi * .1) * 60
cap = mech['selected_motor']['planned_wheel_rpm_cap']
torque = json.loads((root / 'docs/amr-01/calculation_results.json').read_text())['drive']['wheel_torque_with_margin_Nm']
stall = mech['selected_motor']['stall_torque_kgfcm'] * 9.80665 / 100
motor = mech['selected_motor']
no_load = motor['no_load_rpm']

# Catalog masses override simplified hollow/solid geometry. Estimates are named.
mass = [
    {'part': 'NFSL6-3030 installed 2.2 m', 'kg': 1.672, 'basis': 'manufacturer 0.76 kg/m'},
    {'part': 'FIT0185 pair', 'kg': .410, 'basis': 'manufacturer 205 g each'},
    {'part': 'wheel+tire pair', 'kg': .600, 'basis': 'seller approximately 300 g each'},
    {'part': 'KP08 x4', 'kg': .148, 'basis': '37 g each reference KP08 supplier; selected vendor unmeasured'},
    {'part': '420G-R50', 'kg': .150, 'basis': 'engineering allowance, not a catalog mass'},
    {'part': 'corner angles x8', 'kg': .240, 'basis': '30 g each allowance; ribs omitted from CAD'},
    {'part': 'couplings x2', 'kg': .040, 'basis': '20 g each allowance'},
    {'part': 'plain nuts / remaining washers / grub screws', 'kg': .050, 'basis': 'unmodeled fastener allowance'}
]
excluded_prefix = ('Rail400_', 'Cross300_', 'Gearbox', 'MotorCan', 'Encoder', 'MotorShaft', 'KP08_', 'Angle_', 'Coupler', 'WheelMetal', 'Tire')
caster_bought = {'CasterTop', 'SwivelRace', 'CasterFork', 'CasterTire', 'CasterCore'}
for o in parts:
    if o.Name.startswith(excluded_prefix) or o.Name in caster_bought:
        continue
    steel = o in fasteners or o.Name.startswith(('WheelShaft', 'HubL', 'HubR'))
    rho = 7.85e-6 if steel else 2.70e-6
    mass.append({'part': o.Name, 'kg': o.Shape.Volume * rho, 'basis': 'simplified CAD volume x ' + ('steel' if steel else 'aluminum') + ' density'})
mechanical_kg = sum(i['kg'] for i in mass)
electrical_budget = sum(cfg['mass_estimate_kg'][k] for k in ('battery_and_adapter', 'power_conversion_protection_emergency_stop', 'onboard_compute_sensors_cooling', 'wiring_covers_handles'))
base_limit = cfg['requirements']['base_upper_budget_kg']

# Specific hardware clearance including fasteners omitted by primary pair scan.
wheel_fastener_gap = min(doc.getObject('Collar_2' + side).Shape.distToShape(doc.getObject('HubBolt_' + side + str(j)).Shape)[0] for side in ('L', 'R') for j in range(4))
clearance_pairs = [('MotorCanL', 'MotorCanR'), ('EncoderL', 'EncoderR'), ('CouplerL', 'MotorAngleL'), ('GearboxL', 'Rail400_3'), ('TireL', 'Rail400_4')]
clearances = [{'a': a, 'b': b, 'mm': doc.getObject(a).Shape.distToShape(doc.getObject(b).Shape)[0]} for a,b in clearance_pairs]
result = {
    'status': 'nominal_geometry_checks_only_not_manufacturing_release',
    'part_objects': len(parts),
    'invalid_shapes': [o.Name for o in parts if o.Shape.isNull() or not o.Shape.isValid()],
    'frame_LWH_mm': [fb.XLength, fb.YLength, fb.ZLength],
    'assembled_mechanical_LWH_mm': [bb.XLength, bb.YLength, bb.ZLength],
    'fits_500x400_plan': bb.XLength <= 500 and bb.YLength <= 400,
    'ground_contacts_z_mm': ground,
    'minimum_nonwheel_noncaster_clearance_mm': lowest.Shape.optimalBoundingBox(False, False).ZMin,
    'lowest_component': lowest.Name,
    'primary_pair_count': tested,
    'primary_collisions': collisions,
    'clearance_scan_scope': '67 primary nominal objects; fasteners excluded except specific wheel-head check. Not tolerance, swept caster, deformation or cable clearance certification.',
    'wheel_hub_bolt_to_collar_min_gap_mm': wheel_fastener_gap,
    'selected_clearances': clearances,
    'motor_M3_thread_engagement_mm': 2,
    'motor_M3_max_engagement_mm': 3,
    'drive': {
        'sizing_gross_mass_kg': cfg['requirements']['gross_mass_calculation_limit_kg'],
        'initial_simultaneous_outer_rpm': initial_rpm,
        'later_simultaneous_outer_rpm': later_rpm,
        'command_rpm_cap_not_rating': cap,
        'initial_command_below_cap': initial_rpm < cap,
        'later_simultaneous_command_below_cap': later_rpm < cap,
        'max_abs_v_plus_half_track_abs_omega_m_s': cap/60 * math.pi*.1,
        'max_yaw_at_v_0p3_rad_s': (cap/60 * math.pi*.1-.3)/(cfg['geometry']['drive_track_mm']/2000),
        'sizing_wheel_torque_with_margin_Nm': torque,
        'stall_torque_Nm_NOT_CONTINUOUS': stall,
        'linear_estimated_rpm_at_sizing_torque_NOT_RATING': no_load * (1 - torque/stall),
        'linear_estimated_rpm_with_low_no_load_tolerance_NOT_RATING': no_load * (1 - motor['no_load_rpm_tolerance_fraction']) * (1 - torque/stall),
        'linear_estimated_current_A_NOT_RATING': motor['no_load_current_A']+(motor['stall_current_A']-motor['no_load_current_A'])*torque/stall,
        'continuous_torque_verified': False
    },
    'mass': {
        'mechanical_estimate_kg': mechanical_kg,
        'additional_electrical_wiring_guard_budget_kg': electrical_budget,
        'estimated_base_with_electrical_budget_kg': mechanical_kg + electrical_budget,
        'base_upper_budget_kg': base_limit,
        'remaining_after_mechanical_only_kg': base_limit - mechanical_kg,
        'remaining_after_electrical_budget_kg': base_limit - mechanical_kg - electrical_budget,
        'estimated_over_upper_budget_kg': max(0, mechanical_kg + electrical_budget - base_limit),
        'estimated_base_within_upper_budget': mechanical_kg + electrical_budget <= base_limit,
        'note': 'User revised the base limit to 10 kg including battery and electronics. Estimate, not scale measurement. All stability CG positions remain hypothetical, including the 6.78 kg estimate and 10 kg upper-limit cases.',
        'breakdown': mass
    },
    'unverified_interfaces': mech['unverified_interfaces']
}
assert not result['invalid_shapes']
assert not collisions, collisions
assert result['fits_500x400_plan']
assert all(abs(z) < 1e-6 for z in ground.values())
assert lowest.Shape.optimalBoundingBox(False, False).ZMin >= cfg['geometry']['minimum_ground_clearance_target_mm']
assert wheel_fastener_gap > .5
assert math.isclose(mechanical_kg, cfg['mass_estimate_kg']['mechanical_chassis'], abs_tol=.005), 'Update the rounded mechanical mass estimate in design_parameters.json'
assert len([o for o in parts if o.Name.startswith('SlotNut_')]) == 40
assert math.isclose(fb.XLength, cfg['geometry']['frame_length_mm'])
assert math.isclose(fb.YLength, cfg['geometry']['frame_width_mm'])
assert math.isclose(doc.getObject('TireL').Shape.optimalBoundingBox(False, False).XLength, cfg['geometry']['wheel_diameter_mm'])
assert math.isclose(doc.getObject('TireL').Shape.optimalBoundingBox(False, False).Center.y - doc.getObject('TireR').Shape.optimalBoundingBox(False, False).Center.y, cfg['geometry']['drive_track_mm'])
bom = json.loads((HERE/'bom.json').read_text())
counts = {'F01': 'Rail400_', 'F02': 'Cross300_', 'F03': 'Angle_', 'D01': 'Gearbox', 'D02': 'Tire', 'D03': 'HubL|HubR', 'D04': 'WheelShaft', 'D05': 'KP08_', 'D06': 'Coupler', 'D07': 'Collar_', 'C01': 'CasterTop'}
for item in bom['items']:
    if item['id'] in counts:
        prefixes = tuple(counts[item['id']].split('|'))
        assert sum(o.Name.startswith(prefixes) for o in parts) == item['used'], item['id']
(HERE/'validation_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('mass','unverified_interfaces')},ensure_ascii=False))
print(json.dumps({k:v for k,v in result['mass'].items() if k!='breakdown'},ensure_ascii=False))
