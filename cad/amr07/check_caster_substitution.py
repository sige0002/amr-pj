"""Check TYG-50 catalog load against existing load cases and trail tolerance."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from calculate_design import envelope

HERE = Path(__file__).resolve().parent


def main():
    raw = (HERE / 'requirements.json').read_bytes()
    config = json.loads(raw)
    part = json.loads((HERE / 'caster_procurement.json').read_text())
    nominal = config['geometry']['caster_trail_mm']
    tolerance = config['geometry']['caster_trail_tolerance_plus_minus_mm']
    allowance = part['catalog_allowable_load_daN'] * 10
    rows = []
    for trail in (nominal - tolerance, nominal, nominal + tolerance):
        c = deepcopy(config)
        c['geometry']['caster_trail_mm'] = trail
        for case in c['cases']:
            result = envelope(c, case)
            reaction = result['normal_reaction_extrema']['caster']
            rows.append({'case': case['id'], 'trail_mm': trail,
                         'maximum_reaction_N': reaction['max_N'],
                         'minimum_reaction_N': reaction['min_N'],
                         'twice_maximum_reaction_N': 2 * reaction['max_N'],
                         'catalog_allowable_N': allowance,
                         'catalog_to_reaction_ratio': allowance / reaction['max_N']})
    assert all(r['twice_maximum_reaction_N'] < allowance for r in rows)
    report = {'part': part['part'], 'requirements_sha256': hashlib.sha256(raw).hexdigest(),
              'method': 'Existing rigid three-contact equilibrium and CG/mass/acceleration limits, caster yaw sampled every0.5deg. Trail nominal and tolerance endpoints checked.',
              'cases': rows,
              'height_tolerance_scope': '65±1.5mm mounting height requires received-part contact-height check/adjustment. Chassis tilt and tire compression are not modeled here.',
              'load_rating_is_not_yield_strength': True,
              'structural_safety_factor_certified': False,
              'impact_and_fatigue_qualified': False,
              'operation_released': False}
    (HERE / 'caster_load_check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'caster_maximum_N': max(r['maximum_reaction_N'] for r in rows),
                      'twice_maximum_N': max(r['twice_maximum_reaction_N'] for r in rows),
                      'catalog_allowable_N': allowance}, ensure_ascii=False))


if __name__ == '__main__':
    main()
