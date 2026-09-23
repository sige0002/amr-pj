from pathlib import Path
import json,hashlib,re,csv
BASE=Path(__file__).resolve().parent.parent;ROOT=BASE.parent.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
std=BASE/'reviewed-design';opt=BASE/'monitor-option'
for here in [std,opt]:
 saved=json.loads((here/'saved_artifact_validation.json').read_text());v=json.loads((here/'validation.json').read_text());assert saved['passed'] and v['passed']
 native=next(here.glob('*.FCStd'));assert saved['native_sha256']==v['native_sha256']==sha(native)
 assert saved['step_sha256']==sha(native.with_suffix('.step'))
 assert saved['validation_sha256']==sha(here/'validation.json')
links=0
for p in [ROOT/'README.md']+list(std.glob('*.md'))+list(opt.glob('*.md'))+list((BASE/'design-review-e3').glob('*.md')):
 for target in re.findall(r'\]\(([^\s)]+)\)',p.read_text()):
  if '://' in target or target.startswith('#'):continue
  assert (p.parent/target.split('#')[0]).resolve().exists(),(p,target)
  links+=1
cost=json.loads((std/'cost_summary.json').read_text());assert cost['BOM_sha256']==sha(std/'BOM.csv')
rows={r['ID']:r for r in csv.DictReader((std/'BOM.csv').open(encoding='utf-8-sig'))}
assert not any(k.startswith('O-') for k in rows) and rows['P04']['CAD形状数']=='12'
assert rows['DECK_plate']['明細金額']==rows['DECK_CNC_SHIP']['明細金額']==''
assert rows['E4_LOWHEAD']['使用数']=='6' and rows['E4_LOWHEAD']['購入予定数']=='10'
assert 'D3_STOP_BOLTS' not in rows and rows['D3_STOP_NUTS']['使用数']=='20'
p=json.loads((opt/'requirements.json').read_text());assert p['standard_native_sha256']==sha(std/'AMR01_Reviewed_E4.FCStd')
for here in [std,opt]:
 files={str(p.relative_to(here)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(here.rglob('*')) if p.is_file() and p.suffix not in ['.FCBak','.FCStd1','.pyc'] and '__pycache__' not in p.parts and p.name!='release_manifest.json'}
 out=dict(revision='E4' if here==std else 'O1 optional',files=files,checked_local_links=links,standard_monitor_included=False,manufacturing_release=False,review_reports={p.name:sha(p) for p in sorted((BASE/'design-review-e3').glob('*.md'))})
 (here/'release_manifest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('E4/O1 manifests bound;',links,'links; standard/optional BOM separated')
