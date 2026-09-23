#!/usr/bin/env python3
"""Compare the two real-solid meshes; report demand without inventing an allowable."""
from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
coarse=read(HERE/'coarse/result.json');fine=read(HERE/'fine/result.json')
geometry=read(HERE/'geometry.json');fixings=read(HERE.parent/'floor_support_review.json')
barrier=read(HERE.parent/'computer_barrier_review.json')
assert barrier['native_sha256']==geometry['source_cad_sha256']
assert coarse['source_cad_sha256']==fine['source_cad_sha256']==geometry['source_cad_sha256']==sha(HERE.parent/'AMR01_TwoStorey_D6.FCStd')
assert coarse['force_balance_passed'] and fine['force_balance_passed']
assert fine['E_MPa']==coarse['E_MPa']==1000
assert fine['analysis_script_sha256']==coarse['analysis_script_sha256']==sha(HERE/'analyze.py')
comparisons=[]
for a,b in zip(coarse['cases'],fine['cases']):
    assert (a['equipment_contact'],a['belt_tension_each_leg_N'])==(b['equipment_contact'],b['belt_tension_each_leg_N'])
    comparisons.append(dict(contact=b['equipment_contact'],belt_tension_each_leg_N=b['belt_tension_each_leg_N'],
        max_down_mm=b['max_down_mm'],max_tensile_MPa=b['max_tensile_MPa'],max_compression_MPa=b['max_compression_MPa'],
        coarse_to_fine_downward_change_percent=100*(b['max_down_mm']/a['max_down_mm']-1),
        coarse_to_fine_peak_tensile_change_percent=100*(b['max_tensile_MPa']/a['max_tensile_MPa']-1),
        linear_twice_all_loads_tensile_demand_MPa=2*b['max_tensile_MPa'],
        tensile_peak_part=max(b['parts'],key=lambda p:p['peak_tensile_principal_MPa'])['part']))

# These K values are a sensitivity assumption, not measured nut factors for PLA.
# T=K*F*d relates tightening torque to axial preload; p=F/A is mean axial bearing.
seats=fixings['panels'][0]['fixings']
areas={'M6_washer':seats[0]['actual_head_or_washer_bearing_projected_area_mm2'],
       'M4_large_washer':seats[3]['actual_head_or_washer_bearing_projected_area_mm2']}
preloads=[]
for name,d in [('M6_washer',.006),('M4_large_washer',.004)]:
    for torque in [.2,.5,1.]:
        f0,f1=torque/(.30*d),torque/(.15*d)
        preloads.append(dict(seat=name,torque_Nm=torque,assumed_K_range=[.15,.30],
            preload_range_N=[f0,f1],CAD_projected_area_mm2=areas[name],
            mean_axial_compression_range_MPa=[f0/areas[name],f1/areas[name]]))
material=dict(assumed_product='Bambu PLA Basic; not confirmed by owner',assumed_infill_percent=100,
    analysis_E_MPa=1000,analysis_nu=.35,model='isotropic homogeneous sensitivity model, not measured orthotropic print',
    TDS_reference=dict(tensile_XY_MPa=[35,4],tensile_Z_MPa=[31,3],Young_XY_MPa=[2580,220],Young_Z_MPa=[2060,170],
        printed_specimens_infill_percent=100,specimens_annealed_dried_C=55,specimens_annealed_dried_hours=8),
    TDS_URL='https://store.bblcdn.com/s1/default/58b85d0f3db94878854a28fdb8a0006e/Bambu_PLA_Basic_Technical_Data_Sheet.pdf',
    tested_allowable_tensile_MPa=None,tested_allowable_compression_MPa=None,validated_continuous_temperature_C=None,
    proposed_slicer=dict(nozzle_mm=.4,layer_mm=.2,wall_loops=6,top_layers=6,bottom_layers=6,infill_percent=100,
        floor_orientation='plate horizontal, ribs downward, with supports; assembly Z is build Z',
        seam_beam_orientation='broad flange toward bed, check belt-channel bridging',
        sliced=False,printed=False,annealing_required_by_this_review=False,
        note='proposal only; different settings/orientation/infill require re-evaluation. No claim that this reproduces TDS specimens.'))
