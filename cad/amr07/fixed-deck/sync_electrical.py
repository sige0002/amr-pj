"""Bring shared electrical requirements to the current CAD/load/price revision."""
from pathlib import Path
from copy import deepcopy
import json, hashlib

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
p=BASE/'electrical_plan.json'
e=json.loads(p.read_text())
v=json.loads((HERE/'payload_budget.json').read_text())
if 'D65_calculations' not in e['reference_only']:
    e['reference_only']['D65_calculations']=deepcopy(e['calculations'])
    e['reference_only']['D65_candidate_price_subtotal_JPY']=e['cost']['priced_purchase_subtotal_jpy_incl_tax']
e.update(design='AMR01_FixedDeck_D69',date='2026-09-23',requirements_file='fixed-deck/requirements.json')
e['power']['positive_path']=['battery','adapter_manual_switch_if_present','F0_near_source',
    'rear_main_connector','main_switch_amon3214','independent_latching_UV_temperature_disconnect',
    'Fdrv','D0','K1_NO','K2_NO','MOTOR_BUS','FL_or_FR','motor']
e['power']['main_manual_switch']=dict(part='amon3214',DC24V_catalog_A=10,
    inrush_and_transient_qualification_complete=False,source='https://www.amon.jp/products2/detail.php?product_code=3214')
for part in e['candidate_parts']:
    if part['id']=='S1':
        part.update(purchase_price_jpy_incl_tax=3153,source='https://www.amazon.co.jp/dp/B077Y8DN8G')
    if part['id']=='U1':
        part.update(part_number='Raspberry Pi Pico, user-owned; variant and headers unconfirmed',
            purchased_quantity=0,purchase_price_jpy_incl_tax=0,source=None,status='user_owned_variant_unconfirmed')
        part['note']='Confirm variant, pin headers and supply interface before PCB pinout; USB lead remains separately budgeted.'
for id,number,price,url,note in [
    ('S_ARM','amon3212',835,'https://www.amazon.co.jp/dp/B075SQ41JN','Momentary NO; new press needed after fault recovery.'),
    ('S_MAIN','amon3214',621,'https://www.amazon.co.jp/dp/B075SW22KP','Manual all-load switch; DC24V10A catalog, actual motor/DC-DC inrush unqualified.')]:
    if not any(x['id']==id for x in e['candidate_parts']):
        e['candidate_parts'].append(dict(id=id,part_number=number,used_quantity=1,purchased_quantity=1,
            purchase_price_jpy_incl_tax=price,source=url,note=note,status='selected_not_purchased'))
policy_path = BASE/'electrical-buildability/requirements.json'
policy = json.loads(policy_path.read_text())
withdrawn_ids = {x.removeprefix('ELEC_') for x in policy['withdrawn_BOM_ids']}
old_candidates = e['reference_only'].setdefault('E1_withdrawn_candidates', [])
for part in e['candidate_parts']:
    if part['id'] in withdrawn_ids and not any(x['id'] == part['id'] for x in old_candidates):
        old_candidates.append(deepcopy(part))
e['candidate_parts'] = [x for x in e['candidate_parts'] if x['id'] not in withdrawn_ids]
for part in e['candidate_parts']:
    if part['id'] == 'U1':
        part['note'] = 'User owns Pico, but variant and headers are unconfirmed. Do not require user soldering. This is not a complete controller.'
    elif part['id'] in ['S_ARM', 'S_MAIN']:
        part['status'] = 'mechanical_candidate_wiring_not_designed'
e['status'] = 'custom_PCB_recommendation_withdrawn_assembled_replacement_not_designed'
e['manufacturing_requirements_file'] = 'electrical-buildability/requirements.json'
e['manufacturing_requirements_sha256'] = hashlib.sha256(policy_path.read_bytes()).hexdigest()
e['implementation_disposition'] = 'power/restart_and_watchdog/control/regeneration retain the withdrawn implementation proposal for comparison; none is a complete or released wiring design. Required functions are in manufacturing_requirements_file.'
for key in ['power', 'restart_and_watchdog', 'control', 'regeneration']:
    e[key]['implementation_status'] = 'withdrawn_legacy_custom_circuit_proposal'
