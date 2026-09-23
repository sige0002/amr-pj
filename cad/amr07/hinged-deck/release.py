"""Package prototype prints and bind the final CAD, evidence and BOM by hashes."""
from pathlib import Path
import csv, hashlib, json, zipfile

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
def read(p): return json.loads(p.read_text())
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
v=read(HERE/'validation.json'); s=read(HERE/'saved_artifact_validation.json')
loads=read(HERE/'payload_budget.json'); cost=read(HERE/'BOM-costs.json'); req=read(HERE/'requirements.json')
assert s['native_sha256']==digest(HERE/'AMR01_HingedDeck_D67.FCStd')
assert s['continuous_motion_report_sha256']==digest(HERE/'validation.json')
assert s['source_native_sha256']==digest(BASE/'control-layout/AMR01_RearControls_D66.FCStd')
assert loads['requirements_sha256']==digest(HERE/'requirements.json')
assert cost['BOM_sha256']==digest(HERE/'BOM.csv')
assert loads['vehicle_mass_estimate_kg']==v['mass']['estimated_base_kg']<req['mass']['base_max_kg']
assert req['mass']['base_target_is_hard_limit'] is False
assert len(s['meshes'])==18 and len(s['positive_stop_checks'])==2
assert len(list(HERE.glob('cad-screen-*.png')))==8
assert not v['closed_collisions'] and not v['reference_collisions']
assert not v['continuous_opening_bbox_hits'] and not v['internal_hinge_sample_hits']
assert s['empty_lid_torque']['minimum_initial_hold_ratio']>=req['hatch_requirements']['minimum_initial_torque_hold_ratio_required']
assert read(BASE/'electrical_plan.json')['calculations']['requirements_sha256']==loads['requirements_sha256']
rows=list(csv.DictReader((HERE/'BOM.csv').open(encoding='utf-8-sig')))
by={r['ID']:r for r in rows}
for id,use,buy in [('D3_M6',56,70),('F04',78,100),('D62_FLOOR_SCREWS',24,60),
                   ('D3_STOP_NUTS',32,40),('D64_FLOOR_WASHERS',28,40),
                   ('ELEC_CASE_WASHER',18,30),('HATCH_HINGES',2,2),('HATCH_LOCKS',2,18)]:
    assert int(by[id]['使用数'])==use and int(by[id]['購入予定数'])==buy
    assert int(by[id]['余剰数'])==buy-use
assert digest(BASE/'two-story/AMR01_TwoStorey_D6.FCStd')=='7a9798e5f8c0f5045029e37143bbb3b625a548ea4855cb096cd126c6e4862bf8'

print_readme='''# D6.7 試作印刷部品

18個のSTLを元の設計フォルダ名ごとに収録しています。

- two-story: 各4点固定の床4枚、支持梁、計算機下カバー（6個）
- aluminum-direct-deck: 既存荷物ストッパ（4個）
- control-layout: 後方操作ケース・蓋（4個）
- hinged-deck: トルクヒンジ用アダプター（4個）

全メッシュは閉じた形状で、各部品の最大寸法256mm未満です。
組立軸のまま正座標へ移したSTLであり、印刷向き・サポートが確定した
スライス済みファイルではありません。非導電・無充填材のPLAを前提とします。
ヒンジ可動板はXY面、固定アダプターはX側面を下へ向けて試作します。
荷重経路は中実相当とし、ナットポケット・工具空間を塞がない支持を選びます。
床・支持梁・カバー・操作ケースの注意は各print_manifest.jsonを参照してください。

ヒンジは空の天板専用。閉鎖時の荷重はアルミレールで受けます。
開閉前に主電源OFF、荷物・ベルト・蝶ボルト2本と座金を取り外します。
形状、印刷強度、クリープ、ねじ緩み、E-stop押下荷重の実機検証は未実施です。
CAD確認済みであることを、使用強度や電気安全性の認定とは扱わないでください。
'''
package=[]
with zipfile.ZipFile(HERE/'D67-print-prototypes.zip','w',zipfile.ZIP_DEFLATED) as z:
    z.writestr('README.ja.md',print_readme)
    for m in s['meshes']:
        p=BASE/m['file']; assert digest(p)==m['sha256']
        z.write(p,m['file']); package.append(m)
    for folder in ['two-story','aluminum-direct-deck','control-layout','hinged-deck']:
        z.write(BASE/folder/'print_manifest.json',folder+'/print_manifest.json')
    for filename in ['README.ja.md','PAYLOAD_REVIEW.ja.md','parameters.json','saved_artifact_validation.json']:
        z.write(HERE/filename,'hinged-deck/'+filename)
    z.writestr('package_manifest.json',json.dumps(dict(revision='D6.7',prototype_only=True,files=package),ensure_ascii=False,indent=2)+'\n')

suffixes={'.py','.json','.md','.csv','.stl','.step','.FCStd','.png','.gif','.zip'}
files={}
for p in sorted(HERE.iterdir()):
    if p.is_file() and p.suffix in suffixes and p.name!='release_manifest.json':
        files[p.name]=dict(bytes=p.stat().st_size,sha256=digest(p))
linked=[BASE/'electrical_plan.json',BASE/'ELECTRICAL_AND_VALIDATION.ja.md',BASE/'two-story/release_manifest.json']
linked += [p for p in sorted((BASE/'control-layout').rglob('*')) if p.is_file() and p.suffix in suffixes]
out=dict(revision='D6.7',date='2026-09-23',files=files,
    linked_design_files={str(p.relative_to(BASE)):digest(p) for p in linked},
    quoted_files_unchanged=s['quoted_files_SHA256'],physical_parts=383,prototype_prints=18,
    actual_FreeCAD_GUI_screenshots=8,animation='Actual FreeCAD GUI captures; not a physics simulation',
    main_checks_passed=['Saved native/STEP consistency','Closed interference involving new geometry',
        'Continuous 0..90 degree opening envelope','90 degree stop contact / 91 degree interference',
        'Battery and computer service, closed and open','Rear controls and hinge tool access',
        'Quoted plate unchanged','BOM sums and shared hardware purchase quantities'],
    legacy_D65_shape_and_analysis_scope='Unchanged floor and frame; old six-clamp deck FEA is not evidence for the new two-lock boundary.',
    bought_hardware_models='Catalogue-dimension envelopes; not supplier STEP',
    loaded_operation_released=False,printed_strength_and_creep_qualified=False,
    electrical_protection_implemented=False,Prime_account_checkout_verified=False,
    cost_scope='Partially priced procurement; PC/PCB/wiring unknown, motor price provisional.')
(HERE/'release_manifest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(f'D6.7 release: {len(files)} local artifacts, {len(linked)} linked artifacts, 18 prototype prints.')
