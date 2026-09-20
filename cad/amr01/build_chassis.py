"""AMR-01 A: reproducible FreeCAD concept assembly (mm, not production CAD).

Run inside FreeCAD: exec(compile(open(PATH).read(), PATH, 'exec'), {'__file__': PATH})
Purchased parts are dimension-based simplified models, not vendor CAD.
"""
from pathlib import Path
import json
import math
import FreeCAD as App
import Part

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CFG = json.loads((ROOT / 'docs/amr-01/design_parameters.json').read_text())
V = App.Vector
NAME = 'AMR01_FirstDesign_A'
if NAME in App.listDocuments():
    App.closeDocument(NAME)
doc = App.newDocument(NAME)
doc.Label = 'AMR-01 A | 3030 | 460 x 300 | 12V'
groups = {}
objects = []
AL = (0.77, 0.80, 0.84)
STEEL = (0.47, 0.51, 0.57)
BLUE = (0.19, 0.42, 0.62)
BLACK = (0.14, 0.15, 0.17)
ORANGE = (0.87, 0.47, 0.13)


def box(x, y, z, lx, ly, lz):
    return Part.makeBox(lx, ly, lz, V(x, y, z))


def cyl(r, length, pos, axis=(0, 0, 1)):
    return Part.makeCylinder(r, length, V(*pos), V(*axis))


def cut_all(shape, cutters):
    return shape.cut(Part.makeCompound(cutters)).removeSplitter() if cutters else shape


def add(name, label, shape, group, color=AL, source='', note=''):
    if group not in groups:
        groups[group] = doc.addObject('App::DocumentObjectGroup', group)
        groups[group].Label = group.replace('_', ' ')
    obj = doc.addObject('PartDesign::Feature', name)
    obj.Label = label
    obj.Shape = shape
    obj.addProperty('App::PropertyString', 'SourceURL', 'Selection').SourceURL = source
    obj.addProperty('App::PropertyString', 'ModelNote', 'Selection').ModelNote = note or 'Nominal simplified geometry; confirm received part before fabrication.'
    groups[group].addObject(obj)
    if App.GuiUp:
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.LineColor = (0.17, 0.20, 0.24)
        obj.ViewObject.DisplayMode = 'Flat Lines'
        obj.ViewObject.LineWidth = 1.0
    objects.append(obj)
    return obj


def mirrored(shape):
    return shape.mirror(V(0, 0, 0), V(0, 1, 0))


def side_add(stem, label, shape, side, group, color=AL, source='', note=''):
    return add(stem + side, label + ' ' + side, shape if side == 'L' else mirrored(shape), group, color, source, note)


def bolt(name, xyz, axis, diameter, length, group='06_Fasteners', csk=False):
    p, d = V(*xyz), V(*axis)
    # xyz is the underside of a normal screw head, or flush head plane for CSK.
    shaft = Part.makeCylinder(diameter / 2, length, p, d)
    if csk:
        head = Part.makeCone(diameter, diameter / 2, diameter / 2, p, d)
    else:
        head = Part.makeCylinder({3: 2.75, 4: 3.5, 6: 5}[diameter], diameter, p - d * diameter, d)
    obj = add(name, name.replace('_', ' '), shaft.fuse(head), group, STEEL,
               note='Simplified screw; threads and drive recess omitted. Quantity in BOM includes washers/nuts.')
    if name.startswith(('JointA_', 'JointB_', 'GussetBolt_', 'TrayBolt_', 'BearingBolt_', 'MotorFootBolt_')):
        t = 1.6 if diameter == 6 else .8
        washer = Part.makeCylinder(diameter, t, p, d).cut(Part.makeCylinder(diameter / 2 + .2, t, p, d))
        add('Washer_' + name, 'Washer M' + str(diameter), washer, group, STEEL)
    nut_distance = None
    if name.startswith(('JointA_', 'JointB_')):
        nut_distance = 10.6
    elif name.startswith('GussetBolt_'):
        nut_distance = 8.6
    elif name.startswith('TrayBolt_'):
        nut_distance = 7.6
    elif name.startswith('CassetteBolt_'):
        nut_distance = 48
    elif name.startswith('CasterFrameBolt_'):
        nut_distance = 14
    if nut_distance is not None:
        ns = box(-6.4, -6.4, -2, 12.8, 12.8, 4).cut(cyl(3.1, 6, (0, 0, -3)))
        ns.Placement = App.Placement(p + d * nut_distance, App.Rotation(V(0, 0, 1), d))
        add('SlotNut_' + name, 'M6 slot nut | nominal envelope', ns, group, STEEL,
            note='Simplified nut envelope; exact series6-compatible profile must be checked on delivery.')
    return obj


