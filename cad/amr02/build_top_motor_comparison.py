"""Option C: top-motor layout comparison only; NOT a manufacturing design.

Run headlessly: freecadcmd /absolute/path/build_top_motor_comparison.py
Only this script and AMR01_Option_C_TopMotor.FCStd/.step belong to this option.
Purchased parts are nominal envelopes, generated here without external models.
"""
from pathlib import Path
import json
import math
import struct
import tempfile
import xml.etree.ElementTree as ET
import zipfile

import FreeCAD as App
import Part

HERE = Path(__file__).resolve().parent
NAME = "AMR01_Option_C_TopMotor"
STATUS = "比較配置のみ、製作設計ではない / Layout comparison only, not for manufacture"
V = App.Vector
if NAME in App.listDocuments():
    App.closeDocument(NAME)
doc = App.newDocument(NAME)
doc.Label = "AMR-01 C | 上置き比較配置のみ・製作設計ではない"
doc.Comment = STATUS
groups, objects, styles = {}, [], {}

FRAME = (0.73, 0.77, 0.81)
SUPPORT = (0.22, 0.43, 0.68)
MOTOR = (0.91, 0.44, 0.13)
SHAFT = (0.18, 0.71, 0.88)
PULLEY = (0.91, 0.69, 0.17)
BELT = (0.11, 0.58, 0.33)
METAL = (0.47, 0.52, 0.57)
BLACK = (0.12, 0.13, 0.15)

CENTER_DISTANCE = 90.0
AXLE_X, AXLE_Z = 90.0, 50.0
UPPER_DX = 45.0
UPPER_Z = AXLE_Z + math.sqrt(CENTER_DISTANCE**2 - UPPER_DX**2)
PITCH, TEETH, BELT_WIDTH = 3.0, 30, 10.0
PITCH_RADIUS = PITCH * TEETH / (2 * math.pi)
BELT_Y = 94.0
UPPER_BEARING_Y = (76.0, 114.0)
BASE_TOP = UPPER_Z - 15.0
BASE_BOTTOM = BASE_TOP - 3.0


def box(x, y, z, lx, ly, lz):
    return Part.makeBox(lx, ly, lz, V(x, y, z))


def cyl(radius, length, xyz, axis=(0, 0, 1)):
    return Part.makeCylinder(radius, length, V(*xyz), V(*axis))


def add(name, label, shape, group, color=FRAME, note="", transparency=0):
    if group not in groups:
        groups[group] = doc.addObject("App::DocumentObjectGroup", group)
        groups[group].Label = group.replace("_", " ")
    obj = doc.addObject("Part::Feature", name)
    obj.Label, obj.Shape = label, shape
    obj.addProperty("App::PropertyString", "DesignStatus", "Comparison").DesignStatus = STATUS
    obj.addProperty("App::PropertyString", "ModelNote", "Comparison").ModelNote = note
    obj.addProperty("App::PropertyColor", "DisplayColor", "Comparison").DisplayColor = color
    obj.addProperty("App::PropertyInteger", "DisplayTransparency", "Comparison").DisplayTransparency = transparency
    groups[group].addObject(obj)
    styles[obj.Name] = (color, transparency)
    if App.GuiUp:
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.LineColor = (0.17, 0.18, 0.20)
        obj.ViewObject.DisplayMode = "Flat Lines"
        obj.ViewObject.Transparency = transparency
    objects.append(obj)
    return obj


def side_shape(shape, side):
    return shape if side == "L" else shape.mirror(V(0, 0, 0), V(0, 1, 0))


def sadd(name, label, shape, side, group, color=FRAME, note="", transparency=0):
    return add(name + side, label + " " + side, side_shape(shape, side), group, color, note, transparency)


def profile(length):
    shape = box(0, -15, -15, length, 30, 30)
    cutters = [cyl(3.4, length + 2, (-1, 0, 0), (1, 0, 0))]
    slot = box(-1, -4, 12, length + 2, 8, 4).fuse(box(-1, -6.5, 7, length + 2, 13, 6))
    for angle in (0, 90, 180, 270):
        tool = slot.copy()
        tool.rotate(V(0, 0, 0), V(1, 0, 0), angle)
        cutters.append(tool)
    return shape.cut(Part.makeCompound(cutters)).removeSplitter()


