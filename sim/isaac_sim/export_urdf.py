"""Export D6.5 from the saved FreeCAD assembly. Run with FreeCAD Python.

CAD is in mm; URDF and binary STL are in m. No edits to the source CAD.
The inertia ledger uses catalog/estimated masses, not solid-metal motor mass.
"""
from collections import defaultdict
from pathlib import Path
import hashlib
import json
import math
import struct
import subprocess
import xml.etree.ElementTree as ET

import FreeCAD as App
import Part
import MeshPart

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CAD = ROOT / "cad/amr07/two-story"
SOURCE = CAD / "AMR01_TwoStorey_D6.FCStd"
V = App.Vector
RHO = {"aluminum": 2.70e-6, "steel": 7.85e-6, "PLA": 1.24e-6}
ORIGINS = {  # absolute CAD coordinates, in mm; all frames have CAD orientation
    "base_link": [90, 0, 50.35],
    "left_wheel_link": [90, 174.5, 50.35],
    "right_wheel_link": [90, -174.5, 50.35],
    "caster_swivel_link": [-150, 0, 58],
    "caster_wheel_link": [-166, 0, 25],
    "payload_link": [0, 0, 313],
}
COLORS = {
    "aluminum": [.72, .75, .79, 1], "steel": [.38, .40, .43, 1],
    "pla": [.22, .61, .38, 1], "posts": [.12, .13, .15, 1],
    "mounts": [.15, .43, .69, 1], "motor": [.30, .31, .33, 1],
    "rubber": [.055, .06, .065, 1], "battery": [.02, .40, .40, 1],
    "computer": [.50, .54, .57, 1], "electronics": [.12, .37, .67, 1],
    "estop": [.85, .08, .06, 1], "belts": [.88, .47, .07, 1],
    "wires": [.76, .30, .08, 1], "payload": [.66, .44, .23, 1],
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fmt(values):
    if isinstance(values, (float, int)):
        return f"{values:.12g}"
    return " ".join(fmt(v) for v in values)


def box(center, size):
    return Part.makeBox(*size, V(*[c - s / 2 for c, s in zip(center, size)]))


def mass_properties(shape, mass):
    """Uniform density inside this component's solids; inertia about its COM."""
    solids = shape.Solids
    volume = sum(s.Volume for s in solids)
    center = [sum(s.CenterOfMass[i] * s.Volume for s in solids) / volume for i in range(3)]
    inertia = [[0.0] * 3 for _ in range(3)]
    for s in solids:
        m = mass * s.Volume / volume
        d = [s.CenterOfMass[i] - center[i] for i in range(3)]
        matrix = s.MatrixOfInertia
        for i in range(3):
            for j in range(3):
                inertia[i][j] += (getattr(matrix, f"A{i+1}{j+1}") * m / s.Volume
                                  + m * ((sum(x*x for x in d) if i == j else 0) - d[i]*d[j])) * 1e-6
    return dict(mass_kg=mass, com_cad_mm=center, inertia_kg_m2=inertia)


def aggregate(components, origin):
    mass = sum(c["mass_kg"] for c in components)
    center = [sum(c["mass_kg"] * c["com_cad_mm"][i] for c in components) / mass for i in range(3)]
    inertia = [[0.0] * 3 for _ in range(3)]
    for c in components:
        d = [(c["com_cad_mm"][i] - center[i]) / 1000 for i in range(3)]
        for i in range(3):
            for j in range(3):
                inertia[i][j] += c["inertia_kg_m2"][i][j] + c["mass_kg"] * (
                    (sum(x*x for x in d) if i == j else 0) - d[i]*d[j])
    return dict(mass_kg=mass, com_cad_mm=center,
                com_local_m=[(center[i] - origin[i]) / 1000 for i in range(3)], inertia_kg_m2=inertia)


def main():
    requirements = json.loads((CAD.parent / "requirements.json").read_text())
    budget = json.loads((CAD / "payload_budget.json").read_text())
    assert requirements["design_revision"] == budget["revision"] == "D6.5"
    doc = App.openDocument(str(SOURCE))
    objects = {o.Name: o for o in doc.Objects if hasattr(o, "MaterialBasis") and hasattr(o, "Shape")}
    shapes = {n: o.Shape for n, o in objects.items()}
    visuals = defaultdict(lambda: defaultdict(list))
    components = defaultdict(list)
    collision = defaultdict(list)
    exclusions = ["CargoEnvelopeD3", "StrapRouteX", "StrapRouteY"]

    def component(link, name, shape, mass, basis):
        assert mass > 0 and shape.Volume > 0, name
        components[link].append(dict(name=name, basis=basis, **mass_properties(shape, mass)))

    def visual(link, name, shape, material):
        visuals[link][material].append((name, shape))

    # Nominal rotor/stator partition for simulation; vendor STEP is NOT an
    # internal assembly. The cut at |Y|=153 isolates the external rotating can.
    for side, sign, link in [("L", 1, "left_wheel_link"), ("R", -1, "right_wheel_link")]:
        shape = shapes["M0601Motor" + side]
        outside = Part.makeBox(500, 200, 500, V(-200, 153 if sign == 1 else -353, -100))
        rotor = shape.common(outside)
        stator = shape.cut(outside)
        assert rotor.isValid() and stator.isValid()
        assert abs(rotor.Volume + stator.Volume - shape.Volume) / shape.Volume < 1e-6
        # Both inertia shares use the full motor envelope: most stator mass is
        # inside the can, not in the small visible fixed shaft left by this cut.
        component(link, "motor_rotor_"+side, shape, .200, "ASSUMPTION: 0.200kg rotating out of catalog 0.485kg motor; distributed over full vendor envelope")
        component("base_link", "motor_stator_"+side, shape, .285, "remaining catalog motor mass; inertia distributed over full vendor envelope, NOT just visible fixed shaft")
        visual(link, "motor_rotor_"+side, rotor, "motor")
        visual("base_link", "motor_stator_"+side, stator, "motor")
        for prefix, mass, color in [("Tire", .220, "rubber"), ("TireCover", .030, "motor")]:
            name = prefix + side
            component(link, name, shapes[name], mass, "ASSUMPTION: 0.250kg tire kit = 0.220kg tire + 0.030kg cover")
            visual(link, name, shapes[name], color)

    # Catalog caster assembly mass is 165g. Internal distribution is estimated
    # from nominal geometry and relative steel/rubber/polymer densities.
    caster = {"CasterTop": ("base_link", 7.85), "SwivelRace": ("caster_swivel_link", 7.85),
              "CasterFork": ("caster_swivel_link", 7.85), "CasterTire": ("caster_wheel_link", 1.10),
              "CasterCore": ("caster_wheel_link", 1.40)}
    norm = sum(shapes[n].Volume * rho for n, (_, rho) in caster.items())
    for n, (link, rho) in caster.items():
        component(link, n, shapes[n], .165 * shapes[n].Volume * rho / norm,
                  "TYG-50 catalog assembly 0.165kg; internal mass distribution ASSUMED from proxy geometry")
        visual(link, n, shapes[n], "rubber" if n == "CasterTire" else "steel")

    # CAD-volume material masses, with the same catalog overrides as D6.5.
    for n, o in objects.items():
        if o.MaterialBasis in ("reference", "purchased"):
            continue
        mass, basis = shapes[n].Volume * RHO[o.MaterialBasis], "CAD volume times assumed " + o.MaterialBasis + " density"
        if n.startswith("Rail400_"): mass, basis = .304, "3030 catalog 0.76kg/m, 400mm"
        elif n.startswith(("Cross300_", "UpperRail3030_")): mass, basis = .228, "3030 catalog 0.76kg/m, 300mm"
        elif n.startswith("Upright3030_"): mass, basis = .084, "SUS SF2 catalog 0.84kg/m, 100mm"
        elif n.startswith("Bracket_"): mass, basis = .015, "HBLFSN6 catalog 15g (retained lower brackets)"
        # Added LevelBracket masses intentionally retain the D6.5 CAD ledger.
        component("base_link", n, shapes[n], mass, basis)
        material = o.MaterialBasis.lower()
        if n.startswith("Upright"): material = "posts"
        elif n.startswith(("CustomMotor", "CasterAdapter")): material = "mounts"
        visual("base_link", n, shapes[n], material)

    electrical = {"BatteryBL1860B": .680, "BatteryAdapter03": .123, "Reserved_Computer": .500,
                  "Reserved_SupervisorRS485": .050, "Reserved_Protection": .200, "Reserved_ClampAndPower": .200}
    for n, m in electrical.items():
        component("base_link", n, shapes[n], m, "D6.5 electrical catalog mass or equipment budget; uniform envelope")
    for n, o in objects.items():
        if o.MaterialBasis != "reference" or n in exclusions: continue
        color = "rubber"
        if n == "BatteryBL1860B": color = "battery"
        elif n == "Reserved_Computer": color = "computer"
        elif n == "Reserved_EmergencyStop": color = "estop"
        elif n.startswith("Reserved_"): color = "electronics"
        elif "Belt" in n or "Buckle" in n: color = "belts"
        elif "Harness" in n or "Connector" in n: color = "wires"
        visual("base_link", n, shapes[n], color)

    component("base_link", "wiring_allowance", box([0, 0, 128], [380, 220, 35]), .400,
              "D6.5 wiring allowance; ASSUMED distributed across first floor, not copper-fill CAD density")
    component("base_link", "battery_belt_pads", box([-146, 0, 150], [120, 30, 85]), .150,
              "D6.5 125g battery belt plus 25g pads, simplified distribution")
    component("base_link", "computer_belts_pads", box([0, 10, 130], [120, 100, 40]), .030,
              "D6.5 computer/supervisor retaining allowance")
    component("base_link", "inherited_small_hardware", box([90, 0, 60], [80, 280, 20]), .030,
              "Inherited unmodeled retaining/grub screw allowance")
    component("base_link", "inherited_strap_allowance", box([-136.5, 0, 150], [113, 75, 20]), .040,
              "Legacy strap allowance retained in D6.5 ledger; no new additional mass")
    component("base_link", "cargo_belts_pads", box([0, 0, 243], [200, 180, 20]), .280,
              "D6.5 cargo belts/pads allowance stowed on deck in empty variant")

    def box_collision(link, name, lo, hi):
        origin = ORIGINS[link]
        collision[link].append(dict(name=name, kind="box", size_m=[(hi[i]-lo[i])/1000 for i in range(3)],
                                    xyz_m=[((hi[i]+lo[i])/2-origin[i])/1000 for i in range(3)]))

    def from_bbox(link, name, shape):
        b = shape.BoundBox
        box_collision(link, name, [b.XMin, b.YMin, b.ZMin], [b.XMax, b.YMax, b.ZMax])

    for n in shapes:
        if n.startswith(("Rail400_", "Cross300_", "Upright3030_", "UpperRail3030_", "CustomMotorMount", "PrintedStop")) or n in (
                "AluminumDeckD3", "ComputerBarrierPLA", "CasterAdapter", "CasterTop", *electrical, "Reserved_EmergencyStop", "BatteryBuckleEnvelope"):
            from_bbox("base_link", n, shapes[n])
        elif n.startswith("FloorPLA_"):
            b = shapes[n].BoundBox
            box_collision("base_link", n, [b.XMin, b.YMin, 99], [b.XMax, b.YMax, 101.4])
            ix,iy=map(int,n.split('_')[1:])
            lo_x,hi_x=(-200,-32) if ix==0 else (32,200)
            lo_y,hi_y=(-32.2,-14.8) if iy==0 else (14.8,32.2)
            # Conservative rectangular proxy of the tapered underside rib.
            box_collision("base_link",n+'_rib',[lo_x,lo_y,84],[hi_x,hi_y,99])
        elif n=='SeamBeamPLA':
            for index,(lo,hi) in enumerate([
                ([-32,-50,94],[32,50,96.5]),([-32,-50,96.5],[32,-8.5,99]),
                ([-32,8.5,96.5],[32,50,99]),([-32,-50,79],[-28.8,50,94]),
                ([28.8,-50,79],[32,50,94]),([-32,-50,74],[32,-46.8,94]),
                ([-32,46.8,74],[32,50,94])]):
                box_collision('base_link','seam_beam_'+str(index),lo,hi)
    collision["caster_swivel_link"].append(dict(name="swivel_race", kind="cylinder", radius_m=.019,
                                              length_m=.009, xyz_m=[0, 0, 0], rpy=[0, 0, 0]))
    for i, s in enumerate(shapes["CasterFork"].Solids): from_bbox("caster_swivel_link", "fork_"+str(i), s)
    for link, radius, width in [("left_wheel_link", .05035, .043), ("right_wheel_link", .05035, .043),
                                ("caster_wheel_link", .025, .020)]:
        collision[link].append(dict(name="rolling_contact", kind="cylinder", radius_m=radius,
                                   length_m=width, xyz_m=[0, 0, 0], rpy=[math.pi/2, 0, 0]))

    # One visual mesh per link/material, with each vertex already in meters.
    (HERE / "meshes").mkdir(parents=True, exist_ok=True)
    mesh_manifest = []
    mesh_refs = defaultdict(list)
    def export_mesh(link, material, items, suffix=""):
        shape = Part.makeCompound([s for _, s in items])
        mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=.15, AngularDeflection=.25, Relative=False)
        points, triangles = mesh.Topology
        origin = ORIGINS[link]
        vertices = [V(*[(v[i]-origin[i])/1000 for i in range(3)]) for v in points]
        facets = []
        for tri in triangles:
            a, b, c = [vertices[i] for i in tri]
            normal = (b-a).cross(c-a)
            length = normal.Length
            if length < 1e-20:
                continue
            facets.append(struct.pack("<12fH", *[x/length for x in normal], *a, *b, *c, 0))
        path = HERE / "meshes" / f"{link}_{material}{suffix}.stl"
        with path.open("wb") as out:
            out.write(b"AMR D6.5 visual; METERS; FreeCAD tessellation".ljust(80, b" "))
            out.write(struct.pack("<I", len(facets)))
            out.writelines(facets)
        entry = dict(file=path.relative_to(HERE).as_posix(), material=material, link=link,
                     triangles=len(facets), degenerate_facets_removed=len(triangles)-len(facets),
                     sha256=sha(path), source_objects=[n for n, _ in items],
                     bounds_m=[[min(v[i] for v in vertices) for i in range(3)], [max(v[i] for v in vertices) for i in range(3)]])
        mesh_manifest.append(entry)
        return entry
    for link, by_color in visuals.items():
        for color, items in by_color.items(): mesh_refs[link].append(export_mesh(link, color, items))
    loaded_belts = export_mesh("base_link", "belts", [(n, shapes[n]) for n in ["StrapRouteX", "StrapRouteY"]], "_loaded")

    joints = [
        dict(name="left_wheel_joint", parent="base_link", child="left_wheel_link", axis=[0, 1, 0], effort=.96, velocity=115*2*math.pi/60, damping=0),
        dict(name="right_wheel_joint", parent="base_link", child="right_wheel_link", axis=[0, 1, 0], effort=.96, velocity=115*2*math.pi/60, damping=0),
        dict(name="caster_swivel_joint", parent="base_link", child="caster_swivel_link", axis=[0, 0, 1], effort=0, velocity=30, damping=0),
        dict(name="caster_wheel_joint", parent="caster_swivel_link", child="caster_wheel_link", axis=[0, 1, 0], effort=0, velocity=30, damping=0),
    ]
    variants = {}
    for payload in [0, 10]:
        robot = ET.Element("robot", name="amr_d65" + ("_payload_10kg" if payload else ""))
        robot.append(ET.Comment("Generated from D6.5. SI units; +X forward, +Y left, +Z up. Inertias are estimates."))
        for color, rgba in COLORS.items():
            ET.SubElement(ET.SubElement(robot, "material", name=color), "color", rgba=fmt(rgba))
        comp = {k: list(v) for k, v in components.items()}
        if payload:
            comp["base_link"] = [c for c in comp["base_link"] if c["name"] != "cargo_belts_pads"]
            comp["base_link"].append(dict(name="cargo_belts_pads", basis="D6.5 loaded restraint allowance at CAD z310mm",
                                         **mass_properties(box([0, 0, 310], [230, 220, 160]), .280)))
            comp["payload_link"] = [dict(name="example_cargo_10kg", basis="Example uniform restrained cargo 200x200x160mm",
                                         **mass_properties(box(ORIGINS["payload_link"], [200, 200, 160]), payload))]
        properties = {n: aggregate(c, ORIGINS[n]) for n, c in comp.items()}
        total = sum(p["mass_kg"] for p in properties.values())
        assert abs(total - budget["vehicle_mass_estimate_kg"] - payload) < 1e-8, total
        for link, prop in properties.items():
            el = ET.SubElement(robot, "link", name=link)
            inertial = ET.SubElement(el, "inertial")
            ET.SubElement(inertial, "origin", xyz=fmt(prop["com_local_m"]), rpy="0 0 0")
            ET.SubElement(inertial, "mass", value=fmt(prop["mass_kg"]))
            tensor = prop["inertia_kg_m2"]
            ET.SubElement(inertial, "inertia", **{key: fmt(tensor[i][j]) for key, i, j in [
                ("ixx", 0, 0), ("ixy", 0, 1), ("ixz", 0, 2), ("iyy", 1, 1), ("iyz", 1, 2), ("izz", 2, 2)]})
            refs = mesh_refs[link] + ([loaded_belts] if payload and link == "base_link" else [])
            for ref in refs:
                vis = ET.SubElement(el, "visual", name=Path(ref["file"]).stem)
                ET.SubElement(ET.SubElement(vis, "geometry"), "mesh", filename=ref["file"], scale="1 1 1")
                ET.SubElement(vis, "material", name=ref["material"])
            cols = list(collision[link])
            if link == "payload_link":
                vis = ET.SubElement(el, "visual", name="example_cargo")
                ET.SubElement(ET.SubElement(vis, "geometry"), "box", size="0.2 0.2 0.16")
                ET.SubElement(vis, "material", name="payload")
                cols.append(dict(name="cargo_box", kind="box", size_m=[.2, .2, .16], xyz_m=[0, 0, 0]))
            for c in cols:
                col = ET.SubElement(el, "collision", name=link+"_"+c["name"])
                ET.SubElement(col, "origin", xyz=fmt(c["xyz_m"]), rpy=fmt(c.get("rpy", [0, 0, 0])))
                geo = ET.SubElement(col, "geometry")
                if c["kind"] == "box": ET.SubElement(geo, "box", size=fmt(c["size_m"]))
                else: ET.SubElement(geo, "cylinder", radius=fmt(c["radius_m"]), length=fmt(c["length_m"]))
        for j in joints + ([dict(name="payload_fixed_joint", parent="base_link", child="payload_link")] if payload else []):
            el = ET.SubElement(robot, "joint", name=j["name"], type="continuous" if "axis" in j else "fixed")
            ET.SubElement(el, "parent", link=j["parent"]); ET.SubElement(el, "child", link=j["child"])
            ET.SubElement(el, "origin", xyz=fmt([(a-b)/1000 for a, b in zip(ORIGINS[j["child"]], ORIGINS[j["parent"]])]), rpy="0 0 0")
            if "axis" in j:
                ET.SubElement(el, "axis", xyz=fmt(j["axis"]))
                ET.SubElement(el, "limit", effort=fmt(j["effort"]), velocity=fmt(j["velocity"]))
                ET.SubElement(el, "dynamics", damping=fmt(j["damping"]), friction="0")
        ET.indent(robot)
        path = HERE / (robot.attrib["name"] + ".urdf")
        ET.ElementTree(robot).write(path, encoding="utf-8", xml_declaration=True)
        variants[path.name] = dict(payload_kg=payload, mass_kg=total, sha256=sha(path), links=properties,
                                   assembly=aggregate([c for v in comp.values() for c in v], ORIGINS["base_link"]),
                                   components=comp)

    settings = dict(schema_version=1, design_revision="D6.5", target_isaac_sim="5.0 / 5.1",
        wheel_radius_m=.05035, track_m=.349, caster_radius_m=.025, caster_trail_m=.016,
        base_origin_in_cad_mm=ORIGINS["base_link"], spawn_translation_m=[0, 0, .05235],
        max_motor_torque_Nm=.96, rated_motor_speed_rad_s=115*2*math.pi/60,
        initial_speed_m_s=.15, initial_yaw_rate_rad_s=.3, acceleration_limit_m_s2=.2,
        drive_damping_Nm_per_rad_s=.4, tire_static_friction=.8, tire_dynamic_friction=.6,
        physics_dt_s=1/240, gravity_m_s2=9.80665,
        driven_joints=["left_wheel_joint", "right_wheel_joint"],
        passive_joints=["caster_swivel_joint", "caster_wheel_joint"],
        contact_note="Friction and velocity servo gain are starting assumptions, not measured tire/controller properties.")
    (HERE / "simulation_config.json").write_text(json.dumps(settings, indent=2)+"\n")
    manifest = dict(schema_version=1, design_revision="D6.5", source_cad=SOURCE.relative_to(ROOT).as_posix(),
        source_cad_sha256=sha(SOURCE), source_git_commit=subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
        source_git_commit_scope="Checkout parent when exporting; uncommitted generated revision is identified by the CAD and mass-budget SHA256 values, not by this parent commit alone.",
        source_mass_budget_sha256=sha(CAD / "payload_budget.json"), units="meter kilogram second radian",
        link_origins_cad_mm=ORIGINS, joints=joints, meshes=mesh_manifest, variants=variants,
        excluded_empty_visuals=exclusions, source_cad_modified=False, isaac_sim_runtime_tested=False,
        mass_note="Totals reconcile exactly with D6.5 ledger. Component densities, rotor/stator split, caster distribution, unselected electronics and allowances are estimates. CAD-derived tensor is not a measured tensor.",
        collision_note="Explicit boxes/cylinders for mobility, with deck holes/slots/small hardware omitted. No structural deformation, tire compliance, electrical brake, regenerative power or motor thermal model.")
    (HERE / "export_manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    App.closeDocument(doc.Name)
    print(json.dumps(dict(meshes=len(mesh_manifest), triangles=sum(m["triangles"] for m in mesh_manifest),
                         variants={n:dict(mass_kg=v["mass_kg"], com_cad_mm=v["assembly"]["com_cad_mm"]) for n,v in variants.items()})))


if __name__ == "__main__":
    main()