def plate_holes(shape, xy, z, t, r):
    return cut_all(shape, [cyl(r, t + 2, (x, y, z - 1)) for x, y in xy])


def profile(length):
    s = box(0, -15, -15, length, 30, 30)
    cutters = [cyl(3.4, length + 2, (-1, 0, 0), (1, 0, 0))]
    # A legible nominal T-slot, not the exact NFSL die section.
    slot = box(-1, -4, 12, length + 2, 8, 4).fuse(box(-1, -6.5, 7, length + 2, 13, 6))
    for angle in (0, 90, 180, 270):
        tool = slot.copy()
        tool.rotate(V(0, 0, 0), V(1, 0, 0), angle)
        cutters.append(tool)
    return cut_all(s, cutters)


for idx, y in enumerate((-135, -65, 65, 135), 1):
    s = profile(400)
    s.translate(V(-200, y, 90))
    add('Rail400_' + str(idx), 'NFSL6-3030-400 | stock 400 mm', s, '01_Frame', AL,
        'https://www.amazon.co.jp/dp/B0DKF2CCW3', '400 mm stock, no cut. Slot cross-section is illustrative; structural I comes from catalog.')
for idx, x in enumerate((-215, 215), 1):
    s = profile(300)
    s.rotate(V(0, 0, 0), V(0, 0, 1), 90)
    s.translate(V(x, -150, 90))
    add('Cross300_' + str(idx), 'NFSL6-3030-300 | stock 300 mm', s, '01_Frame', AL,
        'https://www.amazon.co.jp/dp/B0DKDZ8G9G')

# One interior angle at each rail end; four top gussets reinforce outer corners.
for end in (-1, 1):
    for y in (-120, -50, 50, 120):
        fx, fy = end * 200, y
        dx, dy = -end, -1 if y > 0 else 1
        s = box(min(fx, fx + dx * 28), min(fy, fy + dy * 5), 76, 28, 5, 28)
        s = s.fuse(box(min(fx, fx + dx * 5), min(fy, fy + dy * 28), 76, 5, 28, 28))
        s = cut_all(s, [cyl(3.3, 7, (fx - dx, fy + dy * 15, 90), (dx, 0, 0)),
                        cyl(3.3, 7, (fx + dx * 15, fy - dy, 90), (0, dy, 0))])
        tag = ('P' if end > 0 else 'N') + str(y).replace('-', 'N')
        add('Angle_' + tag, '3030 corner angle 28 x 28 | M6', s, '01_Frame', STEEL,
            'https://www.amazon.co.jp/dp/B0D4F38VX2', '8 installed from 20-piece kit; nominal envelope. Confirm slot-nut compatibility.')
        bolt('JointA_' + tag, (fx + dx * 6.6, fy + dy * 15, 90), (-dx, 0, 0), 6, 12)
        bolt('JointB_' + tag, (fx + dx * 15, fy + dy * 6.6, 90), (0, -dy, 0), 6, 12)
    for side in (-1, 1):
        pts = [V(end * 230, side * 150, 105), V(end * 170, side * 150, 105), V(end * 230, side * 90, 105)]
        s = Part.Face(Part.makePolygon(pts + [pts[0]])).extrude(V(0, 0, 3))
        holes = [(end * 185, side * 135), (end * 215, side * 105)]
        s = plate_holes(s, holes, 105, 3, 3.3)
        tag = str(end).replace('-', 'N') + str(side).replace('-', 'N')
        add('Gusset_' + tag, 'A5052 t3 corner gusset | 60 x 60', s, '02_Mounts', BLUE)
        for i, (x, y) in enumerate(holes):
            bolt('GussetBolt_' + tag + str(i), (x, y, 109.6), (0, 0, -1), 6, 12)