e['operation_release']['wiring_diagram_complete'] = False
e['operation_release']['replacement_electrical_BOM_complete'] = False
e['cost']['priced_purchase_subtotal_jpy_incl_tax']=sum(x['purchase_price_jpy_incl_tax'] for x in e['candidate_parts'])
assert e['cost']['priced_purchase_subtotal_jpy_incl_tax']==1456
e['cost']['scope']='Remaining ARM/main-switch candidate prices only; owned Pico0 and USB lead500 JPY give1956 JPY in the current BOM. Replacement E-stop, assembled modules and harnesses are unpriced. Withdrawal is not a saving.'
e['cost']['withdrawn_electrical_reference_JPY'] = sum(x['purchase_price_jpy_incl_tax'] for x in old_candidates)
e['cost']['withdrawal_is_cost_saving'] = False
e['cost']['unpriced'] = ['assembled communications and controller', 'assembled drive cutoff and manual rearm',
    'independent control/communication fault response', 'battery protection and all-load disconnect',
    'assembled regeneration protection', 'no-solder E-stop replacement', 'assembled DC/DC and fuses',
    'preterminated harnesses and connectors', 'required harness assembly and inspection',
    'voltage/current/temperature monitoring', 'heatsink fixing and guarding', 'shipping', 'main computer and its converter']
e['cost']['unpriced']=[x for x in e['cost']['unpriced'] if x not in ['ARM pushbutton','battery and charger']]
e['cad_reservations']=[x for x in e['cad_reservations'] if x['id']!='EmergencyStopAccess']
for x in e['cad_reservations']:
    if x['id']=='ComputerD6': x['xyz_LWH_mm'][2]=110
e['current_CAD']='fixed-deck/AMR01_FixedDeck_D69.FCStd'
e['current_layout_revision']='D6.9'
params=json.loads((HERE/'parameters.json').read_text())
for key in ['estop','arm','main_power']:
    e['current_controls_layout'][key].update(params[key])
e['current_controls_layout']['price_scope']='Mechanical placement candidates only; current BOM explicitly leaves replacement electrical hardware and wiring unpriced.'
e['current_controls_layout']['estop'].update(purchase_JPY=None, historical_candidate_JPY=3153,
    procurement_status='withdrawn_solder_terminal_model', CAD_geometry_is_obsolete_placement_reference=True)
e['current_controls_layout']['unreleased']=['assembled_electrical_replacement_selection', 'terminal_numbered_wiring_diagram',
    'PC_product_and_DCDC', 'preterminated_harnesses', 'actual_module_CAD_layout', 'electrical_qualification']
e['calculations']['requirements_sha256']=hashlib.sha256((HERE/'requirements.json').read_bytes()).hexdigest()
t=v['torque']
e['calculations']['load_cases']=[dict(id='normal',gross_mass_kg=t['gross_mass_kg'],slope_deg=0,
    torque_Nm_per_wheel=t['service_torque_Nm_each'],torque_with_margin_1p5_Nm_per_wheel=t['with_margin_Nm_each'],
    status='calculation_not_hardware_validation')]
for case in e['calculations']['kinematics_and_energy']:
    case['reviewed_gross_mass_kg']=t['gross_mass_kg']
    case['translation_energy_J']=.5*t['gross_mass_kg']*case['speed_m_s']**2
e['validation']['thermal_test_torques_Nm']=[t['with_margin_Nm_each']]
e['validation']['thermal_matrix_strategy']=e['validation']['thermal_matrix_strategy'].replace('0.383 Nm','0.401 Nm')
e['validation']['reviewed_gross_mass_kg']=t['gross_mass_kg']
p.write_text(json.dumps(e,ensure_ascii=False,indent=2)+'\n')
print('Shared electrical plan: D6.9 mechanical layout; E1 no-fabrication constraint and incomplete replacement electronics.')
