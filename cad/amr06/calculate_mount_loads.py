"""Reproducible A5 load comparisons using only Python's standard library.

This is not FEA, a material/fastener qualification, or operating approval.
Run normally to write load_calculations.json; --check-only writes no files.
"""
from pathlib import Path
import argparse
import json
import math

HERE = Path(__file__).resolve().parent


def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0]]


def add(*vectors):
    return [sum(v[i] for v in vectors) for i in range(3)]


def scale(vector, factor):
    return [factor*x for x in vector]


def wrench_residual(forces_at_points, expected_force, expected_moment):
    force = add(*(f for _, f in forces_at_points))
    moment = add(*(cross(p, f) for p, f in forces_at_points))
    return {
        "force_N": max(abs(force[i]-expected_force[i]) for i in range(3)),
        "moment_Nmm": max(abs(moment[i]-expected_moment[i]) for i in range(3)),
    }


def validate_inputs(c):
    def finite(value):
        if isinstance(value, dict):
            for x in value.values():
                finite(x)
        elif isinstance(value, list):
            for x in value:
                finite(x)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            if not math.isfinite(value):
                raise ValueError("Non-finite numeric input")
    finite(c)
    geo, mount = c["geometry"], c["mount"]
    positive = [c["gravity_m_s2"], c["mass"]["base_upper_mass_kg"],
                c["mass"]["payload_kg"], geo["drive_track_mm"],
                geo["wheel_diameter_mm"], mount["flange_thickness_mm"],
                mount["motor_PCD_mm"], mount["frame_bolt_pitch_x_mm"],
                c["stiffness"]["elastic_modulus_assumed_MPa"],
                *mount["frame_contact_arm_sensitivity_mm"],
                *mount["gross_section_width_sensitivity_mm"]]
    if min(positive) <= 0:
        raise ValueError("Masses, geometry and stiffness inputs must be positive")
    if c["strength"]["static_safety_factor_target"] < 1:
        raise ValueError("Safety factor target must be >= 1")
    n = geo["caster_orientation_samples"]
    if not isinstance(n, int) or n < 4:
        raise ValueError("At least four integer caster samples required")
    if min(c["strength"]["lateral_force_over_vertical_sensitivity"]) < 0:
        raise ValueError("This comparison uses positive-outboard lateral ratios")
    if not math.isclose(mount["rear_wall_mm"]+mount["seat_depth_mm"],
                        mount["web_thickness_mm"]):
        raise ValueError("Pocket plus rear wall must equal web thickness")
    if not math.isclose(geo["drive_axis_z_mm"], geo["wheel_diameter_mm"]/2):
        raise ValueError("Ground-contact model requires axis height equal to nominal radius")


def support_reactions(weight, cg_xy, contacts):
    """Closed-form three-point vertical equilibrium for one drive axle."""
    left, right, caster = contacts
    axle_x = left[0]
    if not math.isclose(right[0], axle_x):
        raise ValueError("Drive contacts must share x")
    denominator = axle_x-caster[0]
    if abs(denominator) < 1e-12:
        raise ValueError("Degenerate support triangle")
    rc = weight*(axle_x-cg_xy[0])/denominator
    drive_sum = weight-rc
    rl = (weight*cg_xy[1]-rc*caster[1]-right[1]*drive_sum)/(left[1]-right[1])
    return [rl, drive_sum-rl, rc]


def triangle_margin(point, contacts):
    # L,C,R is counterclockwise for this chassis.
    polygon = [contacts[0], contacts[2], contacts[1]]
    margins = []
    for i, a in enumerate(polygon):
        b = polygon[(i+1) % 3]
        dx, dy = b[0]-a[0], b[1]-a[1]
        margins.append((dx*(point[1]-a[1])-dy*(point[0]-a[0]))/math.hypot(dx, dy))
    return min(margins)


def contact_points(c, angle):
    geo = c["geometry"]
    x, half_track = geo["drive_axis_x_mm"], geo["drive_track_mm"]/2
    cx, cy = geo["caster_pivot_xy_mm"]
    trail = geo["caster_trail_mm"]
    return [(x, half_track), (x, -half_track),
            (cx-trail*math.cos(angle), cy-trail*math.sin(angle))]


