"""Keep current design summaries tied to the verified CAD/load/cost ledgers."""
from pathlib import Path
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def read(name):return json.loads((HERE/name).read_text())
v=read('validation.json');p=read('payload_budget.json');c=read('cost_summary.json')
f=read('floor_support_review.json');prints=read('print_manifest.json')
pla=read('pla-strength/summary.json')
pla_feet={x['belt_tension_each_leg_N']:x for x in pla['mesh_comparison'] if x['contact']=='four_10mm_feet'}
mass=p['vehicle_mass_estimate_kg'];delta=p['plain_hole_rework_increase_from_D63_kg']
delta_word=f"約{abs(delta)*1000:.0f}g{'減' if delta<0 else '増'}"
grams=sum(x['solid_mass_g'] for x in prints)
filament_delta=c['plain_hole_rework_from_D63']['PLA_material_reference_increase_JPY']
comp=p['mass_components_kg'];rad=p['motor_load_comparison_at_reviewed_vehicle_mass']
def components():
    names={'retained_lower_structure_drive_and_hardware':'下段骨格・足回り・既存締結材',
        'aluminum_cargo_plate':'アルミ荷台','upper_rails_posts_joints':'上段レール・支柱・金具・締結材',
        'new_floor_hardware':'床・支持梁の金属締結材（現行D6.4）','all_PLA':'PLA床・支持梁・荷物ストッパ',
        'battery_adapter_and_other_electrical':'電池・アダプター・その他電装',
        'cargo_belts_and_edge_pads':'荷物ベルト・端部保護','equipment_belts_and_pads':'電装保持ベルト・パッド'}
    return '\n'.join(f'| {names[k]} | {m:.3f} |' for k,m in comp.items())

payload=f'''# D6.4：車体重量と積載

**車体は推計{mass:.3f}kg、前版D6.3から{delta_word}。通常積載の設計目標10kgを維持する。** ユーザーの指示により、車体10kgは厳密な上限から目安へ変更した。必要な支持を省いて10kgへ合わせない。

今回の比較計算は車体10.5kgまでを対象とし、通常荷物10kgなら総重量20.5kg、構造比較の荷物15kgなら25.5kg。10.5kgは新しいユーザー指定上限ではなく、現行計算の範囲。実測が超えた場合や機器を追加する場合は、重量・重心・輪荷重を再計算する。構造比較15kg/SF2は走行積載の認定値ではない。

| 内訳 | kg |
|---|---:|
{components()}
| **車体合計** | **{mass:.3f}** |
| 通常荷物10kgを加えた推計 | {mass+10:.3f} |

電池0.680kg、アダプター0.123kgを含む。主計算機0.5kgなどは未選定機器の予算で、実測重量ではない。ケース、配線、将来のアーム等は車体側へ加算する。

## 駆動力と輪荷重

平坦な床、加減速度0.2m/s²、転がり抵抗係数0.03、タイヤ直径100.7mm、左右均等駆動を仮定する。

| 車体の比較条件（全て荷物10kg追加） | 車体kg | 必要トルク/輪 | 選定余裕1.5倍込み |
|---|---:|---:|---:|
'''
for t in p['same_cargo_torque_comparisons']:
    payload+=f"| {t['revision']} | {t['base_mass_kg']:.3f} | {t['service_torque_Nm_each']:.3f}N·m | {t['with_margin_Nm_each']:.3f}N·m |\n"
payload+=f'''
[M0601C_111メーカー仕様](https://shop.directdrive.com/pages/m0601c-111-specs)の定格0.96N·mとの数値比較を通る。低速連続運転の発熱、向きを変えるキャスターの抵抗、タイヤのこじり、実際の停止性能は別途確認する。

車体10.5kgまでの通常条件で、モーターの保守的ラジアル荷重比較は{rad['radial_N']:.2f}N／表示120N、軸方向{rad['axial_N']:.2f}N／表示60N。キャスターはトレール公差を含み通常条件で最大{p['caster_normal_maximum_with_trail_tolerance_N']:.2f}N／表示300N。複合荷重や衝撃までの認定ではない。

車体重心X±25・Y±15・床上160mm以下、荷物重心X/Y±30・床上330mm以下を継続する。使用範囲は平坦な屋内床。追加機械ブレーキは採用しない。実機の荷重・温度・保持・停止試験は未実施。

[質量台帳・計算結果](payload_budget.json)／[再計算スクリプト](check_payload_budget.py)／[全荷重計算](../load_calculations.json)／[費用とBOM](BOM.ja.md)
'''
(HERE/'PAYLOAD_REVIEW.ja.md').write_text(payload)