summary=dict(revision='D6.5',source_cad_sha256=geometry['source_cad_sha256'],material=material,
    mesh_comparison=comparisons,bolt_preload_sensitivity=preloads,
    preload_formula_source='https://ntrs.nasa.gov/api/citations/19900009424/downloads/19900009424.pdf',
    material_strength_factor_2_demonstrated=False,creep_qualified=False,whole_frame_qualified=False,
    issues=[
        'Local peaks near small seam fixings and belt slots are mesh/boundary dependent; two meshes do not establish convergence.',
        'Patch supports idealize washers. Seam coupling includes four translations but omits interface rotations/moment transfer.',
        'Countersink removed; full2.4mm web and OD12 washers. Preload/contact/creep still require joint qualification.',
        'Actual equipment feet, pads, strap tension, filament, print quality and temperature remain unmeasured.',
        'No PLA diaphragm action is credited to the lower3030 frame. Retained8HBLFSN6 joints still need a racking assessment.'],
    preferred_next_design_actions=[
        'Spread foot loads over a stiff pad/backing part and verify its bending and contact; soft foam alone is not a proven spreader.',
        'Route strap reactions into ribs or metal rails and qualify required retention force; do not prescribe10N as a safe strap limit from this sweep.',
        'Plain holes and larger washers adopted. If measured preload retention/creep is insufficient, evaluate compression sleeves or route clamp load into metal without weakening the floor.',
        'Correlate a printed assembly under known masses and measured strap tension; then test retention at actual temperature and duration.'])
old=json.loads(subprocess.check_output(['git','-C',str(HERE),'show','c0b236d:cad/amr07/two-story/pla-strength/fine/result.json']))
old_fix=json.loads(subprocess.check_output(['git','-C',str(HERE),'show','b38b90b:cad/amr07/two-story/floor_support_review.json']))
old_area=old_fix['panels'][0]['fixings'][3]['actual_head_or_washer_bearing_projected_area_mm2']
before_after=[]
for a,b in zip(old['cases'],fine['cases']):
    if b['equipment_contact']!='four_10mm_feet':continue
    before_after.append(dict(belt_tension_each_leg_N=b['belt_tension_each_leg_N'],
        old_down_mm=a['max_down_mm'],new_down_mm=b['max_down_mm'],
        old_peak_tensile_MPa=a['max_tensile_MPa'],new_peak_tensile_MPa=b['max_tensile_MPa']))
summary['washer_change_history_D64']=dict(baseline_commit='b38b90b372581ddf84677df203ba63511863da0e',
    old_M4_projected_area_mm2=old_area,new_M4_projected_area_mm2=areas['M4_large_washer'],
    projected_bearing_area_ratio=areas['M4_large_washer']/old_area,
    same_preload_mean_pressure_reduction_percent=100*(1-old_area/areas['M4_large_washer']),
    old_minimum_web_mm=.65,new_minimum_web_mm=2.4,old_PC_seat_z_mm=104,new_PC_seat_z_mm=108,
    hard_support_top_z_mm=107,head_top_z_mm=106.4,liner_free_case_head_clearance_mm=1.6,
    fully_compressed_liner_case_head_clearance_mm=.6,
    geometry_checks='Four ordinary M4x16 screws, upper/lower OD12x1 washers, full floor web; tool approach and service envelopes checked.',
    scope='Historical D6.3 to D6.4 washer/web change; retained without further modification in D6.5.')
summary['D65_change']=dict(baseline_commit='c0b236db11846b06c95ed06e7cc03919c3524e16',
    barrier_mass_kg=barrier['mass_kg'],continuous_barrier_mm=2,old_PC_seat_z_mm=108,new_PC_seat_z_mm=110,
    before_after_same_four_foot_contact=before_after,
    bare_PCB_mounting_complete=False,dielectric_strength_verified=False,
    scope='Same five floor/beam solids, support locations and contact model. Add barrier mass to PC loads at aligned floor bosses; no barrier spanning stiffness or load-spreading credit. Local compression screen is separate.',
    local_compression_review='../computer_barrier_review.json')
