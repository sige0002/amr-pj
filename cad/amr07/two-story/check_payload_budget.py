"""Separate vehicle mass margin from cargo capacity after D6.2 floor reinforcement.

Uses existing accepted flat-floor requirements and the saved CAD mass ledger.
No payload increase, operating qualification or low-speed thermal rating is
inferred from a favorable torque/catalog-load comparison.
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sys.path.insert(0, str(BASE))
from calculate_design import envelope, torque

v = json.loads((HERE/'validation.json').read_text())
raw = (BASE/'requirements.json').read_bytes()
requirements = json.loads(raw)
loads = json.loads((BASE/'load_calculations.json').read_text())
caster = json.loads((BASE/'caster_load_check.json').read_text())
before_revision = 'feab761c8073f468b3668fac1b18b88a18fa6ba7'
before = json.loads(subprocess.check_output([
    'git', '-C', str(HERE), 'show',
    before_revision+':cad/amr07/two-story/validation.json']))
mass = v['mass']['estimated_base_kg']
payload = requirements['mass']['normal_payload_kg']
limit = requirements['mass']['base_max_kg']
assert payload == 10 and mass <= limit
assert requirements['mass']['base_target_is_hard_limit'] is False
assert loads['requirements_sha256'] == caster['requirements_sha256'] == hashlib.sha256(raw).hexdigest()

comparisons = []
for label, base_mass in [('D3', v['mass']['source_D3_kg']),
                         ('D6.1', before['mass']['estimated_base_kg']),
                         ('D6.2', mass), ('design_upper_bound', limit)]:
    config = deepcopy(requirements)
    config['mass']['base_max_kg'] = base_mass
    sized = torque(config, payload, 0)
    comparisons.append(dict(revision=label, base_mass_kg=base_mass, **sized))

actual = deepcopy(requirements)
actual['mass']['base_max_kg'] = mass
actual['load_placement']['reviewed_base_mass_interval_kg'] = [mass, mass]
normal_case = next(c for c in requirements['cases'] if c['id'] == 'normal')
actual_load = envelope(actual, normal_case)
budget_load = next(c for c in loads['load_cases'] if c['id'] == 'normal')
assert actual_load['conservative_radial_comparison_N'] <= budget_load['conservative_radial_comparison_N']

delta_groups = {'upper_rails_posts_joints': 0., 'battery_and_adapter': 0.,
                'equipment_belts_and_pads': 0., 'floor_cradles_and_other_geometry_net': 0.}
for entry in v['cg_difference']['ledger']:
    name = entry['name']
    if name.startswith(('add Upright3030_', 'add UpperRail3030_', 'add Level')):
        key = 'upper_rails_posts_joints'
    elif name in ['remove old battery budget', 'BatteryBL1860B', 'BatteryAdapter03']:
        key = 'battery_and_adapter'
    elif name in ['battery full125g belt plus25g pads', 'PC and supervisor belts/pads']:
        key = 'equipment_belts_and_pads'
    else:
        key = 'floor_cradles_and_other_geometry_net'
    delta_groups[key] += entry['mass_kg']
assert abs(sum(delta_groups.values())-(mass-v['mass']['source_D3_kg'])) < 1e-8
deck_mass = next(e['mass_kg'] for e in v['cg_difference']['ledger']
                 if e['name'] == 'new position AluminumDeckD3')
components = dict(aluminum_cargo_plate=deck_mass,
                  upper_rails_posts_joints=v['mass']['upper_structure_metal_and_hardware_kg'],
                  new_floor_hardware=v['mass']['floor_added_hardware_kg'],
                  all_PLA=v['mass']['total_solid_PLA_kg'],
                  battery_adapter_and_other_electrical=v['mass']['electrical_total_kg'],
                  cargo_belts_and_edge_pads=.28,
                  equipment_belts_and_pads=v['mass']['new_straps_and_pads_allowance_kg'])
components['retained_lower_structure_drive_and_hardware'] = mass-sum(components.values())
assert abs(sum(components.values())-mass) < 1e-9

out = dict(
    revision=v['parameters']['revision'], date='2026-09-22',
    requirements_sha256=hashlib.sha256(raw).hexdigest(),
    baseline_D61_commit=before_revision,
    vehicle_mass_estimate_kg=mass, reviewed_vehicle_mass_upper_bound_kg=limit,
    vehicle_mass_target_kg=10, vehicle_mass_target_is_hard_limit=False,
    remaining_to_reviewed_envelope_kg=limit-mass,
    mass_above_soft_10kg_target_kg=max(0,mass-10),
    normal_cargo_design_target_kg=payload,
    normal_gross_at_estimate_kg=mass+payload,
    normal_gross_reviewed_upper_bound_kg=limit+payload,
    structural_cargo_comparison_kg=requirements['mass']['structural_payload_kg'],
    structural_scope='15kg cargo/25.5kg gross is a static structural comparison, not an operating cargo rating.',
    mass_components_kg=components,
    net_increase_from_D3_kg=delta_groups,
    floor_reinforcement_increase_from_D61_kg=mass-before['mass']['estimated_base_kg'],
    same_cargo_torque_comparisons=comparisons,
    torque_comparison_basis=dict(
        rolling_resistance_assumption=requirements['drive']['rolling_resistance_assumption'],
        acceleration_m_s2=requirements['drive']['acceleration_and_service_deceleration_max_m_s2'],
        sizing_multiplier=requirements['drive']['continuous_torque_sizing_margin'],
        wheel_diameter_mm=requirements['geometry']['wheel_diameter_mm'],
        scope='Two motors share longitudinal force equally, flat smooth floor; caster swivel breakaway, scrubbing, rotational inertia, thermal behavior and uneven drive-force sharing are not modeled.'),
    normal_reactions_at_estimated_mass=actual_load,
    motor_load_comparison_at_reviewed_vehicle_mass=dict(
        radial_N=budget_load['conservative_radial_comparison_N'],
        catalog_radial_N=requirements['catalog_comparison_only']['motor_radial_N'],
        axial_N=budget_load['conservative_axial_comparison_N'],
        catalog_axial_N=requirements['catalog_comparison_only']['motor_axial_N']),
    caster_normal_maximum_with_trail_tolerance_N=max(
        c['maximum_reaction_N'] for c in caster['cases'] if c['case']=='normal'),
    caster_catalog_allowable_N=requirements['catalog_comparison_only']['caster_allowable_N'],
    source='https://shop.directdrive.com/pages/m0601c-111-specs',
    source_checked_date='2026-09-22',
    payload_target_reduced=False,
    extra_vehicle_equipment_policy='Battery, computer, cases, sensors and any future arm are vehicle mass.10kg is a soft target; additions require a new measured mass/CG and wheel-load check. Cargo target stays10kg.',
    mass_estimate_limitations=['Vehicle not weighed; computer0.5kg and other electrical items are budgets, not a fully selected/measured assembly.',
        'The10.5kg calculation envelope is a review assumption, not a new strict user weight limit or a measured uncertainty bound.',
        'Accepted reinforcement is retained. Do not remove required joints merely to meet the mass number.'],
    assembly_strength_and_operation_qualified=False)
(HERE/'payload_budget.json').write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n')
print(json.dumps(dict(vehicle_mass_kg=mass,normal_cargo_kg=payload,
                     gross_kg=mass+payload,vehicle_headroom_kg=limit-mass,
                     torque_each_with_margin_Nm=comparisons[2]['with_margin_Nm_each'],
                     load_comparison_at_reviewed_gross=out['motor_load_comparison_at_reviewed_vehicle_mass']),ensure_ascii=False))
