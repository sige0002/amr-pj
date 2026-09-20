"""Independent beam solutions, force balance, input constraints and saved output."""
import copy
import json
import math
from pathlib import Path
import unittest
import calculate_design as calc

HERE=Path(__file__).resolve().parent


class MechanicalCalculationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=json.loads((HERE/'design_parameters.json').read_text())
        cls.baseline=json.loads((HERE.parents[1]/'docs/amr-01/design_parameters.json').read_text())

    def test_midspan_matches_standard_simple_beam(self):
        p,l,d,e=100,80,8,205000
        result=calc.shaft_response(p,[0,l],l/2,d,e)
        inertia=math.pi*d**4/64
        self.assertEqual(result['inner_outer_signed_reaction_N'],[50,50])
        self.assertAlmostEqual(result['max_bending_moment_Nm'],p*l/4/1000)
        self.assertAlmostEqual(result['load_point_deflection_mm'],p*l**3/(48*e*inertia))

    def test_left_and_right_overhang_are_symmetric(self):
        left=calc.shaft_response(100,[0,27],-32,8,205000)
        right=calc.shaft_response(100,[0,27],59,8,205000)
        self.assertEqual(left['inner_outer_signed_reaction_N'],right['inner_outer_signed_reaction_N'][::-1])
        self.assertAlmostEqual(left['load_point_deflection_mm'],right['load_point_deflection_mm'])
        self.assertAlmostEqual(right['max_bending_moment_Nm'],3.2)
        self.assertLess(right['inner_outer_signed_reaction_N'][0],0)

    def test_load_at_support_has_no_beam_bending(self):
        result=calc.shaft_response(100,[115,192],192,8,205000)
        self.assertEqual(result['inner_outer_signed_reaction_N'],[0,100])
        self.assertEqual(result['load_point_deflection_mm'],0)
        self.assertEqual(result['max_bending_stress_MPa'],0)

    def test_three_wheel_forces_balance_both_moments(self):
        contacts={'left':(90,170),'right':(90,-170),'caster':(-140,12)}
        mass,xy=14,(65,20)
        f=calc.wheel_reactions(mass,xy,contacts)
        self.assertAlmostEqual(sum(f.values()),mass*calc.G)
        for index in (0,1):
            self.assertAlmostEqual(sum(f[k]*contacts[k][index] for k in f),mass*calc.G*xy[index])
        self.assertNotAlmostEqual(f['left'],f['right'])

    def test_forward_cg_unloads_caster(self):
        contacts={'left':(90,170),'right':(90,-170),'caster':(-150,0)}
        self.assertLess(calc.wheel_reactions(10,(100,0),contacts)['caster'],0)
        self.assertLess(calc.support_margin((100,0),[contacts[k] for k in ('caster','right','left')]),0)

    def test_inconsistent_geometry_and_nonfinite_inputs_rejected(self):
        for value in (float('nan'),float('inf')):
            bad=copy.deepcopy(self.config);bad['drive']['initial_v_m_s']=value
            with self.assertRaises(ValueError): calc.evaluate(bad,self.baseline)
        bad=copy.deepcopy(self.config);bad['geometry']['drive_track_mm']+=2
        with self.assertRaises(ValueError): calc.evaluate(bad,self.baseline)
        with self.assertRaises(ValueError): calc.shaft_response(100,[115,115],170,8,205000)

    def test_saved_result_and_no_implicit_operation_approval(self):
        actual=json.loads(json.dumps(calc.evaluate(self.config,self.baseline),allow_nan=False))
        saved=json.loads((HERE/'calculation_results.json').read_text())
        saved.pop('input_files')
        self.assertEqual(actual,saved)
        self.assertFalse(actual['operation_approved'])
        self.assertTrue(all(not c['operation_approved'] for c in actual['stability_cases'].values()))
        self.assertAlmostEqual(actual['drive']['wheel_torque_with_margin_Nm'],.7077934164015369)
        self.assertEqual(actual['drive']['gross_mass_kg'],14)

    def test_more_caster_samples_converge(self):
        parts=[(8.1,0,0,85),(2,40,10,200)]
        a=calc.static_case(parts,calc.contact_samples(self.config['geometry'],720))
        b=calc.static_case(parts,calc.contact_samples(self.config['geometry'],1440))
        self.assertLess(abs(a['worst_sampled_caster_support_margin_mm']-b['worst_sampled_caster_support_margin_mm']),.001)


if __name__=='__main__': unittest.main()