floor=f'''# D6.4：皿穴をなくし、通常ねじと大径座金で固定

旧D6.1は各板3点、内側2本の間隔20mm、中央継ぎ目の張り出し約50mmだった。**各板4点・計16点へ変更し、固定位置をX方向200mm、Y方向115mmに分散した。**

![各板4点の固定を見せたFreeCAD実画面](cad-screen-floor-fixings-top.png)

| 板 | 外側400mmレール・M6 | 外側400mmレール隅・M6 | 端300mmレール・M6 | 中央支持梁・M4通常ねじ |
|---|---|---|---|---|
'''
for xsgn,ysgn,label in [(-1,1,'後左'),(-1,-1,'後右'),(1,1,'前左'),(1,-1,'前右')]:
    floor+='| '+label+' | '+' | '.join(f'({xsgn*x}, {ysgn*y})' for x,y in [(25,135),(185,135),(215,20),(15,25)])+' |\n'
floor+=f'''
座標はmm、車体中心を原点、X前方・Y左方。**3点は3030へ直接固定し、4点目は両端を3030へ固定した支持梁を介して留める。** 隣の板だけを相手にしたねじ留めではない。

![裏リブと中央支持梁・FreeCAD実画面](cad-screen-floor-support-under.png)

支持梁はPLA製64×100×25mm。両端の各2本、合計4本のM6×12・OD18大径座金・溝ナットで内側3030の側面溝へ固定する。床から梁へはM4×16六角穴付きねじ・上下OD12×t1平座金・M4六角ナットで貫通締結する。φ4.5の通し穴で、皿加工はなくし、穴周囲に床厚2.4mmを残す。外周の角は従来からM6通常ねじ＋OD18座金であり、その構成を維持する。

PCは床と一体の10×10×5.6mm受け4個（中心X±50・Y±40）と1mm軟質パッドで支持する。PC下面は104→108mm、ねじ頭上端106.4mmとの差は1.6mm。パッドが完全に縮んでも硬い受け上面107mmとの間に0.6mmを残す。PCのケース・脚形状は未選定であり、現物公差と床の変形を含む最終確認は残る。

![中央の通常ねじ・座金・PC受け](cad-screen-floor-seam-joint.png)

![支持梁の両端固定・FreeCAD実画面](cad-screen-seam-beam-anchors.png)

各板の継ぎ目沿いに高さ15mmの裏リブを追加した。継ぎ目端からリブ開始まで14.6mm。リブは中央支持梁から端レールまで続き、既存金具の手前25mmで浅くして0.8mmの公称隙間を残す。中央梁のベルト溝は幅17mm・深さ2.5mm。PCベルトとの最小隙間{f['beam_to_PC_belt_clearance_mm']:.1f}mm、電池ベルトと裏リブの隙間{f['ribs_to_battery_belt_clearance_mm']:.1f}mmをCADで確認した。

四隅の切欠きと、平面の三角補強板4枚をD6.3で廃止した。フレームは既存の内側HBLFSN6金具8個で接合し、PLA床は別に固定する。内側レール上にあった4本の床ねじを外側の隅へ移し、追加部品を使わずに延長した角を固定する。[三案の比較と締結詳細](CORNER_REVIEW.ja.md)

## 組立と印刷

1. 内側3030へ梁の溝ナットを入れ、支持梁のM6を先に固定する。
2. 基礎フレームのHBLFSN6金具8個を各2本のM6で締める。4枚の床を載せ、各板のM6を3本、中央のM4通常ねじを1本、上下のOD12座金各1枚と共に取り付ける。M4は上から3mm六角レンチ、下から7mmナット用ソケットを入れる。PCを載せる前に締める。
3. 機器・パッド・ベルトを取り付ける。梁のM6を再調整する場合は床とM4を先に外す。

PLAを挟む部分へ金属同士と同じM6締付トルクを使わない。締付けと緩みの保持は現物で確認する。CADでは上記工程の梁ねじ用ドライバー4経路とM4ナット用ソケット4経路も検査した。

印刷対象は床4枚＋梁1個。最大229.8×149.8×26mmでP1Sの256mm範囲に収まる。5部品の中実CAD体積換算は約{grams:.0f}g。荷物ストッパ4個はD3のSTLを継承する。STLは配置座標から原点移動したデータで、印刷姿勢は未設定。床はリブを下にしてサポートを使うか、中央継ぎ目を下に立ててブリムと位置決め壁の局所サポートを検討する。梁は広い上面をベッド側とし、ベルト溝のブリッジを確認する。実スライス・サポート量・印刷試験は未完了。

## 確認した範囲

保存CADから16固定点、上下座金の座面・φ4.5通し穴の全厚2.4mm、3030への支持面、梁と各板の当たり、両端2本ずつの固定、工具経路、ベルト隙間を独立検査した。車体全体の体積干渉と、電池・PC交換の連続包絡も合格した。

リブ単独・梁単独へそれぞれ50Nを中央集中させた短時間の単純梁比較を行った。リブは床幅40mmだけを有効幅とし、端のテーパーを1mm刻みの断面積分に含めた。弾性率1000MPaと仮定したたわみは、リブ{f['short_term_elastic_screens']['panel_rib']['deflection_mm_by_E_MPa']['1000']:.2f}mm、梁{f['short_term_elastic_screens']['seam_beam']['deflection_mm_by_E_MPa']['1000']:.2f}mm。1000MPaは感度確認用の仮定で、許容値ではない。[メーカー資料](https://store.bblcdn.com/s1/default/58b85d0f3db94878854a28fdb8a0006e/Bambu_PLA_Basic_Technical_Data_Sheet.pdf)のXY曲げ弾性率2750±160MPaも比較値として記録した。

実CADの床4枚＋支持梁について、電装2.4kgとPLA自重を与えた二次四面体解析も追加した。100%充填の均質体・E=1000MPaを仮定し、機器を10mm角の脚4個で受ける場合、最大たわみは重力だけで{pla_feet[0]['max_down_mm']:.2f}mm、ベルト張力10N／脚で{pla_feet[10]['max_down_mm']:.2f}mm、30N／脚で{pla_feet[30]['max_down_mm']:.2f}mm。粗細2メッシュを比較し、荷重と反力のつり合いを検査した。局所応力は収束未確認。[計算条件・応力・ねじ締付け・改善点](pla-strength/README.ja.md)

このPLA床は電装用で、荷物15kgを支える上段の金属構造とは別。D6.4で中央の皿穴をなくした。大径座金の床接触面は約97.19mm²、旧皿頭34.24mm²の約2.84倍。ただし全体たわみは同程度で、ベルト反力と締付けの検証が必要。印刷方向・長期クリープ・機器温度・締付け軸力まで含む安全率2は未確認。実物の既知重量・測定したベルト張力で解析を照合し、実機相当温度での保持を確認して使用範囲を決める。暫定の印刷条件は上記計算書に記載した。

前版D6.2との重量差は{delta_word}。PLA材料消費の参考増額は{filament_delta:,}円（2円/gの既存基準）。今回の金具・ねじの追加は0個。三角板4枚とM6ねじ・座金・溝ナット各8個を削除し、床ねじ4組を隅へ移設する。三角板の素材仮枠500円を除き、計上小計は410円減。ねじ類の購入パック価格は未確定のため、16点のねじ・座金削減による金額効果を追加で差し引かない。従来の未計上価格は残るが、今回の追加金属切断・穴加工・CNC見積は発生しない。

[全検査値](floor_support_review.json)／[検査スクリプト](review_floor_support.py)／[印刷ZIP](D6-first-floor-print-files.zip)／[全車BOM](BOM.ja.md)
'''
(HERE/'FLOOR_REVIEW.ja.md').write_text(floor)