def static_case(c, name, components, historical=False):
    mass = sum(p["mass_kg"] for p in components)
    cg = [sum(p["mass_kg"]*p["cg_xyz_mm"][i] for p in components)/mass for i in range(3)]
    weight = mass*c["gravity_m_s2"]
    samples = c["geometry"]["caster_orientation_samples"]
    ranges = {key: {"min_signed_N": math.inf, "max_signed_N": -math.inf}
              for key in ("left", "right", "caster")}
    residual = {"force_N": 0.0, "moment_Nmm": 0.0}
    margin = math.inf
    for i in range(samples):
        angle = i*math.tau/samples
        contacts = contact_points(c, angle)
        reactions = support_reactions(weight, cg[:2], contacts)
        for key, reaction in zip(ranges, reactions):
            entry = ranges[key]
            entry["min_signed_N"] = min(entry["min_signed_N"], reaction)
            if reaction > entry["max_signed_N"]:
                entry.update(max_signed_N=reaction, max_at_caster_angle_deg=math.degrees(angle))
        forces = [([x, y, 0], [0, 0, r]) for (x, y), r in zip(contacts, reactions)]
        error = wrench_residual(forces, [0, 0, weight], cross(cg, [0, 0, weight]))
        residual = {key: max(residual[key], error[key]) for key in residual}
        margin = min(margin, triangle_margin(cg, contacts))
    maximum = max(ranges[side]["max_signed_N"] for side in ("left", "right"))
    published = c["motor_current_catalog"]["allowable_radial_load_N"]
    return {
        "name": name, "historical_only": historical,
        "components": components, "gross_mass_kg": mass, "assumed_cg_xyz_mm": cg,
        "caster_samples": samples, "reaction_ranges_N": ranges,
        "all_sampled_reactions_nonnegative": min(v["min_signed_N"] for v in ranges.values()) >= -1e-9,
        "minimum_sampled_support_margin_mm": margin,
        "maximum_drive_vertical_reaction_N": maximum,
        "maximum_drive_vertical_equivalent_kg": maximum/c["gravity_m_s2"],
        "current_published_radial_value_N": published,
        "vertical_reaction_alone_exceeds_published_radial_value": maximum > published,
        "catalog_comparison_status": "conditional_numeric_comparison_only; lot_and_load_datum_unknown; no_division_by_SF",
        "equilibrium_max_abs_residual": residual,
        "operation_approved": False,
    }


def motor_bolt_group(force, moment, mount):
    """No pocket/friction load sharing; normal springs may be compressive."""
    radius = mount["motor_PCD_mm"]/2
    pts = [(radius*math.cos(math.radians(a)), radius*math.sin(math.radians(a)))
           for a in mount["motor_hole_angles_deg"]]
    # The model below requires the symmetric 120-degree group in requirements.
    if abs(sum(x for x, _ in pts))+abs(sum(z for _, z in pts)) > 1e-8:
        raise ValueError("Motor bolt group must be centered")
    if abs(sum(x*z for x, z in pts)) > 1e-8:
        raise ValueError("Motor bolt group principal axes not aligned")
    ix, iz = sum(x*x for x, _ in pts), sum(z*z for _, z in pts)
    polar = ix+iz
    fx, fy, p = force
    mx, my, mz = moment
    bolt_forces = []
    output = []
    for x, z in pts:
        f = [fx/len(pts)+my*z/polar,
             fy/len(pts)-mx*z/iz+mz*x/ix,
             p/len(pts)-my*x/polar]
        bolt_forces.append(([x, 0, z], f))
        output.append({"position_relative_mm": [x, 0, z], "force_on_mount_N": f,
                       "in_plane_shear_N": math.hypot(f[0], f[2])})
    return {
        "model": "equal_stiffness_signed_normal_springs_no_pocket_or_friction; not_actual_bolt_force",
        "bolts": output,
        "maximum_in_plane_shear_N": max(v["in_plane_shear_N"] for v in output),
        "maximum_tensile_direction_spring_force_N": max(0, *(v["force_on_mount_N"][1] for v in output)),
        "maximum_absolute_normal_spring_force_N": max(abs(v["force_on_mount_N"][1]) for v in output),
        "equilibrium_max_abs_residual": wrench_residual(bolt_forces, force, moment),
    }


