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
e.update(design='AMR01_DirectHinge_D68',date='2026-09-23',requirements_file='direct-hinge/requirements.json')
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
e['cost']['priced_purchase_subtotal_jpy_incl_tax']=sum(x['purchase_price_jpy_incl_tax'] for x in e['candidate_parts'])
assert e['cost']['priced_purchase_subtotal_jpy_incl_tax']==7975
e['cost']['scope']='Selected electrical parts only; USB lead500 JPY is in current BOM, giving8475 JPY. Shared washers and shipping excluded here; current BOM is authoritative.'
e['cost']['unpriced']=[x for x in e['cost']['unpriced'] if x not in ['ARM pushbutton','battery and charger']]
e['cad_reservations']=[x for x in e['cad_reservations'] if x['id']!='EmergencyStopAccess']
for x in e['cad_reservations']:
    if x['id']=='ComputerD6': x['xyz_LWH_mm'][2]=110
e['current_CAD']='direct-hinge/AMR01_DirectHinge_D68.FCStd'
e['current_layout_revision']='D6.8'
params=json.loads((HERE/'parameters.json').read_text())
for key in ['estop','arm','main_power']:
    e['current_controls_layout'][key].update(params[key])
e['current_controls_layout']['price_scope']='Current electrical part prices above; complete current purchase quantities and costs in direct-hinge/BOM.csv.'
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
print('Shared electrical plan: D6.8 loads, rear controls, owned Pico and current prices.')
