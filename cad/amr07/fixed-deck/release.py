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
assert electrical['current_CAD'] == 'pico-control/AMR01_PicoControl_E3.FCStd'
assert electrical['calculations']['requirements_sha256'] == load['requirements_sha256']
buildability_dir = BASE / 'electrical-buildability'
buildability_path = buildability_dir / 'requirements.json'
buildability = json.loads(buildability_path.read_text())
assert electrical['manufacturing_requirements_sha256'] == digest(buildability_path)
assert read('cost_summary.json')['electrical_buildability_sha256'] == digest(buildability_path)
assert not buildability['user_soldering_required'] and not buildability['custom_PCBA_is_selected']
assert not electrical['operation_release']['wiring_diagram_complete']
for item in saved['exports']:
    assert item['sha256'] == digest(HERE / item['file'])
by = {r['ID']: r for r in csv.DictReader((HERE / 'BOM.csv').open(encoding='utf-8-sig'))}
assert not any(id.startswith('HATCH_') or id == 'ELEC_CASE_WASHER' for id in by)
withdrawn = list(csv.DictReader((buildability_dir / 'withdrawn-parts.csv').open(encoding='utf-8-sig')))
assert {r['ID'] for r in withdrawn} == set(buildability['withdrawn_BOM_ids'])
assert not set(buildability['withdrawn_BOM_ids']).intersection(by)
assert sum(float(r['明細金額']) for r in withdrawn) == read('cost_summary.json')['withdrawn_electrical_reference_JPY']
assert not read('cost_summary.json')['electrical_withdrawal_is_cost_saving']
deferred = list(csv.DictReader((buildability_dir / 'deferred-parts.csv').open(encoding='utf-8-sig')))
assert {r['ID'] for r in deferred} == set(buildability['deferred_BOM_ids'])
assert not set(buildability['deferred_BOM_ids']).intersection(by)
assert sum(float(r['明細金額']) for r in deferred if r['明細金額']) == read('cost_summary.json')['deferred_electrical_reference_JPY']
assert all(not by[id]['明細金額'] for id in ['U03', 'U04', 'U06', 'U07', 'U08', 'U13', 'U24'])
assert electrical['status'] == buildability['status']
assert electrical['control']['baseline'] == buildability['baseline_communication']
assert electrical['control']['computer']['platform'] == 'Linux mini PC'
assert electrical['control']['computer']['model'] is None
assert electrical['control']['onboard_computer_required_for_first_test']
assert not electrical['power']['estop_cuts_computer_supply']
assert electrical['control']['Pico_required_for_first_test']
assert 'ELEC_U1' in by and 'ELEC_MAIN' in by and 'ELEC_ARM' not in by
assert float(by['U22']['明細金額']) == 2387
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
for p in [ROOT / 'README.md', BASE / 'ELECTRICAL_AND_VALIDATION.ja.md', BASE / 'control-layout/ELECTRONICS_OPTIONS.ja.md'] + list(HERE.glob('*.md')) + list(buildability_dir.glob('*.md')):
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
           electrical_buildability_files={str(p.relative_to(BASE)): dict(bytes=p.stat().st_size, sha256=digest(p))
                                         for p in sorted(buildability_dir.iterdir()) if p.is_file()},
           scope='Archived D6.9 mechanical source, 14-part print package and images; current BOM/shared electrical plan refer to E3 in pico-control. E3 has its own CAD, 16-part print package and validation. Final electrical parts and wiring remain incomplete. Existing actual machining quote reused for unchanged deck geometry. Not production release.',
           checks=['Changed-part static and reserved-envelope collision check',
                   'Continuous battery/computer service envelopes with deck installed',
                   'Six-bolt top tool access and vertical deck removal',
                   'Floor-supported rear control access',
                   '36 grid fixing envelopes',
                   'Saved native and STEP solids/volumes',
                   'Historical quoted plate STEP/PDF hashes and native shape equivalence',
                   '14 closed STL meshes and256mm printer envelope',
                   'BOM purchase packs, currencies and linked current requirements',
                   'Withdrawn custom-circuit and solder-terminal candidates excluded from purchase BOM; replacement costs unpriced',
                   'E3 conditional/later parts excluded from baseline BOM; scope and costs agree'],
           production_released=False, physical_strength_tests_complete=False,
           electrical_wiring_design_complete=False, electrical_replacement_CAD_validated=False)
(HERE / 'release_manifest.json').write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n')
print('D6.9 bound artifacts', len(files), 'local links', checked_links)
