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
            'CORNER_REVIEW.ja.md','corner_joint_review.json','cad-screen-corner-joint.png']:
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
assert saved['physical_parts']==v['physical_parts']==272
assert all(c['below_individual_catalog_comparison_values'] for c in loads['load_cases'])
b=req['load_placement'];ranges=v['cg_difference']['conditional_base_cg_xyz_ranges_mm']
for axis,key in enumerate(['base_cg_x_interval_mm','base_cg_y_interval_mm']):
    assert b[key][0]<=ranges[axis][0]<=ranges[axis][1]<=b[key][1]
assert ranges[2][1]<=b['base_cg_max_z_mm']
assert v['mass']['estimated_base_kg']<req['mass']['base_max_kg']
assert saved['quoted_plate_BRep_matches'] and saved['computer_and_battery_above_base_frame']
assert len(list(HERE.glob('cad-screen-*.png')))==13
floor=json.loads((HERE/'floor_support_review.json').read_text())
assert floor['native_sha256']==digest(HERE/'AMR01_TwoStorey_D6.FCStd')
assert floor['total_panel_fixings']==16 and floor['beam_anchors_per_end']==2
corners=json.loads((HERE/'corner_joint_review.json').read_text())
assert corners['native_sha256']==floor['native_sha256']
assert all(c['auxiliary_flat_gusset_removed'] and c['outer_floor_corner_continuous'] and not c['plastic_in_structural_clamp'] for c in corners['corners'])
assert corners['additional_parts']==0 and corners['removed_parts']==28
assert len(corners['retained_lower_frame_joints'])==8
assert req['mass']['base_target_is_hard_limit'] is False
names=[p.name for p in sorted(HERE.iterdir()) if p.is_file() and p.suffix in ['.py','.json','.md','.csv','.stl','.step','.FCStd','.png','.zip'] and p.name!='release_manifest.json']
files={n:dict(bytes=(HERE/n).stat().st_size,sha256=digest(HERE/n)) for n in names}
linked=[BASE/n for n in ['requirements.json','electrical_plan.json','load_calculations.json','caster_load_check.json','hardware_geometry.py','printed-deck-frame/build_p1.py','makita-power/power_selection.json','aluminum-direct-deck/validation.json','aluminum-direct-deck/fea/summary.json']]
out=dict(revision=v['parameters']['revision'],date='2026-09-22',source_D3_revision=v['parameters']['source_revision'],files=files,
    linked_design_files={str(p.relative_to(BASE)):digest(p) for p in linked},
    quoted_plate_files_unchanged=saved['quoted_files_SHA256'],
    source_D3_prints_still_used=['PrintedStopXN.stl','PrintedStopXP.stl','PrintedStopYN.stl','PrintedStopYP.stl'],
    current_print_panels=4,current_print_support_beams=1,actual_GUI_screenshots=13,
    nominal_CAD_checks_passed=True,current_load_calculations_match_requirements=True,
    conditional_CG_model_within_reviewed_bounds=True,loaded_use_released=False,
    battery_adapter_interface_measured=False,mixed_brand_frame_joint_physically_qualified=False,
    new_metal_quote_needed=False,
    supplier_profile_source=dict(url='https://fa.sus.co.jp/service/cad/SFF-324-STP.lzh',
        archive_sha256='4aa1e58e04fde3e0a28c5a7d3add0be6f6e1316ad692eb38cfc7f66705ec9961',file='SUS-SFF-324-source.step',
        note='Manufacturer SFF-324 profile,500mm. Build takes100mm section. File line endings normalized; original header encoding preserved. Black/silver share nominal section.'))
(HERE/'release_manifest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('D6.3:',len(files),'hashed artifacts,',len(parts),'printed parts; current CAD/load/quote links checked.')
