#!/usr/bin/env python3
"""Build the A5 quotation candidates without changing previous quote files.

Run: python3 cad/amr06/build_mount_candidates.py
New comparisons only: ... --candidates D3 D4
Existing STEP/JSON snapshots are hash-checked and retained, never overwritten.
System Python starts a separate headless FreeCAD process.  Inside FreeCAD,
make_candidate() returns an assembly-coordinate shape for other CAD builders.
Exported quotation STEP files use their minimum bounding-box corner as origin.
These are nominal quotation candidates, not strength/manufacturing releases.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
A4 = HERE.parent / "amr05"
OUT = HERE / "candidates"
DATE = "2026-09-21"
REVISION = "A5-Q1"
CANDIDATES = {
    "D1": {"seat_radius_mm": 2.0, "stem": "M0601C_mount_D1_R2", "priority": "first_quotation_candidate", "root_mode": "all4"},
    "D2": {"seat_radius_mm": 2.5, "stem": "M0601C_mount_D2_R2p5", "priority": "comparison_only_not_recommended_for_adoption", "root_mode": "all4"},
    "D3": {"seat_radius_mm": 2.0, "stem": "M0601C_mount_D3_R2_LongRoots", "priority": "long_root_fillet_quotation_comparison_pending", "root_mode": "long2"},
    "D4": {"seat_radius_mm": 2.0, "stem": "M0601C_mount_D4_R2_NoRootFillet", "priority": "seat_only_quotation_comparison_pending", "root_mode": "none"},
    "D5": {"seat_radius_mm": 2.0, "stem": "M0601C_mount_D5_Compact_R2", "priority": "compact_thicker_flange_quotation_comparison_pending", "root_mode": "long2", "flange_width_mm": 75, "web_width_mm": 45, "frame_hole_pitch_mm": 60, "flange_thickness_mm": 6},
}

try:
    import FreeCAD as App
    import Part
except ImportError:
    if __name__ != "__main__":
        raise
    exe = shutil.which("freecadcmd")
    if not exe:
        raise SystemExit("freecadcmd is required")
    code = f"import sys;sys.path.insert(0,{str(HERE)!r});import build_mount_candidates as m;m.main({sys.argv[1:]!r})"
    raise SystemExit(subprocess.run([exe, "-c", code], env=dict(os.environ, QT_QPA_PLATFORM="offscreen")).returncode)

sys.path.insert(0, str(A4))
from custom_mount import make_mount, report as a4_report

V = App.Vector
EPS = 1e-6


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def xyz(point):
    return [point.x, point.y, point.z]


def box_record(shape):
    b = shape.BoundBox
    return {"minimum_mm": [b.XMin, b.YMin, b.ZMin],
            "maximum_mm": [b.XMax, b.YMax, b.ZMax],
            "size_mm": [b.XLength, b.YLength, b.ZLength]}


def close_sequence(a, b, tol=EPS):
    return len(a) == len(b) and all(abs(x-y) < tol for x, y in zip(a, b))


def shape_valid(shape):
    return shape.isValid() and len(shape.Solids) == 1


def support_faces(shape):
    """Find the actual retained flat fragments, not ideal full profile lines."""
    result = []
    for face in shape.Faces:
        surface = face.Surface
        if not isinstance(surface, Part.Plane):
            continue
        n, p = surface.Axis, surface.Position
        distance = abs(n.x*(p.x-90) + n.z*(p.z-50.35))
        if abs(n.y) > EPS or abs(distance-8.25) > EPS:
            continue
        b = face.BoundBox
        assert abs(b.YMin-138) < EPS and abs(b.YMax-147) < EPS
        result.append({"normal_world": xyz(n), "axis_distance_mm": distance,
                       "depth_mm": b.YLength, "surface_area_mm2": face.Area,
                       "support_length_mm": face.Area/b.YLength,
                       "bbox_world_mm": box_record(face),
                       "vertices_world_mm": [xyz(vertex.Point) for vertex in face.Vertexes]})
    return sorted(result, key=lambda r: r["bbox_world_mm"]["minimum_mm"])


def radial_support_faces(shape):
    result = []
    for face in shape.Faces:
        c = face.Surface
        if not isinstance(c, Part.Cylinder) or abs(c.Radius-9.70) > EPS:
            continue
        assert abs(abs(c.Axis.y)-1) < EPS
        assert abs(c.Center.x-90) < EPS and abs(c.Center.z-50.35) < EPS
        assert abs(face.BoundBox.YLength-9) < EPS
        result.append({"radius_mm": c.Radius, "depth_mm": 9,
                       "arc_length_mm": face.Area/9, "surface_area_mm2": face.Area,
                       "bbox_world_mm": box_record(face)})
    return sorted(result, key=lambda r: r["bbox_world_mm"]["minimum_mm"])


def hole_measurements(shape, frame_x=(52.5, 127.5), frame_bottom=64):
    motor, frame = [], []
    for face in shape.Faces:
        c = face.Surface
        if not isinstance(c, Part.Cylinder):
            continue
        if abs(c.Radius-1.4) < EPS and abs(abs(c.Axis.y)-1) < EPS:
            motor.append({"center_world_xz_mm": [c.Center.x, c.Center.z],
                          "diameter_mm": 2*c.Radius, "material_length_mm": face.BoundBox.YLength,
                          "material_y_limits_mm": [face.BoundBox.YMin, face.BoundBox.YMax]})
        if abs(c.Radius-3.3) < EPS and abs(abs(c.Axis.z)-1) < EPS:
            frame.append({"center_world_xy_mm": [c.Center.x, c.Center.y],
                          "diameter_mm": 2*c.Radius, "material_length_mm": face.BoundBox.ZLength,
                          "material_z_limits_mm": [face.BoundBox.ZMin, face.BoundBox.ZMax]})
    motor.sort(key=lambda r: r["center_world_xz_mm"])
    frame.sort(key=lambda r: r["center_world_xy_mm"])
    assert len(motor) == 3 and len(frame) == 2
    expected_motor = [[83.4182069312383, 46.55], [90, 57.95], [96.5817930687617, 46.55]]
    for record, expected in zip(motor, expected_motor):
        assert close_sequence(record["center_world_xz_mm"], expected)
        assert close_sequence(record["material_y_limits_mm"], [130, 138])
    for record, expected in zip(frame, [[x, 135] for x in frame_x]):
        assert close_sequence(record["center_world_xy_mm"], expected)
        assert close_sequence(record["material_z_limits_mm"], [frame_bottom, 69])
    return {"motor": motor, "frame": frame}


def enlarge_seat_corners(base, radius):
    """Keep each tangent point while enlarging six R1.65 relief arcs."""
    normals = [(0, -1), (-math.sqrt(3)/2, .5), (math.sqrt(3)/2, .5)]
    centers = []
    for face in base.Faces:
        c = face.Surface
        if isinstance(c, Part.Cylinder) and abs(c.Radius-1.65) < EPS:
            p = c.Center
            if not any(math.hypot(p.x-x, p.z-z) < EPS for x, z in centers):
                centers.append((p.x, p.z))
    assert len(centers) == 6
    cuts, moves = [], []
    for x, z in sorted(centers):
        normal = min(normals, key=lambda n: abs(8.25-(n[0]*(x-90)+n[1]*(z-50.35))-1.65))
        assert abs(8.25-(normal[0]*(x-90)+normal[1]*(z-50.35))-1.65) < EPS
        delta = radius-1.65
        nx, nz = x-delta*normal[0], z-delta*normal[1]
        cuts.append(Part.makeCylinder(radius, 9, V(nx, 138, nz), V(0, 1, 0)))
        moves.append({"old_center_world_xz_mm": [x, z], "new_center_world_xz_mm": [nx, nz],
                      "flat_outward_normal_xz": list(normal), "center_shift_mm": delta})
    result = base.cut(Part.makeCompound(cuts)).removeSplitter()
    assert shape_valid(result)
    remaining = [f for f in result.Faces if isinstance(f.Surface, Part.Cylinder)
                 and abs(f.Surface.Radius-1.65) < EPS]
    enlarged = [f for f in result.Faces if isinstance(f.Surface, Part.Cylinder)
                and abs(f.Surface.Radius-radius) < EPS and abs(abs(f.Surface.Axis.y)-1) < EPS]
    assert not remaining and len(enlarged) == 6
    return result, moves


def root_edges(shape, mode="all4", web_width=60, root_z=64):
    """Select the specified original concave edges by geometric coordinates."""
    if mode == "none":
        return []
    assert mode in ("all4", "long2")
    result = []
    for edge in shape.Edges:
        pts = [v.Point for v in edge.Vertexes]
        if len(pts) != 2 or not all(abs(p.z-root_z) < EPS for p in pts):
            continue
        along_x = any(all(abs(p.y-y) < EPS for p in pts) for y in (130, 147))
        along_y = any(all(abs(p.x-x) < EPS for p in pts) for x in (90-web_width/2, 90+web_width/2))
        if (along_x and abs(edge.Length-web_width) < EPS) or (mode == "all4" and along_y and abs(edge.Length-17) < EPS):
            result.append(edge)
    assert len(result) == (4 if mode == "all4" else 2)
    return result


def root_surface_analysis(shape, root_z=64):
    """Record actual analytic surfaces and trim curves at root_z-2..root_z."""
    records = []
    for face in shape.Faces:
        b = face.BoundBox
        if b.ZMin < root_z-2-EPS or b.ZMax > root_z+EPS or isinstance(face.Surface, Part.Plane):
            continue
        surface = face.Surface
        record = {"surface_type": type(surface).__name__, "area_mm2": face.Area,
                  "bbox_world_mm": box_record(face),
                  "trim_edge_curve_types": dict(Counter(type(e.Curve).__name__ for e in face.Edges))}
        if isinstance(surface, Part.Cylinder):
            record.update({"radius_mm": surface.Radius, "axis_world": xyz(surface.Axis)})
        records.append(record)
    return {"all_face_surface_types": dict(Counter(type(f.Surface).__name__ for f in shape.Faces)),
            "root_transition_surface_count": len(records), "root_transition_surfaces": records,
            "note": "Analytic B-rep types and trim curves only; these do not determine a vendor CAM strategy, tool count, setup count or quotation."}


def make_candidate(candidate_id, base=None):
    """Return (world-coordinate B-rep, numeric report); never writes files."""
    spec = CANDIDATES[candidate_id]
    base = make_mount() if base is None else base
    width = spec.get("flange_width_mm", 90)
    web_width = spec.get("web_width_mm", 60)
    pitch = spec.get("frame_hole_pitch_mm", 75)
    thickness = spec.get("flange_thickness_mm", 5)
    root_z = 69-thickness
    frame_x = (90-pitch/2, 90+pitch/2)
    body = base
    if width != 90:
        # Recover the exact motor-side voids from the A4 web only.  This excludes
        # the old outboard M6 holes, so narrowing does not leave half-holes at
        # the new flange ends.  Cut the two new M6 positions independently.
        original_web = Part.makeBox(60, 17, 34, V(60, 130, 35))
        functional_voids = original_web.cut(base)
        flange = Part.makeBox(width, 30, thickness, V(90-width/2, 120, root_z))
        web = Part.makeBox(web_width, 17, 34, V(90-web_width/2, 130, 35))
        body = flange.fuse(web).cut(functional_voids)
        for x in frame_x:
            body = body.cut(Part.makeCylinder(3.3, thickness+2, V(x, 135, root_z-1)))
        body = body.removeSplitter()
        assert shape_valid(body)
    pocketed, moves = enlarge_seat_corners(body, spec["seat_radius_mm"])
    edges = root_edges(pocketed, spec["root_mode"], web_width, root_z)
    edge_records = [{"length_mm": e.Length, "vertices_world_mm": [xyz(v.Point) for v in e.Vertexes]} for e in edges]
    result = pocketed.makeFillet(2.0, edges).removeSplitter() if edges else pocketed
    assert shape_valid(result)
    flats, base_flats = support_faces(result), support_faces(base)
    arcs, base_arcs = radial_support_faces(result), radial_support_faces(base)
    assert len(flats) == 4 and len(arcs) == 3 and len(base_arcs) == 3
    assert close_sequence(sorted(r["support_length_mm"] for r in flats), sorted(r["support_length_mm"] for r in base_flats))
    origin = [90-width/2, 120, 35]
    assert close_sequence(box_record(result)["minimum_mm"], origin)
    assert close_sequence(box_record(result)["size_mm"], [width, 30, 34])
    holes = hole_measurements(result, frame_x, root_z)
    base_holes = hole_measurements(base)
    back = Part.makeBox(web_width, 8, 34, V(90-web_width/2, 130, 35))
    lost_back = base.common(back).cut(result.common(back)).Volume
    assert lost_back < EPS
    added = result.cut(base).Volume
    removed = base.cut(result).Volume
    root_added = result.Volume-pocketed.Volume
    assert abs((added-removed)-(result.Volume-base.Volume)) < 1e-5
    expected_added = {"all4": 135.26258245575, "long2": 2*web_width*(4-math.pi), "none": 0}[spec["root_mode"]]
    assert abs(root_added-expected_added) < .01
    assert pocketed.cut(result).Volume < EPS
    info = a4_report(result)
    info.update({
        "candidate_id": candidate_id, "drawing_revision": REVISION, "date": DATE,
        "priority": spec["priority"], "status": "quotation_candidate_not_manufacturing_or_strength_release",
        "quantity": 2, "same_part_both_sides": True,
        "overall_LWH_mm": [width, 30, 34], "web_width_thickness_mm": [web_width, 17],
        "frame_hole_pitch_mm": pitch, "flange_thickness_mm": thickness,
        "frame_screw": f"2x M6x12 per mount, direct head seating on {thickness} mm flange; nominal head bearing Z{root_z}, tip Z{root_z+12} in world coordinates. Effective thread engagement and tolerances are unverified.",
        "seat_small_corner_radius_mm": spec["seat_radius_mm"], "seat_small_corner_count": 6,
        "web_flange_root_radius_mm": 2.0 if edges else 0.0, "web_flange_root_edge_count": len(edges),
        "web_flange_root_mode": spec["root_mode"], "web_flange_root_world_z_mm": root_z,
        "root_surface_analysis": root_surface_analysis(result, root_z),
        "seat_corner_method": "Shift each arc center inward by delta R to retain the original flat tangent point; then cut only Y138..147.",
        "corner_center_moves": moves, "root_edges_before_fillet": edge_records,
        "world_bbox_mm": box_record(result), "quote_origin_world_mm": origin,
        "quote_axis_local_xz_mm": [width/2, 15.35], "quote_mounting_contact_z_mm": 34,
        "geometry_checks": {"one_valid_solid": shape_valid(result), "solid_count": len(result.Solids),
                            "flat_fragment_lengths_preserved": True, "rear_wall_material_not_reduced": True,
                            "rear_wall_removed_volume_mm3": lost_back, "root_fillets_only_add_material": True,
                            "overall_envelope_preserved": width == 90, "all_five_holes_preserved": pitch == 75,
                            "overall_envelope_matches_candidate_target": True,
                            "motor_holes_preserved": True, "frame_holes_match_candidate_target": True},
        "rear_wall_check_scope_world_mm": box_record(back),
        "frame_clearance_reference_mm": {"hole_axis_to_flange_end": (width-pitch)/2,
                                          "hole_axis_to_web_end": (pitch-web_width)/2,
                                          "hole_edge_to_flange_end": (width-pitch)/2-3.3,
                                          "hole_edge_to_web_end": (pitch-web_width)/2-3.3,
                                          "note": "Nominal planar distances only; not a cutter/bolt-head/washer/assembly clearance certification."},
        "flat_support_faces": flats, "baseline_flat_support_faces": base_flats,
        "radial_support_faces": arcs, "baseline_radial_support_faces": base_arcs,
        "radial_support_total_length_mm": sum(r["arc_length_mm"] for r in arcs),
        "radial_support_retained_ratio": sum(r["arc_length_mm"] for r in arcs)/sum(r["arc_length_mm"] for r in base_arcs),
        "holes": holes, "baseline_holes": base_holes,
        "volume_comparison": {"baseline_volume_mm3": base.Volume, "candidate_volume_mm3": result.Volume,
                              "body_before_seat_relief_volume_mm3": body.Volume,
                              "body_change_net_volume_mm3": body.Volume-base.Volume,
                              "seat_relief_removed_mm3": body.Volume-pocketed.Volume,
                              "root_fillets_added_mm3": root_added,
                              "added_to_baseline_mm3": added, "removed_from_baseline_mm3": removed,
                              "net_change_mm3": result.Volume-base.Volume},
        "tolerance_scope": {"quoted_special_tolerance": "Only seat flat distance from shaft axis: 8.25 +/- 0.05 mm; same scope as A4 quotation.",
                            "all_other_dimensions": "ISO 2768-m provisional quotation condition; not manufacturing approval.",
                            "new_hole_position_or_profile_tolerances_added": False,
                            "unresolved": "Received motor lot, complete contour clearance, geometric/hole-position tolerances and functional contacts require approval before production."},
        "limitations": ["Lower flat consists of two short 0.308903 mm fragments; do not count it as an equal third support face.",
                        "Reduced radial support arc lengths are geometric data, not contact-pressure or load-capacity certification.",
                        "No full chassis interference, CAM, strength or safety-factor certification in this candidate generator.",
                        "Identical two-piece quantity is for price comparison; no manufacturing or purchasing authorization."]})
    return result, info


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", nargs="+", choices=list(CANDIDATES), default=list(CANDIDATES))
    args = parser.parse_args([] if argv is None else argv)
    OUT.mkdir(parents=True, exist_ok=True)
    source_paths = [A4/"custom_mount.py", A4/"reconstruct_motor_seat.py", A4/"motor-seat-profile-source.json",
                    A4/"M0601C_custom_mount_quote.step", A4/"custom_mount_dimensions.json"]
    source_hashes = {str(p.relative_to(HERE.parent)): sha256(p) for p in source_paths}
    base = make_mount()
    assert shape_valid(base)
    prior = json.loads((A4/"custom_mount_dimensions.json").read_text())
    assert abs(base.Volume-prior["volume_mm3_each"]) < 1e-5
    manifest_path = OUT/"candidate_manifest.json"
    previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"candidates": []}
    records = {r["candidate"]: r for r in previous["candidates"]}
    for candidate_id in args.candidates:
        spec = CANDIDATES[candidate_id]
        step = OUT/(spec["stem"]+".step")
        report_path = OUT/(spec["stem"]+".json")
        if step.exists() or report_path.exists():
            if not (step.exists() and report_path.exists() and candidate_id in records):
                raise ValueError(f"Incomplete existing snapshot: {candidate_id}; refusing overwrite")
            frozen = json.loads(report_path.read_text())
            assert sha256(step) == frozen["step_sha256"] == records[candidate_id]["step_sha256"]
            assert frozen["source_a4_sha256"] == source_hashes
            print(f"Retained existing {candidate_id} STEP/JSON snapshot; no overwrite")
            continue
        shape, info = make_candidate(candidate_id, base)
        local = shape.copy()
        local.translate(V(*[-value for value in info["quote_origin_world_mm"]]))
        local.exportStep(str(step))
        loaded = Part.Shape()
        loaded.read(str(step))
        assert shape_valid(loaded)
        assert close_sequence(box_record(loaded)["minimum_mm"], [0, 0, 0])
        assert close_sequence(box_record(loaded)["size_mm"], info["overall_LWH_mm"])
        assert abs(loaded.Volume-shape.Volume) < .001
        info.update({"source_a4_sha256": source_hashes, "generator_sha256": sha256(__file__),
                     "step_file": step.name, "step_sha256": sha256(step),
                     "exported_step_checks": {"one_valid_solid": True, "local_bbox_mm": box_record(loaded),
                                               "volume_mm3": loaded.Volume,
                                               "volume_roundtrip_difference_mm3": loaded.Volume-shape.Volume}})
        report_path.write_text(json.dumps(info, ensure_ascii=False, indent=2)+"\n")
        records[candidate_id] = {"candidate": candidate_id, "step": step.name, "json": spec["stem"]+".json",
                        "step_sha256": info["step_sha256"], "valid": True,
                        "volume_mm3": shape.Volume, "mass_g_each": info["mass_kg_each_estimate"]*1000,
                        "radial_support_retained_ratio": info["radial_support_retained_ratio"]}
    assert all(sha256(HERE.parent/path) == checksum for path, checksum in source_hashes.items())
    manifest = {"revision": REVISION, "status": "quotation_candidates_only_not_released",
                "source_a4_unchanged": True, "source_a4_sha256": source_hashes,
                "candidates": [records[c] for c in CANDIDATES if c in records]}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main(sys.argv[1:])
