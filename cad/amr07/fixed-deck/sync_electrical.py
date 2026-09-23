"""Bind the E3 Pico/HAT scope and CAD packaging to the shared electrical plan."""
from pathlib import Path
from copy import deepcopy
import json, hashlib

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
p = BASE / 'electrical_plan.json'
e = json.loads(p.read_text())
policy_path = BASE / 'electrical-buildability/requirements.json'
policy = json.loads(policy_path.read_text())
ref = e['reference_only']
for key in ['power', 'restart_and_watchdog', 'control', 'regeneration', 'validation', 'operation_release']:
    if 'pre_E2_' + key not in ref:
        ref['pre_E2_' + key] = deepcopy(e[key])
if 'E2_deferred_candidates' not in ref:
    ref['E2_deferred_candidates'] = deepcopy(e['candidate_parts'])
e['candidate_parts'] = [dict(id='U1',part_number='User-owned Pico',purchase_price_jpy_incl_tax=0),dict(id='S_MAIN',part_number='amon3214',purchase_price_jpy_incl_tax=621),dict(id='S1',part_number='HW1B-V402R',purchase_price_jpy_incl_tax=2387)]
e.update(design='AMR01_PicoControl_E3', date=policy['date'],
         status=policy['status'], requirements_file='fixed-deck/requirements.json',
         manufacturing_requirements_file='electrical-buildability/requirements.json',
         manufacturing_requirements_sha256=hashlib.sha256(policy_path.read_bytes()).hexdigest(),
         implementation_disposition='E3 Pico/HAT scope. Previous custom circuits, multi-relay monitoring and thresholds are archived in reference_only; they are not baseline requirements.')
e['power'] = dict(baseline=policy['baseline_power'],
    positive_path=['battery','source_fuse','main_switch','left_or_right_branch_fuse','respective_Estop_NC','respective_motor'],
    computer_branch=['main_switch_output','computer_branch_fuse','compatible_computer_supply','Linux_mini_PC','USB_Pico','UART_RS485_HAT'],
    estop_cuts_computer_supply=False,
    return_and_signal_ground_wiring='pending terminal-numbered diagram',
    additional_relay='conditional_one_only_if_direct_switching_is_unsuitable',
    battery_protection='check_existing_battery_adapter_protection_before_adding_hardware',
    part_selection_complete=False)
e['control'] = dict(baseline=policy['baseline_communication'], bus_masters=1, separate_RS485_channels=2,
    motor='M0601C_111_with_integrated_driver',
    onboard_computer_required_for_first_test=True, Pico_required_for_first_test=True,
    computer=deepcopy(policy['baseline_computer']),
    additional_USB_RS485_required=False, pico_interface=deepcopy(policy['pico_interface']), software_design=deepcopy(policy['software_design']), operating_host_interface_confirmed=False,
    protocol_and_software_validation_complete=False)
e['stopping_behavior'] = deepcopy(policy['stopping_behavior'])
e['restart_and_watchdog'] = dict(dedicated_ARM_button_required=False,
    external_watchdog_required=False, dual_relays_and_weld_diagnostics_required=False,
    software_behavior='Verify start at zero, normal stop, communication loss and power restoration using actual motor/protocol. Do not claim an independent restart/stop guarantee.',
    verified=False)
e['regeneration'] = dict(additional_hardware_selected=False,
    disposition='Check motor/source compatibility and bus voltage during deceleration and cutoff; add only a demonstrated necessary countermeasure.',
    compatibility_verified=False)
e['operation_release'] = dict(wiring_diagram_complete=False,
    replacement_electrical_BOM_complete=False, electrical_CAD_validated=False,
    motion_test_complete=False)
e['validation'] = dict(scope='Initial manual drive on the existing flat-floor operating envelope',
    compatibility_checks=policy['electrical_compatibility_checks'],
    behavior_checks=['wheels raised: directions, speed command and normal stop',
                     'physical E-stop removes both motor supplies',
                     'power restoration and communication loss behavior',
                     'low-speed manual drive and stop on flat floor'],
    hardware_tests_complete=False)
e['cost'].update(priced_purchase_subtotal_jpy_incl_tax=3008,
    scope='Main switch621 + E-stop2387 =3008 JPY; USB provisional500 and default-Tokyo shipping780 are separate BOM lines. HAT, fuses and harness remain unpriced.',
    deferred_electrical_reference_JPY=835,
    withdrawal_is_cost_saving=False,
    unpriced=['Linux mini PC, storage and necessary cooling', 'compatible computer supply connection/converter if needed',
              'assembled Pico UART-RS485 HAT',
              'source fuse and holder', 'power/signal connectors and suitable cables',
              'necessary mounting and terminal insulation', 'shipping'],
    conditional_or_later=policy['optional_or_conditional'])
e['current_CAD'] = policy['current_CAD']
e['current_layout_revision'] = 'E3_on_D6.9_chassis'
g=json.loads((BASE/'pico-control/geometry.json').read_text())
e['current_controls_layout'] = dict(estop=g['estop'], main_power=g['main_power'], arm=dict(installed=False),
    pico=g['pico'], limitations=g['checks_pending'], vehicle_estimate_with_existing_electrical_allowance_kg=g['mass']['estimated_base_kg'])
e['operation_release']['functional_wiring_diagram_complete'] = True
e['power']['budget'] = deepcopy(policy['power_budget'])
e['power']['estop'] = deepcopy(policy['estop'])
e['power']['main_switch'] = deepcopy(policy['main_switch'])
e['calculations']['requirements_sha256'] = hashlib.sha256((HERE / 'requirements.json').read_bytes()).hexdigest()
p.write_text(json.dumps(e, ensure_ascii=False, indent=2) + '\n')
print('Shared electrical plan: E3 Pico/HAT, independent direct motor cutoff, all-load main switch.')
