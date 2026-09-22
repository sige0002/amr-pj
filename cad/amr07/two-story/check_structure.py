"""D6 member screening and explicit limits of reusing the D3 plate-only FEA."""
from pathlib import Path
import hashlib,json,math
HERE=Path(__file__).resolve().parent
D3=HERE.parent/'aluminum-direct-deck'
g=9.80665;E=69000.;SF=2.
force=(15+1.6)*g+80 #15kg cargo,1.6kg plate-borne allowance,4x20N belt legs
rail_L=210.;rail_I=26800.;rail_Z=rail_I/15
rail_F=force/2
# Each rail receives half the upper load, all placed at the center of the
# post-to-post span (more bending than the six-patch reactions used by D3).
M=rail_F*rail_L/4
stress=SF*M/rail_Z
deflection=SF*rail_F*rail_L**3/(48*E*rail_I)
post_area=.84/2700*1e6;post_I=28700.;post_L=100.
# Vertical comparison deliberately puts the complete upper force on ONE post.
post_stress=SF*force/post_area
euler=math.pi**2*E*post_I/(2*post_L)**2
#60N frame push is an assembly test target, not a qualified operating load.
# Four equal paths assumed for the bracket-strip screen; joint slipping,
# uneven sharing, casting radii and prying are outside this calculation.
push=60.;joint_moment=push/4*post_L
bracket_screen=6*joint_moment/(20*4.5**2)
fea=json.loads((D3/'fea/summary.json').read_text())
out=dict(revision='D6',date='2026-09-22',scope='member-level elastic screening, not whole-frame SF2 release',
    upper_vertical_service_force_N=force,static_factor=SF,
    upper_rails=dict(part='NFSL6-3030',support_span_mm=rail_L,I_mm4=rail_I,E_MPa=E,
        force_per_rail_N=rail_F,factored_stress_MPa=stress,factored_center_deflection_mm=deflection,
        assumption='simple support at posts; half total plate load concentrated at rail midpoint; torsion and joint compliance omitted',
        source='https://jp.misumi-ec.com/vona2/detail/110311092329/'),
    posts=dict(part='SF2-30・30',length_mm=post_L,catalog_mass_kg_m=.84,I_mm4=post_I,
        area_from_catalog_mass_mm2=post_area,one_post_factored_compression_MPa=post_stress,
        ideal_Euler_load_K2_N=euler,
        source='https://fa.sus.co.jp/service/detail?ItemNo=SFF-324'),
    joints=dict(new_brackets=8,arrangement='one bottom and one top bracket on opposite post faces; post ends bear directly on horizontal rails',
        physical_push_test_target_N=push,physical_push_test_completed=False,
        equal_share_bracket_strip_stress_MPa=bracket_screen,
        assumptions='four equal paths;20x4.5mm root strip under1500Nmm. No casting strength or joint slip acceptance inferred.',
        mixed_manufacturer_interface='HBLFSN6/HNTT6-6 vs SUS SF2; nominal CAD fit only; actual tabs/seating/bolt bottoming to verify',
        clamp_torque_or_preload_qualified=False,frame_racking_qualified=False),
    previous_plate_FEA=dict(files='aluminum-direct-deck/fea',
        quoted_step_sha256=fea['plate_step_sha256'],
        justification='same manufactured plate and six ideal clamped patches at x=-105,0,105;y=+-135. Only rigid translation+130mm. Prior model already omitted all other rail contacts.',
        maximum_reference_deflection_mm=fea['fine']['max_downward_deflection_mm'],
        factored_reference_stress_MPa=fea['fine']['factored_surface_stress_screen_MPa'],
        limitations='New frame joint flexibility is not in old plate model. Local mesh peak stress was not converged; material/preload/contact/impact qualification outstanding.'),
    required_mock_checks=['Panel and battery retention force45N, no permanent shift; no vehicle operation during test.',
        'Complete metal frame: apply60N horizontally in both axes and both directions; check slip, permanent set, and access after load.',
        'Received post lengths/coplanarity, slotnut engagement, bracket locating tabs and torque to manufacturer instructions.',
        'Weigh completed vehicle including wires, cases and fasteners; base<=10kg. Verify mass placement against updated requirements.'],
    static_factor_2_achieved=False,loaded_operation_released=False)
assert stress<10 and deflection<.1 and post_stress<2
(HERE/'structure_screening.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(rail_factored_stress_MPa=stress,rail_factored_deflection_mm=deflection,one_post_factored_compression_MPa=post_stress,whole_frame_qualified=False)))