readme=f'''# D6.4：PLA床の皿穴を廃止、通常ねじ＋大径座金へ

**PC下の中央4本をM4通常ねじ＋上下OD12座金へ変更し、皿穴周辺の0.65mmの薄肉をなくした。PC受けを床に一体印刷し、PC座面だけ4mm高くする。** 各床4点・計16点固定、角のM6＋大径座金、中央の両端支持を維持する。 車体推計{mass:.3f}kg、前版から{delta_word}。車体10kgは目安とし、通常積載目標10kgを継続する。

[床の見直し・座標・組立順](FLOOR_REVIEW.ja.md)／[重量・積載の計算](PAYLOAD_REVIEW.ja.md)／[読みやすいBOM](BOM.ja.md)

![床の16固定点・FreeCAD実画面](cad-screen-floor-fixings-top.png)

![組立・FreeCAD実画面](cad-screen-assembled.png)

電池・計算機・電源は基礎3030上の1階、格子穴アルミ荷台は2階。[参照したロボコン機体と設計理由](REFERENCE_DESIGNS.ja.md)。青い箱は未選定機器の予約外形。電池とアダプターもカタログ寸法の包絡であり、ラッチまで再現したCADではない。

| 項目 | 現行構成 |
|---|---|
| 1階床 | PLA4分割、基本厚2.4mm・裏リブ15mm、床上面101.4mm |
| 床固定 | 各板3本のM6＋OD18座金、中央1本のM4通常ねじ＋上下OD12座金 |
| 中央支持梁 | PLA64×100×25mm、両端を各2本のM6で内側3030へ固定 |
| 電池 | BL1860B113×75×62mm、アダプター95×90×30mm、座面104mm |
| PC | 120×100×60mm・0.5kgの予約、座面108mm、硬い受け4か所＋1mmパッド、上15mm通風・横30mmコネクタ空間 |
| 荷台 | 6061-T6・300×300×4mm、上面233mm、φ4.5格子穴36個・50mmピッチ |
| 上段支持 | 切断済100mm3030支柱4本＋300mm上段レール2本。下端金具各2個・上端各1個 |
| 電池交換 | 電源OFF・配線とベルト解除→8mm持上げ→後方220mm、荷台を残す |
| PC交換 | 配線・ベルト解除→8mm持上げ→側方230mm |

![リブ・支持梁を下面から確認](cad-screen-floor-support-under.png)

上下段の鉛直荷重はアルミ部材の端面で受ける。上段支柱用金具12個・M6×12ねじ24本・溝ナット24個というD6.1の根元両側補強は継続する。SUS支柱とMISUMI金具の公称寸法はCADで照合済みだが、混用の現物座面・ねじ底付き・締付け・横揺れは未検証。[上下締結画面](cad-screen-frame-joint.png)／[下端](cad-screen-frame-joint-lower.png)／[上端](cad-screen-frame-joint-upper.png)／[前回の接合部レビュー](JOINT_REVIEW.ja.md)

## 配置・交換・検査

![電池交換](cad-screen-battery-exchange.png)

![PC交換](cad-screen-computer-exchange.png)

{v['physical_parts']}物理部品・{v['checked_physical_pairs']:,}組の体積干渉、予約機器、連続交換包絡、キャスター旋回、タイヤの外向き抜出し、36格子穴、支柱金具の工具経路を検査した。保存FCStd・STEPの体積と形状を再照合し、印刷5部品の閉じたSTLを確認した。床固定の座面と工具経路も別スクリプトで検査する。電池交換上端と荷台裏締結部の余裕は16.3mm。

通常荷物10kg、構造比較荷物15kg/SF2は設計目標で、実機認定ではない。今回の比較範囲は車体10.5kgまで。車体CGはX±25・Y±15・Z160mm以下、荷物CGはX/Y±30・Z330mm以下。追加機械ブレーキなし、平坦な屋内床を対象とする。

上段レールの2倍荷重比較は応力7.13MPa・たわみ0.0253mm、支柱1本へ集中する圧縮比較は1.56MPa。天板は同じ加工形状・6固定点なので従来の板単体解析を限定的に参照する。接合部の柔軟性、PLAの長期保持、実機温度・停止性能は含まない。[部材計算と限界](structure_screening.json)

1階PLAは実形状5部品の解析を追加した。電装2.4kg＋PLA自重・100%充填相当・E=1000MPaの仮定で、脚4個の機器を載せた最大たわみは{pla_feet[0]['max_down_mm']:.2f}mm、ベルト10N／脚では{pla_feet[10]['max_down_mm']:.2f}mm。皿穴をなくして全厚2.4mmを残し、座金の支持面積を増やした。ベルト反力の課題は残る。局所応力の収束、締付けと長期保持は未確認。[PLA計算書・解析画像](pla-strength/README.ja.md)

## 四隅の見直し

四隅の61mm角の逃げを廃止し、床を外周まで伸ばした。平面三角板は廃止し、既存の内側HBLFSN6金具8個でフレームを接合する。延長した床は上から独立して締める。[上面配置・撤去・下面配置の比較](CORNER_REVIEW.ja.md)

![角の締結・FreeCAD実画面](cad-screen-corner-joint.png)

## 費用・データ

全車の途中小計は**{c['subtotal']['JPY']:,.0f}円＋{c['subtotal']['USD']:.2f}USD＋未計上分**、記録済み参考為替では約{c['full_running_subtotal_JPY_reference']:,.0f}円。今回のPLA材料消費参考は前版より{filament_delta:,}円増。中央ねじ60本770円・座金50枚288円・2店舗送料参考775円で1833円を計上した。使用するのはねじ4本と座金8枚で、新たに増える物理部品は上座金4枚。下座金4枚は交換。旧皿ねじ代は未計上だったため架空の節約分を差し引かず、途中小計は1839円増。配送先・まとめ買いで送料は再確認する。[販売ページ記録](plain_hole_fastener_observations.json)。溝ナットは70/100個使用し、追加パック不要。PLA単価2円/gは材料消費基準で、実スライス・サポート・失敗分・工賃は含まない。

荷台の製造STEP/PDFは既存D3と同一。JLCCNCの天板38.65USD、モーター金具82.25USDという実サイト見積記録を、同じ加工品として継承する（送料込み、未発注・担当者審査前）。今回の床支持で追加金属加工は不要。

- [FreeCAD](AMR01_TwoStorey_D6.FCStd)／[構造STEP](AMR01_TwoStorey_D6.step)／[電池・PC外形付きSTEP](AMR01_TwoStorey_D6-with-equipment-envelopes.step)
- [床4枚＋支持梁1個の印刷ZIP](D6-first-floor-print-files.zip)／[寸法・材料体積・印刷注意](print_manifest.json)
- [BOM・費用割合](BOM.ja.md)／[全明細CSV](BOM.csv)／[費用JSON](cost_summary.json)
- [CAD検査](validation.json)／[保存物再検査](saved_artifact_validation.json)／[床支持検査](floor_support_review.json)
- [設計要件](../requirements.json)／[電源選定](../makita-power/power_selection.json)／[成果物ハッシュ](release_manifest.json)
- [D6.4 URDF・Isaac Sim5向け手順とMuJoCo走行GIF](../../../sim/isaac_sim/README.ja.md)

実物の印刷・組立・通電・積載走行は未実施。3DプリントはP1S寸法内だが、スライサー設定と実物確認が必要。荷物ストッパはD3の[XN](../aluminum-direct-deck/PrintedStopXN.stl)・[XP](../aluminum-direct-deck/PrintedStopXP.stl)・[YN](../aluminum-direct-deck/PrintedStopYN.stl)・[YP](../aluminum-direct-deck/PrintedStopYP.stl)を継承する。
'''
(HERE/'README.ja.md').write_text(readme)

