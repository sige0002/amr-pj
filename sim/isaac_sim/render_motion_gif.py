"""Render an actual MuJoCo URDF physics run to GIF; no animated body poses.

MUJOCO_GL=egl python render_motion_gif.py
Requires the existing validation environment, ffmpeg, and a Japanese font.
The floor grid and wheel markers are visual aids, not physical model changes.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import shutil
import subprocess
import tempfile

import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from drive import CONFIG, ramp, wheel_speeds
from smoke_mujoco import HERE, make_model

FPS = 15
DURATION = 16
WIDTH, HEIGHT = 800, 600
PHASES = [
    (0, 1, "接地待ち", 0.0, 0.0),
    (1, 5, "直進", .10, 0.0),
    (5, 6, "停止", 0.0, 0.0),
    (6, 11, "左旋回", 0.0, .30),
    (11, 14, "直進", .10, 0.0),
    (14, 16, "停止", 0.0, 0.0),
]


def phase_at(t):
    return next(p for p in PHASES if p[0] <= t < p[1])


def add_visual_guides(scene, data, model):
    """World-fixed10cm grid and rotating wheel indicators in render scene only."""
    def geom(kind, size, pos, color, matrix=None):
        assert scene.ngeom < scene.maxgeom
        target = scene.geoms[scene.ngeom]
        mujoco.mjv_initGeom(target, kind, np.asarray(size, dtype=float), np.asarray(pos, dtype=float),
                            np.asarray(matrix if matrix is not None else np.eye(3), dtype=float).reshape(9),
                            np.asarray(color, dtype=np.float32))
        target.category = mujoco.mjtCatBit.mjCAT_DECOR
        scene.ngeom += 1

    for k in range(-10, 16):
        c = k/10
        color = [.53, .60, .67, 1] if k % 5 == 0 else [.67, .72, .77, 1]
        geom(mujoco.mjtGeom.mjGEOM_BOX, [1.25, .00065, .00015], [.25, c, .0002], color)
        geom(mujoco.mjtGeom.mjGEOM_BOX, [.00065, 1.25, .00015], [c, .25, .0002], color)
    for link, sign in [("left_wheel_link", 1), ("right_wheel_link", -1)]:
        body = model.body(link).id
        rotation = data.xmat[body].reshape(3, 3)
        # A thin stripe outside the cover makes wheel rotation visible.
        pos = data.xpos[body] + rotation @ np.array([0, sign*.0290, .010])
        geom(mujoco.mjtGeom.mjGEOM_BOX, [.0020, .0005, .012], pos, [.95, .71, .16, 1], rotation)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", type=Path, default=Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"))
    args = parser.parse_args()
    if not args.font.is_file():
        parser.error("Pass --font with a Japanese TTF/TTC/OTF font")
    if shutil.which("ffmpeg") is None:
        parser.error("ffmpeg is required")
    font = ImageFont.truetype(str(args.font), 19)
    small = ImageFont.truetype(str(args.font), 15)
    urdf = HERE / "amr_d64.urdf"
    output = HERE / "amr_d64_motion_mujoco.gif"
    model, data = make_model(urdf, visuals=True)
    model.vis.global_.offwidth, model.vis.global_.offheight = WIDTH, HEIGHT
    model.geom_group[model.geom("test_floor").id] = 2
    model.geom_rgba[model.geom("test_floor").id] = [.87, .90, .94, 1]
    option = mujoco.MjvOption()
    option.geomgroup[0] = 0  # hide collisions; preserve URDF visual geometry
    camera = mujoco.MjvCamera()
    camera.lookat = [.18, .10, .06]
    camera.distance, camera.azimuth, camera.elevation = 1.47, 130, -40
    dt = CONFIG["physics_dt_s"]
    steps_per_frame = round(1 / FPS / dt)
    assert math.isclose(steps_per_frame * dt * FPS, 1)
    dofs = model.jnt_dofadr[[model.joint(n).id for n in CONFIG["driven_joints"]]]
    previous = [0, 0]
    records = []
    max_torque, max_tilt, nonwheel_contacts = 0.0, 0.0, 0
    base_id = model.body("base_link").id
    min_z = 1.0
    mujoco.mj_forward(model, data)

    with tempfile.TemporaryDirectory(prefix="amr-motion-frames-") as temp:
        frames_dir = Path(temp)
        with mujoco.Renderer(model, height=HEIGHT, width=WIDTH) as renderer:
            for step in range(round(DURATION / dt)):
                t = step*dt
                _, _, phase, v, yaw = phase_at(t)
                previous = ramp(previous, wheel_speeds(v, yaw), dt)
                torques = np.clip(CONFIG["drive_damping_Nm_per_rad_s"] * (np.asarray(previous)-data.qvel[dofs]),
                                  -CONFIG["max_motor_torque_Nm"], CONFIG["max_motor_torque_Nm"])
                data.qfrc_applied[:] = 0
                data.qfrc_applied[dofs] = torques
                mujoco.mj_step(model, data)
                assert np.isfinite(data.qpos).all() and np.isfinite(data.qvel).all()
                max_torque = max(max_torque, float(np.abs(torques).max()))
                min_z = min(min_z, float(data.qpos[2]))
                rotation = data.xmat[base_id].reshape(3, 3)
                max_tilt = max(max_tilt, math.acos(np.clip(rotation[2, 2], -1, 1)))
                for contact in data.contact:
                    for gid in (contact.geom1, contact.geom2):
                        if model.body(int(model.geom_bodyid[gid])).name not in (
                                "world", "left_wheel_link", "right_wheel_link", "caster_wheel_link"):
                            nonwheel_contacts += 1
                if step % steps_per_frame:
                    continue
                renderer.update_scene(data, camera=camera, scene_option=option)
                add_visual_guides(renderer.scene, data, model)
                image = Image.fromarray(renderer.render())
                draw = ImageDraw.Draw(image)
                draw.rectangle((0, 0, WIDTH, 64), fill=(22, 31, 43))
                draw.text((18, 7), "AMR D6.4 走行シミュレーション / MuJoCo", font=font, fill=(242, 246, 250))
                draw.text((18, 36), f"空車 {model.body_mass.sum():.3f} kg    格子 10 cm    実時間再生    {t:04.1f} / {DURATION} s", font=small, fill=(181, 199, 216))
                draw.rectangle((0, HEIGHT-44, WIDTH, HEIGHT), fill=(22, 31, 43))
                speed = float(np.linalg.norm(data.qvel[:2]))
                draw.text((18, HEIGHT-34), f"{phase}  |  速度 {speed:.2f} m/s", font=font, fill=(248, 205, 106))
                draw.text((WIDTH-326, HEIGHT-31), "直進 → 停止 → 左旋回 → 直進 → 停止", font=small, fill=(225, 232, 238))
                # A time bar distinguishes normal loop restart from continuous motion.
                draw.rectangle((0, HEIGHT-3, round(WIDTH*t/DURATION), HEIGHT), fill=(87, 170, 212))
                image.save(frames_dir / f"frame_{len(records):04d}.png")
                records.append(dict(time_s=t, phase=phase, command_m_s=v, command_yaw_rad_s=yaw,
                                    base_xyz_m=data.qpos[:3].tolist(), yaw_rad=math.atan2(rotation[1, 0], rotation[0, 0]),
                                    speed_m_s=speed, wheel_velocity_rad_s=data.qvel[dofs].tolist()))
                if len(records) % (FPS*4) == 0:
                    print(f"Rendered {len(records)}/{FPS*DURATION} frames", flush=True)
        assert min_z > .045 and max_tilt < .05 and nonwheel_contacts == 0
        assert max_torque <= CONFIG["max_motor_torque_Nm"] + 1e-9
        assert data.qpos[0] > .40 and data.qpos[1] > .15
        assert np.linalg.norm(data.qvel[:3]) < .005 and abs(data.qvel[5]) < .01
        assert not any(w.number for w in data.warning)
        filters = ("[0:v]split[a][b];[a]palettegen=stats_mode=diff[p];"
                   "[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle")
        subprocess.run(["ffmpeg", "-v", "error", "-framerate", str(FPS), "-i", str(frames_dir/"frame_%04d.png"),
                        "-filter_complex", filters, "-loop", "0", "-y", str(output)], check=True)
    with Image.open(output) as gif:
        assert gif.is_animated and gif.n_frames == FPS*DURATION and gif.size == (WIDTH, HEIGHT)
        playback_ms = 0
        for i in range(gif.n_frames):
            gif.seek(i)
            gif.load()
            playback_ms += gif.info["duration"]
        assert abs(playback_ms/1000-DURATION) < .02
        assert gif.info.get("loop") == 0
    report = dict(simulator="MuJoCo "+mujoco.__version__, isaac_sim_runtime_tested=False,
        urdf=urdf.name, urdf_sha256=hashlib.sha256(urdf.read_bytes()).hexdigest(),
        config_sha256=hashlib.sha256((HERE/"simulation_config.json").read_bytes()).hexdigest(),
        gif=output.name, gif_sha256=hashlib.sha256(output.read_bytes()).hexdigest(), gif_bytes=output.stat().st_size,
        pixels=[WIDTH, HEIGHT], frames=len(records), frames_per_second=FPS, playback_duration_ms=playback_ms,
        simulated_seconds=float(data.time), playback_speed=1, mass_kg=float(model.body_mass.sum()),
        driven_joints=CONFIG["driven_joints"], passive_joints=CONFIG["passive_joints"],
        camera=dict(lookat=list(camera.lookat), distance=camera.distance, azimuth=camera.azimuth, elevation=camera.elevation),
        visual_aids="10cm floor grid; gold wheel-cover stripes follow simulated wheel body rotations; no collision/mass changes",
        verification=dict(status="passed", maximum_drive_torque_Nm=max_torque, maximum_body_tilt_deg=math.degrees(max_tilt),
                          minimum_base_origin_z_m=min_z, nonwheel_floor_contacts=nonwheel_contacts,
                          final_xyz_m=data.qpos[:3].tolist(), final_speed_m_s=float(np.linalg.norm(data.qvel[:3]))),
        scope="Recorded physics run using the existing uncalibrated model, not prescribed body animation or hardware footage.",
        samples=records)
    (HERE/"motion_gif_manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k not in ("samples", "camera")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