def slot_x(x, y, z, centers_distance, radius, thickness, along_y=False):
    """Capsule hole; x,y,z denotes its center, length excludes round caps."""
    if along_y:
        return (box(x - centers_distance / 2, y, z - radius, centers_distance, thickness, radius * 2)
                .fuse(cyl(radius, thickness, (x - centers_distance / 2, y, z), (0, 1, 0)))
                .fuse(cyl(radius, thickness, (x + centers_distance / 2, y, z), (0, 1, 0))))
    return (box(x - centers_distance / 2, y - radius, z, centers_distance, radius * 2, thickness)
            .fuse(cyl(radius, thickness, (x - centers_distance / 2, y, z)))
            .fuse(cyl(radius, thickness, (x + centers_distance / 2, y, z))))


def capsule(x1, z1, x2, z2, radius, y, width):
    """A swept circular envelope in XZ, extruded along the shaft direction."""
    dx, dz = x2 - x1, z2 - z1
    c = math.hypot(dx, dz)
    nx, nz = -dz / c * radius, dx / c * radius
    points = [V(x1 + nx, y, z1 + nz), V(x2 + nx, y, z2 + nz),
              V(x2 - nx, y, z2 - nz), V(x1 - nx, y, z1 - nz)]
    straight = Part.Face(Part.makePolygon(points + [points[0]])).extrude(V(0, width, 0))
    return (straight.fuse(cyl(radius, width, (x1, y, z1), (0, 1, 0)))
            .fuse(cyl(radius, width, (x2, y, z2), (0, 1, 0))).removeSplitter())


def pulley(x, y, z):
    """Nominal envelope only: tooth profile and bore fixing are not designed."""
    rim = cyl(PITCH_RADIUS - 0.85, 11, (x, y - 5.5, z), (0, 1, 0))
    rim = rim.fuse(cyl(16, 1, (x, y - 6.5, z), (0, 1, 0)))
    rim = rim.fuse(cyl(16, 1, (x, y + 5.5, z), (0, 1, 0)))
    rim = rim.fuse(cyl(9, 18, (x, y - 9, z), (0, 1, 0)))
    return rim.cut(cyl(4, 20, (x, y - 10, z), (0, 1, 0))).removeSplitter()


def kp08(x, y, z):
    foot = box(x - 27.5, y - 6.5, z - 15, 55, 13, 5)
    body = foot.fuse(cyl(14, 13, (x, y - 6.5, z), (0, 1, 0)))
    body = body.fuse(cyl(8, 15, (x, y - 7.5, z), (0, 1, 0)))
    body = body.cut(cyl(4, 17, (x, y - 8.5, z), (0, 1, 0)))
    for hx in (x - 21, x + 21):
        body = body.cut(cyl(2.25, 7, (hx, y, z - 16)))
    return body.removeSplitter()


def kfl08(y, outer=False):
    # Nominal 48 x 27 flange, total axial width 12; actual procurement unresolved.
    flange_y = y + 8 if outer else y
    body = box(AXLE_X - 18.5, flange_y, AXLE_Z - 9.5, 37, 4, 19)
    for x in (AXLE_X - 18.5, AXLE_X + 18.5):
        body = body.fuse(cyl(5.5, 4, (x, flange_y, AXLE_Z), (0, 1, 0)))
        body = body.cut(cyl(2.25, 6, (x, flange_y - 1, AXLE_Z), (0, 1, 0)))
    body = body.fuse(cyl(13.5, 12, (AXLE_X, y, AXLE_Z), (0, 1, 0)))
    return body.cut(cyl(4, 14, (AXLE_X, y - 1, AXLE_Z), (0, 1, 0))).removeSplitter()


for i, y in enumerate((-135, -65, 65, 135), 1):
    shape = profile(400)
    shape.translate(V(-200, y, 90))
    add("Rail400_" + str(i), "3030 stock 400 mm", shape, "01_Frame", FRAME,
        "Stock lengths unchanged; T-slot cross section is illustrative.")
for i, x in enumerate((-215, 215), 1):
    shape = profile(300)
    shape.rotate(V(0, 0, 0), V(0, 0, 1), 90)
    shape.translate(V(x, -150, 90))
    add("Cross300_" + str(i), "3030 stock 300 mm", shape, "01_Frame")

