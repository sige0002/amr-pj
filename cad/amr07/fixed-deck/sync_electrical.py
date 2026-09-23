"""Bind the minimum E2 scope to the existing D6.9 mechanical reference."""
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
e['candidate_parts'] = []  # Replacement baseline parts have not been selected.
e.update(design='AMR01_FixedDeck_D69', date=policy['date'],
         status=policy['status'], requirements_file='fixed-deck/requirements.json',
         manufacturing_requirements_file='electrical-buildability/requirements.json',
         manufacturing_requirements_sha256=hashlib.sha256(policy_path.read_bytes()).hexdigest(),
         implementation_disposition='E2 minimum manual-drive scope. Previous custom circuits, multi-relay monitoring and thresholds are archived in reference_only; they are not baseline requirements.')
e['power'] = dict(baseline=policy['baseline_power'],
    positive_path=['battery', 'source_fuse', 'DC_rated_estop_disconnect', 'left_and_right_motor_power_inputs'],
    return_and_signal_ground_wiring='pending terminal-numbered diagram',
    additional_relay='conditional_one_only_if_direct_switching_is_unsuitable',
    battery_protection='check_existing_battery_adapter_protection_before_adding_hardware',
    part_selection_complete=False)
e['control'] = dict(baseline=policy['baseline_communication'], bus_masters=1,
    motor='M0601C_111_with_integrated_driver',
    onboard_computer_required_for_first_test=False, Pico_required_for_first_test=False,
    USB_RS485_part_selected=False, operating_host_interface_confirmed=False,
    protocol_and_software_validation_complete=False)
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
e['cost'].update(priced_purchase_subtotal_jpy_incl_tax=0,
    scope='No baseline electrical models newly selected. USB cable retains a 500 JPY provisional allowance in the BOM. ARM/main switch prices are deferred, not a finished-system saving.',
    deferred_electrical_reference_JPY=1456,
    withdrawal_is_cost_saving=False,
    unpriced=['assembled USB-RS485 interface', 'latching DC-rated E-stop disconnect',
              'source fuse and holder', 'power/signal connectors and suitable cables',
              'necessary mounting and terminal insulation', 'shipping'],
    conditional_or_later=policy['optional_or_conditional'])
e['current_CAD'] = 'fixed-deck/AMR01_FixedDeck_D69.FCStd'
e['current_layout_revision'] = 'D6.9_geometry_E2_electrical_scope_pending_layout'
params = json.loads((HERE / 'parameters.json').read_text())
for key in ['estop', 'arm', 'main_power']:
    e['current_controls_layout'][key].update(params[key])
    e['current_controls_layout'][key]['purchase_JPY'] = None
    e['current_controls_layout'][key]['CAD_geometry_is_obsolete_placement_reference'] = True
e['current_controls_layout']['estop']['procurement_status'] = 'replacement_DC_rated_no_solder_part_pending'
for key in ['arm', 'main_power']:
    e['current_controls_layout'][key]['procurement_status'] = 'not_required_for_first_build'
e['current_controls_layout']['price_scope'] = 'Old control geometry only; initial build does not require ARM or the separate main rocker.'
e['current_controls_layout']['unreleased'] = ['minimum_part_selection', 'terminal_numbered_wiring',
    'actual_module_and_control_CAD_layout', 'motion_and_stop_verification']
e['calculations']['requirements_sha256'] = hashlib.sha256((HERE / 'requirements.json').read_bytes()).hexdigest()
p.write_text(json.dumps(e, ensure_ascii=False, indent=2) + '\n')
print('Shared electrical plan: E2 minimum manual-drive scope; D6.9 mechanical reference unchanged.')