def frame_bolt_group(force, moment, mount, arm):
    """One outboard compression resultant plus two bolts, with zero friction."""
    fx, fy, p = force
    mx, my, mz = moment
    half_pitch = mount["frame_bolt_pitch_x_mm"]/2
    sum_x2 = 2*half_pitch**2
    compression = mx/arm
    total_tension_component = compression-p
    reactions = [([0, arm, 0], [0, 0, -compression])]
    output = []
    for x in (-half_pitch, half_pitch):
        # Reactions ON the mount; a positive z is the bolt head pulling upward.
        f = [-fx/2, -fy/2-mz*x/sum_x2, total_tension_component/2+my*x/sum_x2]
        reactions.append(([x, 0, 0], f))
        output.append({"position_relative_mm": [x, 0, 0], "reaction_on_mount_N": f,
                       "in_plane_shear_N": math.hypot(f[0], f[1])})
    return {
        "contact_arm_mm_assumed": arm,
        "model": "assumed_contact_resultant_and_rigid_joint; preload_prying_local_contact_unknown",
        "contact_compression_N": compression,
        "bolts": output,
        "maximum_additional_tension_component_N": max(v["reaction_on_mount_N"][2] for v in output),
        "maximum_in_plane_shear_N": max(v["in_plane_shear_N"] for v in output),
        "contact_and_tension_signs_compatible_with_assumption": compression >= 0 and min(v["reaction_on_mount_N"][2] for v in output) >= 0,
        "equilibrium_max_abs_residual": wrench_residual(reactions, scale(force, -1), scale(moment, -1)),
    }


def module_load_case(c, service_p, service_torque, lateral_ratio, factor):
    geo, mount = c["geometry"], c["mount"]
    radius = geo["wheel_diameter_mm"]/2
    service_force = [service_torque*1000/radius, lateral_ratio*service_p, service_p]
    force = scale(service_force, factor)
    wheel_y = geo["drive_track_mm"]/2
    frame_arm = [0, wheel_y-geo["outer_rail_center_y_mm"], -geo["frame_bottom_top_z_mm"][0]]
    motor_arm = [0, wheel_y-geo["motor_fixed_face_y_mm"], -geo["drive_axis_z_mm"]]
    frame_moment, motor_moment = cross(frame_arm, force), cross(motor_arm, force)
    catalog = c["motor_current_catalog"]
    radial_proxy, axial_proxy = math.hypot(service_force[0], service_force[2]), abs(service_force[1])
    assumed_service_allowable = (c["strength"]["procurement_minimum_yield_requirement_MPa"]
                                / c["strength"]["static_safety_factor_target"])
    return {
        "service_torque_comparison_Nm": service_torque,
        "lateral_ratio_sensitivity_NOT_LIMIT": lateral_ratio,
        "linear_load_multiplier": factor,
        "service_force_xyz_N": service_force,
        "applied_force_xyz_N": force,
        "frame_joint_moment_xyz_Nmm": frame_moment,
        "motor_face_moment_xyz_Nmm": motor_moment,
        "gross_section_bending": [
            {"assumed_width_mm": b, "thickness_mm": mount["flange_thickness_mm"],
             "sigma_from_Mx_only_MPa": abs(frame_moment[0])*6/(b*mount["flange_thickness_mm"]**2),
             "service_Mx_only_stress_over_assumed_allowable":
                 abs(frame_moment[0])*6/(factor*b*mount["flange_thickness_mm"]**2*assumed_service_allowable),
             "scope": "gross_Mx_only_not_full_von_Mises_or_local_joint_qualification"}
            for b in mount["gross_section_width_sensitivity_mm"]],
        "frame_bolt_contact_models": [frame_bolt_group(force, frame_moment, mount, arm)
                                      for arm in mount["frame_contact_arm_sensitivity_mm"]],
        "motor_bolt_no_sharing_model": motor_bolt_group(force, motor_moment, mount),
        "service_catalog_force_comparison": {
            "uses_unfactored_service_vector_only": True,
            "radial_force_proxy_sqrt_Fx2_Fz2_N": radial_proxy,
            "axial_force_proxy_abs_Fy_N": axial_proxy,
            "radial_proxy_exceeds_published_value": radial_proxy > catalog["allowable_radial_load_N"],
            "axial_proxy_exceeds_published_value": axial_proxy > catalog["allowable_axial_load_N"],
            "status": "conditional_comparison_only; load_datum_combined_load_rule_and_lot_unknown; not_a_SF_check",
        },
    }


