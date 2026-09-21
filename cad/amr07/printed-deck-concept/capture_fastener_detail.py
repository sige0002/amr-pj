"""Show a section of the saved P0 assembly; this does not revise its design.

Run inside the FreeCAD GUI. Images are direct captures of FreeCAD, with labels
and section geometry in a separate document. The source assembly is untouched.
"""
from pathlib import Path
import hashlib
import json

import FreeCAD as App
import FreeCADGui as Gui
import Part
from PySide import QtWidgets
from pivy import coin

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "AMR01_PrintedDeck_P0.FCStd"
NAME = "P0_Fastener_Detail"
V = App.Vector


def main():
    previous = App.ActiveDocument.Name if App.ActiveDocument else None
    window = Gui.getMainWindow()
    old_size = window.size()
    source = App.listDocuments().get("AMR01_PrintedDeck_P0")
    if source is None:
        source = App.openDocument(str(SOURCE))
    if NAME in App.listDocuments():
        raise RuntimeError("Close the previous P0_Fastener_Detail before rebuilding.")
    doc = App.newDocument(NAME)
    doc.Label = "PLA P0 | support fastening section | nominal fit only"

    # Section normal is X, through the existing inner fastener at (115, 65).
    # Rotate the cropped rear half to face FreeCAD's Front view, Z unchanged.
    crop = Part.makeBox(18, 50, 65, V(97, 40, 65))
    specs = [
        ("Rail400_3", "Lower3030", "下側3030フレーム", (.73, .78, .84)),
        ("ExtraSupportL", "SupportBar", "アルミ角棒 15×15", (.96, .56, .16)),
        ("PrintedDeckPanel4", "PLAPanel", "PLA上板 厚さ10", (.20, .68, .73)),
        ("ExtraFrameBoltL1", "M6Bolt", "M6×30ボルト", (.87, .24, .20)),
        ("ExtraWasherL10", "Washer1", "M6座金 1", (.87, .24, .20)),
        ("ExtraWasherL11", "Washer2", "M6座金 2", (.87, .24, .20)),
        ("CompressionSleeve9", "Sleeve", "金属スリーブ 長さ4", (.64, .37, .85)),
        ("ExtraSlotNutL1", "SlotNut", "3030内のM6溝ナット", (.95, .79, .16)),
    ]
    for original, name, label, color in specs:
        shape = source.getObject(original).Shape.common(crop).removeSplitter()
        assert shape.isValid() and shape.Volume > 0, original
        shape.translate(V(-115, -65, -99))
        shape.rotate(V(0, 0, 0), V(0, 0, 1), -90)
        obj = doc.addObject("PartDesign::Feature", name)
        obj.Label = label
        obj.Shape = shape
        obj.addProperty("App::PropertyString", "SourceObject", "Evidence")
        obj.SourceObject = original
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.LineColor = (.16, .20, .24)
        obj.ViewObject.DisplayMode = "Flat Lines"
        obj.ViewObject.LineWidth = 1.3

    def note(name, text, x, z, size=24):
        obj = doc.addObject("App::Annotation", name)
        obj.LabelText = text
        obj.Position = V(x, -1, z)
        obj.ViewObject.FontName = "Noto Sans CJK JP"
        obj.ViewObject.FontSize = size
        obj.ViewObject.TextColor = (.12, .17, .22)
        return obj

    def leader(name, points):
        obj = doc.addObject("PartDesign::Feature", name)
        obj.Shape = Part.makePolygon([V(x, -.3, z) for x, z in points])
        obj.ViewObject.LineColor = (.19, .24, .29)
        obj.ViewObject.LineWidth = 2.0

    note("Title", "PLA案 P0：中間支持材と下側フレームの締結", -67, 45, 27)
    note("Subtitle", "既存CADのボルト中心で切断（内側の取付位置）", -67, 38, 19)
    note("BoltNote", "M6×30 ボルト", 32, 29)
    leader("BoltLeader", [(3, 26), (27, 29), (30, 29)])
    note("WasherNote", "座金 2枚", 32, 20)
    leader("WasherLeader", [(5, 21), (27, 20), (30, 20)])
    note("SleeveNote", "金属スリーブ 長さ4mm", 32, 11)
    leader("SleeveLeader", [(4.1, 17), (27, 11), (30, 11)])
    note("NutNote", "M6溝ナット", 32, -6)
    leader("NutLeader", [(6.7, -4), (27, -6), (30, -6)])
    note("PLANote", "PLA上板：厚さ10mm", -67, 24)
    leader("PLALeader", [(-28, 24), (-24, 22), (-17, 22)])
    note("SupportNote", "アルミ角棒：15×15mm", -67, 7)
    leader("SupportLeader", [(-25, 7), (-21, 7), (-7.5, 7)])
    note("FrameNote", "下側3030フレーム", -67, -17)
    leader("FrameLeader", [(-30, -17), (-21, -17), (-14, -17)])
    note("StackNote", "ボルトは角棒の通し穴を抜け、3030内の溝ナットへ締結", -67, -39, 22)
    note("QualificationNote", "共締め構成 ／ スリーブ寸法・公差・締付条件は未確定", -67, -47, 19)

    doc.addObject("App::DocumentObjectGroup", "Evidence").Label = "Section derived from P0; no design change"
    doc.recompute()
    Gui.Selection.clearSelection()
    App.setActiveDocument(doc.Name)
    window.resize(1600, 1100)
    dock_visibility = {}
    for dock in window.findChildren(QtWidgets.QDockWidget):
        dock_visibility[dock.objectName()] = dock.isVisible()
        if dock.objectName() in ("Python console", "Report view", "Tasks"):
            dock.hide()
    view = Gui.activeDocument().activeView()
    view.viewFront()
    view.fitAll()
    # fitAll does not include the complete extent of screen-facing annotation
    # text. Leave an explicit margin so labels and title are not clipped.
    camera_node = view.getCameraNode()
    camera_node.height.setValue(114)
    Gui.updateGui()
    QtWidgets.QApplication.processEvents()
    doc.saveAs(str(HERE / (NAME + ".FCStd")))
    view.saveImage(str(HERE / "viewport-fastener-section.png"), 1600, 1100, "White")
    assert window.grab().save(str(HERE / "cad-screen-fastener-section.png"))
    evidence = {
        "source_file": SOURCE.name,
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "source_objects": [s[0] for s in specs],
        "section_plane_x_mm": 115,
        "bolt_xy_mm": [115, 65],
        "crop_bounds_mm": [97, 40, 65, 115, 90, 130],
        "display_transform": "translate(-115,-65,-99); rotate Z -90 degrees",
        "design_modified": False,
        "status": "P0 nominal section; sleeve selection, tolerances and preload unverified",
        "bolt": "M6x30",
        "support_bar_mm": [300, 15, 15],
        "support_through_hole_mm": 6.6,
        "sleeve_OD_ID_L_mm": [10, 6.6, 4],
        "washer_count": 2,
        "washer_thickness_mm": 1.6,
        "fastener_count_outer_inner": [6, 4],
        "maintenance": "Same bolts retain deck and support bars; bars are not independently fastened.",
    }
    (HERE / "fastener-section.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    for dock in window.findChildren(QtWidgets.QDockWidget):
        if dock.objectName() in dock_visibility:
            dock.setVisible(dock_visibility[dock.objectName()])
    window.resize(old_size)
    if previous:
        App.setActiveDocument(previous)
    print("Saved P0 section document, evidence and direct FreeCAD captures.")


if __name__ == "__main__":
    main()
