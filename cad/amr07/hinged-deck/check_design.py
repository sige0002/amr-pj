"""Current load envelope and explicit limited hand calculations for hinged deck."""
from pathlib import Path
from copy import deepcopy
import json,hashlib,sys,math
HERE=Path(__file__).resolve().parent;BASE=HERE.parent
sys.path.insert(0,str(BASE));from calculate_design import envelope,torque
v=json.loads((HERE/'validation.json').read_text());cv=json.loads((BASE/'control-layout/validation.json').read_text())
r=json.loads((BASE/'requirements.json').read_text());r['design']='AMR01_HingedDeck_D67';r['design_revision']='D6.7'
r['mass'].update(base_max_kg=11.5,base_max_basis='D6.7 calculation envelope, not a hard user mass limit; re-evaluate actual mass/CG outsidebounds.',interpretation='Cargo only:normal10kg;staticstructuralcomparison15kg. Vehicle review11.5kg means21.5/26.5kg gross.')
r['load_placement'].update(reviewed_base_mass_interval_kg=[6,11.5],base_cg_y_interval_mm=[-20,20],status='D6.7 closed-lid acceptance bounds. Conditional CAD model recorded inpayload_budget.json; actual cases/wiring/printmass not measured. Opening permitted unloadedandstationaryonly.')
r['current_layout']=dict(revision='D6.7',CAD='AMR01_HingedDeck_D67.FCStd',controls='../control-layout/parameters.json',hinged_lid='parameters.json',old_D65_requirements_preserved_for_FEM=True)
r['hatch_requirements']=dict(unload_before_open=True,open_angle_deg=[0,90],closed_metal_lock_qty=2,minimum_initial_torque_hold_ratio_required=1.2,prototype_proof_and_creep_tests_complete=False,open_lid_driving_permitted=False,open_lid_electrical_interlock_implemented=False)
(HERE/'requirements.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');raw=(HERE/'requirements.json').read_bytes()
cases=[envelope(r,case) for case in r['cases']];t=torque(r,10,0)
cast=[];nom=r['geometry']['caster_trail_mm'];dt=r['geometry']['caster_trail_tolerance_plus_minus_mm']
for trail in [nom-dt,nom,nom+dt]:
 c=deepcopy(r);c['geometry']['caster_trail_mm']=trail
 for case in r['cases']:
  q=envelope(c,case)['normal_reaction_extrema']['caster'];cast.append(dict(case=case['id'],trail_mm=trail,max_N=q['max_N'],twice_max_N=2*q['max_N']))
assert all(q['conservative_radial_comparison_N']<120 and q['conservative_axial_comparison_N']<60 for q in cases)
assert all(q['twice_max_N']<300 for q in cast)
assert t['numeric_margin_check']
ranges=[[(cv['mass']['estimated_base_kg']*x+sum(e['mass_kg']*e['center_mm'][i] for e in v['mass']['ledger']))/v['mass']['estimated_base_kg'] for x in xs] for i,xs in enumerate(cv['conditional_cg_xyz_ranges_mm'])]
assert ranges[0][0]>=-25 and ranges[0][1]<=25 and ranges[1][0]>=-20 and ranges[1][1]<=20 and ranges[2][1]<=160
# Sensitivity screen: 50% effective width, simply supported240mmspan, central
# pointload15kg*2. Not a substitute for hole/edge/preload/contactFEA.
force=15*9.80665*2;span=240;width=150;thickness=4;E=69000;I=width*thickness**3/12
plate=dict(load_N=force,effective_width_assumption_mm=width,span_mm=span,thickness_mm=thickness,E_assumption_MPa=E,bending_stress_MPa=force*span/4/(I/(thickness/2)),central_deflection_mm=force*span**3/(48*E*I),reference_yield_MPa=240,local_hole_and_slot_stress_qualified=False)
# Printed movingadapter section: deliberately use only30mm of50mmwidth and
# t6 at pockets, peakinitial2.1Nm/hinge. Strength is a print-specific target.
pla=dict(maximum_initial_hinge_torque_Nmm=2100,effective_width_assumption_mm=30,minimum_local_thickness_mm=6,nominal_bending_screen_MPa=2100/(30*6**2/6),required_measured_coupon_strength_for_SF2_MPa=2*2100/(30*6**2/6),load_path_layers='Movingadapter XY; fixedadapter YZ layers byprintingonXside',material_strength_is_measured=False,creep_qualified=False,proof_load_factor_target=2)
out=dict(revision='D6.7',requirements_sha256=hashlib.sha256(raw).hexdigest(),vehicle_mass_estimate_kg=v['mass']['estimated_base_kg'],reviewed_vehicle_mass_upper_bound_kg=11.5,normal_payload_kg=10,structural_comparison_payload_kg=15,torque=t,load_cases=cases,caster_trail_sensitivity=cast,closed_conditional_CG_xyz_ranges_mm=ranges,plate_simply_supported_sensitivity=plate,printed_adapter_screen=pla,empty_lid=v['torque'],source_motor_spec='https://shop.directdrive.com/pages/m0601c-111-specs',operation_released=False)
(HERE/'payload_budget.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(mass_kg=out['vehicle_mass_estimate_kg'],torque=t,CG=ranges,plate=plate,PLA=pla),ensure_ascii=False))
