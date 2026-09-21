#!/usr/bin/env python3
"""A6 payload/CG envelope, incline torque and mount comparison.

Standard library only. Slope azimuth extrema are analytic; caster orientation
is sampled at 0.5 degrees. This is rigid-body statics, not a tire/contact FEA.
"""
from pathlib import Path
from itertools import product
import argparse
import hashlib
import importlib.util
import json
import math

HERE = Path(__file__).resolve().parent


def reactions(mass, cg, contacts, gn, tx, ty):
    """Normal reactions with effective gravity tangent = gravity - acceleration."""
    x, y, h = cg
    (xa, s), _, (xc, yc) = contacts
    weight = mass * gn
    mx = weight * x + mass * h * tx
    my = weight * y + mass * h * ty
    rc = (weight * xa - mx) / (xa - xc)
    rl = (weight - rc + (my - rc * yc) / s) / 2
    return [rl, weight - rc - rl, rc]


def envelope(c, case):
    g = c['drive']['gravity_m_s2']
    geom, bounds = c['geometry'], c['load_placement']
    theta = math.radians(case['slope_deg'])
    gn, gt = g * math.cos(theta), g * math.sin(theta)
    names = ('left', 'right', 'caster')
    extrema = {n: {'min_N': math.inf, 'max_N': -math.inf} for n in names}
    residual = {'force_N': 0., 'first_moment_Nmm': 0.}
    count = 0
    for mb, sx, sy, axsign, aysign, hz in product(bounds['reviewed_base_mass_interval_kg'], (-1, 1), (-1, 1), (-1, 1), (-1, 1), (0, 1)):
        mp = case['payload_kg']
        mass = mb + mp
        # Positive masses make coincident base/cargo endpoints the CG extrema.
        cg = [sx * (mb * bounds['base_cg_x_interval_mm'][1] + mp * bounds['payload_cg_x_interval_mm'][1]) / mass,
              sy * (mb * bounds['base_cg_y_interval_mm'][1] + mp * bounds['payload_cg_y_interval_mm'][1]) / mass,
              hz * (mb * bounds['base_cg_max_z_mm'] + mp * bounds['payload_cg_max_z_mm']) / mass]
        ax = axsign * case['acceleration_m_s2']
        ay = aysign * case['lateral_acceleration_m_s2']
        for i in range(geom['caster_samples']):
            phi = math.tau * i / geom['caster_samples']
            xc = geom['caster_pivot_xy_mm'][0] - geom['caster_trail_mm'] * math.cos(phi)
            yc = geom['caster_pivot_xy_mm'][1] - geom['caster_trail_mm'] * math.sin(phi)
            contacts = [(geom['drive_axis_x_mm'], geom['drive_track_mm']/2),
                        (geom['drive_axis_x_mm'], -geom['drive_track_mm']/2), (xc, yc)]
            base = reactions(mass, cg, contacts, gn, -ax, -ay)
            rx = reactions(mass, cg, contacts, gn, 1-ax, -ay)
            ry = reactions(mass, cg, contacts, gn, -ax, 1-ay)
            for j, name in enumerate(names):
                bx, by = rx[j]-base[j], ry[j]-base[j]
                radius = gt * math.hypot(bx, by)
                for kind, sign in [('min', -1), ('max', 1)]:
                    value = base[j] + sign * radius
                    previous = extrema[name][kind+'_N']
                    if (value < previous if sign < 0 else value > previous):
                        heading = math.atan2(by, bx) + (math.pi if sign < 0 else 0)
                        tx, ty = gt * math.cos(heading)-ax, gt * math.sin(heading)-ay
                        r = reactions(mass, cg, contacts, gn, tx, ty)
                        residual['force_N'] = max(residual['force_N'], abs(sum(r)-mass*gn))
                        residual['first_moment_Nmm'] = max(residual['first_moment_Nmm'],
                            abs(sum(p[0]*v for p,v in zip(contacts,r))-mass*(gn*cg[0]+cg[2]*tx)),
                            abs(sum(p[1]*v for p,v in zip(contacts,r))-mass*(gn*cg[1]+cg[2]*ty)),
                            abs(r[j]-value))
                        extrema[name].update({kind+'_N': value, kind+'_case': {
                            'base_mass_kg': mb, 'gross_mass_kg': mass, 'cg_xyz_mm': cg,
                            'acceleration_xy_m_s2': [ax, ay], 'slope_azimuth_deg': math.degrees(heading)%360,
                            'caster_angle_deg': math.degrees(phi), 'all_reactions_N': r}})
            count += 1
    gross = c['mass']['base_max_kg'] + case['payload_kg']
    maximum = max(extrema[n]['max_N'] for n in ('left', 'right'))
    # Use the entire longitudinal force on one wheel as a catalog sensitivity,
    # distinct from the equal torque split used for motor sizing.
    longitudinal_total = gross * (gt + case['acceleration_m_s2'] + c['drive']['rolling_resistance_assumption']*gn)
    lateral_total = gross * (gt + case['lateral_acceleration_m_s2'])
    result = dict(case, evaluated_pose_vertices=count, normal_reaction_extrema=extrema,
                  minimum_reaction_N=min(e['min_N'] for e in extrema.values()),
                  maximum_drive_normal_N=maximum,
                  conservative_radial_comparison_N=math.hypot(maximum, longitudinal_total),
                  conservative_axial_comparison_N=lateral_total,
                  equilibrium_max_abs_residual=residual,
                  caster_sampling_note='0.5 degree samples; slope azimuth extrema exact for this rigid-body model',
                  radial_note='Independent worst normal and total longitudinal load placed on one drive wheel; not a combined-load qualification',
                  operation_approved=False)
    assert result['minimum_reaction_N'] > 0
    assert residual['force_N'] < 1e-9 and residual['first_moment_Nmm'] < 1e-7
    return result