def drive_case(c, mass, slope, acceleration=None):
    d = c["drive"]
    g = c["gravity_m_s2"]
    a = d["acceleration_m_s2"] if acceleration is None else acceleration
    theta = math.radians(slope)
    force = mass*(a+g*math.sin(theta)+d["rolling_resistance_assumed"]*g*math.cos(theta))
    torque = force*c["geometry"]["wheel_diameter_mm"]/2000/2
    margin_torque = torque*d["sizing_margin_factor"]
    return {"mass_kg": mass, "slope_deg": slope, "acceleration_m_s2": a,
            "total_tractive_force_N": force, "torque_per_wheel_Nm": torque,
            "torque_with_sizing_margin_Nm": margin_torque,
            "catalog_rated_to_margin_requirement_ratio": d["rated_torque_Nm"]/margin_torque if margin_torque else None,
            "margin_requirement_exceeds_catalog_rated_torque": margin_torque > d["rated_torque_Nm"],
            "operation_approved": False}


def fit_and_beam(c, p):
    f, m, b, stiff = c["fit"], c["mount"], c["frame_beam_comparison"], c["stiffness"]
    flat_nom = f["pocket_flat_distance_nominal_mm"]-f["motor_flat_distance_nominal_mm"]
    flat_tol = f["pocket_flat_distance_tolerance_pm_mm"]+f["motor_flat_distance_tolerance_pm_mm"]
    arc_nom = f["pocket_main_arc_radius_nominal_mm"]-f["motor_boss_diameter_nominal_mm"]/2
    arc_min = (f["pocket_main_arc_radius_nominal_mm"]-f["pocket_main_arc_radius_tolerance_pm_mm"]
               -(f["motor_boss_diameter_nominal_mm"]+f["motor_boss_diameter_upper_deviation_mm"])/2)
    arc_max = (f["pocket_main_arc_radius_nominal_mm"]+f["pocket_main_arc_radius_tolerance_pm_mm"]
               -(f["motor_boss_diameter_nominal_mm"]+f["motor_boss_diameter_lower_deviation_mm"])/2)
    load_a = c["geometry"]["drive_axis_x_mm"]-b["left_end_x_mm"]
    load_b = b["span_mm"]-load_a
    if min(load_a, load_b) <= 0:
        raise ValueError("Comparison load must lie inside the hypothetical beam")
    delta = p*load_a**2*load_b**2/(3*stiff["elastic_modulus_assumed_MPa"]*b["second_moment_mm4"]*b["span_mm"])
    sigma = p*load_a*load_b*b["extreme_fiber_distance_mm"]/(b["span_mm"]*b["second_moment_mm4"])
    side_offset = m["motor_PCD_mm"]/2*math.sqrt(3)/2
    return {
        "one_sided_flat_gap_mm": {"min": flat_nom-flat_tol, "nominal": flat_nom, "max": flat_nom+flat_tol},
        "one_sided_main_arc_radial_gap_mm": {"min": arc_min, "nominal": arc_nom, "max": arc_max},
        "D1_D2_full_corner_profile_fit_verified": False,
        "lower_motor_hole_to_rear_slot_ligament_mm": side_offset-m["motor_clearance_hole_diameter_mm"]/2-m["cable_rear_throat_width_mm"]/2,
        "lower_motor_head_edge_to_rear_slot_mm": side_offset-m["motor_screw_head_diameter_mm"]/2-m["cable_rear_throat_width_mm"]/2,
        "motor_screw_nominal_engagement_mm": m["motor_screw_nominal_length_mm"]-m["rear_wall_mm"],
        "motor_screw_nominal_bottoming_margin_mm": m["motor_thread_depth_max_mm"]-(m["motor_screw_nominal_length_mm"]-m["rear_wall_mm"]),
        "head_seating_annulus_mm2": {
            "motor_M2p5": math.pi/4*(m["motor_screw_head_diameter_mm"]**2-m["motor_clearance_hole_diameter_mm"]**2),
            "frame_M6": math.pi/4*(m["frame_screw_head_diameter_mm"]**2-m["frame_clearance_hole_diameter_mm"]**2)},
        "axis_stiffness_needed_if_candidate_accepted_N_per_mm": p/stiff["axis_displacement_candidate_mm"],
        "stiffness_candidate_accepted": stiff["candidate_accepted"],
        "hypothetical_single_rail_beam": {
            "service_load_N": p, "load_distances_from_ends_mm": [load_a, load_b],
            "sigma_MPa": sigma, "deflection_at_load_mm": delta,
            "status": "reference_beam_only_not_actual_mount_displacement_or_pass_fail"},
        "pocket_two_point_comparison": [
            {"span_mm": span,
             "inner_reaction_N": p*(1-(c["geometry"]["drive_track_mm"]/2-c["geometry"]["motor_fixed_face_y_mm"])/span),
             "outer_reaction_N": p*(c["geometry"]["drive_track_mm"]/2-c["geometry"]["motor_fixed_face_y_mm"])/span,
             "status": "no_end_face_or_bolt_sharing_not_actual_contact_force"}
            for span in m["pocket_two_point_span_sensitivity_mm"]],
    }


