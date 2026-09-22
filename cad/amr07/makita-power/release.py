"""Package replacement prints and hash the delivered D5 review artifacts."""
from pathlib import Path
import hashlib
import json
import zipfile
HERE=Path(__file__).resolve().parent
parts=json.loads((HERE/'print_manifest.json').read_text())
with zipfile.ZipFile(HERE/'D5-power-print-files.zip','w',zipfile.ZIP_DEFLATED) as z:
    for name in [p['file'] for p in parts]+['print_manifest.json','parameters.json','README.ja.md']:
        z.write(HERE/name,name)
validation=json.loads((HERE/'saved_artifact_validation.json').read_text())
design=json.loads((HERE/'validation.json').read_text())
requirements=json.loads((HERE.parent/'requirements.json').read_text())
loads=json.loads((HERE.parent/'load_calculations.json').read_text())
caster=json.loads((HERE.parent/'caster_load_check.json').read_text())
requirements_hash=hashlib.sha256((HERE.parent/'requirements.json').read_bytes()).hexdigest()
assert loads['requirements_sha256']==caster['requirements_sha256']==requirements_hash
bounds=requirements['load_placement'];ranges=design['cg_difference']['conditional_base_cg_xyz_ranges_mm']
assert bounds['base_cg_x_interval_mm'][0]<=ranges[0][0]<=ranges[0][1]<=bounds['base_cg_x_interval_mm'][1]
assert bounds['base_cg_y_interval_mm'][0]<=ranges[1][0]<=ranges[1][1]<=bounds['base_cg_y_interval_mm'][1]
assert ranges[2][1]<=bounds['base_cg_max_z_mm']
assert design['mass']['estimated_base_kg']<requirements['mass']['base_max_kg']
assert all(c['below_individual_catalog_comparison_values'] for c in loads['load_cases'])
names=['AMR01_MakitaPower_D5.FCStd','AMR01_MakitaPower_D5.step','AMR01_MakitaPower_D5-with-power-envelopes.step',
       'D5-power-print-files.zip','validation.json','saved_artifact_validation.json','BOM.csv','cost_summary.json',
       'parameters.json','print_manifest.json','power_selection.json','README.ja.md','build_d5.py','build_bom.py',
       'validate_saved.py','capture_screens.py','release.py']
names += [p.name for p in sorted(HERE.glob('cad-screen-*.png'))]
files={name:dict(bytes=(HERE/name).stat().st_size,sha256=hashlib.sha256((HERE/name).read_bytes()).hexdigest()) for name in names}
linked={str(p.relative_to(HERE.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
        [HERE.parent/n for n in ['requirements.json','electrical_plan.json','load_calculations.json','caster_load_check.json']]}
manifest=dict(revision='D5',date='2026-09-22',source_revision='099686bacaad0f72e8bc4ce15005cd708a5b2f83',
    files=files,linked_current_design_files=linked,quoted_plate_files_unchanged=validation['quoted_files_SHA256'],
    battery_selected=True,charger_new_purchase=True,loaded_use_released=False,new_metal_quote_requested=False,
    supplier_power_geometry='catalog envelopes; received mating dimensions not verified',
    revised_CG_bounds_contain_conditional_mass_model=True,
    current_load_and_caster_calculations_match_requirements=True,
    source_D3_prints_still_used=['FrontElectronicsTrayPLA','PrintedStopXN','PrintedStopXP','PrintedStopYN','PrintedStopYP'],
    source_D3_prints_replaced=['BatteryCradlePLA','ElectronicsTrayPLA'])
(HERE/'release_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('D5:',len(parts),'replacement prints,',len(files),'hashed deliverables')
