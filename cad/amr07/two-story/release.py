"""Package current D6 prints and bind verified artifacts to current requirements."""
from pathlib import Path
import hashlib,json,zipfile
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
parts=json.loads((HERE/'print_manifest.json').read_text())
with zipfile.ZipFile(HERE/'D6-first-floor-print-files.zip','w',zipfile.ZIP_DEFLATED) as z:
    for name in [p['file'] for p in parts]+['print_manifest.json','parameters.json','README.ja.md']:
        z.write(HERE/name,name)
v=json.loads((HERE/'validation.json').read_text())
saved=json.loads((HERE/'saved_artifact_validation.json').read_text())
req=json.loads((BASE/'requirements.json').read_text())
loads=json.loads((BASE/'load_calculations.json').read_text())
caster=json.loads((BASE/'caster_load_check.json').read_text())
assert loads['requirements_sha256']==caster['requirements_sha256']==digest(BASE/'requirements.json')
assert all(c['below_individual_catalog_comparison_values'] for c in loads['load_cases'])
b=req['load_placement'];ranges=v['cg_difference']['conditional_base_cg_xyz_ranges_mm']
for axis,key in enumerate(['base_cg_x_interval_mm','base_cg_y_interval_mm']):
    assert b[key][0]<=ranges[axis][0]<=ranges[axis][1]<=b[key][1]
assert ranges[2][1]<=b['base_cg_max_z_mm']
assert v['mass']['estimated_base_kg']<req['mass']['base_max_kg']
assert saved['quoted_plate_BRep_matches'] and saved['computer_and_battery_above_base_frame']
assert len(list(HERE.glob('cad-screen-*.png')))==9
names=[p.name for p in sorted(HERE.iterdir()) if p.is_file() and p.suffix in ['.py','.json','.md','.csv','.stl','.step','.FCStd','.png','.zip'] and p.name!='release_manifest.json']
files={n:dict(bytes=(HERE/n).stat().st_size,sha256=digest(HERE/n)) for n in names}
linked=[BASE/n for n in ['requirements.json','electrical_plan.json','load_calculations.json','caster_load_check.json','hardware_geometry.py','printed-deck-frame/build_p1.py','makita-power/power_selection.json','aluminum-direct-deck/validation.json','aluminum-direct-deck/fea/summary.json']]
out=dict(revision='D6',date='2026-09-22',source_D3_revision=v['parameters']['source_revision'],files=files,
    linked_design_files={str(p.relative_to(BASE)):digest(p) for p in linked},
    quoted_plate_files_unchanged=saved['quoted_files_SHA256'],
    source_D3_prints_still_used=['PrintedStopXN.stl','PrintedStopXP.stl','PrintedStopYN.stl','PrintedStopYP.stl'],
    current_print_panels=4,actual_GUI_screenshots=9,
    nominal_CAD_checks_passed=True,current_load_calculations_match_requirements=True,
    conditional_CG_model_within_reviewed_bounds=True,loaded_use_released=False,
    battery_adapter_interface_measured=False,mixed_brand_frame_joint_physically_qualified=False,
    new_metal_quote_needed=False,
    supplier_profile_source=dict(url='https://fa.sus.co.jp/service/cad/SFF-324-STP.lzh',
        archive_sha256='4aa1e58e04fde3e0a28c5a7d3add0be6f6e1316ad692eb38cfc7f66705ec9961',file='SUS-SFF-324-source.step',
        note='Manufacturer SFF-324 profile,500mm. Build takes100mm section. File line endings normalized; original header encoding preserved. Black/silver share nominal section.'))
(HERE/'release_manifest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('D6:',len(files),'hashed artifacts,',len(parts),'print panels; current CAD/load/quote links checked.')
