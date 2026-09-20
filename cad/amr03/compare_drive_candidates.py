"""Compare published DDSM115 wheel data to existing A2 sizing, not a load approval."""
from pathlib import Path
import json
import math
HERE=Path(__file__).resolve().parent
base=json.loads((HERE/'calculation_results.json').read_text())
bom=json.loads((HERE/'bom.json').read_text())
old_diameter=base['drive']['sizing_inputs']['wheel_diameter_mm']
diameter=100.7
radius=diameter/2000
force=base['drive']['force_N']
margin=base['drive']['torque_margin']
torque=force*radius/2*margin
command=base['drive']['speed_cases']['initial']
track=base['drive']['sizing_inputs']['track_mm']/1000
rpm=(command['v_m_s']+command['omega_rad_s']*track/2)*60/(2*math.pi*radius)
old_subtotal=sum(i['packs']*i['pack_price_jpy'] for i in bom['items'] if i['id'].startswith('D'))
max_static=max(c['wheel_reaction_min_max_N'][wheel][1] for c in base['static_support']['cases'] for wheel in ('left','right'))
result={
 'status':'candidate_comparison_not_selected_hardware',
 'source_sizing':'calculation_results.json',
 'candidate':'DDSM115','diameter_mm':diameter,
 'required_torque_Nm_per_wheel':torque,'required_initial_outer_rpm':rpm,
 'published_rated_voltage_V':18,'published_rated_torque_Nm':.96,'published_rated_rpm':115,
 'rated_to_required_torque_numeric_ratio_NOT_safety_factor':.96/torque,
 'maximum_drive_wheel_force_in_A2_assumed_static_cases_N':max_static,
 'static_force_scope':'Existing A2 support/CG assumptions only. A changed wheel mount and track need recomputation. Not a shock or tested wheel load.',
 'published_single_wheel_load_kg':10,
 'A2_existing_drive_parts_subtotal_JPY_excludes_driver':old_subtotal,
 'DDSM115_pair_JPY_includes_internal_driver':12991*2,
 'partial_subtotal_difference_JPY_NOT_complete_cost_delta':12991*2-old_subtotal,
 'cost_note':'Old subtotal excludes motor-driver electronics. New subtotal excludes brackets, RS485 interface, power design and wiring. Shipping/order changes and deleted fabrication still need accounting.',
 'sources':{'manufacturer':'https://www.waveshare.com/wiki/DDSM115','domestic_price':'https://www.switch-science.com/products/9628'},
 'remaining':['38.5rpm low-speed continuous torque/thermal performance at intended battery voltage','Mounting footprint and wheel track','Dynamic wheel loads and bracket stiffness','Actual driver power-stop/regeneration behavior and full drive BOM'],
}
assert math.isclose(torque,base['drive']['wheel_torque_with_margin_Nm']*diameter/old_diameter)
assert math.isclose(rpm,base['drive']['initial_outer_wheel_rpm']*old_diameter/diameter)
assert old_subtotal==18037
(HERE/'drive_candidate_comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