def torque(c, payload, angle):
    d = c['drive']; g = d['gravity_m_s2']; theta = math.radians(angle)
    mass = c['mass']['base_max_kg'] + payload
    specific = d['acceleration_and_service_deceleration_max_m_s2'] + g*math.sin(theta) + d['rolling_resistance_assumption']*g*math.cos(theta)
    required = mass * specific * c['geometry']['wheel_diameter_mm']/4000
    sized = required * d['continuous_torque_sizing_margin']
    return {'payload_kg':payload, 'gross_mass_kg':mass, 'slope_deg':angle,
            'service_torque_Nm_each':required, 'with_margin_Nm_each':sized,
            'catalog_rated_torque_Nm_each':d['rated_torque_Nm_each'],
            'numeric_margin_check':sized <= d['rated_torque_Nm_each'],
            'operation_approved':False}


def mount_comparison(c):
    path = HERE.parent/'amr06'/'calculate_mount_loads.py'
    spec = importlib.util.spec_from_file_location('previous_mount_math', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    old = json.loads((path.parent/'requirements.json').read_text())
    old['mount']['motor_clearance_hole_diameter_mm'] = 3.2
    old['mount']['flange_thickness_mm'] = 5
    old['mount']['frame_bolt_pitch_x_mm'] = 75
    p = c['strength']['mount_comparison_vertical_N']
    fy = c['strength']['mount_comparison_lateral_N']
    return {'purpose':'isolated fixture comparison, not a wheel/motor permissible service load',
            'cases':[module.module_load_case(old, p, c['strength']['mount_comparison_torque_Nm'], fy/p, factor) for factor in (1, 2)],
            'safety_factor_achieved':False,
            'omitted':'local contact, hole/slot concentrations, female thread strength, preload, prying, fatigue and impacts'}


def calculate():
    raw = (HERE/'requirements.json').read_bytes()
    c = json.loads(raw)
    results = [envelope(c, case) for case in c['cases']]
    reference_results = [envelope(c, case) for case in c['reference_cases']]
    # Independent exact central equilibrium: equal drives and known caster load.
    test = reactions(25, [0,0,0], [(90,174.5),(90,-174.5),(-166,0)], 9.80665, 0, 0)
    assert abs(test[2]-25*9.80665*90/256) < 1e-10 and abs(test[0]-test[1]) < 1e-10
    sizing = [torque(c,c['mass']['normal_payload_kg'],0)]
    reference_sizing = [torque(c,8,5),torque(c,10,5),torque(c,15,5)]
    assert sizing[0]['numeric_margin_check'] and reference_sizing[0]['numeric_margin_check']
    assert not reference_sizing[1]['numeric_margin_check'] and not reference_sizing[2]['numeric_margin_check']
    cat = c['catalog_comparison_only']
    for result in results + reference_results:
        result['below_individual_catalog_comparison_values'] = (
            result['conservative_radial_comparison_N'] < cat['motor_radial_N'] and
            result['conservative_axial_comparison_N'] < cat['motor_axial_N'] and
            result['normal_reaction_extrema']['caster']['max_N'] < cat['caster_allowable_N'])
        assert result['below_individual_catalog_comparison_values']
    return {'requirements_sha256':hashlib.sha256(raw).hexdigest(), 'load_cases':results,
            'torque_cases':sizing, 'reference_load_cases':reference_results,
            'reference_torque_cases':reference_sizing,
            'reference_scope':'Slope comparisons are retained for history, outside the current flat-floor prototype operation and required qualification.',
            'mount':mount_comparison(c),
            'limits':'Rigid chassis, three floor contacts, no impact or wheel unloading; CG limits and tire datum must be verified. Positive reactions do not establish grip or thermal capability.',
            'operation_approved':False, 'strength_safety_factor_achieved':False}


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--check-only',action='store_true'); args = p.parse_args()
    result = calculate()
    if not args.check_only:
        (HERE/'load_calculations.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':'PASS', 'normal_reaction_maxima_N':{r['id']:r['maximum_drive_normal_N'] for r in result['load_cases']},
                      'torque_with_margin_Nm':[r['with_margin_Nm_each'] for r in result['torque_cases']],
                      'not_operation_or_strength_certification':True},ensure_ascii=False))
