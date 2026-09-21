#!/usr/bin/env python3
"""Create exact-projection, two-sheet quotation drawings for A5 candidates.

Run after build_mount_candidates.py with system Python 3.  Reuses the A4
headless STEP/TechDraw projection and drawing primitives; no GUI is used and
no A4 files are modified.  Requires freecadcmd, PyGObject/Rsvg and pycairo.
The main SVG is sheet 1; *_notes.svg is sheet 2; the same-stem PDF has both.
Existing drawing snapshots are hash-checked and never overwritten.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
OUT = HERE / "candidates"
A4_DRAWER = HERE.parent / "amr05" / "make_mount_drawing.py"
spec = importlib.util.spec_from_file_location("a4_quote_drawing", A4_DRAWER)
a4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a4)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"A4 drawing template changed; review replacement: {old}")
    return text.replace(old, new, 1)


def candidate_priority(cid):
    return {"D1": "第一見積候補", "D2": "加工費比較用・採用推奨なし",
            "D3": "根元長辺2本の加工費比較・採用未定",
            "D4": "受けRのみ変更の加工費比較・採用未定",
            "D5": "幅75・板厚6の加工費比較・採用未定"}[cid]


def root_labels(params):
    count = params["web_flange_root_edge_count"]
    if params["candidate_id"] == "D5":
        return ("根元長辺2本 R2.0", "X方向長辺2本だけR2.0", "Z28：Y10/27のX15…60、長さ45×2辺", "端辺X15/60はR追加なし")
    if count == 4:
        return ("根元4辺 R2.0", "4凹エッジの根元R2.0", "Z29：X15/75のY10…27、Y10/27のX15…75", "全4辺 R2.0、肉を追加する丸み")
    if count == 2:
        return ("根元長辺2本 R2.0", "X方向長辺2本だけR2.0", "Z29：Y10/27のX15…75、長さ60×2辺", "端辺X15/75はA4同様、R追加なし")
    assert count == 0
    return ("根元R追加なし", "根元形状はA4同様、R追加なし", "Z29：4根元辺ともモデル上は直角", "数学的なゼロRの加工保証は指定しない")


def extract_views(step, params):
    """Use real STEP projections and a shaft-center section for any width."""
    if params["overall_LWH_mm"] == [90, 30, 34]:
        a4.STEP = step
        return a4.extract_views()
    exe = shutil.which("freecadcmd")
    if not exe:
        raise RuntimeError("freecadcmd is required")
    axis_x = params["quote_axis_local_xz_mm"][0]
    with tempfile.TemporaryDirectory(prefix="amr06-compact-drawing-") as folder:
        folder = Path(folder)
        out, macro = folder/"views.json", folder/"extract.py"
        macro.write_text(
            "import json\nimport Part,FreeCAD as App,TechDraw\n"
            f"s=Part.Shape();s.read({str(step)!r})\n"
            "b=s.BoundBox;source_min=[b.XMin,b.YMin,b.ZMin]\n"
            "s.translate(App.Vector(-b.XMin,-b.YMin,-b.ZMin));b=s.BoundBox\n"
            "assert s.isValid() and len(s.Solids)==1\n"
            f"assert max(abs(a-bb) for a,bb in zip([b.XLength,b.YLength,b.ZLength],{params['overall_LWH_mm']!r}))<1e-5\n"
            f"x={axis_x!r}\n"
            "plane=Part.Face(Part.makePolygon([App.Vector(x,-10,-10),App.Vector(x,40,-10),App.Vector(x,40,50),App.Vector(x,-10,50),App.Vector(x,-10,-10)]))\n"
            "loops=[]\n"
            "for edges in Part.sortEdges(s.section(plane).Edges):\n"
            " w=Part.Wire(edges);assert w.isClosed()\n"
            " loops.append([[p.y,p.z] for p in w.discretize(Deflection=0.005)])\n"
            "r={'valid':s.isValid(),'solids':len(s.Solids),'volume_mm3':s.Volume,'bbox_mm':[b.XLength,b.YLength,b.ZLength],'source_min_mm':source_min,'section_loops_yz_mm':loops}\n"
            "for name,direction in [('front',App.Vector(0,1,0)),('side',App.Vector(1,0,0)),('top',App.Vector(0,0,1))]:r[name]=TechDraw.projectToSVG(s,direction)\n"
            f"open({str(out)!r},'w').write(json.dumps(r))\n")
        proc = subprocess.run([exe, str(macro)], env=dict(os.environ, QT_QPA_PLATFORM="offscreen"), capture_output=True, text=True)
        if proc.returncode or not out.exists():
            raise RuntimeError(proc.stdout+proc.stderr)
        return json.loads(out.read_text())


def make_compact_sheet1(views, params, step_hash):
    """Dedicated 75 mm wide / 6 mm thick drawing, never reuse 90 mm labels."""
    assert params["candidate_id"] == "D5"
    assert params["overall_LWH_mm"] == [75, 30, 34] and params["flange_thickness_mm"] == 6
    d = a4.Drawing()
    d.raw('<svg xmlns="http://www.w3.org/2000/svg" width="420mm" height="297mm" viewBox="0 0 420 297">')
    d.raw('<title>M0601C_111 D5 compact mount — quotation only — sheet 1 of 2</title>')
    d.raw('<desc>Exact STEP projections; 75x30x34, flange 6, web45, pitch60. Not approved for manufacturing or loads.</desc>')
    d.raw('<defs><pattern id="hatch" width="2.2" height="2.2" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="2.2" stroke="#a3afb8" stroke-width="0.35"/></pattern><clipPath id="detailClip"><rect x="282" y="156" width="98" height="92"/></clipPath></defs>')
    d.raw('<g font-family="Noto Sans CJK JP, sans-serif">')
    d.rect(0, 0, 420, 297, "white", "none")
    d.rect(8, 8, 404, 281, width=.35)
    d.text(15, 19, "M0601C_111 金具 D5 — 幅75・板厚6 見積用寸法図", 4.8, weight="bold")
    d.text(15, 26, "製作未承認 ／ 小型化と厚板化の比較候補 ／ 現物照合・公差・荷重条件の承認前は製作保留", 3.1, fill="#913b2b")
    d.text(406, 19, "AMR-06 / MOUNT-D5", 3.1, anchor="end")
    d.text(406, 25, "単位 mm　A3　寸法値優先　1 / 2", 2.9, anchor="end")
    # Front: actual 75 mm width, centered at drawing X120 with a 2:1 scale.
    d.projection(views['front'], [0,-2,2,0,45,113], 2)
    d.hdim(45,195,45,35,"75")
    d.vdim(45,113,45,29,"34")
    d.vdim(45,57,195,211,"6")
    d.vdim(45,82.3,195,229,"18.65")
    d.hdim(75,165,113,121,"45")
    d.hdim(110.5,129.5,113,131,"9.5")
    d.cross(120,82.3,22)
    d.circle(120,82.3,15.2,"3 1 .5 1")
    d.leader([(120,67.1),(153,63),(180,63)],"3× Ø2.8 通し",181,62)
    d.leader([(132,72.95),(159,85),(180,85)],"PCD 15.2",181,84)
    d.text(120,141,"モータ側正面（+Y側から）  2:1",3.2,anchor="middle",weight="bold")
    # Exact section through the D5 local shaft X37.5.
    sx, sy = 274, 45
    d.projection(views['side'],[0,-2,-2,0,sx,sy+68],2,color="#b3bac0",width=.17)
    for loop in views['section_loops_yz_mm']:
        points=" ".join(f"{sx+2*y:g},{sy+2*(34-z):g}" for y,z in loop)
        d.raw(f'<polygon points="{points}" fill="url(#hatch)" stroke="#142433" stroke-width="0.3"/>')
    d.hdim(274,334,45,35,"30")
    d.hdim(294,310,82,95,"8")
    d.hdim(310,328,76,95,"9")
    d.hdim(294,328,113,119,"17")
    d.text(310,129,"軸中心 X=37.5 の断面  2:1",3.1,anchor="middle",weight="bold")
    d.text(310,134,"薄灰色は外形投影。下側は配線開口。",2.7,anchor="middle")
    d.leader([(310,80),(349,85)],"受け底 Y=18",351,86)
    d.leader([(328,68),(350,67)],"入口 Y=27",351,68)
    d.leader([(294,72),(350,76)],"背面 Y=10",351,77)
    d.text(350,99,"9：受け深さ",2.9)
    d.text(350,105,"8：残る背面肉厚",2.9)
    # Top: pitch60, both end offsets 7.5, and a 45 mm web reference.
    d.projection(views['top'],[2,0,0,-2,45,228],2)
    d.raw('<rect x="75" y="174" width="90" height="34" fill="none" stroke="#82909a" stroke-width="0.18" stroke-dasharray="3 1"/>')
    for x in (60,180): d.cross(x,198,10)
    d.line(45,198,195,198,"#788793",.16,"4 1 .5 1")
    d.hdim(60,180,198,154,"60")
    d.vdim(168,228,45,29,"30")
    d.vdim(168,198,195,212,"15")
    d.hdim(45,60,228,240,"7.5")
    d.leader([(180,198),(203,242),(168,242)],"2× Ø6.6 通し",166,243,anchor="end")
    d.text(120,251,"3030接触面（+Z側から）  2:1",3.2,anchor="middle",weight="bold")
    d.text(30,258,"破線：下側web外周。全て通し穴、タップなし。",2.75)
    # Detail uses the real front projection with the new local shaft position.
    d.text(330,148,"受け部詳細  4:1",3.2,anchor="middle",weight="bold")
    d.raw('<g clip-path="url(#detailClip)">')
    d.projection(views['front'],[0,-4,4,0,180,256.4],4,width=.29)
    d.raw('</g>')
    d.cross(330,195,36)
    d.circle(330,195,30.4,"3 1 .5 1")
    d.leader([(340,157.5),(377,157.5)],"R9.70",379,158.5)
    d.leader([(311.538962,160.975446),(277,176),(249,176)],"6× R2.0",249,181)
    d.leader([(343,204),(386,215)],"背側幅7",387,216)
    d.leader([(347,237),(385,237)],"前側幅9.5",387,238)
    d.text(253,157,"輪郭はSTEP参照",2.8)
    d.text(249,251,"受け平面の軸距離：8.25 ±0.05（見積公差）",3.0)
    d.text(249,257,"元輪郭 +0.15、接点を保つR変更。現物照合前。",2.75)
    d.text(249,263,"下端から6 mmまでは背側も幅9.5へ開放。",2.75)
    d.text(249,269,"受け6箇所 R2.0 ／ web–flange 長辺2本 R2.0（2頁参照）",2.55)
    d.text(15,266,"原点：外形最小隅。軸X37.5 / Z15.35。接触面Z34・頭座面Z28。",2.75)
    d.line(8,270,412,270,width=.3)
    for x in (120,234,320): d.line(x,270,x,289,width=.25)
    d.text(12,276,"材質：A6061-T6 ／ 同形2個",3.2,weight="bold")
    d.text(12,282,"一体CNC加工。公差・強度の承認前は製作保留。",2.65)
    d.text(12,287,f"質量参考：{params['mass_kg_each_estimate']*1000:.3f} g/個（ρ=2.70）",2.6)
    d.text(124,276,"提出物：本図2頁・同名STEP",3.0)
    d.text(124,282,"見積総額 Q：2個、材料・加工・税・送料込み",2.7)
    d.text(124,287,"未注記寸法：ISO 2768-m（未承認条件）",2.6)
    d.text(238,276,f"図番 MOUNT-D5 / Rev. {params['drawing_revision']}",2.9)
    d.text(238,282,"見積用・製作未承認",3.1,weight="bold",fill="#913b2b")
    d.text(238,287,params['date'],2.6)
    d.text(324,276,"投影元：同梱STEP",2.8)
    d.text(324,282,"SHA-256（先頭16桁）",2.6)
    d.text(324,287,step_hash[:16],2.8)
    d.raw('</g></svg>')
    return "\n".join(d.items)


def make_sheet1(views, params, step_hash):
    cid = params["candidate_id"]
    radius = params["seat_small_corner_radius_mm"]
    revision = params["drawing_revision"]
    priority = candidate_priority(cid)
    markup = a4.build_svg(views, params, step_hash)
    replacements = {
        "M0601C_111 custom motor mount — quotation only": f"M0601C_111 {cid} mount — quotation only — sheet 1 of 2",
        "M0601C_111 専用モータ金具 — 見積用寸法図": f"M0601C_111 金具 {cid} — 見積用寸法図",
        "製作保留：現物照合・公差承認前の手配不可 ／ モータ側形状参照、車体側は新規設計": f"製作未承認 ／ {priority} ／ 現物照合・公差・荷重条件の承認前は製作保留",
        "AMR-05 / MOUNT-Q01": f"AMR-06 / MOUNT-{cid}",
        "単位 mm　A3　寸法値優先": "単位 mm　A3　寸法値優先　1 / 2",
        "3平面の軸距離：8.25 ±0.05（公差案）": "受け平面の軸距離：8.25 ±0.05（見積公差）",
        "元輪郭 +0.15。全輪郭の公差適合は未確定。": "元輪郭 +0.15、接点を保つR変更。現物照合前。",
        "質量参考：104 g/個（ρ=2.70、CAD値）": f"質量参考：{params['mass_kg_each_estimate']*1000:.3f} g/個（ρ=2.70）",
        "提出物：本図・STEP・加工依頼仕様": "提出物：本図2頁・同名STEP",
        "未注記公差／内隅R／端部処理は見積時提案": "未注記寸法：ISO 2768-m（未承認条件）",
        "図番 MOUNT-Q01 / Rev. A": f"図番 MOUNT-{cid} / Rev. {revision}",
    }
    for old, new in replacements.items():
        markup = replace_once(markup, old, html.escape(new) if "&" in new else new)
    extra = a4.Drawing()
    # Anchor the leader to the exact retained tangent point of the upper-left
    # relief arc.  The same point is preserved in D1 and D2 by construction.
    corner = next(c for c in params["corner_center_moves"]
                  if c["new_center_world_xz_mm"][0] < 90
                  and c["new_center_world_xz_mm"][1] > 50.35
                  and c["flat_outward_normal_xz"][0] < 0)
    cx, cz = corner["new_center_world_xz_mm"]
    nx, nz = corner["flat_outward_normal_xz"]
    tangent_x, tangent_z = cx+radius*nx, cz+radius*nz
    detail_anchor = (150+4*(tangent_x-45), 256.4-4*(tangent_z-35))
    extra.leader([detail_anchor, (277, 176), (249, 176)], f"6× R{radius:.1f}", 249, 181)
    extra.text(249, 269, f"受け6箇所 R{radius:.1f} ／ web–flange {root_labels(params)[0]}（2頁参照）", 2.55)
    markup = replace_once(markup, "</g></svg>", "\n".join(extra.items)+"\n</g></svg>")
    return markup


def table(d, x, y, widths, rows, row_h=8, size=3):
    total = sum(widths)
    for index, row in enumerate(rows):
        d.rect(x, y+index*row_h, total, row_h, "#edf2f5" if index == 0 else "white", "#a7b1b8", .16)
        cur = x
        for col, (width, text) in enumerate(zip(widths, row)):
            if col:
                d.line(cur, y+index*row_h, cur, y+(index+1)*row_h, "#a7b1b8", .16)
            d.text(cur+2, y+index*row_h+5.5, str(text), size,
                   weight="bold" if index == 0 else "normal")
            cur += width
    return y+len(rows)*row_h


def make_sheet2(params, step_hash):
    cid = params["candidate_id"]
    radius = params["seat_small_corner_radius_mm"]
    retained = params["radial_support_retained_ratio"]*100
    arc = params["radial_support_faces"][0]["arc_length_mm"]
    v = params["volume_comparison"]
    roots = root_labels(params)
    compact = cid == "D5"
    axis = params["quote_axis_local_xz_mm"][0]
    origin = params["quote_origin_world_mm"][0]
    width = params["overall_LWH_mm"][0]
    web = params["web_width_thickness_mm"][0]
    thick = params["flange_thickness_mm"]
    pitch = params["frame_hole_pitch_mm"]
    motor_coordinates = "、".join(f"({h['center_world_xz_mm'][0]-origin:.4f},{h['center_world_xz_mm'][1]-35:.2f})" for h in params['holes']['motor'])
    d = a4.Drawing()
    d.raw('<svg xmlns="http://www.w3.org/2000/svg" width="420mm" height="297mm" viewBox="0 0 420 297">')
    d.raw(f'<title>M0601C_111 {cid} mount — quotation only — sheet 2 of 2</title>')
    d.raw('<desc>Quotation conditions, nominal local coordinates and measured support geometry. No manufacturing approval, load rating, complete fit or safety-factor certification.</desc>')
    d.raw('<g font-family="Noto Sans CJK JP, sans-serif">')
    d.rect(0, 0, 420, 297, "white", "none")
    d.rect(8, 8, 404, 281, width=.35)
    d.text(15, 19, f"M0601C_111 金具 {cid} — 加工条件・機能寸法・比較記録", 5, weight="bold")
    d.text(406, 19, f"Rev. {params['drawing_revision']}　2 / 2", 3.1, anchor="end")
    d.text(15, 27, "製作未承認：この資料は見積比較用。安全率2、全輪郭のはめあい、公差累積、加工工程の成立を認定しない。", 3.2, fill="#913b2b")

    d.text(15, 38, "見積条件（A4と同じ公差範囲）", 3.8, weight="bold")
    table(d, 15, 42, [59, 331], [
        ["項目", "指定・依頼内容"],
        ["数量・材質・処理", "同形2個、A6061-T6、表面処理なし。左右用は同じ部品。製造10日の比較条件、納期確約ではない。"],
        ["特別公差", "受け平面の軸距離8.25 ±0.05 mmのみ。穴位置やRへ新たな±0.05指定を追加していない。"],
        ["その他の寸法", "ISO 2768-mを見積条件とする。幾何公差・穴位置・全輪郭適合は現物ロット確認後に決める。"],
        ["仕上げ・形状変更", "バリ取り。接触平面・受け深さ・ねじ座面を削らない。STEP輪郭や内隅Rの変更は製作前に要確認。"],
    ], size=3.0)

    d.text(15, 91, "部品座標と加工対象（形状は同名STEP、1頁の実投影を参照）", 3.8, weight="bold")
    d.text(15, 98, f"O=外形最小隅。車体座標から({origin:g},120,35) mmを引いた座標。軸X{axis:g}/Z15.35、3030接触面Z34。", 3)
    table(d, 15, 102, [66, 192, 132], [
        ["対象", "局所座標・寸法 mm", "注記"],
        ["外形／根元", f"{width:g}×30×34、flange t{thick:g}、web{web:g}×17", roots[1]],
        ["受け／背肉", "前面Y27、底Y18、背面Y10", "受け深さ9、背肉8"],
        ["根元", roots[2], roots[3]],
        ["受け輪郭", f"大円弧R9.70、6小円弧R{radius:.1f}、軸距離8.25 ±0.05", "接点を保ち小円弧中心を移動"],
        ["モータ穴", "3×Ø2.8、PCD15.2、材料内長8（Y10…18）", "全通し穴、タップなし"],
        ["モータ穴 X/Z", motor_coordinates, "CAD座標参照値、追加の公差指定ではない"],
        ["3030穴 X/Y", f"2×Ø6.6：(7.5,15)、({width-7.5:g},15)、pitch{pitch:g}", f"材料内長{thick:g}（Z{34-thick:g}…34）、全通し"],
        ["ケーブル開口", "背側幅7、前側と下端Z0…6は幅9.5", "背側のM2.5頭座面を残す"],
    ], size=2.95)

    d.text(15, 191, "変更前A4からの幾何比較（加工費・荷重性能の保証値ではない）", 3.8, weight="bold")
    table(d, 15, 195, [82, 158, 150], [
        ["計測項目", f"{cid} の値", "解釈・限界"],
        ["支持平面の有効長", "斜め2面：各10.117806、下側：0.308903×2片", "全4片を維持。下側を同等の第3支持面としない"],
        ["R9.70円弧の有効長", f"3箇所：各{arc:.6f}、A4比{retained:.1f}%", "隙間ばめ。全壁の同時全面接触は未確認"],
        ["追加／除去体積 mm³", f"根元追加{v['root_fillets_added_mm3']:.6f} ／ 受け除去{v['seat_relief_removed_mm3']:.6f}", "受け背肉保持、M6ピッチ変更。1 solid / valid" if compact else "背肉減少0、5穴・外形を維持。1 solid / valid"],
        ["質量／候補の扱い", f"{params['mass_kg_each_estimate']*1000:.3f} g/個、ρ=2.70 g/cm³", candidate_priority(cid)],
    ], size=2.95)
    if compact:
        d.text(15, 242, "M6×12：頭座面の車体Z63、先端Z75。簡略ナットZ71…75と公称一致。有効ねじ長・公差・工具接近は未確認。", 2.95)
        d.text(15, 249, "幅縮小＋厚板化の見積比較案。穴・局所応力・接合・実接触の認定なし。M2.5の3本だけへ全荷重を逃がす仕様ではない。", 2.95)
    else:
        d.text(15, 242, "CADの公称形状と製造工具の選定は別。CAM、実公差、実機接触、輪荷重・横力、車体干渉は別途確認する。", 3.0)
        d.text(15, 249, "回り止めの平面・円弧を残す設計。M2.5の3本だけへ全荷重を逃がす仕様ではない。現物照合と強度確認前は製作保留。", 2.95)
    d.text(15, 259, f"投影・座標元：{params['step_file']}", 3.0)
    d.text(15, 265, f"STEP SHA-256：{step_hash}", 2.7)
    d.line(8, 270, 412, 270, width=.3)
    d.text(15, 278, f"AMR-06 / MOUNT-{cid} / Rev. {params['drawing_revision']}", 3.2, weight="bold")
    d.text(15, 285, "単位 mm。寸法値優先。A4原本・旧見積から独立したA5候補。", 2.9)
    d.text(405, 278, params["date"], 3, anchor="end")
    d.text(405, 285, "見積用・製作未承認", 3.1, anchor="end", weight="bold", fill="#913b2b")
    d.raw('</g></svg>')
    return "\n".join(d.items)


def render_pdf(svg_paths, pdf, candidate_id):
    import cairo
    import gi
    gi.require_version("Rsvg", "2.0")
    from gi.repository import Rsvg
    width, height = 420*72/25.4, 297*72/25.4
    surface = cairo.PDFSurface(str(pdf), width, height)
    surface.set_metadata(cairo.PDF_METADATA_TITLE, f"M0601C_111 {candidate_id} mount — quotation only — not released")
    ctx = cairo.Context(surface)
    for path in svg_paths:
        handle = Rsvg.Handle.new_from_file(str(path))
        viewport = Rsvg.Rectangle()
        viewport.x = viewport.y = 0
        viewport.width, viewport.height = width, height
        if not handle.render_document(ctx, viewport):
            raise RuntimeError(f"SVG rendering failed: {path}")
        ctx.show_page()
    surface.finish()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", nargs="+")
    args = parser.parse_args(argv)
    template_hash = sha256(A4_DRAWER)
    manifest = json.loads((OUT/"candidate_manifest.json").read_text())
    output = []
    for candidate in manifest["candidates"]:
        if args.candidates and candidate["candidate"] not in args.candidates:
            continue
        step = OUT/candidate["step"]
        params = json.loads((OUT/candidate["json"]).read_text())
        step_hash = sha256(step)
        assert step_hash == params["step_sha256"] == candidate["step_sha256"]
        snapshot = OUT/(step.stem+"_drawing.json")
        if snapshot.exists():
            frozen = json.loads(snapshot.read_text())
            assert frozen["step_sha256"] == step_hash
            for file, key in [(step.with_suffix(".svg"), "svg_sha256"),
                              (step.with_name(step.stem+"_notes.svg"), "notes_svg_sha256"),
                              (step.with_suffix(".pdf"), "pdf_sha256")]:
                assert file.exists() and sha256(file) == frozen[key]
            output.append({"candidate": params["candidate_id"], "status": "retained_existing_snapshot_hash_verified"})
            continue
        compact = params["candidate_id"] == "D5"
        expected = {"flange_thickness_mm": 6 if compact else 5, "seat_depth_mm": 9, "rear_wall_mm": 8,
                    "seat_flat_distance_mm": 8.25, "seat_large_arc_radius_mm": 9.70,
                    "motor_holes_diameter_mm": 2.8, "motor_holes_PCD_mm": 15.2,
                    "frame_holes_diameter_mm": 6.6, "frame_hole_pitch_mm": 60 if compact else 75,
                    "cable_through_throat_width_mm": 7, "cable_front_and_lower_relief_width_mm": 9.5,
                    "web_flange_root_radius_mm": 0.0 if params["candidate_id"] == "D4" else 2.0,
                    "web_flange_root_edge_count": {"D1": 4, "D2": 4, "D3": 2, "D4": 0, "D5": 2}[params["candidate_id"]]}
        for key, value in expected.items():
            if abs(params[key]-value) > 1e-8:
                raise ValueError(f"Drawing annotations need revision: {key}")
        if params["overall_LWH_mm"] != [75 if compact else 90, 30, 34] or params["web_width_thickness_mm"] != [45 if compact else 60, 17]:
            raise ValueError("Drawing outline dimensions need revision")
        assert not params["tolerance_scope"]["new_hole_position_or_profile_tolerances_added"]
        views = extract_views(step, params)
        assert abs(views["volume_mm3"]-params["volume_mm3_each"]) < .01
        svg = step.with_suffix(".svg")
        notes = step.with_name(step.stem+"_notes.svg")
        pdf = step.with_suffix(".pdf")
        svg.write_text((make_compact_sheet1 if compact else make_sheet1)(views, params, step_hash))
        notes.write_text(make_sheet2(params, step_hash))
        ET.parse(svg)
        ET.parse(notes)
        render_pdf([svg, notes], pdf, params["candidate_id"])
        record = {"candidate": params["candidate_id"], "revision": params["drawing_revision"],
                  "status": "quotation_only_not_manufacturing_or_strength_release", "pdf_pages": 2,
                  "step_sha256": step_hash, "svg_sha256": sha256(svg), "notes_svg_sha256": sha256(notes),
                  "pdf_sha256": sha256(pdf), "drawing_generator_sha256": sha256(__file__),
                  "a4_drawing_template_sha256": template_hash,
                  "projection_source": "Exact same-stem STEP using headless FreeCAD TechDraw.projectToSVG",
                  "center_section_source": f"Exact STEP section at local X{params['quote_axis_local_xz_mm'][0]:g}; display discretization deflection 0.005 mm",
                  "bbox_mm": views["bbox_mm"], "volume_mm3": views["volume_mm3"],
                  "valid": views["valid"], "solids": views["solids"],
                  "section_loops": len(views["section_loops_yz_mm"]),
                  "files": [svg.name, notes.name, pdf.name]}
        snapshot.write_text(json.dumps(record, ensure_ascii=False, indent=2)+"\n")
        output.append(record)
    assert sha256(A4_DRAWER) == template_hash
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