for side, upper_x in (("L", 135.0), ("R", 45.0)):
    group = "02_Wheel_Box_" + side
    outer_belt = capsule(AXLE_X, AXLE_Z, upper_x, UPPER_Z, PITCH_RADIUS + 0.75,
                         BELT_Y - BELT_WIDTH / 2, BELT_WIDTH)
    inner_belt = capsule(AXLE_X, AXLE_Z, upper_x, UPPER_Z, PITCH_RADIUS - 0.75,
                         BELT_Y - BELT_WIDTH / 2 - 1, BELT_WIDTH + 2)
    belt = outer_belt.cut(inner_belt).removeSplitter()

    for tag, y in (("Inner", 105), ("Outer", 198)):
        wall = box(34, y, 25, 112, 4, 80)
        wall = wall.cut(cyl(7, 6, (90, y - 1, 50), (0, 1, 0)))
        for x in (71.5, 108.5):
            wall = wall.cut(slot_x(x, y - 1, 50, 2, 2.25, 6, along_y=True))
        sadd(tag + "Wall", "Concept wheel-box " + tag.lower() + " wall t4", wall, side, group,
             SUPPORT, "Wall locations match B: inner y105..109, outer y198..202. Joints not detailed.", 55)
    bridge = box(30, 50, 105, 120, 152, 4)
    # A rectangular clearance window also removes the closed belt loop's interior.
    cross = outer_belt.common(box(-250, 80, 104.9, 500, 30, 4.2)).BoundBox
    bridge_window = box(cross.XMin - 3, 83.5, 104, cross.XLength + 6, 21, 6)
    bridge = bridge.cut(bridge_window).removeSplitter()
    sadd("BoxBridge", "Wheel-box top bridge WITH belt window", bridge, side, group, SUPPORT,
         "B's unmodified bridge crosses the belt. This comparison adds a nominal window; stiffness and fixings unverified.", 55)
    sadd("KFLInner", "KFL08 nominal inner bearing", kfl08(109), side, group, METAL,
         "Nominal center y115. Vendor size, alignment and allowable load unverified.")
    sadd("KFLOuter", "KFL08 nominal outer bearing", kfl08(186, outer=True), side, group, METAL,
         "Nominal center y192. Mounting arrangement provisional.")
    sadd("WheelAxle", "Wheel axle dia8 x125, y80..205", cyl(4, 125, (90, 80, 50), (0, 1, 0)),
         side, group, SHAFT, "Longer axle needed than B's 100 mm part. End retention and pulley clamp unresolved.")
    tire = cyl(50, 25.4, (90, 157.3, 50), (0, 1, 0)).cut(cyl(44, 27.4, (90, 156.3, 50), (0, 1, 0)))
    wheel = cyl(44, 3, (90, 167, 50), (0, 1, 0)).cut(cyl(4, 5, (90, 166, 50), (0, 1, 0)))
    wheel = wheel.fuse(cyl(44, 25.4, (90, 157.3, 50), (0, 1, 0)).cut(cyl(41, 27.4, (90, 156.3, 50), (0, 1, 0))))
    sadd("WheelRim", "Wheel 100 x25.4 at y170, simplified rim", wheel, side, group, METAL,
         "Simplified wheel web, not selected hub-hole geometry.")
    sadd("Tire", "Tire diameter100, track340", tire, side, group, BLACK)
    hub = cyl(12, 13, (90, 170, 50), (0, 1, 0)).cut(cyl(4, 15, (90, 169, 50), (0, 1, 0)))
    sadd("WheelHub", "Wheel hub envelope", hub, side, group, METAL,
         "Hub/shaft locking and screw access need design; model is a space reservation.")

    group = "03_Top_Drive_" + side
    sadd("TimingBelt", "S3M270 x10, 30:30, C90 | pitch-path envelope", belt, side, group, BELT,
         "1.5 mm thick visual band about nominal pitch path. Teeth, bending and tension not modelled.")
    sadd("LowerPulley", "Lower 30T S3M pulley envelope / bore8", pulley(90, 94, 50), side, group, PULLEY,
         "Pitch dia28.648; flange dia32, width18 are assumptions. Tooth and clamping design unresolved.")
    sadd("UpperPulley", "Upper 30T S3M pulley envelope / bore8", pulley(upper_x, 94, UPPER_Z),
         side, group, PULLEY, "Same teeth count as lower pulley: ratio1:1. Nominal envelope only.")
    sadd("UpperShaft", "Independent supported upper shaft dia8", cyl(4, 78, (upper_x, 55, UPPER_Z), (0, 1, 0)),
         side, group, SHAFT, "Pulley lies between bearings y76 and114. Shaft retention not detailed.")
    for index, y in enumerate(UPPER_BEARING_Y, 1):
        sadd("UpperBearing" + str(index), "Upper KP08 nominal bearing y" + str(int(y)),
             kp08(upper_x, y, UPPER_Z), side, group, METAL,
             "Dimensions reused from first concept. Rating and actual fit unconfirmed.")

    # Both bearings and motor move together on this slotted cassette.
    cassette = box(upper_x - 36, -40, BASE_BOTTOM, 83, 177, 3)
    cross = outer_belt.common(box(-250, 80, BASE_BOTTOM - 0.1, 500, 30, 3.2)).BoundBox
    cassette = cassette.cut(box(cross.XMin - 3, 83.5, BASE_BOTTOM - 1, cross.XLength + 6, 21, 5))
    pad_x = upper_x + 39 if side == "L" else upper_x - 29
    for y in (65, 125):
        cassette = cassette.cut(slot_x(pad_x, y, BASE_BOTTOM - 1, 20, 3.3, 5))
    sadd("UpperCassette", "Upper cassette, belt window and x-adjust slots", cassette.removeSplitter(),
         side, group, SUPPORT,
         "Approximate x slots allow motor AND bearings to move together. Supports, screw access and slot-end margins unverified.", 35)
    # These pads only illustrate the mounting space; do not represent verified joints.
    for j, y in enumerate((65, 125), 1):
        support_from_z = 109 if 30 < pad_x < 150 else 105
        pad = box(pad_x - 14, y - 10, support_from_z, 28, 20, BASE_BOTTOM - support_from_z)
        pad = pad.cut(cyl(3.3, 10, (pad_x, y, support_from_z - 1)))
        sadd("CassetteSupport" + str(j), "PROVISIONAL cassette support pad", pad, side, group, SUPPORT,
             "Support concept only: stiffness, nut placement and adjustment fasteners unresolved.")

    cx = upper_x - 7
    mount = box(cx - 24, 32, BASE_TOP, 48, 3, 36)
    mount = mount.fuse(box(cx - 24, 24, BASE_TOP, 48, 11, 3))
    mount = mount.cut(cyl(6.3, 5, (upper_x, 31, UPPER_Z), (0, 1, 0)))
    for angle in (90, 210, 330):
        x = cx + 15.5 * math.cos(math.radians(angle))
        z = UPPER_Z + 15.5 * math.sin(math.radians(angle))
        mount = mount.cut(cyl(1.65, 5, (x, 31, z), (0, 1, 0)))
    sadd("MotorMount", "FIT0185 top motor bracket envelope", mount.removeSplitter(), side, group, SUPPORT,
         "Three M3 locations reused from first concept; bracket fastening to cassette not designed.")
    sadd("MotorGearbox", "FIT0185 upper gearbox nominal", cyl(18.5, 24, (cx, 8, UPPER_Z), (0, 1, 0)),
         side, group, MOTOR, "Gearbox length24 provisional. Output axis offset7 in x.")
    sadd("MotorCan", "FIT0185 upper motor nominal", cyl(16.5, 29, (cx, -21, UPPER_Z), (0, 1, 0)),
         side, group, MOTOR, "Motor front at |y|32; left/right units are staggered90 in x.")
    sadd("MotorEncoder", "Encoder / cable-exit envelope", cyl(16.5, 12, (cx, -33, UPPER_Z), (0, 1, 0)),
         side, group, BLACK, "Cable bend space omitted.")
    motor_shaft = cyl(3, 15, (upper_x, 38, UPPER_Z), (0, 1, 0))
    motor_shaft = motor_shaft.fuse(cyl(6, 6, (upper_x, 32, UPPER_Z), (0, 1, 0)))
    sadd("MotorOutput", "Motor output dia6, no belt load intended", motor_shaft, side, group, SHAFT)
    coupling = cyl(10, 25, (upper_x, 42, UPPER_Z), (0, 1, 0))
    coupling = coupling.cut(cyl(3, 12.5, (upper_x, 42, UPPER_Z), (0, 1, 0)))
    coupling = coupling.cut(cyl(4, 12.5, (upper_x, 54.5, UPPER_Z), (0, 1, 0)))
    sadd("MotorCoupling", "6-to-8 coupling: motor to supported shaft", coupling, side, group, METAL,
         "Coupler torque rating, shaft flats and end retention unverified; output shaft radial rating unpublished.")