corners=read('corner_joint_review.json')
corner_text=f'''# 四隅の固定：D6.3で変更、D6.4でも維持

**四隅の切欠きをなくし、平面の三角金属板4枚を廃止した。床を外周まで伸ばし、各板4点で固定する。フレームは既存の内側HBLFSN6金具8個で接合する。** 追加部品0個、削減28部品。

![四隅を延長した床・実際のFreeCAD画面](cad-screen-floor-fixings-top.png)

## 比較と採用理由

| 案 | 利点 | 今回の判断 |
|---|---|---|
| 床の上から金属板を重ねる | 上から組みやすく、床も押さえられる | 単純な共締めではフレームの締付力がPLAのへたりに影響される。金属の圧縮止めと金具の穴位置の再設計が必要なため不採用 |
| 金属板を3030の下面へ移す | PLAを挟まずフレームを締められる | 詳細レビューで従来板の穴位置不備が判明。同じ部品を移すだけでは成立しないため不採用 |
| **三角板を外し、床の角をボルト固定** | **既存の内側金具で金属フレームを接合し、床を別締結できる。28部品と板加工を減らせる** | **初号機の設計案として採用。PLA床をフレームの筋交いとして強度計算に加えない。全車のねじれ剛性は実機確認を残す** |

ユーザーが挙げた「金属をなくしてボルト固定する」案を採用した。削除するのは追加の平面三角板で、3030同士をつなぐHBLFSN6金具は残す。コストと組立点数を減らす判断であり、10kgに合わせるために支持を削ったものではない。

## 従来の三角板で見つかった不備

D6.2保存CADから再計算すると、60×60mm直角三角板のM6穴中心が斜辺上にあり、8か所とも座金の当たりが約49.26mm²しかなかった。座金の全面積98.52mm²に対して50%で、閉じた丸穴にもなっていない。体積干渉ゼロだけではこの不備を検出できない。

当初検討した下面移設案もこの形状を引き継ぐため撤回した。将来、ねじれ試験の結果から平面補強板を追加する場合は、穴の縁距離と座面を確保した別設計とする。

## 現行の締結

![角の内側金具と独立した床ねじ・FreeCAD実画面](cad-screen-corner-joint.png)

| 部位 | 現行構成 |
|---|---|
| 基礎3030の接合 | 内側HBLFSN6金具8個、M6×12ねじ16本、HNTT6-6溝ナット16個を継続 |
| 1階床 | 四隅まで延長、各板4点固定を維持 |
| 各板の固定先 | 外側400mmレール2点・端300mmレール1点・中央支持梁1点 |
| 移す床ねじ4組 | `(±175, ±65)`→`(±185, ±135)`。ねじ・大径座金・溝ナットを流用 |
| フレームと床の関係 | フレームの金属締結にPLAを挟まない。床は電装用 |
| 廃止 | 三角板4枚＋M6ねじ8本＋座金8枚＋溝ナット8個＝28部品 |

支柱端面と根元金具を直接金属へ当てるための切欠きは、四隅の切欠きとは別なので残す。内側レールは引き続き床下面を支持する。

メーカーは[HBLFSN6](https://jp.misumi-ec.com/vona2/detail/110300442340/?HissuCode=HBLFSN6)について、2本の縦材間の横材を金具2個で支える条件で1個当たり1176Nを示す。今回の全方向の許容荷重・許容モーメントへ転用しない。現行の金属接合方式を初号機案に採用する判断で、車体全体の15kg積載・安全率2達成の証明ではない。

![平面三角板を廃止した下面・中央支持梁・裏リブ](cad-screen-floor-support-under.png)

## 重量・費用・検査

D6.2→D6.3の四隅変更は約122g減。四隅のPLAは約44.3g増え、板と締結材の削除で約{corners['removed_metal_mass_kg']*1000:.1f}g減った。現行D6.4は中央ねじ・PC受けの変更で別途{delta_word}となり、車体推計{mass:.3f}kg。

D6.2→D6.3ではPLA材料消費参考90円増（従来基準2円/g、中実体積切上げ）、三角板素材の仮枠500円を削り、計上小計410円減だった。これは四隅だけの過去比較で、D6.4のねじ・座金・PC受け変更分は別に[BOM](BOM.ja.md)へ計上する。実スライス・サポート・失敗分は含まない。基礎のねじ・座金一式仮枠2300円は購入パック未確定のため据置き。溝ナットは70/100個使用で購入パック数は変わらない。410円は確定購入額の節約ではない。

保存CADで四隅の連続形状、既存8金具の形状不変・各2本の3030への接触、16本のねじの座面と公称ねじ掛かり、床を載せる前の25mm直線工具経路を確認した。全車干渉、電池・PC交換、キャスター旋回、タイヤ交換、各床4点の固定も確認した。工具の柄全体や手の動きは再現していない。

実物の座面・締付け、前後左右の横揺れと対角ねじれ、PLAの長期保持は未確認。組立は金属骨格→支持梁→床→電装の順。必要な剛性が得られない場合は、床へ補強を負担させず金属接合を見直す。

[PLA床の実形状解析](pla-strength/README.ja.md)は鉛直の電装荷重とベルト荷重を評価するもの。床を筋交いとしてフレームの横揺れ・ねじりに寄与させた計算ではなく、三角板廃止後の骨格全体の安全率2を証明しない。

[保存CADの検査値](corner_joint_review.json)／[床固定・印刷](FLOOR_REVIEW.ja.md)／[費用表](BOM.ja.md)／[重量・積載](PAYLOAD_REVIEW.ja.md)
'''
(HERE/'CORNER_REVIEW.ja.md').write_text(corner_text)

