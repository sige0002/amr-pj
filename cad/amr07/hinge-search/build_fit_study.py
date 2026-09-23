"""Rejected direct-mount trial, not a replacement AMR design.

Run in FreeCAD. Copy D6.8 geometry and rotate only the moving HG-TP20 leaf
to horizontal. The plate/frame positions stay unchanged. This checks the
specific 'just remove the angle' idea, not every mounting arrangement.
"""
from pathlib import Path
import hashlib
import json
import FreeCAD as App
import Part

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / 'direct-hinge/AMR01_DirectHinge_D68.FCStd'
NAME = 'AMR_Hinge_DirectFit_Study'
V = App.Vector


def main():
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    source = next((d for d in App.listDocuments().values()
                   if d.FileName == str(SOURCE)), None)
    opened = source is None
    if opened:
        source = App.openDocument(str(SOURCE))
    if NAME in App.listDocuments():
        App.closeDocument(NAME)
    doc = App.newDocument(NAME)
    doc.Label = 'HINGE FIT STUDY | REJECTED | not production CAD'
    meta = doc.addObject('App::FeaturePython', 'StudyInfo')
    for key, value in {
        'Status': 'REJECTED: moving leaf intersects upper 3030 frame',
        'SourceSha256': digest,
        'Scope': 'HG-TP20 moving leaf rotated +90 deg; original lid and frame retained',
        'Limit': 'D6.8 nominal drawing reconstruction, not manufacturer STEP; no new assembly release',
    }.items():
        meta.addProperty('App::PropertyString', key, 'Study')
        setattr(meta, key, value)

    frame = source.getObject('UpperRail3030_1').Shape.copy()
    plate = source.getObject('AluminumDeckD3').Shape.copy()
    fixed = source.getObject('HGTP20_Fixed_1').Shape.copy()
    moving = source.getObject('HGTP20_Moving_1').Shape.copy()
    moving.rotate(V(0, 156, 230), V(1, 0, 0), 90)
    intersection = moving.common(frame)
    assert intersection.Volume > 1, 'Expected rejected configuration must intersect frame'
    crop = Part.makeBox(66, 80, 80, V(72, 95, 190))

    def add(name, shape, label, color):
        obj = doc.addObject('PartDesign::Feature', name)
        obj.Shape = shape
        obj.Label = label
        if App.GuiUp:
            obj.ViewObject.ShapeColor = color
            obj.ViewObject.DisplayMode = 'Flat Lines'
            obj.ViewObject.LineColor = (.12, .14, .17)
        return obj

    for name, shape, label, color in [
        ('Frame', frame.common(crop), '3030 frame: top Z229, slot Z214', (.65, .68, .73)),
        ('Plate', plate.common(crop), '4 mm lid: Z229 to Z233', (.33, .64, .91)),
        ('FixedLeaf', fixed, 'Fixed HG-TP20 leaf: frame direct', (.48, .5, .53)),
        ('MovingLeaf', moving, 'Moving leaf horizontal: seat Z224', (1.0, .63, .08)),
        ('Clash', intersection, 'REJECTED: moving leaf / 3030 overlap', (.92, .06, .05)),
    ]:
        assert shape.isValid(), name
        add(name, shape, label, color)

    # Dimension lines are model geometry, not an image overlay.
    marks = [Part.makeLine(V(137, 150, z), V(137, 171, z)) for z in (224, 233)]
    marks += [Part.makeLine(V(137, 168, 224), V(137, 168, 233))]
    for z in (224, 233):
        marks.append(Part.makeLine(V(137, 166, z-1), V(137, 170, z+1)))
    add('SeatMismatch9mm', Part.makeCompound(marks), '9 mm mounting-face mismatch', (.12, .20, .75))

    result = {
        'date': '2026-09-23',
        'status': 'rejected',
        'source': '../direct-hinge/AMR01_DirectHinge_D68.FCStd',
        'source_sha256': digest,
        'candidate': 'HG-TP20, moving leaf horizontal, dedicated angle removed',
        'frame_top_z_mm': 229,
        'frame_slot_center_z_mm': 214,
        'lid_bottom_z_mm': 229,
        'lid_top_z_mm': 233,
        'hinge_axis_yz_mm': [156, 230],
        'axis_to_mounting_back_plane_mm': 6,
        'axis_to_fixed_hole_row_mm': 16,
        'horizontal_moving_leaf_back_plane_z_mm': 224,
        'back_plane_to_lid_top_mismatch_mm': 9,
        'moving_leaf_frame_intersection_mm3': intersection.Volume,
        'moving_leaf_plate_intersection_mm3': moving.common(plate).Volume,
        'scope': 'One specific mounting arrangement, no claim that all direct-mount hinges are impossible',
        'limitations': ['Nominal D6.8 reconstruction; assumed leaf thickness 2 mm.',
                        'No new production design or BOM selection.',
                        'Other candidate products received catalog/dimension screening only.'],
    }
    (HERE / 'fit_result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    doc.recompute()
    doc.saveAs(str(HERE / (NAME+'.FCStd')))
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == digest
    if opened:
        App.closeDocument(source.Name)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
