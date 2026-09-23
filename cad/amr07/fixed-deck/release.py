"""Bind current CAD, saved quote evidence, costs and prototype print package."""
from pathlib import Path
import csv, json, hashlib, zipfile, re

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parent.parent


def read(name):
    return json.loads((HERE / name).read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


v = read('validation.json')
saved = read('saved_artifact_validation.json')
load = read('payload_budget.json')
cost = read('BOM-costs.json')
req = read('requirements.json')
q = read('cost_summary.json')['machining_quote']
assert v['passed'] and not v['hinges_present']
assert saved['native_sha256'] == digest(HERE / 'AMR01_FixedDeck_D69.FCStd')
assert saved['validation_sha256'] == digest(HERE / 'validation.json')
assert saved['source_native_sha256'] == digest(BASE / 'direct-hinge/AMR01_DirectHinge_D68.FCStd') == v['source_native_sha256']
assert v['restoration_source_sha256'] == digest(BASE / 'two-story/AMR01_TwoStorey_D6.FCStd')
assert load['requirements_sha256'] == digest(HERE / 'requirements.json')
assert cost['BOM_sha256'] == digest(HERE / 'BOM.csv')
assert load['vehicle_mass_estimate_kg'] == v['mass']['estimated_base_kg'] < req['mass']['base_max_kg']
assert not req['mass']['base_target_is_hard_limit']
assert req['mass']['structural_gross_kg'] == req['mass']['base_max_kg'] + req['mass']['structural_payload_kg']
assert saved['grid_clear_count'] == 36
assert len(saved['meshes']) == 14 and len(list(HERE.glob('cad-screen-*.png'))) == 5
assert q['source_sha256'] == digest((HERE / q['source']).resolve())
assert q['step_sha256'] == saved['quote_geometry'][0]['sha256']
assert not q['re_queried_this_revision']
electrical = json.loads((BASE / 'electrical_plan.json').read_text())
assert electrical['current_CAD'] == 'fixed-deck/AMR01_FixedDeck_D69.FCStd'
assert electrical['calculations']['requirements_sha256'] == load['requirements_sha256']
for item in saved['exports']:
    assert item['sha256'] == digest(HERE / item['file'])
by = {r['ID']: r for r in csv.DictReader((HERE / 'BOM.csv').open(encoding='utf-8-sig'))}
assert not any(id.startswith('HATCH_') or id == 'ELEC_CASE_WASHER' for id in by)
for id, use, buy in [('D3_M6', 50, 70), ('F04', 70, 100), ('D62_FLOOR_SCREWS', 20, 60),
                     ('D3_STOP_NUTS', 28, 40), ('D64_FLOOR_WASHERS', 24, 40)]:
    assert int(by[id]['使用数']) == use and int(by[id]['購入予定数']) == buy and int(by[id]['余剰数']) == buy-use, id
packnote = '''# D6.9 PLA試作部品14個

床4、中央支持梁1、計算機の非導電カバー1、荷物止め4、後方操作ケースと蓋4。
全14個の形状はD6.8から変更なしです。後方床2枚と操作ケース・蓋には
direct-hingeフォルダの形状を使い、ヒンジ本体や接続金具は含みません。

全STLは閉じたメッシュ、外形は各256mm未満。スライス済みではありません。
床は下面、ケースは底、蓋は平らな外面をベッドに向ける方向が試作候補です。
ナットポケットを支持材で塞がないよう確認します。無充填・非導電PLAを使い、
荷重を受ける座・壁・リブは中実相当を計算前提としています。
実印刷の強度・クリープ・保持・ねじ座面・非常停止押下は未検証です。
固定天板の構成と検証範囲はfixed-deck/README.ja.mdを参照してください。
'''
with zipfile.ZipFile(HERE / 'D69-print-prototypes.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('README.ja.md', packnote)
    for m in saved['meshes']:
        p = BASE / m['file']; assert digest(p) == m['sha256']; z.write(p, m['file'])
    for name in ['README.ja.md', 'PAYLOAD_REVIEW.ja.md', 'print_manifest.json', 'saved_artifact_validation.json']:
        z.write(HERE / name, 'fixed-deck/'+name)
    z.writestr('package_manifest.json', json.dumps(dict(revision='D6.9', prototype_only=True, meshes=saved['meshes']), indent=2)+'\n')

# Local links in the current landing page and newly delivered documentation.
checked_links = 0
for p in [ROOT / 'README.md'] + list(HERE.glob('*.md')):
    for target in re.findall(r'\]\(([^\s)]+)\)', p.read_text()):
        if '://' in target or target.startswith('#'):
            continue
        assert (p.parent / target.split('#')[0]).resolve().exists(), (p, target)
        checked_links += 1
files = {}
for p in sorted(HERE.rglob('*')):
    if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.FCBak', '.pyc', '.FCStd1'] and p.name != 'release_manifest.json':
        files[str(p.relative_to(HERE))] = dict(bytes=p.stat().st_size, sha256=digest(p))
out = dict(revision='D6.9', date='2026-09-23', files=files, physical_parts=329,
           PLA_print_parts=14, FreeCAD_GUI_screenshots=5, checked_local_links=checked_links,
           shared_electrical_plan_sha256=digest(BASE / 'electrical_plan.json'),
           scope='Fixed-deck design update; existing actual machining quote reused for equivalent geometry. Prototype review, not production release.',
           checks=['Changed-part static and reserved-envelope collision check',
                   'Continuous battery/computer service envelopes with deck installed',
                   'Six-bolt top tool access and vertical deck removal',
                   'Floor-supported rear control access',
                   '36 grid fixing envelopes',
                   'Saved native and STEP solids/volumes',
                   'Historical quoted plate STEP/PDF hashes and native shape equivalence',
                   '14 closed STL meshes and256mm printer envelope',
                   'BOM purchase packs, currencies and linked current requirements'],
           production_released=False, physical_strength_tests_complete=False)
(HERE / 'release_manifest.json').write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n')
print('D6.9 bound artifacts', len(files), 'local links', checked_links)
