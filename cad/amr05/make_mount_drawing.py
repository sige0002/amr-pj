#!/usr/bin/env python3
"""Create an A3 quotation drawing from the real STEP, using headless FreeCAD.

Run with system Python 3. Requires freecadcmd, PyGObject/Rsvg and pycairo.
No FreeCAD GUI document is opened. SVG/PDF are quotation documents, not releases.
The STEP is translated internally to its minimum bounding-box corner, so the
source may use assembly coordinates or local part coordinates.
"""
from __future__ import annotations

import hashlib
import html
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
STEP = HERE / "M0601C_custom_mount_quote.step"
PARAMS = HERE / "custom_mount_dimensions.json"
SVG = HERE / "M0601C_custom_mount_quote.svg"
PDF = HERE / "M0601C_custom_mount_quote.pdf"
DATE = "2026-09-21"
NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)


def extract_views():
    exe = shutil.which("freecadcmd")
    if not exe:
        raise RuntimeError("freecadcmd is required for STEP projections")
    with tempfile.TemporaryDirectory(prefix="amr05-mount-drawing-") as folder:
        folder = Path(folder)
        out = folder / "views.json"
        macro = folder / "extract_views.py"
        macro.write_text(
            "import json\nimport Part, FreeCAD as App, TechDraw\n"
            f"s=Part.Shape();s.read({str(STEP)!r})\n"
            "b=s.BoundBox\n"
            "source_min=[b.XMin,b.YMin,b.ZMin]\n"
            "s.translate(App.Vector(-b.XMin,-b.YMin,-b.ZMin))\n"
            "b=s.BoundBox\n"
            "assert s.isValid() and len(s.Solids)==1\n"
            "assert max(abs(a-bb) for a,bb in zip([b.XLength,b.YLength,b.ZLength],[90,30,34]))<1e-5\n"
            "plane=Part.Face(Part.makePolygon([App.Vector(45,-10,-10),App.Vector(45,40,-10),App.Vector(45,40,50),App.Vector(45,-10,50),App.Vector(45,-10,-10)]))\n"
            "sec=s.section(plane)\n"
            "section_loops=[]\n"
            "for edges in Part.sortEdges(sec.Edges):\n"
            " w=Part.Wire(edges)\n"
            " assert w.isClosed()\n"
            " pts=w.discretize(Deflection=0.005)\n"
            " section_loops.append([[p.y,p.z] for p in pts])\n"
            "result={'valid':s.isValid(),'solids':len(s.Solids),'volume_mm3':s.Volume,'bbox_mm':[b.XLength,b.YLength,b.ZLength],'source_min_mm':source_min,'section_loops_yz_mm':section_loops}\n"
            "for name,direction in [('front',App.Vector(0,1,0)),('side',App.Vector(1,0,0)),('top',App.Vector(0,0,1))]:\n"
            " result[name]=TechDraw.projectToSVG(s,direction)\n"
            f"open({str(out)!r},'w').write(json.dumps(result))\n"
        )
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
        proc = subprocess.run([exe, str(macro)], env=env, capture_output=True, text=True)
        if proc.returncode or not out.exists():
            raise RuntimeError(proc.stdout + proc.stderr)
        return json.loads(out.read_text())


