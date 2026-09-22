"""Additional CPU physics smoke check of URDF; explicitly NOT Isaac Sim.

Adds a test-only floating root, floor and torque-limited wheel velocity servo.
The delivered URDF is read without modification. No calibrated tire model.
"""
from pathlib import Path
import argparse
import json
import math
import xml.etree.ElementTree as ET

import mujoco
import numpy as np

from drive import CONFIG, ramp, wheel_speeds

HERE = Path(__file__).resolve().parent


def make_model(path, visuals=False):
    xml = ET.parse(path).getroot()
    for mesh in xml.findall(".//mesh"):
        mesh.set("filename", str(path.parent / mesh.get("filename")))
    ET.SubElement(ET.SubElement(xml, "mujoco"), "compiler", discardvisual="false" if visuals else "true",
                  fusestatic="false", strippath="false")
    spec = mujoco.MjSpec.from_string(ET.tostring(xml, encoding="unicode"))
    base = spec.body("base_link")
    base.add_freejoint(name="test_floating_base")
    base.pos = CONFIG["spawn_translation_m"]
    for geom in spec.geoms:
        if geom.contype or geom.conaffinity:
            geom.contype, geom.conaffinity = 1, 2  # floor contact, no self collision
            geom.friction = [CONFIG["tire_dynamic_friction"], 0, 0]
            geom.condim = 3
            geom.rgba = [.45, .50, .55, 1]
    spec.worldbody.add_geom(name="test_floor", type=mujoco.mjtGeom.mjGEOM_PLANE, size=[4, 4, .01],
                            rgba=[.84, .87, .90, 1], contype=2, conaffinity=1, condim=3,
                            friction=[CONFIG["tire_dynamic_friction"], 0, 0])
    if visuals:
        spec.worldbody.add_light(pos=[.4, .2, 2], dir=[0, 0, -1], diffuse=[.8, .8, .8])
    spec.option.timestep = CONFIG["physics_dt_s"]
    spec.option.gravity = [0, 0, -CONFIG["gravity_m_s2"]]
    spec.option.integrator = mujoco.mjtIntegrator.mjINT_IMPLICITFAST
    model = spec.compile()
    return model, mujoco.MjData(model)


def run_case(path, speed, yaw):
    model, data = make_model(path)
    ids = [model.joint(n).id for n in CONFIG["driven_joints"]]
    dofs = model.jnt_dofadr[ids]
    previous = [0, 0]
    dt = CONFIG["physics_dt_s"]
    torque_max = 0.0
    min_z, max_tilt, max_nonwheel_contacts = 1.0, 0.0, 0
    requested = wheel_speeds(speed, yaw)
    snapshots = []
    for step in range(round(8/dt)):
        t = step*dt
        previous = ramp(previous, requested if 1 <= t < 6 else [0, 0], dt)
        torques = np.clip(CONFIG["drive_damping_Nm_per_rad_s"] * (np.array(previous)-data.qvel[dofs]),
                          -CONFIG["max_motor_torque_Nm"], CONFIG["max_motor_torque_Nm"])
        data.qfrc_applied[:] = 0
        data.qfrc_applied[dofs] = torques
        mujoco.mj_step(model, data)
        assert np.isfinite(data.qpos).all() and np.isfinite(data.qvel).all()
        torque_max = max(torque_max, float(np.abs(torques).max()))
        min_z = min(min_z, float(data.qpos[2]))
        rotation = data.xmat[model.body("base_link").id].reshape(3, 3)
        tilt = math.acos(np.clip(rotation[2, 2], -1, 1))
        max_tilt = max(max_tilt, tilt)
        bad = 0
        for contact in data.contact:
            for geom_id in (contact.geom1, contact.geom2):
                b = model.body(int(model.geom_bodyid[geom_id])).name
                if b not in ("world", "left_wheel_link", "right_wheel_link", "caster_wheel_link"):
                    bad += 1
        max_nonwheel_contacts = max(max_nonwheel_contacts, bad)
        if step in (round(1/dt)-1, round(6/dt)-1): snapshots.append(data.qpos[:3].tolist())
    angle = math.atan2(rotation[1, 0], rotation[0, 0])
    assert min_z > .045 and max_tilt < .05 and max_nonwheel_contacts == 0
    assert torque_max <= .96 + 1e-8
    assert float(np.linalg.norm(data.qvel[:3])) < .03, "Failed to stop"
    if speed > 0:
        assert data.qpos[0] > .3 and abs(data.qpos[1]) < .06
    if yaw > 0:
        # Correct-direction mobility check, not a yaw tracking qualification.
        # Wide cylinders scrub during skid steering; this uncalibrated P servo
        # has steady error, especially with payload. Record it explicitly.
        assert .5 < angle < 1.7 and np.linalg.norm(data.qpos[:2]) < .10, dict(yaw=angle, xyz=data.qpos[:3].tolist(), torque=torque_max)
    assert not any(w.number for w in data.warning), [w.number for w in data.warning]
    return dict(status="passed", command_m_s=speed, command_yaw_rad_s=yaw, simulated_seconds=float(data.time),
                mass_kg=float(model.body_mass.sum()), final_xyz_m=data.qpos[:3].tolist(), final_yaw_rad=angle,
                final_linear_speed_m_s=float(np.linalg.norm(data.qvel[:3])), maximum_drive_torque_Nm=torque_max,
                maximum_body_tilt_deg=math.degrees(max_tilt), minimum_base_origin_z_m=min_z,
                nonwheel_floor_contacts=max_nonwheel_contacts, pose_after_settle_and_drive_m=snapshots)


def preview(path):
    from PIL import Image
    model, data = make_model(path, visuals=True)
    for _ in range(240): mujoco.mj_step(model, data)
    model.vis.global_.offwidth, model.vis.global_.offheight = 1200, 900
    camera = mujoco.MjvCamera()
    camera.lookat = [-.07, 0, .16]
    camera.distance, camera.azimuth, camera.elevation = .92, 140, -25
    option = mujoco.MjvOption()
    option.geomgroup[0] = 0  # hide robot collision proxies
    # URDF visual geoms are group1; ground is group0 so give it group2.
    model.geom_group[model.geom("test_floor").id] = 2
    with mujoco.Renderer(model, height=900, width=1200) as renderer:
        renderer.update_scene(data, camera=camera, scene_option=option)
        Image.fromarray(renderer.render()).save(HERE / "urdf_preview_mujoco.png")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args()
    result = {name: {"straight": run_case(HERE/name, .10, 0), "turn_left": run_case(HERE/name, 0, .30)}
              for name in ("amr_d61.urdf", "amr_d61_payload_10kg.urdf")}
    if args.render: preview(HERE / "amr_d61.urdf")
    report = dict(status="passed", simulator="MuJoCo "+mujoco.__version__, isaac_sim_runtime_tested=False,
                  urdf_models=result, added_test_fixtures="floating base, flat floor, no self collision, torque-limited SI velocity servo",
                  scope="CPU smoke check only: contact, mass/inertia loading, straight/turn/stop. Friction is assumed; no rolling-resistance, controller latency, tire deformation or power model.")
    (HERE / "mujoco_smoke_validation.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
