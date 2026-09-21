#!/usr/bin/env python3
"""Exact STEP projections plus explicit functional tolerances, two A3 sheets."""
from pathlib import Path
import hashlib
import importlib.util
import json
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
STEM = 'M0601C_mount_A6_R1'


def module(path, name):
    spec = importlib.util.spec_from_file_location(name,path)
    obj = importlib.util.module_from_spec(spec); spec.loader.exec_module(obj)
    return obj


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    a4 = module(HERE.parent/'amr05'/'make_mount_drawing.py','a4_projection')
    a5 = module(HERE.parent/'amr06'/'make_quote_drawings.py','a5_pdf')
    step = HERE/(STEM+'.step')
    params = json.loads(step.with_suffix('.json').read_text())
    assert params['motor_holes_diameter_mm']==3.2 and params['seat_axis_local_xz_mm']==[45,15.18]
    assert params['seat_large_arc_radius_mm']==9.67 and params['seat_flat_distance_mm']==8.22
    assert digest(step)==params['step_sha256']
    a4.STEP = step
    views = a4.extract_views()
    assert abs(views['volume_mm3']-params['volume_mm3_each'])<.01
    sheet1 = a4.build_svg(views,params,params['step_sha256'])
    replacements = {
        'M0601C_111 専用モータ金具 — 見積用寸法図':'M0601C_111 金具 A6-R1 — 機能公差修正版',
        '製作保留：現物照合・公差承認前の手配不可 ／ モータ側形状参照、車体側は新規設計':'見積用・製作未承認 ／ 受け軸と穴群中心は高さ0.17差 ／ 機能公差は2頁参照',
        'AMR-05 / MOUNT-Q01':'AMR-07 / MOUNT-A6-R1',
        '単位 mm　A3　寸法値優先':'単位 mm　A3　1 / 2',
        '3× Ø2.8 通し':'3× Ø3.2 +0.10/0 通し',
        'R9.70':'R9.67 BASIC',
        '背側幅7':'背側幅6.5',
        '3平面の軸距離：8.25 ±0.05（公差案）':'受け平面の軸距離8.22 BASIC、輪郭公差0.10',
        '元輪郭 +0.15。全輪郭の公差適合は未確定。':'受けZ15.18、穴群Z15.35。位置関係を変更しない。',
        '受け底 Y=18':'B：受け底 Y=18',
        '8：残る背面肉厚':'8 ±0.05：背肉',
        '部品座標：外形最小隅 O=(0,0,0)。軸中心 X45 / Z15.35。取付接触面 Z34。':'A：取付面Z34、B：端面座Y18、C：幅90の中央面X45。原点は外形最小隅。',
        '一体CNC加工。製作公差・仕上げは要承認。':'一体CNC加工。機能公差は2頁の指定による。',
        '質量参考：104 g/個（ρ=2.70、CAD値）':f"質量参考：{params['mass_kg_each_estimate']*1000:.3f} g/個（ρ=2.70）",
        '提出物：本図・STEP・加工依頼仕様':'提出物：本図2頁＋同名STEP',
        '未注記公差／内隅R／端部処理は見積時提案':'未注記寸法ISO 2768-m、2頁の指定を優先',
        '図番 MOUNT-Q01 / Rev. A':'図番 MOUNT-A6 / Rev. R1',
    }
    for old,new in replacements.items():
        assert sheet1.count(old)==1, old
        sheet1 = sheet1.replace(old,new)
    # Numeric center dimension is BASIC because its location is controlled by
    # the specified positional tolerance, not general +/- size tolerances.
    sheet1 = sheet1.replace('>18.65</text>','>18.65 BASIC</text>')
    d = a4.Drawing()
    d.raw('<svg xmlns="http://www.w3.org/2000/svg" width="420mm" height="297mm" viewBox="0 0 420 297">')
    d.raw('<g font-family="Noto Sans CJK JP, sans-serif">')
    d.rect(0,0,420,297,'white','none'); d.rect(8,8,404,281,width=.35)
    d.text(15,19,'M0601C_111 金具 A6-R1 — 機能公差・検査基準',5,weight='bold')
    d.text(405,19,'2 / 2',3.2,anchor='end')
    d.text(15,27,'同形2個、A6061-T6、生地、タップなし。自動見積用。購入ロットの現物照合・強度試験前は製作未承認。',3.1,fill='#913b2b')
    d.text(15,38,'データムと公差（寸法単位 mm。BASIC は理論的に正確な寸法）',3.8,weight='bold')
    a5.table(d,15,42,[48,202,140],[
        ['対象','指定','検査・適用'],
        ['基準 A','3030接触平面 Z34：平面度0.05','一次データム、取り付け面'],
        ['基準 B','モータ端面座 Y18：平面度0.05、直角度0.05 | A','二次データム、受け底の実接触面'],
        ['基準 C','外形X0/X90の対向面から導く中央面 X45','三次データム。左右の原点を共通化'],
        ['受け全輪郭','面の輪郭度0.10 | A | B | C、対称配置 ±0.05','形状と位置を含む総合公差。円弧だけ除外しない'],
        ['輪郭基本寸法','受け中心 X45/Z15.18、R9.67、平面軸距離8.22','6小円弧R1.62、全輪郭はSTEP BASIC'],
        ['穴群の位置','3×Ø3.2 +0.10/0、位置度 Ø0.10 | A | B | C','材料長8、全通し。PCD15.2 BASIC'],
        ['穴群 X/Z BASIC','(45,22.95)、(38.418207,11.55)、(51.581793,11.55)','群中心X45/Z15.35。受け中心から+0.17'],
        ['背肉／受け深さ','8 ±0.05 (Y10…18) ／ 9 ±0.10 (Y18…27)','端面座Bと背面の平行度0.05'],
        ['小ねじ頭側座ぐり','3×Ø6.2 +0.10/0、深0.50±0.05、中心は各穴と同じ','位置度Ø0.10 | A | B | C、底面平行度0.05 | B'],
        ['3030通し穴','2×Ø6.6 +0.20/0、X/Y=(7.5,15),(82.5,15)','フランジ5±0.10。溝に沿う位置は±0.20'],
    ],row_h=7.6,size=2.8)
    d.text(15,138,'輪郭度は切欠き以外の受け壁に適用。背側配線幅6.5±0.10、前・下端9.5は一般公差。R9.67に別の位置誤差±0.05を加算しない。',2.9)
    d.text(15,145,'データムA/Bを侵す面取り不可。バリ取りC0.1以下。M6頭側はC0.3±0.1。厚い皮膜なし。',2.9)
    d.text(15,152,'web根元は元A4同様。形状に影響する工具Rは提案・再審査。全体へ±0.05を一律指定するものではない。',2.9)
    d.text(15,161,'組付け条件と公差の使い方（完成機の許容荷重・安全率を証明する記載ではない）',3.8,weight='bold')
    lines = [
        '1. 公称モータ軸Z15.35、受け軸Z15.18。タイヤ反力側の輪郭（車体+Z）へボスを着座させて端面を締結。',
        '2. 公表ボスØ18.85…19.05／平面距離7.85…8.15の条件で着座量0.04…0.295、穴群中心から−0.130…+0.125。',
        '3. 金具孔位置半径0.05＋実モータ孔群偏心0.05以下を受入条件とする。モータ側0.05は未確認の条件。',
        '4. 最大中心差0.130+0.10=0.230 < (3.2−2.5)/2=0.350。片側余裕0.120は上記条件が成立した場合のみ。',
        '5. M2.5×12＋小径座金t0.5、座ぐり底背肉7.5で公称ねじ込み4。首元・座金・穴底を現物確認。',
        '6. 3本の同時挿入、荷重側輪郭接触、端面/頭/座金の全周座り、配線φ6予約を確認。全面同時接触とは仮定しない。',
        '7. 装着高さ・タイヤの荷重たわみを測り、キャスター接地を再調整。CAD公称接地0は現物の高さ保証ではない。',
        '8. 材質証明、ねじ規格、実ナット/フレーム溝寸法、接触・ねじ山・溝縁の荷重確認後に製作/運用を判断。',
    ]
    for i,line in enumerate(lines): d.text(15,170+i*9,line,2.9)
    d.text(15,248,'比較基準：A4 幅90/厚5/孔ピッチ75を維持。D5幅75/厚6は価格低減せず、今回の採用対象から外す。',3)
    d.text(15,257,'引用元の motor STEP / メーカー寸法図 / 公開ブラケット輪郭は MOUNT_INTERFACE_REVIEW.ja.md を参照。',2.9)
    d.line(8,266,412,266,width=.3)
    d.text(15,274,'MOUNT-A6 / Rev. R1 / 見積用・製作未承認 / 2026-09-21',3.2,weight='bold')
    d.text(15,283,'STEP SHA-256: '+params['step_sha256'],2.6)
    d.raw('</g></svg>')
    sheet2 = '\n'.join(d.items)
    svg = step.with_suffix('.svg'); notes=HERE/(STEM+'_notes.svg'); pdf=step.with_suffix('.pdf')
    svg.write_text(sheet1); notes.write_text(sheet2)
    ET.parse(svg); ET.parse(notes)
    a5.render_pdf([svg,notes],pdf,'A6-R1')
    manifest = {'revision':'A6-R1','status':'quotation_only_not_manufacturing_release','pdf_pages':2,
        'step_sha256':digest(step),'pdf_sha256':digest(pdf),'svg_sha256':digest(svg),'notes_svg_sha256':digest(notes),
        'drawing_generator_sha256':digest(Path(__file__)),
        'functional_tolerance_total_profile_mm':.1,'position_diameter_mm':.1,
        'critical_back_wall_tolerance_pm_mm':.05,'projection_source':'exact same-stem STEP',
        'bbox_mm':views['bbox_mm'],'volume_mm3':views['volume_mm3']}
    (HERE/(STEM+'_drawing.json')).write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest))


if __name__=='__main__': main()
