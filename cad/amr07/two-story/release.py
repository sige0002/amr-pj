"""Package current D6 prints and bind verified artifacts to current requirements."""
from pathlib import Path
import hashlib,json,zipfile
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
parts=json.loads((HERE/'print_manifest.json').read_text())
with zipfile.ZipFile(HERE/'D6-first-floor-print-files.zip','w',zipfile.ZIP_DEFLATED) as z:
    for name in [p['file'] for p in parts]+['print_manifest.json','parameters.json','README.ja.md',
            'FLOOR_REVIEW.ja.md','floor_support_review.json','cad-screen-floor-fixings-top.png',
            'cad-screen-floor-support-under.png','cad-screen-seam-beam-anchors.png',
            'CORNER_REVIEW.ja.md','corner_joint_review.json','cad-screen-corner-joint.png',
            'COMPUTER_BARRIER.ja.md','computer_barrier_review.json',
            'cad-screen-pc-isolation.png','cad-screen-pc-isolation-exploded.png',
            'cad-screen-floor-seam-joint.png','plain_hole_fastener_observations.json',
            'pla-strength/README.ja.md','pla-strength/summary.json',
            'pla-strength/fine/result.json','pla-strength/coarse/result.json',
            'pla-strength/fine/floor-deflection-T0.png','pla-strength/fine/floor-deflection-T10.png']:
        z.write(HERE/name,name)
v=json.loads((HERE/'validation.json').read_text())
saved=json.loads((HERE/'saved_artifact_validation.json').read_text())
req=json.loads((BASE/'requirements.json').read_text())
loads=json.loads((BASE/'load_calculations.json').read_text())
caster=json.loads((BASE/'caster_load_check.json').read_text())
payload=json.loads((HERE/'payload_budget.json').read_text())
costs=json.loads((HERE/'BOM-costs.json').read_text())
assert loads['requirements_sha256']==caster['requirements_sha256']==digest(BASE/'requirements.json')
assert payload['requirements_sha256']==loads['requirements_sha256']
assert costs['BOM_sha256']==digest(HERE/'BOM.csv')
assert payload['vehicle_mass_estimate_kg']==v['mass']['estimated_base_kg']
assert payload['normal_cargo_design_target_kg']==req['mass']['normal_payload_kg']==10
assert v['parameters']['new_HBLFSN6_qty']==12
assert saved['physical_parts']==v['physical_parts']==277
assert all(c['below_individual_catalog_comparison_values'] for c in loads['load_cases'])
b=req['load_placement'];ranges=v['cg_difference']['conditional_base_cg_xyz_ranges_mm']
for axis,key in enumerate(['base_cg_x_interval_mm','base_cg_y_interval_mm']):
    assert b[key][0]<=ranges[axis][0]<=ranges[axis][1]<=b[key][1]
