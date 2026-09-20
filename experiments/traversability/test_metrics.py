import unittest
from run import classification, fixtures, safe


class TraversabilityMetricsTest(unittest.TestCase):
    def test_confusion_denominators_and_unknown(self):
        rows = [dict(label=0,p=.9),dict(label=0,p=.1),dict(label=1,p=.9),
                dict(label=1,p=.1),dict(label=1,p=None)]
        m=classification(rows,.5)
        self.assertEqual((m['tp'],m['tn'],m['fp'],m['fn'],m['unknown']),(1,1,1,1,1))
        self.assertEqual(m['unsafe_false_accept_rate'],.5)
        self.assertEqual(m['safe_false_reject_rate'],.5)
        self.assertEqual(m['known_fraction'],.8)
        self.assertEqual(m['f1'],.5)

    def test_missing_class_is_not_zero_error(self):
        self.assertIsNone(classification([dict(label=1,p=.9)],.5)['unsafe_false_accept_rate'])
        with self.assertRaises(ValueError):
            classification([dict(label=0,p=float('nan'))],.5)

    def test_direction_rotation_and_independent_geometry(self):
        limits=dict(uphill_deg=15,downhill_deg=25,cross_slope_deg=12,step_m=.2,roughness_m=.15)
        cases=fixtures()
        self.assertEqual(len(cases),144)
        for t in cases:
            if t['scenario']=='directional_ramp':
                s=t['routes'][0][1]
                reverse=t['id'].endswith('_reverse')
                self.assertEqual(safe(s,limits),reverse)
                self.assertAlmostEqual(s['probabilities'][s['heading']//45],.85 if reverse else .04)
            if t['scenario']=='false_safe_input':
                s=t['routes'][0][1]
                self.assertFalse(safe(s,limits))
                self.assertGreater(s['probabilities'][s['heading']//45],.9)


if __name__=='__main__':
    unittest.main()