root=ROOT/'README.md';s=root.read_text()
start=s.index('車体は**');end=s.index('\n構造比較',start)
s=s[:start]+f'車体は**推計{mass:.3f}kg**。D6.4で中央4本の皿ねじを通常ねじ＋上下の大径座金へ変更し、薄肉をなくしました。PC受けだけ4mm高くし、各床4点固定と中央の両端支持・裏リブを維持します。車体10kgは目安とし、必要な支持を優先します。**通常荷物10kgの設計目標は維持**し、車体10.5kgまでの範囲で足回りを再計算しています。[四隅の設計比較](cad/amr07/two-story/CORNER_REVIEW.ja.md)／[重量と積載](cad/amr07/two-story/PAYLOAD_REVIEW.ja.md)\n'+s[end:]
start=s.index('D5からの小計増は') if 'D5からの小計増は' in s else s.index('全車の途中小計は')
end=s.index('\n- [現行',start)
s=s[:start]+f'全車の途中小計は{c["subtotal"]["JPY"]:,.0f}円＋{c["subtotal"]["USD"]:.2f}USD＋未計上分、記録済み参考為替では約{c["full_running_subtotal_JPY_reference"]:,.0f}円。今回のねじ・座金は購入パックと掲載送料参考で1833円、PLA材料参考は{filament_delta:,}円増です。旧皿ねじ代は未計上だったため、小計は1839円増。追加加工は不要です。従来からの未計上品は残り、完成車購入総額ではありません。\n'+s[end:]
s=s.replace('電装床4枚の印刷ZIP','電装床4枚＋支持梁の印刷ZIP')
if 'pla-strength/README.ja.md' not in s:
    s=s.replace('- [現行D6：', '- [PLA床の実形状解析・たわみ画像・締付けの課題](cad/amr07/two-story/pla-strength/README.ja.md)\n- [現行D6：')
if 'cad-screen-floor-fixings-top.png' not in s:
    s=s.replace('![FreeCAD実画面：D6.3組立]', '![FreeCAD実画面：各床4点・計16点の固定](cad/amr07/two-story/cad-screen-floor-fixings-top.png)\n\n![FreeCAD実画面：D6.3組立]')
s=s.replace('D6.3','D6.4').replace('amr_d63','amr_d64')
if 'cad-screen-floor-seam-joint.png' not in s:
    s=s.replace('![FreeCAD実画面：各床4点', '![FreeCAD実画面：皿穴をなくした中央固定](cad/amr07/two-story/cad-screen-floor-seam-joint.png)\n\n![FreeCAD実画面：各床4点')
root.write_text(s)
print('D6.4 design, floor review, payload review and root summaries regenerated.')