# Rear caster: contact and proportions only, to make the complete layout readable.
add("CasterPlate", "Caster mounting plate envelope", box(-190, -85, 65, 80, 170, 4), "04_Caster", SUPPORT,
    "Caster attachment spacers and fasteners omitted in this drive-layout comparison.")
add("CasterSwivel", "Caster swivel envelope", cyl(19, 12, (-150, 0, 53)), "04_Caster", METAL)
add("CasterFork", "Caster fork envelope", box(-174, -16, 24, 28, 4, 33).fuse(box(-174, 12, 24, 28, 4, 33)), "04_Caster", METAL)
add("CasterWheel", "Rear caster dia50, floor contact", cyl(25, 20, (-166, -10, 25), (0, 1, 0)), "04_Caster", BLACK)

metadata = doc.addObject("App::DocumentObjectGroup", "00_Comparison_ReadMe")
metadata.Label = STATUS
metadata.addProperty("App::PropertyString", "Status", "Review").Status = STATUS
metadata.addProperty("App::PropertyString", "SourceMemo", "Review").SourceMemo = "docs/reviews/top-drive-review.ja.md"
metadata.addProperty("App::PropertyString", "Limitations", "Review").Limitations = (
    "Only nominal self-validity and layout arithmetic checked. NO full assembly-interference, strength, "
    "belt-capacity, motor-duty, fastener, guard, cable or procurement approval. Mounting supports remain provisional."
)
metadata.addProperty("App::PropertyString", "Legend", "Review").Legend = (
    "Orange=motor; cyan=independent shafts; yellow=pulleys; green=belts; blue=metal mounting concepts; gray=3030."
)
doc.recompute()