def module_cases(c, service_p):
    return [module_load_case(c, service_p, torque, lateral, factor)
            for factor in (1, c["strength"]["static_safety_factor_target"])
            for torque in c["strength"]["service_torque_comparison_Nm"]
            for lateral in c["strength"]["lateral_force_over_vertical_sensitivity"]]


def width_geometry(c, mount, relief_half_width, root_radius):
    """Nominal distances from input dimensions, without a STEP/tolerance check."""
    axis_x = c["geometry"]["drive_axis_x_mm"]
    flange_half, web_half = mount["flange_width_mm"]/2, mount["web_width_mm"]/2
    pitch_half = mount["frame_bolt_pitch_x_mm"]/2
    head_r, hole_r = mount["frame_screw_head_diameter_mm"]/2, mount["frame_clearance_hole_diameter_mm"]/2
    motor_r = mount["motor_PCD_mm"]/2
    motor_xmax = max(abs(motor_r*math.cos(math.radians(a))) for a in mount["motor_hole_angles_deg"])
    motor_head_top = (c["geometry"]["drive_axis_z_mm"]
                      + max(motor_r*math.sin(math.radians(a)) for a in mount["motor_hole_angles_deg"])
                      + mount["motor_screw_head_diameter_mm"]/2)
    flange_top = c["geometry"]["frame_bottom_top_z_mm"][0]
    flange_bottom = flange_top-mount["flange_thickness_mm"]
    tip = flange_bottom+mount["frame_screw_nominal_length_mm"]
    nut_low, nut_high = mount["frame_slotnut_z_limits_mm"]
    return {
        "flange_x_limits_mm": [axis_x-flange_half, axis_x+flange_half],
        "web_x_limits_mm": [axis_x-web_half, axis_x+web_half],
        "frame_bolt_x_mm": [axis_x-pitch_half, axis_x+pitch_half],
        "frame_hole_center_to_flange_outer_edge_mm": flange_half-pitch_half,
        "frame_hole_center_to_unfilleted_web_edge_mm": pitch_half-web_half,
        "frame_hole_edge_to_flange_outer_edge_mm": flange_half-pitch_half-hole_r,
        "frame_hole_edge_to_unfilleted_web_edge_mm": pitch_half-web_half-hole_r,
        "frame_head_edge_to_flange_outer_edge_mm": flange_half-pitch_half-head_r,
        "frame_head_edge_to_unfilleted_web_edge_mm": pitch_half-web_half-head_r,
        "motor_hole_edge_to_web_outer_edge_mm": web_half-motor_xmax-mount["motor_clearance_hole_diameter_mm"]/2,
        "motor_head_edge_to_web_outer_edge_mm": web_half-motor_xmax-mount["motor_screw_head_diameter_mm"]/2,
        "main_arc_only_to_web_outer_edge_mm": web_half-c["fit"]["pocket_main_arc_radius_nominal_mm"],
        "R2_relief_cut_half_width_mm": relief_half_width,
        "R2_relief_to_web_outer_edge_nominal_mm": web_half-relief_half_width,
        "flange_bottom_top_z_mm": [flange_bottom, flange_top],
        "frame_screw_tip_z_mm": tip,
        "frame_screw_overlap_with_nominal_nut_mm": max(0, min(tip, nut_high)-max(flange_bottom, nut_low)),
        "frame_screw_tip_beyond_nominal_nut_top_mm": tip-nut_high,
        "frame_screw_tip_to_slot_cavity_top_mm": mount["frame_slot_cavity_top_z_mm"]-tip,
        "frame_head_bottom_z_mm": flange_bottom-mount["frame_screw_head_height_mm"],
        "upper_motor_head_top_z_mm": motor_head_top,
        "upper_motor_head_to_flange_underside_z_gap_mm": flange_bottom-motor_head_top,
        "upper_motor_head_to_long_root_fillet_bbox_z_gap_mm": flange_bottom-root_radius-motor_head_top,
        "frame_head_seating_annulus_mm2": math.pi*(head_r**2-hole_r**2),
        "scope": "nominal_2D_dimension_chain_only; fillet_shape_tool_access_chamfers_effective_threads_and_tolerances_unverified",
    }