for side in ('L', 'R'):
    sg = 1 if side == 'L' else -1
    group = '03_Drive_' + side
    # Four posts transfer wheel loads to both longitudinal rails on each side.
    base = box(48, 50, 31, 84, 108, 4).cut(box(62, 49, 30, 44, 29, 6))
    posts = [(x, y) for x in (56, 124) for y in (65, 135)]
    base = plate_holes(base, posts, 31, 4, 3.3)
    for x, y in posts:
        base = base.cut(Part.makeCone(6, 3.3, 2.7, V(x, y, 31), V(0, 0, 1)))
        tube = cyl(6, 40, (x, y, 35)).cut(cyl(3.5, 40, (x, y, 35)))
        side_add('Post_' + str(x) + '_' + str(y), 'M6 spacer L40 OD12 ID7', tube, side, group, AL)
        bolt('CassetteBolt_' + side + str(x) + '_' + str(y), (x, sg * y, 31), (0, 0, 1), 6, 50, csk=True)
    bearing_holes = [(x, y) for x in (69, 111) for y in (118, 145)]
    foot_holes = [(65, 86), (105, 86)]
    base = plate_holes(base, bearing_holes + foot_holes, 31, 4, 2.25)
    side_add('BearingPlate', 'A5052 t4 wheel support plate | 84 x 108', base, side, group, BLUE)
    for j, y in enumerate((118, 145), 1):
        s = box(62.5, y - 6.5, 35, 55, 13, 5)
        s = s.fuse(cyl(14, 13, (90, y - 6.5, 50), (0, 1, 0)))
        s = s.fuse(cyl(8, 15, (90, y - 7.5, 50), (0, 1, 0)))
        s = s.cut(cyl(4, 17, (90, y - 8.5, 50), (0, 1, 0)))
        s = plate_holes(s, [(69, y), (111, y)], 35, 5, 2.5)
        side_add('KP08_' + str(j), 'KP08 | bore 8 | H15 | pitch42', s, side, group, STEEL,
                 'https://www.amazon.co.jp/dp/B0DSKB5QQN')
        for x in (69, 111):
            bolt('BearingBolt_' + side + str(j) + str(x), (x, sg * y, 30.2), (0, 0, 1), 4, 16)
    # Motor front plate, from 40 x 20 x 3 aluminum angle, cut to 50 mm width.
    mount = box(60, 74, 35, 50, 3, 40).fuse(box(60, 74, 35, 50, 20, 3))
    mount = mount.cut(cyl(6.3, 5, (90, 73, 50), (0, 1, 0)))
    motor_holes = [(83 + 15.5 * math.cos(math.radians(a)), 50 + 15.5 * math.sin(math.radians(a))) for a in (90, 210, 330)]
    mount = cut_all(mount, [cyl(1.65, 5, (x, 73, z), (0, 1, 0)) for x, z in motor_holes])
    mount = plate_holes(mount, foot_holes, 35, 3, 2.25)
    side_add('MotorAngle', 'Motor mount | angle 40 x 20 x 3, L50', mount, side, group, BLUE,
             note='Three M3 holes on PCD31 around gearbox center x83,z50; output is offset +7 mm in x. M3x5 engagement 2 mm.')
    for i, (x, z) in enumerate(motor_holes):
        bolt('MotorFaceBolt_' + side + str(i), (x, sg * 77, z), (0, -sg, 0), 3, 5)
    for x, y in foot_holes:
        bolt('MotorFootBolt_' + side + str(x), (x, sg * y, 30.2), (0, 0, 1), 4, 14)
    motor_source = 'https://wiki.dfrobot.com/fit0185/'
    gearbox = cyl(18.5, 24, (83, 50, 50), (0, 1, 0))
    side_add('Gearbox', 'DFRobot FIT0185 | 131:1 gearbox', gearbox, side, group, AL, motor_source,
             'Shared manufacturer drawing: gearbox L24 provisional for 131:1. Verify actual length. Shaft offset 7 mm.')
    side_add('MotorCan', 'FIT0185 | 12V motor dia33 x29', cyl(16.5, 29, (83, 21, 50), (0, 1, 0)), side, group, STEEL, motor_source)
    side_add('Encoder', 'FIT0185 | Hall encoder envelope 12 mm', cyl(16.5, 12, (83, 9, 50), (0, 1, 0)), side, group, BLACK, motor_source)
    shaft = cyl(3, 15, (90, 80, 50), (0, 1, 0)).cut(box(85, 79, 52.5, 10, 17, 3))
    boss = cyl(6, 6, (90, 74, 50), (0, 1, 0))
    side_add('MotorShaft', 'FIT0185 | dia6 D shaft + dia12 boss', shaft.fuse(boss), side, group, STEEL, motor_source)
    coupler = cyl(10, 25, (90, 84, 50), (0, 1, 0))
    coupler = cut_all(coupler, [cyl(3, 12.5, (90, 84, 50), (0, 1, 0)), cyl(4, 12.5, (90, 96.5, 50), (0, 1, 0))])
    side_add('Coupler', 'Jaw coupling 6 to 8 | D20 L25', coupler, side, group, ORANGE,
             'https://www.amazon.co.jp/dp/B0CWNQJWPH', '2 mm gap between motor and wheel shaft ends. Rated torque not published; acceptance test required.')
    side_add('WheelShaft', 'C45 chromed shaft 8 x 100 | no cut', cyl(4, 100, (90, 97, 50), (0, 1, 0)), side, group, STEEL,
             'https://www.amazon.co.jp/dp/B0G3Y7811K')
    for j, y in enumerate((129.5, 152.5), 1):
        collar = cyl(12.5, 8, (90, y, 50), (0, 1, 0)).cut(cyl(4, 8, (90, y, 50), (0, 1, 0)))
        side_add('Collar_' + str(j), 'Split shaft collar 8 / 25 / 8', collar, side, group, STEEL,
                 'https://www.amazon.co.jp/dp/B0DDXP5HL6')
    # Wheel web and lightening holes approximate; OD/width/bore are seller specs.
    wy = CFG['geometry']['drive_track_mm'] / 2 - 12.7
    web = cyl(46, 3, (90, wy, 50), (0, 1, 0)).cut(cyl(4, 3, (90, wy, 50), (0, 1, 0)))
    rim = cyl(46, 25.4, (90, wy, 50), (0, 1, 0)).cut(cyl(43, 25.4, (90, wy, 50), (0, 1, 0)))
    wheel = web.fuse(rim)
    wheel = cut_all(wheel, [cyl(4.2, 5, (90 + 26 * math.cos(math.radians(a)), wy - 1, 50 + 26 * math.sin(math.radians(a))), (0, 1, 0)) for a in range(0, 360, 60)])
    # Hub attachment PCD is defined by mechanical_parameters.json, holes are a machining operation.
    mech = json.loads((HERE / 'mechanical_parameters.json').read_text())
    hub_pcd = mech['wheel_hub']['bolt_pcd_mm']
    hub_r = mech['wheel_hub']['flange_diameter_mm'] / 2
    bolt_r = mech['wheel_hub']['bolt_clearance_diameter_mm'] / 2
    hub_holes = [(90 + hub_pcd / 2 * math.cos(math.radians(a)), 50 + hub_pcd / 2 * math.sin(math.radians(a))) for a in (45, 135, 225, 315)]
    wheel = cut_all(wheel, [cyl(bolt_r, 5, (x, wy - 1, z), (0, 1, 0)) for x, z in hub_holes])
    side_add('WheelMetal', 'Wheel 100 x 25.4 | metal web | machined hub holes', wheel, side, group, AL,
             'https://www.amazon.co.jp/dp/B0B23WBLBK', 'OD100 width25.4 bore8 verified; web/rim/lightening details approximate. Drill hub pattern after inspecting existing holes; not assumed bolt-on.')
    tire = cyl(50, 25.4, (90, wy, 50), (0, 1, 0)).cut(cyl(46, 25.4, (90, wy, 50), (0, 1, 0)))
    side_add('Tire', 'Neoprene tire | dia100 width25.4', tire, side, group, BLACK)
    hub = cyl(hub_r, 3, (90, wy + 3, 50), (0, 1, 0)).fuse(cyl(8, 10, (90, wy + 6, 50), (0, 1, 0)))
    hub = hub.cut(cyl(4, 13, (90, wy + 3, 50), (0, 1, 0)))
    hub = cut_all(hub, [cyl(bolt_r, 5, (x, wy + 2, z), (0, 1, 0)) for x, z in hub_holes])
    side_add('Hub', 'Flange hub | bore8 H13 stem16', hub, side, group, STEEL,
             'https://www.amazon.co.jp/dp/B07PTPFX35', 'Hub is on outward web face, inside wheel cup. Bolt PCD must be checked before drilling.')
    for i, (x, z) in enumerate(hub_holes):
        bolt('HubBolt_' + side + str(i), (x, sg * wy, z), (0, sg, 0), 3, 10)