invalid = [o.Name for o in objects if o.Shape.isNull() or not o.Shape.isValid()]
assert not invalid, invalid
centers = [math.hypot(x - AXLE_X, UPPER_Z - AXLE_Z) for x in (135.0, 45.0)]
assert all(abs(c - 90) < 1e-9 for c in centers)
assert abs(2 * CENTER_DISTANCE + math.pi * 2 * PITCH_RADIUS - 270) < 1e-9
assert all(o.Shape.BoundBox.ZMin >= -1e-7 for o in objects)
frame_bounds = Part.makeCompound([o.Shape for o in groups["01_Frame"].Group]).BoundBox
assert abs(frame_bounds.XLength - 460) < 1e-7 and abs(frame_bounds.YLength - 300) < 1e-7
assert abs(frame_bounds.ZMin - 75) < 1e-7 and abs(frame_bounds.ZMax - 105) < 1e-7
for side in ("L", "R"):
    upper = doc.getObject("UpperShaft" + side).Shape.BoundBox
    lower = doc.getObject("WheelAxle" + side).Shape.BoundBox
    actual_center_distance = math.hypot(upper.Center.x - lower.Center.x, upper.Center.z - lower.Center.z)
    assert abs(actual_center_distance - 90) < 1e-7
    band = doc.getObject("TimingBelt" + side).Shape
    tire_bounds = doc.getObject("Tire" + side).Shape.BoundBox
    assert abs(abs(tire_bounds.Center.y) - 170) < 1e-7
    # Equal-pulley capsule annulus: band volume / (thickness * width) is pitch path length.
    assert abs(band.Volume / (1.5 * BELT_WIDTH) - 270) < 1e-5