def compare_candidate(c, name, spec, service_p):
    baseline = c["mount"]
    override_keys = ("flange_width_mm", "web_width_mm", "flange_thickness_mm",
                     "frame_bolt_pitch_x_mm", "gross_section_width_sensitivity_mm",
                     "frame_screw_nominal_length_mm", "frame_slotnut_z_limits_mm",
                     "frame_slot_cavity_top_z_mm")
    variant_mount = {**baseline, **{key: spec[key] for key in override_keys if key in spec}}
    variant_config = {**c, "mount": variant_mount}
    validate_inputs(variant_config)
    # The same R2 seat is retained in D1 and both D5 width comparisons.
    relief_half_width = max(c["fit"]["pocket_main_arc_radius_nominal_mm"],
                            spec["reference_R2_relief_max_center_abs_x_from_axis_mm"]+spec["seat_corner_radius_mm"])
    relative_sections = []
    for label, old_width, new_width in (
            ("full_flange_width", baseline["flange_width_mm"], variant_mount["flange_width_mm"]),
            ("web_width_as_unverified_effective_width", baseline["web_width_mm"], variant_mount["web_width_mm"])):
        old_t, new_t = baseline["flange_thickness_mm"], variant_mount["flange_thickness_mm"]
        relative_sections.append({
            "comparison": label, "reference_width_thickness_mm": [old_width, old_t],
            "candidate_width_thickness_mm": [new_width, new_t],
            "gross_stress_ratio_same_moment": old_width*old_t**2/(new_width*new_t**2),
            "beam_deflection_ratio_same_E_span_and_load": old_width*old_t**3/(new_width*new_t**3),
            "scope": "rectangular_section_sensitivity_not_whole_mount_deflection_or_verified_effective_width",
        })
    return {
        "candidate": name, "status": spec["status"], "reference_candidate": spec["reference_candidate"],
        "input_specification": spec,
        "reference_D1_dimensions": width_geometry(c, baseline, relief_half_width, baseline["D1"]["root_radius_mm"]),
        "candidate_dimensions": width_geometry(c, variant_mount, relief_half_width, spec["root_radius_mm"]),
        "relative_section_sensitivities": relative_sections,
        "bolt_group_pitch_sensitivity": {
            "reference_pitch_mm": baseline["frame_bolt_pitch_x_mm"],
            "candidate_pitch_mm": variant_mount["frame_bolt_pitch_x_mm"],
            "moment_induced_bolt_force_component_ratio": baseline["frame_bolt_pitch_x_mm"]/variant_mount["frame_bolt_pitch_x_mm"],
            "rotation_compliance_ratio_if_each_bolt_axial_stiffness_unchanged": (baseline["frame_bolt_pitch_x_mm"]/variant_mount["frame_bolt_pitch_x_mm"])**2,
            "scope": "two_identical_axial_springs_only; altered_grip_length_plate_contact_and_fillet_compliance_not_included",
        },
        "module_load_cases": module_cases(variant_config, service_p),
        "fit_stiffness_and_local_dimensions": {
            **fit_and_beam(variant_config, service_p),
            "candidate_full_corner_profile_fit_verified": False},
        "geometry_matches_final_candidate_STEP": None,
        "static_SF2_verified": False,
        "FEA_completed": False,
    }


