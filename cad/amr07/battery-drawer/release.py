"""Package the three replacement prints and record deliverable hashes."""
from pathlib import Path
import hashlib
import json
import zipfile

HERE=Path(__file__).resolve().parent
parts=json.loads((HERE/'print_manifest.json').read_text())
with zipfile.ZipFile(HERE/'D4-battery-print-files.zip','w',zipfile.ZIP_DEFLATED) as z:
    for name in [p['file'] for p in parts]+['print_manifest.json','parameters.json','README.ja.md']:
        z.write(HERE/name,name)
validation=json.loads((HERE/'saved_artifact_validation.json').read_text())
names=['AMR01_BatteryDrawer_D4.FCStd','AMR01_BatteryDrawer_D4.step',
       'D4-battery-print-files.zip','validation.json','saved_artifact_validation.json',
       'BOM.csv','cost_summary.json','parameters.json','print_manifest.json','battery_candidates.json',
       'README.ja.md','build_d4.py','build_bom.py','validate_saved.py','capture_screens.py']
names += [p.name for p in sorted(HERE.glob('cad-screen-*.png'))]
manifest=dict(revision='D4',date='2026-09-22',source_revision='099686bacaad0f72e8bc4ce15005cd708a5b2f83',
    source_D3_quoted_files_unchanged=validation['quoted_files_SHA256'],
    files={name:dict(bytes=(HERE/name).stat().st_size,sha256=hashlib.sha256((HERE/name).read_bytes()).hexdigest()) for name in names},
    battery_selected=False,loaded_use_released=False,new_metal_quote_requested=False,
    source_D3_prints_still_used=['ElectronicsTrayPLA','FrontElectronicsTrayPLA','PrintedStopXN','PrintedStopXP','PrintedStopYN','PrintedStopYP'],
    source_D3_print_removed='BatteryCradlePLA')
(HERE/'release_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('Packaged',len(parts),'replacement prints;',len(names),'hashed deliverables')