assert ranges[2][1]<=b['base_cg_max_z_mm']
assert v['mass']['estimated_base_kg']<req['mass']['base_max_kg']
assert saved['quoted_plate_BRep_matches'] and saved['computer_and_battery_above_base_frame']
assert len(list(HERE.glob('cad-screen-*.png')))==16
floor=json.loads((HERE/'floor_support_review.json').read_text())
assert floor['native_sha256']==digest(HERE/'AMR01_TwoStorey_D6.FCStd')
assert floor['total_panel_fixings']==16 and floor['beam_anchors_per_end']==2
assert floor['M4_countersink_count']==v['parameters']['floor_M4_countersunk_qty']==0
assert floor['M4_minimum_floor_web_mm']==2.4 and len(floor['computer_supports'])==4
assert v['parameters']['floor_M4_cap_qty']==4 and v['parameters']['floor_M4_large_washers_qty']==8
assert req['geometry']['D6_two_storey']['computer_origin_LWH_mm']==v['parameters']['computer_origin_LWH_mm']
assert all(c['hard_support_to_head_mm']>=.59 for c in floor['computer_supports'])
barrier=json.loads((HERE/'computer_barrier_review.json').read_text())
assert barrier['native_sha256']==floor['native_sha256']
assert barrier['continuous_floor_mm']==2 and barrier['through_holes']==0
assert len(barrier['covered_hardware'])==8 and not barrier['metal_intrusions_above_barrier']
assert all(not c['hits'] for c in barrier['service_checks'])
assert not barrier['bare_PCB_mounting_complete'] and not barrier['dielectric_strength_verified']
assert len(parts)==6 and len([p for p in parts if p['file']=='ComputerBarrierPLA.stl'])==1
corners=json.loads((HERE/'corner_joint_review.json').read_text())
assert corners['native_sha256']==floor['native_sha256']
assert all(c['auxiliary_flat_gusset_removed'] and c['outer_floor_corner_continuous'] and not c['plastic_in_structural_clamp'] for c in corners['corners'])
assert corners['additional_parts']==0 and corners['removed_parts']==28
assert len(corners['retained_lower_frame_joints'])==8
assert req['mass']['base_target_is_hard_limit'] is False
pla=json.loads((HERE/'pla-strength/summary.json').read_text())
assert pla['source_cad_sha256']==floor['native_sha256']
for level in ['coarse','fine']:
    fea=json.loads((HERE/f'pla-strength/{level}/result.json').read_text())
    assert fea['source_cad_sha256']==floor['native_sha256'] and fea['force_balance_passed']
    assert fea['analysis_script_sha256']==digest(HERE/'pla-strength/analyze.py')
    assert len(fea['meshes'])==5 and len(fea['cases'])==6
names=[p.name for p in sorted(HERE.iterdir()) if p.is_file() and p.suffix in ['.py','.json','.md','.csv','.stl','.step','.FCStd','.png','.zip'] and p.name!='release_manifest.json']
names += [str(p.relative_to(HERE)) for p in sorted((HERE/'pla-strength').rglob('*'))
          if p.is_file() and p.suffix in ['.py','.json','.md','.step','.png','.zip']]
files={n:dict(bytes=(HERE/n).stat().st_size,sha256=digest(HERE/n)) for n in names}
linked=[BASE/n for n in ['requirements.json','electrical_plan.json','load_calculations.json','caster_load_check.json','hardware_geometry.py','printed-deck-frame/build_p1.py','makita-power/power_selection.json','aluminum-direct-deck/validation.json','aluminum-direct-deck/fea/summary.json']]
out=dict(revision=v['parameters']['revision'],date='2026-09-23',source_D3_revision=v['parameters']['source_revision'],files=files,
    linked_design_files={str(p.relative_to(BASE)):digest(p) for p in linked},
    quoted_plate_files_unchanged=saved['quoted_files_SHA256'],
    source_D3_prints_still_used=['PrintedStopXN.stl','PrintedStopXP.stl','PrintedStopYN.stl','PrintedStopYP.stl'],
    current_print_panels=4,current_print_support_beams=1,current_print_computer_barriers=1,actual_GUI_screenshots=16,
    nominal_CAD_checks_passed=True,current_load_calculations_match_requirements=True,
    conditional_CG_model_within_reviewed_bounds=True,loaded_use_released=False,
    battery_adapter_interface_measured=False,mixed_brand_frame_joint_physically_qualified=False,
    PLA_actual_solid_elastic_screen_complete=True,PLA_printed_strength_or_creep_qualified=False,
    new_metal_quote_needed=False,PCB_specific_mounting_complete=False,electrical_insulation_qualified=False,
    supplier_profile_source=dict(url='https://fa.sus.co.jp/service/cad/SFF-324-STP.lzh',
        archive_sha256='4aa1e58e04fde3e0a28c5a7d3add0be6f6e1316ad692eb38cfc7f66705ec9961',file='SUS-SFF-324-source.step',
        note='Manufacturer SFF-324 profile,500mm. Build takes100mm section. File line endings normalized; original header encoding preserved. Black/silver share nominal section.'))
(HERE/'release_manifest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('D6.5:',len(files),'hashed artifacts,',len(parts),'printed parts; current CAD/load/quote links checked.')