def calculate(c):
    validate_inputs(c)
    mass, cg_inputs = c["mass"], c["cg_cases"]
    gross = mass["base_upper_mass_kg"]+mass["payload_kg"]
    p = gross*c["gravity_m_s2"]
    sf = c["strength"]["static_safety_factor_target"]
    history = cg_inputs["historical_14kg_components"]
    cases = [static_case(c, "historical_14kg_folded_transport", history, True)]
    for name, xyz in cg_inputs["payload_cg_assumed_cases_xyz_mm"].items():
        parts = [{"name": "base", "mass_kg": mass["base_upper_mass_kg"], "cg_xyz_mm": cg_inputs["base_cg_assumed_xyz_mm"]},
                 {"name": "payload", "mass_kg": mass["payload_kg"], "cg_xyz_mm": xyz}]
        cases.append(static_case(c, name, parts))
    load_cases = module_cases(c, p)
    comparisons = {name: compare_candidate(c, name, spec, p)
                   for name, spec in c.get("comparison_candidates", {}).items()}
    drive = {
        "historical_14kg_5deg": drive_case(c, sum(v["mass_kg"] for v in history), c["drive"]["historical_slope_deg"]),
        "primary_gross_historical_5deg": drive_case(c, gross, c["drive"]["historical_slope_deg"]),
        "primary_gross_flat_candidate": drive_case(c, gross, c["drive"]["flat_candidate_slope_deg"]),
        "primary_gross_flat_constant_speed": drive_case(c, gross, 0, 0),
        "alternative_15kg_gross_interpretation": drive_case(c, mass["alternative_gross_mass_interpretation_kg"], c["drive"]["historical_slope_deg"]),
    }
    # Numerical intersection of the sizing curve with the catalog rated torque.
    rated = c["drive"]["rated_torque_Nm"]
    lo, hi = 0.0, 89.0
    if drive_case(c, gross, lo)["torque_with_sizing_margin_Nm"] > rated:
        boundary = None
    else:
        for _ in range(80):
            mid = (lo+hi)/2
            if drive_case(c, gross, mid)["torque_with_sizing_margin_Nm"] > rated:
                hi = mid
            else:
                lo = mid
        boundary = (lo+hi)/2
    per_kg = drive_case(c, 1, c["drive"]["historical_slope_deg"])["torque_with_sizing_margin_Nm"]
    speed = {}
    radius = c["geometry"]["wheel_diameter_mm"]/2000
    track = c["geometry"]["drive_track_mm"]/1000
    for prefix in ("initial", "later"):
        v, omega = c["drive"][prefix+"_v_m_s"], c["drive"][prefix+"_omega_rad_s"]
        speed[prefix] = {"inner_rpm": (v-omega*track/2)*60/(math.tau*radius),
                         "outer_rpm": (v+omega*track/2)*60/(math.tau*radius)}
    result = {
        "schema_version": c["schema_version"], "design": c["design"],
        "status": "analytical_comparisons_not_FEA_not_SF2_certification",
        "input_file": "requirements.json", "gravity_m_s2": c["gravity_m_s2"],
        "mass_basis": {**mass, "primary_gross_mass_kg": gross,
                       "gross_if_future_arm_additional_kg": gross+mass["additional_future_arm_kg"]},
        "one_mount_upper_comparison": {
            "service_vertical_force_N": p, "static_strength_factor_target": sf,
            "linear_factored_vertical_force_N": p*sf,
            "note": "not_a_normal_stable_operating_pose_or_a_test_instruction; do_not_apply_full_weight_to_all_wheels_simultaneously"},
        "static_CG_cases": cases,
        "module_load_cases": load_cases,
        "variant_scope": {"D1": c["mount"]["D1"], "D2": c["mount"]["D2"],
                          "gross_results_shared": True, "gross_results_shared_scope": ["D1", "D2"],
                          "separate_candidate_results": list(comparisons),
                          "local_corner_stress_or_fit_comparison_completed": False},
        "candidate_comparisons": comparisons,
        "assumed_material_comparison": {
            "procurement_minimum_yield_requirement_MPa": c["strength"]["procurement_minimum_yield_requirement_MPa"],
            "service_stress_allowable_if_requirement_guaranteed_MPa": c["strength"]["procurement_minimum_yield_requirement_MPa"]/sf,
            "material_certificate_confirmed": c["strength"]["material_certificate_confirmed"],
            "certified_minimum_yield_MPa": c["strength"]["certified_minimum_yield_MPa"],
            "source_url": c["strength"]["material_property_source_url"],
            "scope_note": c["strength"]["material_property_scope_note"]},
        "fit_stiffness_and_local_dimensions": fit_and_beam(c, p),
        "drive_comparisons": drive,
        "drive_boundaries_NOT_OPERATION_LIMITS": {
            "primary_gross_slope_at_catalog_rated_torque_deg": boundary,
            "gross_mass_at_historical_slope_and_catalog_rated_torque_kg": rated/per_kg,
            "speed_cases": speed, "continuous_operation_verified": False},
        "motor_current_catalog": c["motor_current_catalog"],
        "caster_catalog": c["caster_catalog"],
        "qualification": {"static_SF2_verified": False, "FEA_completed": False,
                          "operation_approved": False, "unresolved": c["unresolved"]},
    }
    result["verification"] = verify_equilibrium(c, result)
    return result


