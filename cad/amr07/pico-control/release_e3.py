"""Bind E3 CAD, images, prototype parts, wiring specification and current BOM."""
from pathlib import Path
import json,hashlib,zipfile,re,csv
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;ROOT=BASE.parent.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
v=read(HERE/'validation.json');s=read(HERE/'saved_artifact_validation.json');g=read(HERE/'geometry.json')
assert v['passed'] and s['passed']
assert s['native_sha256']==v['native_sha256']==sha(HERE/'AMR01_PicoControl_E3.FCStd')
assert s['validation_sha256']==sha(HERE/'validation.json')
assert s['step_sha256']==sha(HERE/'AMR01_PicoControl_E3.step')
assert s['source_native_sha256']==g['source_sha256']==sha(BASE/'fixed-deck/AMR01_FixedDeck_D69.FCStd')
assert g['mass']['estimated_base_kg']<read(BASE/'fixed-deck/requirements.json')['mass']['base_max_kg']
policy=read(BASE/'electrical-buildability/requirements.json');plan=read(BASE/'electrical_plan.json')
assert plan['manufacturing_requirements_sha256']==sha(BASE/'electrical-buildability/requirements.json')
assert plan['current_CAD']=='pico-control/AMR01_PicoControl_E3.FCStd'
assert plan['control']['Pico_required_for_first_test'] and not plan['power']['estop_cuts_computer_supply']
rows={r['ID']:r for r in csv.DictReader((BASE/'fixed-deck/BOM.csv').open(encoding='utf-8-sig'))}
assert 'ELEC_U1' in rows and 'ELEC_MAIN' in rows and 'ELEC_ARM' not in rows
assert float(rows['U22']['明細金額'])==2387 and not rows['U08']['明細金額']
meshes=read(HERE/'print_manifest.json');assert len(meshes)==16
note='''# E3 PLA試作16部品

このZIPのSTLはE3の16部品です。旧D6.9 ZIPの14部品と混ぜないでください。
変更した床1枚・非常停止ケースと蓋、新規Picoケースと蓋を含みます。
基板の実寸・部品干渉・ヘッダー高さは未確認で、Picoケースは仮合わせ用です。
全STLは閉じた形状で外形256mm未満。スライス済みではありません。
床・箱は下面、蓋は平らな外面をベッドへ向ける方向が初期候補です。
非導電PLAを使用し、荷重を受けるねじ座・壁・リブは中実相当を計算前提とします。
実印刷の強度・クリープ・締付・非常停止押下は未検証。設計本文の検証範囲を参照してください。
'''
with zipfile.ZipFile(HERE/'E3-print-prototypes.zip','w',zipfile.ZIP_DEFLATED) as z:
 z.writestr('README.ja.md',note)
 for m in meshes:
  p=BASE/m['file'];assert sha(p)==m['sha256'];z.write(p,m['part']+'.stl')
 z.write(HERE/'print_manifest.json','print_manifest.json')
 z.write(HERE/'README.ja.md','design/README.ja.md')
 z.write(HERE/'validation.json','design/validation.json')
links=0
for p in [ROOT/'README.md',BASE/'electrical-buildability/README.ja.md']+list(HERE.glob('*.md')):
 for target in re.findall(r'\]\(([^\s)]+)\)',p.read_text()):
  if '://' in target or target.startswith('#'):continue
  # The manifest being written by this script may not exist on its first run.
  q=(p.parent/target.split('#')[0]).resolve()
  assert q.exists() or q==HERE/'release_manifest.json',(p,target)
  links+=1
files={}
for p in sorted(HERE.rglob('*')):
 if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.FCBak','.FCStd1','.pyc'] and p.name!='release_manifest.json':files[str(p.relative_to(HERE))]=dict(bytes=p.stat().st_size,sha256=sha(p))
shared=['electrical_plan.json','electrical-buildability/requirements.json','fixed-deck/BOM.csv','fixed-deck/BOM.ja.md','fixed-deck/BOM-details.ja.md','fixed-deck/BOM-costs.json']
out=dict(revision='E3',date='2026-09-23',files=files,shared={n:sha(BASE/n) for n in shared},physical_parts=359,PLA_parts=16,FreeCAD_GUI_screenshots=4,checked_local_links=links,geometry_checks_passed=True,electrical_hardware_validated=False,firmware_implemented=False,production_release=False)
(HERE/'release_manifest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('E3 manifest:',len(files),'files;',links,'local links; 16 prototype STLs')
