"""Independent URDF/mesh/inertia/kinematics validation (no Isaac Sim needed)."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import math
import xml.etree.ElementTree as ET

import numpy as np
import trimesh
from yourdfpy import URDF

from drive import CONFIG, ramp, wheel_speeds

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((HERE / "export_manifest.json").read_text())
    root = HERE.parents[1]
    cad = root / manifest["source_cad"]
    if cad.exists():
        assert sha(cad) == manifest["source_cad_sha256"], "CAD changed: regenerate URDF"
        assert sha(cad.parent / "payload_budget.json") == manifest["source_mass_budget_sha256"]
    checks = {}
    for info in manifest["meshes"]:
        path = HERE / info["file"]
        assert sha(path) == info["sha256"], path
        mesh = trimesh.load_mesh(path, process=False)
        assert np.isfinite(mesh.vertices).all() and len(mesh.faces) == info["triangles"]
        assert np.allclose(mesh.bounds, info["bounds_m"], atol=1e-7), path
        assert mesh.extents.max() < 1, "mm/m conversion error"

    for filename, variant in manifest["variants"].items():
        path = HERE / filename
        assert sha(path) == variant["sha256"]
        xml = ET.parse(path).getroot()
        robot = URDF.load(str(path), load_meshes=True, build_scene_graph=True,
                          load_collision_meshes=True, build_collision_scene_graph=True)
        assert robot.validate() and robot.base_link == "base_link"
        assert set(robot.actuated_joint_names) == set(CONFIG["driven_joints"] + CONFIG["passive_joints"])
        link_names = [link.name for link in robot.robot.links]
        assert len(link_names) == len(set(link_names)) == (6 if variant["payload_kg"] else 5)
        assert len(robot.robot.joints) == len(link_names)-1
        total = 0.0
        eigenvalues = {}
        for link in robot.robot.links:
            assert link.inertial is not None and link.inertial.mass > 0
            mass = link.inertial.mass
            inertia = link.inertial.inertia
            assert np.isfinite(inertia).all() and np.allclose(inertia, inertia.T)
            eig = np.linalg.eigvalsh(inertia)
            assert eig.min() > 0 and eig.max() < (eig.sum()-eig.max())+1e-10, (link.name, eig)
            eigenvalues[link.name] = eig.tolist()
            total += mass
            pos = robot.get_transform(link.name)[:3, 3]
            expected = (np.array(manifest["link_origins_cad_mm"][link.name])-CONFIG["base_origin_in_cad_mm"])/1000
            assert np.allclose(pos, expected, atol=1e-10), (link.name, pos, expected)
        assert math.isclose(total, variant["mass_kg"], abs_tol=1e-8)
        for j in robot.robot.joints:
            if j.name in CONFIG["driven_joints"]:
                assert j.type == "continuous" and np.allclose(j.axis, [0, 1, 0])
                assert math.isclose(j.limit.effort, .96)
            elif j.name in CONFIG["passive_joints"]:
                assert j.type == "continuous" and j.limit.effort == 0 and float(j.dynamics.damping) == 0
            else:
                assert j.name == "payload_fixed_joint" and j.type == "fixed"
        # Analytic collision surfaces of all three wheels share CAD floor Z=0.
        ground = {}
        for n in ["left_wheel_link", "right_wheel_link", "caster_wheel_link"]:
            col = xml.find(f"link[@name='{n}']/collision")
            radius = float(col.find("geometry/cylinder").get("radius"))
            z = robot.get_transform(n)[2, 3] + CONFIG["base_origin_in_cad_mm"][2]/1000-radius
            assert abs(z) < 1e-10
            ground[n] = float(z)
        # 90deg caster yaw moves its trailing axle around the swivel pivot.
        robot.update_cfg({"caster_swivel_joint": math.pi/2})
        caster = robot.get_transform("caster_wheel_link")[:3, 3]
        assert np.allclose(caster, [-.240, -.016, -.02535], atol=1e-10), caster
        robot.update_cfg({"caster_swivel_joint": 0.0})
        bounds = robot.scene.bounds
        assert np.allclose(bounds[:, :2], [[-.320, -.2033], [.140, .2033]], atol=2e-6)
        assert math.isclose(bounds[0, 2], -.05035, abs_tol=2e-6)
        assert bounds[1, 2] < (.35 if variant["payload_kg"] else .21)
        names = [e.get("name") for e in xml.findall(".//collision")]
        assert len(names) == len(set(names))
        checks[filename] = dict(status="passed", links=len(link_names), moving_joints=4, mass_kg=total,
                                inertia_eigenvalues_kg_m2=eigenvalues, floor_contacts_z_m=ground,
                                visual_bounds_base_frame_m=bounds.tolist(),
                                caster_90deg_axle_position_m=caster.tolist())

    forward = wheel_speeds(.1, 0)
    left_turn = wheel_speeds(0, .3)
    assert forward[0] == forward[1] > 0
    assert left_turn[1] == -left_turn[0] > 0
    # Positive wheel angular velocity about +Y gives +X rolling motion.
    assert np.allclose(-np.cross([0, 1, 0], [0, 0, -CONFIG["wheel_radius_m"]]), [CONFIG["wheel_radius_m"], 0, 0])
    assert max(abs(x) for x in ramp([0, 0], [100, -100], .01)) * CONFIG["wheel_radius_m"] <= .002+1e-12
    out = dict(status="passed", validator_versions={p:importlib.metadata.version(p) for p in ["numpy", "trimesh", "yourdfpy"]},
               mesh_files=len(manifest["meshes"]), variants=checks, drive_0p1m_s_rad_s=forward,
               spin_left_0p3rad_s_wheel_rad_s=left_turn, isaac_sim_runtime_tested=False,
               scope="URDF parser, link tree, mesh integrity/units/bounds, positive physical inertias, mass ledger, forward kinematics and contact heights. Not an Isaac Sim run.")
    (HERE / "urdf_validation.json").write_text(json.dumps(out, indent=2)+"\n")
    print(json.dumps(dict(status=out["status"], meshes=out["mesh_files"], variants={n:v["mass_kg"] for n,v in checks.items()})))


if __name__ == "__main__":
    main()