def verify_equilibrium(c, result):
    """Physical equilibrium and limiting cases, not implementation snapshots."""
    checks = []
    max_force = max_moment = 0.0
    residuals = [v["equilibrium_max_abs_residual"] for v in result["static_CG_cases"]]
    load_groups = [result["module_load_cases"]]+[v["module_load_cases"] for v in result["candidate_comparisons"].values()]
    for group in load_groups:
        for case in group:
            residuals.append(case["motor_bolt_no_sharing_model"]["equilibrium_max_abs_residual"])
            residuals.extend(v["equilibrium_max_abs_residual"] for v in case["frame_bolt_contact_models"])
    for residual in residuals:
        max_force = max(max_force, residual["force_N"])
        max_moment = max(max_moment, residual["moment_Nmm"])
    if max_force > 1e-8 or max_moment > 1e-7:
        raise AssertionError("Force/moment equilibrium failed")
    checks.append("all_CG_and_bolt_contact_force_moment_balances")
    for angle in (0, .731, 2.4):
        contacts = contact_points(c, angle)
        for loaded_contact in range(3):
            reactions = support_reactions(100, contacts[loaded_contact], contacts)
            expected = [100 if i == loaded_contact else 0 for i in range(3)]
            if max(abs(a-b) for a, b in zip(reactions, expected)) > 1e-9:
                raise AssertionError("Support vertex limit failed")
        normal = support_reactions(100, (12, 23), contacts)
        mirrored = support_reactions(100, (12, -23), contact_points(c, -angle))
        if max(abs(a-b) for a, b in zip(normal, [mirrored[1], mirrored[0], mirrored[2]])) > 1e-9:
            raise AssertionError("Left-right mirror equilibrium failed")
    checks += ["CG_at_each_support_gives_all_weight_to_that_contact", "mirrored_CG_and_caster_swap_left_right_reactions"]
    sf = c["strength"]["static_safety_factor_target"]
    for group in load_groups:
        for service in group:
            if service["linear_load_multiplier"] != 1:
                continue
            scaled = next(v for v in group
                          if v["linear_load_multiplier"] == sf
                          and v["service_torque_comparison_Nm"] == service["service_torque_comparison_Nm"]
                          and v["lateral_ratio_sensitivity_NOT_LIMIT"] == service["lateral_ratio_sensitivity_NOT_LIMIT"])
            for key in ("applied_force_xyz_N", "frame_joint_moment_xyz_Nmm", "motor_face_moment_xyz_Nmm"):
                if max(abs(a-sf*b) for a, b in zip(scaled[key], service[key])) > 1e-8:
                    raise AssertionError("Consistent load multiplication failed")
    checks.append("strength_multiplier_scales_all_external_forces_and_moments")
    return {"status": "passed", "checks": checks,
            "sampled_CG_states": sum(v["caster_samples"] for v in result["static_CG_cases"]),
            "module_load_groups": len(load_groups), "module_load_cases_checked": sum(map(len, load_groups)),
            "maximum_force_residual_N": max_force, "maximum_moment_residual_Nmm": max_moment}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requirements", type=Path, default=HERE/"requirements.json")
    parser.add_argument("--output", type=Path, default=HERE/"load_calculations.json")
    parser.add_argument("--check-only", action="store_true", help="calculate and verify without writing files")
    args = parser.parse_args()
    result = calculate(json.loads(args.requirements.read_text()))
    if not args.check_only:
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+"\n")
    print(json.dumps({key: result[key] for key in ("one_mount_upper_comparison", "verification")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