report = {
    "status": STATUS, "shape_count": len(objects), "invalid_shapes": invalid,
    "full_assembly_interference_checked": False,
    "frame_outer_LW_mm": [460, 300], "frame_bottom_top_z_mm": [75, 105],
    "belt_plane_abs_y_mm": BELT_Y, "belt_nominal_width_mm": BELT_WIDTH,
    "center_distances_mm": centers, "upper_axes_xz_mm": [[135, UPPER_Z], [45, UPPER_Z]],
    "teeth_driver_driven": [TEETH, TEETH], "ratio_motor_to_wheel": 1.0,
    "belt_pitch_length_mm": 2 * CENTER_DISTANCE + PITCH * TEETH,
    "wheel_diameter_mm": 100, "wheel_track_mm": 340, "wheel_center_abs_y_mm": 170,
    "wheel_shaft_length_mm": 125,
    "no_load_wheel_rpm": 83, "no_load_straight_speed_m_s": math.pi * 0.1 * 83 / 60,
    "x_adjust_example_C_range_mm": [math.hypot(35, UPPER_Z - 50), math.hypot(55, UPPER_Z - 50)],
}
metadata.addProperty("App::PropertyString", "ChecksJSON", "Review").ChecksJSON = json.dumps(report, ensure_ascii=False)
doc.recompute()


def packed_color(rgb):
    r, g, b = [round(v * 255) for v in rgb]
    return (r << 24) | (g << 16) | (b << 8) | 255


def persist_headless_display(source, destination):
    """Write FreeCAD's native material records without starting/loading the GUI.

    DisplayColor properties also retain the palette for an inspecting GUI script.
    MaterialList v3 is one material: four RGBA integers, shininess/transparency,
    and three empty string lengths, preceded by its material count.
    """
    root = ET.Element("Document", SchemaVersion="1")
    providers = ET.SubElement(root, "ViewProviderData", Count=str(len(styles)))
    material_files = {}
    for index, (name, (color, transparency)) in enumerate(styles.items()):
        provider = ET.SubElement(providers, "ViewProvider", name=name, expanded="0")
        props = ET.SubElement(provider, "Properties", Count="8")
        for pname, ptype, tag, value in (
            ("DisplayMode", "App::PropertyEnumeration", "Integer", "0"),
            ("LineWidth", "App::PropertyFloatConstraint", "Float", "1.0"),
            ("LineColor", "App::PropertyColor", "PropertyColor", str(packed_color((0.17, 0.18, 0.20)))),
            ("Transparency", "App::PropertyPercent", "Integer", str(transparency)),
            ("Visibility", "App::PropertyBool", "Bool", "true"),
            ("Selectable", "App::PropertyBool", "Bool", "true"),
            ("ShowInTree", "App::PropertyBool", "Bool", "true"),
        ):
            prop = ET.SubElement(props, "Property", name=pname, type=ptype)
            ET.SubElement(prop, tag, value=value)
        filename = "ComparisonMaterial" + str(index)
        prop = ET.SubElement(props, "Property", name="ShapeAppearance", type="App::PropertyMaterialList")
        ET.SubElement(prop, "MaterialList", file=filename, version="3")
        material_files[filename] = struct.pack("<5I2f3I", 1, 0x555555FF, packed_color(color),
                                               0x888888FF, 0x000000FF, 0.7, transparency / 100, 0, 0, 0)
    gui_xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    with zipfile.ZipFile(source) as original, zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as target:
        for item in original.infolist():
            if item.filename != "GuiDocument.xml":
                target.writestr(item, original.read(item.filename))
        target.writestr("GuiDocument.xml", gui_xml)
        for filename, content in material_files.items():
            target.writestr(filename, content)


fcstd_path = HERE / (NAME + ".FCStd")
step_path = HERE / (NAME + ".step")
Part.export(objects, str(step_path))
step_path.write_text("\n".join(line.rstrip() for line in step_path.read_text().splitlines()) + "\n")
step_shape = Part.Shape()
step_shape.read(str(step_path))
assert not step_shape.isNull() and step_shape.isValid(), "STEP self-validity failed"
report["step_valid"] = True
report["step_solid_count"] = len(step_shape.Solids)
report["FCStd"] = str(fcstd_path)
report["STEP"] = str(step_path)
metadata.ChecksJSON = json.dumps(report, ensure_ascii=False)
doc.recompute()
with tempfile.TemporaryDirectory(prefix="amr-option-c-") as temp:
    temporary_fcstd = Path(temp) / (NAME + ".FCStd")
    doc.saveAs(str(temporary_fcstd))
    if App.GuiUp:
        fcstd_path.write_bytes(temporary_fcstd.read_bytes())
    else:
        persist_headless_display(temporary_fcstd, fcstd_path)
print(json.dumps(report, ensure_ascii=False, indent=2))