# Caster: full swivel envelope evaluated separately, shown trailing behind pivot.
plate = box(-190, -85, 65, 80, 170, 4)
caster_holes = [(x, y) for x in (-173, -127) for y in (-17.5, 17.5)]
mount_holes = [(x, y) for x in (-180, -120) for y in (-65, 65)]
plate = plate_holes(plate, caster_holes + mount_holes, 65, 4, 3.3)
add('CasterAdapter', 'Caster adapter | A5052 80 x170 x4', plate, '04_Caster', BLUE)
for i, (x, y) in enumerate(mount_holes):
    add('CasterSpacer_' + str(i), 'M6 spacer L6', cyl(6, 6, (x, y, 69)).cut(cyl(3.5, 6, (x, y, 69))), '04_Caster')
    bolt('CasterFrameBolt_' + str(i), (x, y, 65), (0, 0, 1), 6, 16)
caster_top = plate_holes(box(-179.5, -23.5, 62.5, 59, 47, 2.5), caster_holes, 62.5, 2.5, 3.25)
add('CasterTop', 'Hammer 420G-R50 | plate59x47 pitch46x35 H65', caster_top, '04_Caster', STEEL,
    'https://www.tanaka-km.com/view/item/000000036665', 'Manufacturer sizes: D50 W20 H65 trail16 load300N. Fork details approximate.')
