"""Bind the delivered CAD, actual quote and BOM, and package current PLA prints."""
from pathlib import Path
import json,csv,hashlib,zipfile
HERE=Path(__file__).resolve().parent;BASE=HERE.parent
def read(n):return json.loads((HERE/n).read_text())
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
v=read('validation.json');saved=read('saved_artifact_validation.json');load=read('payload_budget.json');cost=read('BOM-costs.json');req=read('requirements.json');quote=read('quote-evidence/observed.json')
assert v['passed'] and read('assembly_access.json')['passed']
assert saved['native_sha256']==digest(HERE/'AMR01_DirectHinge_D68.FCStd')
assert saved['validation_sha256']==digest(HERE/'validation.json')
assert saved['source_native_sha256']==digest(BASE/'two-story/AMR01_TwoStorey_D6.FCStd')=='7a9798e5f8c0f5045029e37143bbb3b625a548ea4855cb096cd126c6e4862bf8'
assert load['requirements_sha256']==digest(HERE/'requirements.json')
assert cost['BOM_sha256']==digest(HERE/'BOM.csv')
assert load['vehicle_mass_estimate_kg']==v['mass']['estimated_base_kg']<req['mass']['base_max_kg']
assert req['mass']['base_target_is_hard_limit'] is False
assert req['mass']['structural_gross_kg']==req['mass']['base_max_kg']+req['mass']['structural_payload_kg']
assert len(saved['meshes'])==14 and saved['opening_stops'] is False
assert len(list(HERE.glob('cad-screen-*.png')))==8
assert all(digest(HERE/x['file'])==x['sha256'] for x in read('quote-evidence/final-upload-files.json'))
assert quote['drawing_attachments_verified'] and read('quote-evidence/drawing-association-check.json')['verified']
assert abs(quote['plate_lot_USD']+quote['angle_lot_USD']+quote['shipping_USD']-quote['sum_USD'])<1e-7
assert json.loads((BASE/'electrical_plan.json').read_text())['calculations']['requirements_sha256']==load['requirements_sha256']
by={r['ID']:r for r in csv.DictReader((HERE/'BOM.csv').open(encoding='utf-8-sig'))}
for id,use,buy in [('D3_M6',44,70),('F04',66,100),('D62_FLOOR_SCREWS',28,60),('D3_STOP_NUTS',36,40),('D64_FLOOR_WASHERS',36,40),('ELEC_CASE_WASHER',6,30),('HATCH_HINGES',2,2),('HATCH_LOCKS',2,18),('HATCH_FRAME_M4_NUT',4,10),('HATCH_FRAME_M4_BOLT',4,52),('HATCH_METAL_ANGLES',2,2)]:
 assert int(by[id]['使用数'])==use and int(by[id]['購入予定数'])==buy and int(by[id]['余剰数'])==buy-use,id
readme='''# D6.8 PLA試作部品14個

現行は床4、中央支持梁1、PC非導電カバー1、荷物止め4、後方ケース・蓋4です。
後方床2枚とケース・蓋はdirect-hinge版を使います。旧後方床、旧D6.6ケース、
D6.7ヒンジ用樹脂部品は使用しません。開き止めはありません。

全STLは閉じたメッシュで、外形は各256mm未満。組立向きの形状を正座標へ移した
データで、スライス済みではありません。床は下面、ケースは底、蓋は平らな外面を
ベッドに向ける方向が試作候補。ナットポケットを支持材で塞がないよう確認します。
非導電・無充填PLA、荷重を受ける壁・リブ・座は中実相当が計算前提です。
印刷強度・クリープ・保持・ねじ座面・E-stop押下の実機検証前。
README.ja.mdとPAYLOAD_REVIEW.ja.mdを参照してください。
'''
with zipfile.ZipFile(HERE/'D68-print-prototypes.zip','w',zipfile.ZIP_DEFLATED) as z:
 z.writestr('README.ja.md',readme)
 for m in saved['meshes']:
  p=BASE/m['file'];assert digest(p)==m['sha256'];z.write(p,m['file'])
 for name in ['README.ja.md','PAYLOAD_REVIEW.ja.md','print_manifest.json','saved_artifact_validation.json']:z.write(HERE/name,'direct-hinge/'+name)
 z.writestr('package_manifest.json',json.dumps(dict(revision='D6.8',prototype_only=True,meshes=saved['meshes']),indent=2)+'\n')
files={}
for p in sorted(HERE.rglob('*')):
 if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.FCBak','.pyc'] and p.name!='release_manifest.json':files[str(p.relative_to(HERE))]=dict(bytes=p.stat().st_size,sha256=digest(p))
out=dict(revision='D6.8',date='2026-09-23',files=files,physical_parts=369,PLA_print_parts=14,FreeCAD_GUI_screenshots=8,opening_stops=False,shared_electrical_plan_sha256=digest(BASE/'electrical_plan.json'),scope='Prototype design review, actual site automatic quote, saved nominal geometry verification. Not hardware or production release.',checks=['Saved native and STEP solids/volumes','Actual quoted STEP against assembly geometry','14 closed STL meshes and256mm printer envelope','Changed-part static interference','0..90 opening: continuous bbox culling plus1deg close-pair samples','Battery/PC continuous straight service envelopes','Control access and selected assembly tool approaches','BOM purchase packs and currency sums'],production_released=False,physical_strength_and_holding_tests_complete=False,electrical_protection_implemented=False)
(HERE/'release_manifest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print('D6.8 bound artifacts',len(files))