(HERE/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')

lines=['# D6.5 PLA床：金属接触防止カバーの追加荷重を反映',
'',
'**中央のねじ・座金を厚さ2mmの連続したPLAカバーで覆い、約39gの追加荷重を床4枚と支持梁の解析へ反映した。** カバーの4か所の荷重位置は、床と一体の硬い受けの真上。カバーの曲げ剛性による荷重分散は計上しない。ケース座面は108→110mm。裸基板の固定方法は機種未選定のため未確定である。短時間の線形弾性比較であり、印刷物の安全率2・長期耐久・電気絶縁の認定ではない。',
'',
'![中央金属を覆うPLAカバーのFreeCAD画面](../cad-screen-pc-isolation.png)',
'',
'## 荷重と材料条件',
'',
f'1階電装2.4kg（電池・アダプター等0.953kg、PC等0.525kg、通信0.055kg、保護0.2kg、電源0.2kg、配線等0.467kg）に、カバー{barrier["mass_kg"]*1000:.1f}gと床4枚＋支持梁の中実換算自重{sum(p["solid_mass_kg"] for p in geometry["parts"].values()):.3f}kgを加えた。上段の荷物10kg／構造比較15kgは金属支柱と3030で受けるため、この床荷重に混ぜていない。',
'',
'PCは両条件とも実CADの10×10mm受け4か所（上面Z107mm）に、PCとカバーの全重量およびベルト反力を与えた。カバー上のパッドと床の受けのXY位置が一致することをCADで確認した。カバー自体の曲げ・接触は5部品の有限要素モデルに含めず、[別紙の局部圧縮比較](../COMPUTER_BARRIER.ja.md)に分けた。他の機器が面で接する場合と、10×10mmの脚4個で接する場合を比較した。電池・PC・通信機器の3本の閉じたベルトをモデル化し、各脚の張力を0・10・30Nとした。1本のベルトは機器へ2Tを下向き、床裏へ各Tを上向きに加えるため、全体への追加鉛直力はゼロだが、局所的な曲げが増す。張力は実測値ではなく感度確認用で、0Nは重力だけの比較条件である。',
'',
'銘柄未回答のためPLA Basic相当・100%充填を仮定。弾性率E=1000MPa、ポアソン比0.35の均質等方体とした。E=1000MPaは低剛性側を比較するための仮定で、あらゆる印刷方向の下限保証ではない。内部空隙を含む実印刷形状はモデル化していない。',
'',
'[Bambu TDS V3.0](https://store.bblcdn.com/s1/default/58b85d0f3db94878854a28fdb8a0006e/Bambu_PLA_Basic_Technical_Data_Sheet.pdf)の引張強さはXY35±4MPa・Z31±3MPa、ヤング率はXY2580±220MPa・Z2060±170MPa。ただし100%充填・55°Cで8時間処理した試験片の代表値で、今回の部品の許容値ではない。曲げ強さを引張許容値に流用していない。',
'',
'## 結果',
'',
'下表は細かいメッシュの結果。引張値は積分点の最大主応力で、局所ピークを除外していない。',
'',
'| 機器の接触 | ベルト1脚の張力 | 最大下向きたわみ | 最大引張主応力 | 荷重を全て2倍にした引張要求値 |',
'|---|---:|---:|---:|---:|']
for c in comparisons:
    label='他機器は面・PCは4脚' if c['contact']=='full_pads' else '全機器10mm角の脚4個'
    lines.append(f"| {label} | {c['belt_tension_each_leg_N']}N | {c['max_down_mm']:.3f}mm | {c['max_tensile_MPa']:.2f}MPa | {c['linear_twice_all_loads_tensile_demand_MPa']:.2f}MPa |")
lines += ['', '### 前版D6.4との比較', '',
'機器が全て4脚の条件で比較する。床4枚と支持梁の形状、受けの位置、弾性率と境界条件を維持し、カバー約39gの荷重だけを追加した。各版の実形状からメッシュを生成しており、要素分割による数値差も含む。', '',
'| ベルト1脚 | 旧→新 最大たわみ | 旧→新 引張ピーク |', '|---|---:|---:|']
for d in before_after:
    lines.append(f"| {d['belt_tension_each_leg_N']}N | {d['old_down_mm']:.3f}→{d['new_down_mm']:.3f}mm | {d['old_peak_tensile_MPa']:.2f}→{d['new_peak_tensile_MPa']:.2f}MPa |")
lines += ['', 'D6.5の変更目的は露出金属への接触防止で、床の補強ではない。局所ピークにはメッシュ差があり、わずかな増減をそのまま強度改善率とは解釈しない。']
lines += ['',
'「2倍」は重力・ベルト張力をともに2倍にした線形計算上の要求値で、材料がそれを満たすと確認した値ではない。実機衝撃や締付け軸力は別。全PLAのEを一様に変える場合、たわみは1000/E倍となるが、異方性や部品ごとに異なる剛性はこの倍率では扱えない。',
'',
'![脚4個・ベルトなしの下向きたわみ](fine/floor-deflection-T0.png)',
'',
'![脚4個・ベルト10Nの下向きたわみ](fine/floor-deflection-T10.png)',
'',
'色は変位量、赤い＋は各床の固定位置。形状を変形させたCAD画像ではなく、解析結果の分布図。',
'',
'### メッシュ・境界条件の限界',
'',
'[Gmsh](https://gmsh.info/doc/texinfo/)4.15.0で最大辺長4mmと2.5mmの二次四面体C3D10を作り、CalculiX2.21を1スレッドで実行した。各床5ケース・梁5ケースの単位応答から、中央4接合点の並進を梁の4×4柔軟性行列で連成した。全25ケースの反力・モーメントのつり合い、柔軟性行列の相反性、全体荷重のつり合いを検査した。',
'',
'各床の3本のM6は座金相当範囲の鉛直変位を拘束し、中央M4も半径4.5mmの下面範囲の鉛直変位をそろえる。旧版との比較のため、この範囲は変えず、大径上座金による曲げ剛性の増加は計上しない。梁端は4本のM6周辺を理想固定。レール上の連続接触を省く一方、座面や梁端を理想拘束しているため、全ての応力・たわみの安全側上限とはいえない。中央接合の回転とモーメント伝達、ボルト接触・締付け軸力・すべりは未解析。',
'',
'| 条件 | 粗→細の最大たわみ変化 | 粗→細の最大引張ピーク変化 |',
'|---|---:|---:|']
for c in comparisons:
    label='他機器は面・PCは4脚' if c['contact']=='full_pads' else '全機器4脚'
    lines.append(f"| {label}・{c['belt_tension_each_leg_N']}N | {c['coarse_to_fine_downward_change_percent']:+.1f}% | {c['coarse_to_fine_peak_tensile_change_percent']:+.1f}% |")
lines += ['',
'局所ピークは小さな固定範囲やベルト穴端などに出る。粗細2段階の比較だけでは収束を証明できず、最大値を除いた99パーセンタイルを合否値として置き換えることもしない。大きなたわみの条件は、接触・幾何学非線形も含む追加評価が必要。部品別の位置・反力・応力と各誤差は[result.json](fine/result.json)に記録した。',
'',
'## ねじの締付けは別に計算する',
'',
f'CADからM6座金の投影座面約{areas["M6_washer"]:.2f}mm²、M4大径座金の床接触面約{areas["M4_large_washer"]:.2f}mm²を取得した。D6.3の旧皿頭の{old_area:.2f}mm²からD6.4で約{areas["M4_large_washer"]/old_area:.2f}倍となり、同じ軸力の平均圧縮は約{100*(1-old_area/areas["M4_large_washer"]):.0f}%低下する。肉厚は0.65→2.4mm。これは耐荷重が同じ倍率で増えたという意味ではない。',
'',
'[NASA Fastener Design Manual](https://ntrs.nasa.gov/api/citations/19900009424/downloads/19900009424.pdf)の簡易式T=KFdを使い、K=0.15〜0.30を仮定した感度比較を行った。このK範囲はPLA締結の実測範囲ではなく、トルクの推奨値でもない。投影平均圧縮p=F/Aは、座金の曲げ・不均一接触・裏面の支持圧分布を含まない。',
'',
'| 座面 | 仮定トルク | 軸力 | 投影平均圧縮 |',
'|---|---:|---:|---:|']
for p in preloads:
    lo,hi=p['preload_range_N'];a,b=p['mean_axial_compression_range_MPa']
    lines.append(f"| {'M6座金' if p['seat']=='M6_washer' else 'M4大径座金'} | {p['torque_Nm']}N·m | {lo:.0f}〜{hi:.0f}N | {a:.1f}〜{b:.1f}MPa |")
lines += ['',
'大径座金にしても、小さな締付トルクで機器重量による反力を大きく上回る軸力になり得る。引張強さ31MPaから圧縮や長期クリープの許容値を決めることはできない。金属同士のM6トルクをPLAにそのまま適用しない。',
'',
'## 設計判断と残る確認',
'',
'D6.4で採用した通常ねじと上下の大径座金を維持し、D6.5ではその上を連続カバーで覆った。カバーは接触防止用で、耐電圧・耐熱・印刷欠陥に対する認定はない。PC受けは床と一体の硬いPLAで作り、ケースパッドとカバーを挟んで荷重位置をそろえる。裸基板をこのパッドへ直置きしたり、ベルトで直接押さえたりしない。残る課題はベルト反力と必要保持力、印刷方向、締付け軸力と長期変形。必要なら圧縮カラー・金属への直接締結を次に比較する。柔らかいスポンジを敷くだけで面支持になるとは仮定せず、「ベルト10N以下なら安全」という限界もこの計算からは設定しない。',
'',
'暫定印刷案は0.4mmノズル、0.2mm積層、壁6周、上下6層、100%充填。床は水平・裏リブ下向き＋サポート、中央梁は広いフランジをベッド側として溝のブリッジを確認する。実スライス・サポート量・造形・熱処理は未実施。この条件でもTDSの再現は保証されない。20%などの充填率へ変更した場合は中実モデルの結果を流用しない。',
'',
'長期変形は弾性率と短時間強度だけでは算出できない。同じ材料・造形・荷重・温度に対応するクリープデータが必要。[PLAの長期曲げ実験](https://arxiv.org/abs/2302.11240v2)でもガラス転移温度より低い温度で時間依存変形が報告されている。まず実物に既知重量と測定したベルト張力を与え、たわみ・残留変形・ねじの保持を照合し、その後に実機温度と保持時間で確認する。',
'',
'下部3030の四角形が横荷重でひし形に変形する剛性は、このPLA解析に含まれない。PLAをフレームの筋交いとして計上せず、8個のHBLFSN6接合部のすべり・回転・締付け条件を別に確認する。メーカー1176Nという金具の掲載値は、現車全体のねじりや接合モーメントの許容値ではない。[金属構造の計算と未確認点](../structure_screening.json)。',
'',
'## 再現・成果物',
'',
'[総合JSON](summary.json)／[粗メッシュ](coarse/result.json)／[細メッシュ](fine/result.json)／[解析スクリプト](analyze.py)。STEP5点は保存済みD6.5 FCStdから直接抽出し、[geometry.json](geometry.json)のSHA256で紐付けた。CAD・STL・BOMも同じ改訂へ更新。中実換算質量はBOMへ反映したが、サポート材等の印刷費は実スライスまで未確定。',
'',
'各メッシュの部品別solver.zipは入力INP・メッシュMSH・GEO・実行ログを収録。大容量の生DATはリポジトリへ重複保存せず、SHA256を結果JSONに記録した。INPをCalculiXで実行すれば再計算できる。使用した2.21配布バイナリでは2スレッド時に荷重つり合いの不一致を検出したため、その結果は採用せず、全ケースを1スレッドで計算し直した。RF出力は反力＋節点荷重なので、拘束節点のCLOADを差し引いて反力を評価している。',
'',
'```sh',
'python analyze.py --size 4 --name coarse --work /tmp/pla-coarse --gmsh /path/to/gmsh --ccx /path/to/ccx --ccx-lib /path/to/ccx-libraries',
'python analyze.py --size 2.5 --name fine --work /tmp/pla-fine --gmsh /path/to/gmsh --ccx /path/to/ccx --ccx-lib /path/to/ccx-libraries',
'python review.py',
'```',
'',
'Python依存：numpy・meshio・matplotlib。既存結果の再集計は`--reuse`を付ける（生成入力の一致とつり合いを再検査する）。形状を変えた場合は新しい作業ディレクトリでメッシュから再作成する。',
'']
(HERE/'README.ja.md').write_text('\n'.join(lines))
print(json.dumps(dict(cases=comparisons,whole_print_strength_qualified=False),ensure_ascii=False))