class Drawing:
    def __init__(self):
        self.items = []

    def raw(self, markup):
        self.items.append(markup)

    def text(self, x, y, value, size=3.1, anchor="start", weight="normal", fill="#152331"):
        self.raw(f'<text x="{x:g}" y="{y:g}" font-size="{size:g}" text-anchor="{anchor}" font-weight="{weight}" fill="{fill}">{html.escape(value)}</text>')

    def line(self, x1, y1, x2, y2, color="#334353", width=0.22, dash=None):
        attr = f' stroke-dasharray="{dash}"' if dash else ""
        self.raw(f'<line x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}" stroke="{color}" stroke-width="{width:g}"{attr}/>')

    def rect(self, x, y, w, h, fill="none", stroke="#a7b1b8", width=0.2):
        self.raw(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" fill="{fill}" stroke="{stroke}" stroke-width="{width:g}"/>')

    def circle(self, x, y, r, dash=None, color="#788793", width=0.18):
        attr = f' stroke-dasharray="{dash}"' if dash else ""
        self.raw(f'<circle cx="{x:g}" cy="{y:g}" r="{r:g}" fill="none" stroke="{color}" stroke-width="{width:g}"{attr}/>')

    def arrow(self, x, y, dx, dy, size=1.6):
        length = math.hypot(dx, dy)
        dx, dy = dx / length, dy / length
        bx, by = x + size * dx, y + size * dy
        self.raw(f'<path d="M{x:g},{y:g} L{bx-dy*.5:g},{by+dx*.5:g} L{bx+dy*.5:g},{by-dx*.5:g} Z" fill="#334353"/>')

    def hdim(self, x1, x2, ypart, ydim, label):
        for x in (x1, x2):
            self.line(x, ypart, x, ydim + (1.6 if ydim > ypart else -1.6), width=.15)
        self.line(x1, ydim, x2, ydim)
        self.arrow(x1, ydim, 1, 0)
        self.arrow(x2, ydim, -1, 0)
        width = max(6, len(label)*1.7)
        self.rect((x1+x2-width)/2, ydim-4.3, width, 3.5, "white", "none")
        self.text((x1+x2)/2, ydim-1.1, label, anchor="middle")

    def vdim(self, y1, y2, xpart, xdim, label):
        for y in (y1, y2):
            self.line(xpart, y, xdim + (1.6 if xdim > xpart else -1.6), y, width=.15)
        self.line(xdim, y1, xdim, y2)
        self.arrow(xdim, y1, 0, 1)
        self.arrow(xdim, y2, 0, -1)
        self.raw(f'<text x="{xdim-1.2:g}" y="{(y1+y2)/2:g}" transform="rotate(-90 {xdim-1.2:g} {(y1+y2)/2:g})" text-anchor="middle" font-size="3.1" fill="#334353">{html.escape(label)}</text>')

    def cross(self, x, y, half=3):
        self.line(x-half, y, x+half, y, "#788793", .16, "3 1 .5 1")
        self.line(x, y-half, x, y+half, "#788793", .16, "3 1 .5 1")

    def leader(self, coords, label, x, y, anchor="start"):
        self.raw('<polyline fill="none" stroke="#536270" stroke-width="0.18" points="'+" ".join(f"{a:g},{b:g}" for a,b in coords)+'"/>')
        self.circle(*coords[0], .45, color="#536270")
        self.text(x, y, label, 2.9, anchor=anchor)

    def projection(self, markup, matrix, scale, color="#142433", width=.26):
        group = ET.fromstring(markup)
        group.attrib.pop("transform", None)
        group.set("stroke-width", str(width/scale))
        group.set("stroke", color)
        group.set("transform", "matrix("+" ".join(f"{v:g}" for v in matrix)+")")
        for node in group.iter():
            node.attrib.pop("id", None)
        self.raw(ET.tostring(group, encoding="unicode"))


def build_svg(views, params, source_hash):
    d = Drawing()
    d.raw('<svg xmlns="http://www.w3.org/2000/svg" width="420mm" height="297mm" viewBox="0 0 420 297">')
    d.raw('<title>M0601C_111 custom motor mount — quotation only</title>')
    d.raw('<desc>Exact STEP orthographic projections and nominal quotation dimensions. Not released for manufacturing. Two identical A6061-T6 parts. Source geometry normalized to bounding-box minimum.</desc>')
    d.raw('<defs><pattern id="hatch" width="2.2" height="2.2" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="2.2" stroke="#a3afb8" stroke-width="0.35"/></pattern><clipPath id="detailClip"><rect x="282" y="156" width="98" height="92"/></clipPath></defs>')
    d.raw('<g font-family="Noto Sans CJK JP, sans-serif">')
    d.rect(0, 0, 420, 297, "white", "none")
    d.rect(8, 8, 404, 281, width=.35)
    d.text(15, 19, "M0601C_111 専用モータ金具 — 見積用寸法図", 5.1, weight="bold")
    d.text(15, 26, "製作保留：現物照合・公差承認前の手配不可 ／ モータ側形状参照、車体側は新規設計", 3.2, fill="#913b2b")
    d.text(406, 19, "AMR-05 / MOUNT-Q01", 3.1, anchor="end")
    d.text(406, 25, "単位 mm　A3　寸法値優先", 2.9, anchor="end")
    # Front view: TechDraw raw axes are u=Z,v=X for direction +Y.
    fx, fy, scale = 30, 45, 2
    d.projection(views['front'], [0,-scale,scale,0,fx,fy+34*scale], scale)
    d.text(120, 141, "モータ側正面（+Y側から）  2:1", 3.2, anchor="middle", weight="bold")
    d.hdim(30,210,45,35,"90")
    d.vdim(45,113,30,19,"34")
    d.vdim(45,55,210,219,"5")
    d.vdim(45,82.3,210,231,"18.65")
    d.hdim(60,180,113,121,"60")
    d.hdim(110.5,129.5,113,131,"9.5")
    d.cross(120,82.3,22)
    d.circle(120,82.3,15.2,"3 1 .5 1")
    d.leader([(120,67.1),(153,63),(180,63)],"3× Ø2.8 通し",181,62)
    d.leader([(132,72.95),(159,85),(180,85)],"PCD 15.2",181,84)
    # Actual central section over a faint external side projection.
    sx, sy = 274, 45
    d.projection(views['side'],[0,-2,-2,0,sx,sy+68],2,color="#b3bac0",width=.17)
    for loop in views['section_loops_yz_mm']:
        points=" ".join(f"{sx+2*y:g},{sy+2*(34-z):g}" for y,z in loop)
        d.raw(f'<polygon points="{points}" fill="url(#hatch)" stroke="#142433" stroke-width="0.3"/>')
    d.hdim(274,334,45,35,"30")
    d.hdim(294,310,82,95,"8")
    d.hdim(310,328,76,95,"9")
    d.hdim(294,328,113,119,"17")
    d.text(310,129,"軸中心 X=45 の断面  2:1",3.1,anchor="middle",weight="bold")
    d.text(310,134,"薄灰色は外形投影。下側は配線開口。",2.7,anchor="middle")
    d.leader([(310,80),(349,85)],"受け底 Y=18",351,86)
    d.leader([(328,68),(350,67)],"入口 Y=27",351,68)
    d.leader([(294,72),(350,76)],"背面 Y=10",351,77)
    d.text(350,99,"9：受け深さ",2.9)
    d.text(350,105,"8：残る背面肉厚",2.9)
    # Top mounting face. The under-web footprint is a reference dashed outline.
    tx, ty = 30, 168
    d.projection(views['top'],[2,0,0,-2,tx,ty+60],2)
    d.raw('<rect x="60" y="174" width="120" height="34" fill="none" stroke="#82909a" stroke-width="0.18" stroke-dasharray="3 1"/>')
    for x in (45,195):d.cross(x,198,10)
    d.line(30,198,210,198,"#788793",.16,"4 1 .5 1")
    d.hdim(45,195,198,154,"75")
    d.vdim(168,228,30,19,"30")
    d.vdim(168,198,210,220,"15")
    d.hdim(30,45,228,240,"7.5")
    d.leader([(195,198),(205,242),(168,242)],"2× Ø6.6 通し",166,243,anchor="end")
    d.text(120,251,"3030接触面（+Z側から）  2:1",3.2,anchor="middle",weight="bold")
    d.text(30,258,"破線：下側web外周。穴は全て通し穴、ブラケット側タップなし。",2.75)
    # Detail reuses the exact front STEP projection; no hand-drawn cavity outline.
    d.text(330,148,"受け部詳細  4:1",3.2,anchor="middle",weight="bold")
    d.raw('<g clip-path="url(#detailClip)">')
    d.projection(views['front'],[0,-4,4,0,150,256.4],4,width=.29)
    d.raw('</g>')
    d.cross(330,195,36)
    d.circle(330,195,30.4,"3 1 .5 1")
    d.leader([(340,157.5),(377,157.5)],"R9.70",379,158.5)
    d.leader([(343,204),(386,215)],"背側幅7",387,216)
    d.leader([(347,237),(385,237)],"前側幅9.5",387,238)
    d.text(253,157,"輪郭はSTEP参照",2.8)
    d.text(249,251,"3平面の軸距離：8.25 ±0.05（公差案）",3.0)
    d.text(249,257,"元輪郭 +0.15。全輪郭の公差適合は未確定。",2.75)
    d.text(249,263,"下端から6 mmまでは背側も幅9.5へ開放。",2.75)
    # Part coordinate reference and title block.
    d.text(15,266,"部品座標：外形最小隅 O=(0,0,0)。軸中心 X45 / Z15.35。取付接触面 Z34。",2.75)
    d.line(8,270,412,270,width=.3)
    for x in (120,234,320):d.line(x,270,x,289,width=.25)
    d.text(12,276,"材質：A6061-T6 ／ 同形2個",3.2,weight="bold")
    d.text(12,282,"一体CNC加工。製作公差・仕上げは要承認。",2.75)
    d.text(12,287,"質量参考：104 g/個（ρ=2.70、CAD値）",2.6)
    d.text(124,276,"提出物：本図・STEP・加工依頼仕様",3.0)
    d.text(124,282,"見積総額 Q：2個、材料・加工・税・送料込み",2.7)
    d.text(124,287,"未注記公差／内隅R／端部処理は見積時提案",2.6)
    d.text(238,276,"図番 MOUNT-Q01 / Rev. A",2.9)
    d.text(238,282,"見積用・製作未承認",3.1,weight="bold",fill="#913b2b")
    d.text(238,287,DATE,2.6)
    d.text(324,276,"投影元：同梱STEP",2.8)
    d.text(324,282,"SHA-256（先頭16桁）",2.6)
    d.text(324,287,source_hash[:16],2.8)
    d.raw('</g></svg>')
    return "\n".join(d.items)


def render_pdf():
    import cairo
    import gi
    gi.require_version("Rsvg", "2.0")
    from gi.repository import Rsvg
    width, height = 420 * 72 / 25.4, 297 * 72 / 25.4
    surface = cairo.PDFSurface(str(PDF), width, height)
    surface.set_metadata(cairo.PDF_METADATA_TITLE,"M0601C_111 custom mount — quotation only")
    ctx = cairo.Context(surface)
    handle = Rsvg.Handle.new_from_file(str(SVG))
    viewport = Rsvg.Rectangle()
    viewport.x = viewport.y = 0
    viewport.width, viewport.height = width, height
    if not handle.render_document(ctx, viewport):
        raise RuntimeError("SVG rendering failed")
    surface.finish()


def main():
    params = json.loads(PARAMS.read_text())
    # An annotated engineering drawing must fail rather than retain old labels
    # after a later geometry revision changes the quoted critical dimensions.
    expected = {
        'flange_thickness_mm':5, 'seat_depth_mm':9, 'rear_wall_mm':8,
        'source_floor_offset_mm':.15, 'seat_flat_distance_mm':8.25,
        'seat_large_arc_radius_mm':9.70, 'motor_holes_diameter_mm':2.8,
        'motor_holes_PCD_mm':15.2, 'frame_holes_diameter_mm':6.6,
        'frame_hole_pitch_mm':75, 'cable_through_throat_width_mm':7,
        'cable_front_and_lower_relief_width_mm':9.5,
    }
    for key, value in expected.items():
        if abs(params[key]-value)>1e-8:
            raise ValueError(f'Drawing annotations need revision: {key}')
    if params['overall_LWH_mm'] != [90,30,34] or params['web_width_thickness_mm'] != [60,17]:
        raise ValueError('Drawing outline dimensions need revision')
    views = extract_views()
    assert abs(views['volume_mm3']-params['volume_mm3_each'])<0.01
    source_hash = hashlib.sha256(STEP.read_bytes()).hexdigest()
    SVG.write_text(build_svg(views,params,source_hash))
    ET.parse(SVG)
    render_pdf()
    print(json.dumps({'svg':str(SVG),'pdf':str(PDF),'source_step_sha256':source_hash,'bbox_mm':views['bbox_mm'],'volume_mm3':views['volume_mm3'],'section_loops':len(views['section_loops_yz_mm']),'status':'quotation_only_not_manufacturing_release'},indent=2))


if __name__ == '__main__':
    main()