for i, (x, y) in enumerate(caster_holes):
    bolt('CasterBolt_' + str(i), (x, y, 69), (0, 0, -1), 6, 16)
add('SwivelRace', 'Caster swivel race', cyl(19, 9, (-150, 0, 53.5)), '04_Caster', STEEL)
forks = []
for y in (-14, 11):
    pts = [V(-171, y, 25), V(-157, y, 25), V(-135, y, 53.5), V(-159, y, 53.5)]
    forks.append(Part.Face(Part.makePolygon(pts + [pts[0]])).extrude(V(0, 3, 0)))
fork = Part.makeCompound(forks + [cyl(3, 32, (-166, -16, 25), (0, 1, 0))])
add('CasterFork', 'Caster fork | trailing axle -16 mm', fork, '04_Caster', STEEL)
cw = cyl(25, 20, (-166, -10, 25), (0, 1, 0)).cut(cyl(12, 20, (-166, -10, 25), (0, 1, 0)))
add('CasterTire', 'Caster rubber wheel dia50 width20', cw, '04_Caster', BLACK)
add('CasterCore', 'Caster core', cyl(12, 20, (-166, -10, 25), (0, 1, 0)).cut(cyl(3, 20, (-166, -10, 25), (0, 1, 0))), '04_Caster', AL)

tray_holes = [(x, y) for x in (-170, -10) for y in (-65, 65)]
tray = plate_holes(box(-190, -90, 105, 200, 180, 2), tray_holes, 105, 2, 3.3)
add('EquipmentTray', 'Equipment tray | A5052 200 x180 x2', tray, '05_Tray', BLUE,
    note='Mechanical tray only. Battery, computer, drivers, arm and guards are not selected or included in this cost.')
for i, (x, y) in enumerate(tray_holes):
    bolt('TrayBolt_' + str(i), (x, y, 108.6), (0, 0, -1), 6, 10)

doc.recompute()
invalid = [o.Name for o in objects if o.Shape.isNull() or not o.Shape.isValid()]
assert not invalid, invalid
doc.addObject('App::DocumentObjectGroup', '00_ReadMe').Label = 'A / concept / 460 x 300 frame / see README'
doc.recompute()
if App.GuiUp:
    import FreeCADGui as Gui
    Gui.activeDocument().activeView().viewAxonometric()
    Gui.activeDocument().activeView().fitAll()
doc.saveAs(str(HERE / 'AMR01_FirstDesign_A.FCStd'))
step_path = HERE / 'AMR01_FirstDesign_A.step'
Part.export(objects, str(step_path))
# Keep exporter whitespace out of git diffs; STEP tokens are unchanged.
step_path.write_text('\n'.join(line.rstrip() for line in step_path.read_text().splitlines()) + '\n')
print(json.dumps({'objects': len(objects), 'invalid': invalid, 'FCStd': str(HERE / 'AMR01_FirstDesign_A.FCStd')}, ensure_ascii=False))
