#!/usr/bin/env python3
"""Cross-check adopted geometry, quote evidence, solver archives and BOM.

Passing means consistent review artifacts, not manufacturing/operation release.
"""
from pathlib import Path
import hashlib
import json
import re
import zipfile

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    cfg=read(BASE/'deck_parameters.json');q=read(HERE/'quote-evidence/D2-observed.json')
    geom=read(HERE/'geometry.json')[0];drawing=read(HERE/'drawing_manifest.json')[0]
    association=read(HERE/'quote-evidence/C45-file-association.json')
    assert q['quantity']==1 and q['material_requested']=='6061-T6' and not q['threads_requested']
    assert association['fileName2D']==q['name']+'.pdf' and association['fileName3D']==q['name']+'.step'
    assert association['thread_choice_UI']=='いいえ'
    for ext in ('step','pdf'):
        assert sha(HERE/(q['name']+'.'+ext))==q[ext+'_sha256']==drawing[ext+'_sha256']
    assert sha(HERE/(q['name']+'.zip'))==q['upload_package_sha256']
    with zipfile.ZipFile(HERE/(q['name']+'.zip')) as z:
        for ext in ('step','pdf'):
            name=q['name']+'.'+ext
            assert z.read(name)==(HERE/name).read_bytes()
    assert geom['existing_frame_holes']==cfg['geometry']['frame_holes_xy_mm']
    assert geom['grid_hole_count']==36 and geom['grid_modeled_bore_mm']==4.5
    for rec in q['records']:
        text=(HERE/'quote-evidence'/('C45-'+rec['speed']+'.txt')).read_text()
        assert float(re.search(r'合計価格\s*\$([0-9.]+)',text)[1])==rec['parts_lot_USD']
        assert float(re.search(r'送料見積\s*\$([0-9.]+)\s*UPS',text)[1])==rec['shipping_USD']
        assert abs(rec['parts_lot_USD']+rec['shipping_USD']-rec['total_USD'])<1e-9
    assembly=read(BASE/'assembly_validation.json');service=read(BASE/'service_envelope_validation.json')
    assert assembly['physical_parts']==298 and assembly['physical_pair_count']==44253
    assert not assembly['collisions'] and not assembly['reference_collisions'] and not assembly['harness_collisions']
    assert all(not t['hits'] for t in assembly['tool_and_service_access'])
    assert assembly['grid_access']['checked_locations']==36
    assert all(not t['installed_hardware_hits'] and not t['D12_nut_tool_on_removed_deck_hits'] for t in assembly['grid_access']['checks'])
    assert service['status']=='passed' and all(not t for t in service['tests'].values())
    assert service['quoted_STEP_sha256']==q['step_sha256'] and service['quoted_plate_symmetric_difference_mm3']<.001
    assert service['caster_fixing_clearance']['continuous_gap_lower_bound_mm']>3
    assert assembly['mass']['estimated_base_kg']<10 and assembly['STEP_roundtrip']['valid']
    fea=read(HERE/'fea/summary.json')
    for name in ('coarse','fine'):
        r=read(HERE/'fea'/name/'result.json')
        with zipfile.ZipFile(HERE/'fea'/name/'solver-input-output.zip') as z:
            assert hashlib.sha256(z.read('plate.inp')).hexdigest()==r['input_sha256']
            assert hashlib.sha256(z.read('plate.dat')).hexdigest()==r['dat_sha256']
            snapshot=json.loads(z.read('input_parameters.json'))
            assert hashlib.sha256(z.read('input_parameters.json')).hexdigest()==r['deck_parameters_sha256']
        for key in ('plate_LWT_mm','frame_holes_xy_mm','grid_coordinates_from_center_mm','grid_hole_diameter_mm',
                    'support_mode','support_block_LWT_mm','strap_slots','stop_holes_xy_mm'):
            assert snapshot['geometry'][key]==cfg['geometry'][key]
        for key in ('payload_kg','static_safety_factor_target','minimum_thickness_for_screening_mm','youngs_modulus_MPa',
                    'conditional_proof_stress_MPa','plate_borne_dead_mass_allowance_kg','strap_pretension_N_each','strap_vertical_legs'):
            assert snapshot['structural_screening'][key]==cfg['structural_screening'][key]
        assert r['vertical_force_balance_relative_error']<1e-5
        assert r['factored_surface_stress_screen_MPa']<r['conditional_proof_stress_MPa']
    assert fea['relative_mesh_change']['deflection']<.01 and fea['relative_mesh_change']['stress_screen']<.05
    bom=read(BASE/'procurement_bom.json');assert bom['physical_CAD_objects_reconciled']==298
    assert bom['partial_subtotals']=={'JPY':50468.0,'USD':120.9}
    for name,digest in bom['source_hashes'].items():assert sha(BASE/name)==digest,name
    prints=read(BASE/'printed-accessories/manifest.json');assert len(prints)==4
    for row in prints:
        assert row['watertight'] and max(row['bed_dimensions_mm'])<256
        assert (BASE/'printed-accessories'/row['file']).stat().st_size>100
    fx=read(HERE/'jpy_conversion.json')
    assert fx['quote_source_sha256']==sha(HERE/'quote-evidence/D2-observed.json')
    assert sha(HERE/fx['rate']['saved_XML'])==fx['rate']['downloaded_XML_sha256']
    report={'status':'PASS_consistent_review_artifacts','date':'2026-09-22',
            'CAD_parts':298,'grid_locations':36,'physical_collisions':0,'nominal_service_sweeps_passed':True,
            'quote_STEP_and_PDF_same_uploaded_revision':True,'quote_matches_assembly_plate':True,
            'FEA_input_archives_and_current_structural_parameters_match':True,
            'BOM_subtotals':bom['partial_subtotals'],'manufacturing_release':False,'operating_release':False,
            'artifact_hashes':{str(p.relative_to(BASE)):sha(p) for p in [BASE/'AMR01_M0601C_A6.FCStd',BASE/'AMR01_M0601C_A6.step',
                BASE/'assembly_validation.json',BASE/'service_envelope_validation.json',BASE/'BOM.xlsx',BASE/'procurement_bom.json',
                HERE/'fea/summary.json',HERE/'quote-evidence/D2-observed.json']}}
    (HERE/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
