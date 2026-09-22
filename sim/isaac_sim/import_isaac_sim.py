"""Isaac Sim 5.0/5.1: import, configure, export USD and optionally drive.

Run with Isaac Sim's python.sh, not a generic Python interpreter.
No Isaac Sim runtime is bundled. This script has not yet been run in Isaac Sim.
"""
from pathlib import Path
import argparse
import json
import math
import xml.etree.ElementTree as ET

from drive import CONFIG, ramp, wheel_speeds

HERE = Path(__file__).resolve().parent


def import_into_stage(payload=0):
    """Import into a meter/Z-up stage; never clear an existing user's stage."""
    import omni.kit.app
    import omni.kit.commands
    import omni.usd
    from pxr import Gf, PhysxSchema, Usd, UsdGeom, UsdPhysics, UsdShade

    stage = omni.usd.get_context().get_stage()
    if stage is None:
        raise RuntimeError("Open a new stage first")
    if UsdGeom.GetStageUpAxis(stage) != UsdGeom.Tokens.z or not math.isclose(UsdGeom.GetStageMetersPerUnit(stage), 1):
        raise ValueError("Use a Z-up stage with metersPerUnit=1")
    filename = "amr_d64_payload_10kg.urdf" if payload == 10 else "amr_d64.urdf"
    if payload not in (0, 10):
        raise ValueError("Available payloads: 0 or 10kg")
    root_name = ET.parse(HERE / filename).getroot().attrib["name"]
    if stage.GetPrimAtPath("/"+root_name):
        raise ValueError("This robot is already present; use a new stage or a different stage")
    manager = omni.kit.app.get_app().get_extension_manager()
    manager.set_extension_enabled_immediate("isaacsim.asset.importer.urdf", True)
    ok, config = omni.kit.commands.execute("URDFCreateImportConfig")
    if not ok:
        raise RuntimeError("URDFCreateImportConfig failed")
    config.set_fix_base(False)
    config.set_merge_fixed_joints(False)
    config.set_import_inertia_tensor(True)
    config.set_distance_scale(1.0)
    config.set_up_vector(0, 0, 1)
    config.set_collision_from_visuals(False)
    config.set_convex_decomp(False)
    config.set_replace_cylinders_with_capsules(False)
    config.set_self_collision(False)
    config.set_default_drive_strength(0.0)
    config.set_default_position_drive_damping(0.0)
    config.set_create_physics_scene(False)
    config.set_make_default_prim(False)
    ok, robot_path = omni.kit.commands.execute(
        "URDFParseAndImportFile", urdf_path=str(HERE / filename), import_config=config,
        dest_path="", get_articulation_root=False)
    if not ok or not robot_path or not stage.GetPrimAtPath(robot_path):
        raise RuntimeError(f"URDF import failed: {robot_path}")
    root = stage.GetPrimAtPath(robot_path)
    UsdGeom.XformCommonAPI(root).SetTranslate(Gf.Vec3d(*CONFIG["spawn_translation_m"]))
    prims = list(Usd.PrimRange(root))
    revolute = {p.GetName(): p for p in prims if p.IsA(UsdPhysics.RevoluteJoint)}
    expected = set(CONFIG["driven_joints"] + CONFIG["passive_joints"])
    if set(revolute) != expected:
        raise RuntimeError(f"Unexpected imported joints: {sorted(revolute)}")

    for name, prim in revolute.items():
        # Do not inherit position servos on a continuous wheel or passive caster.
        for instance in ("angular", "linear"):
            if prim.HasAPI(UsdPhysics.DriveAPI, instance):
                prim.RemoveAPI(UsdPhysics.DriveAPI, instance)
        if name in CONFIG["driven_joints"]:
            drive = UsdPhysics.DriveAPI.Apply(prim, "angular")
            drive.CreateTypeAttr("force")
            drive.CreateStiffnessAttr(0.0)
            # USD angular gains use degrees; our configuration is in radians.
            drive.CreateDampingAttr(CONFIG["drive_damping_Nm_per_rad_s"] * math.pi / 180)
            drive.CreateMaxForceAttr(CONFIG["max_motor_torque_Nm"])
            drive.CreateTargetVelocityAttr(0.0)
            PhysxSchema.PhysxJointAPI.Apply(prim).CreateMaxJointVelocityAttr(
                math.degrees(CONFIG["rated_motor_speed_rad_s"]))
        else:
            assert not prim.HasAPI(UsdPhysics.DriveAPI, "angular"), name

    material = UsdShade.Material.Define(stage, robot_path+"/tire_contact_material")
    physics_material = UsdPhysics.MaterialAPI.Apply(material.GetPrim())
    physics_material.CreateStaticFrictionAttr(CONFIG["tire_static_friction"])
    physics_material.CreateDynamicFrictionAttr(CONFIG["tire_dynamic_friction"])
    physics_material.CreateRestitutionAttr(0.0)
    for prim in prims:
        if prim.HasAPI(UsdPhysics.CollisionAPI):
            api = PhysxSchema.PhysxCollisionAPI.Apply(prim)
            api.CreateContactOffsetAttr(.001)
            api.CreateRestOffsetAttr(0.0)
            UsdShade.MaterialBindingAPI.Apply(prim).Bind(material, UsdShade.Tokens.weakerThanDescendants, "physics")
        if prim.HasAPI(UsdPhysics.ArticulationRootAPI):
            api = PhysxSchema.PhysxArticulationAPI.Apply(prim)
            api.CreateEnabledSelfCollisionsAttr(False)
            api.CreateSolverPositionIterationCountAttr(16)
            api.CreateSolverVelocityIterationCountAttr(4)
        if prim.IsA(UsdPhysics.FixedJoint):
            joint = UsdPhysics.FixedJoint(prim)
            if not joint.GetBody0Rel().GetTargets() or not joint.GetBody1Rel().GetTargets():
                raise RuntimeError("Unexpected world-fixed base joint")
    roots = [str(p.GetPath()) for p in prims if p.HasAPI(UsdPhysics.ArticulationRootAPI)]
    masses = [UsdPhysics.MassAPI(p).GetMassAttr().Get() for p in prims if p.HasAPI(UsdPhysics.RigidBodyAPI)]
    expected_mass = json.loads((HERE / "export_manifest.json").read_text())["variants"][filename]["mass_kg"]
    if len(roots) != 1 or any(m is None or m <= 0 for m in masses) or not math.isclose(sum(masses), expected_mass, abs_tol=1e-4):
        raise RuntimeError(f"Imported articulation/mass mismatch: {roots}, {masses}")
    return dict(robot_path=robot_path, articulation_path=roots[0], total_mass_kg=sum(masses),
                joint_paths={n: str(p.GetPath()) for n,p in revolute.items()}, urdf=filename)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=int, choices=[0, 10], default=0)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--seconds", type=float, default=8, help="0 = import/export only")
    parser.add_argument("--speed", type=float, default=.10, help="m/s; initial limit +/-0.15")
    parser.add_argument("--yaw-rate", type=float, default=0, help="rad/s; initial limit +/-0.3")
    parser.add_argument("--output", type=Path, default=HERE / "output/amr_d64_scene.usda")
    args = parser.parse_args()
    targets = wheel_speeds(args.speed, args.yaw_rate)
    if not math.isfinite(args.seconds) or args.seconds < 0:
        parser.error("seconds must be finite and nonnegative")
    output = args.output.resolve()
    if output.exists():
        parser.error("Output already exists; choose a new --output path")
    output.parent.mkdir(parents=True, exist_ok=True)

    # SimulationApp must be created BEFORE importing Kit/Isaac/PXR modules.
    from isaacsim import SimulationApp
    app = SimulationApp({"headless": args.headless})
    try:
        import numpy as np
        import omni.usd
        from pxr import UsdGeom, UsdLux
        from isaacsim.core.api import World
        from isaacsim.core.prims import SingleArticulation
        from isaacsim.core.utils.types import ArticulationAction
        from isaacsim.core.utils.viewports import set_camera_view

        dt = CONFIG["physics_dt_s"]
        world = World(stage_units_in_meters=1.0, physics_dt=dt, rendering_dt=1/60)
        world.get_physics_context().set_gravity(-CONFIG["gravity_m_s2"])
        world.scene.add_ground_plane(size=10, static_friction=CONFIG["tire_static_friction"],
                                     dynamic_friction=CONFIG["tire_dynamic_friction"], restitution=0)
        stage = omni.usd.get_context().get_stage()
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
        info = import_into_stage(args.payload)
        light = UsdLux.DomeLight.Define(stage, "/World/AMRLight")
        light.CreateIntensityAttr(800)
        if not args.headless:
            set_camera_view(eye=np.array([1.0, 1.0, .85]), target=np.array([0, 0, .15]))
        # Save the initial scene, without a persistent nonzero drive command.
        stage.GetRootLayer().Export(str(output))
        robot = world.scene.add(SingleArticulation(prim_path=info["articulation_path"], name="amr"))
        report = dict(**info, usd=str(output), isaac_runtime_imported=True, dynamics_executed=False,
                      note="A simulator smoke run is not hardware qualification or a calibrated traction test")
        if args.seconds > 0:
            world.reset()
            assert set(robot.dof_names) == set(CONFIG["driven_joints"] + CONFIG["passive_joints"]), robot.dof_names
            indices = np.array([robot.get_dof_index(n) for n in CONFIG["driven_joints"]])
            previous = [0.0, 0.0]
            start = None
            for i in range(max(1, round(args.seconds / dt))):
                if not app.is_running(): break
                t = i*dt
                # 1s settle, ramped command, and stop for the final1s.
                request = targets if 1 <= t < max(1, args.seconds-1) else [0, 0]
                previous = ramp(previous, request, dt)
                robot.apply_action(ArticulationAction(joint_velocities=np.array(previous), joint_indices=indices))
                world.step(render=not args.headless and i % 4 == 0)
                pose, rotation = robot.get_world_pose()
                if start is None: start = pose.copy()
                if not np.all(np.isfinite(pose)) or pose[2] < 0 or pose[2] > .20:
                    raise RuntimeError(f"Invalid/fallen robot pose: {pose}")
            if start is None:
                raise RuntimeError("Application closed before a physics step completed")
            report.update(dynamics_executed=True, elapsed_s=world.current_time,
                          initial_xyz_m=start.tolist(), final_xyz_m=pose.tolist(), final_quaternion_wxyz=rotation.tolist(),
                          driven_joint_velocities_rad_s=robot.get_joint_velocities(joint_indices=indices).tolist())
        output.with_suffix(".validation.json").write_text(json.dumps(report, indent=2)+"\n")
        print(json.dumps(report, indent=2))
    finally:
        app.close()


if __name__ == "__main__":
    main()
