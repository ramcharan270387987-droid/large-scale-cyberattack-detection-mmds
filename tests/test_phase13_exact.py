import unittest
from src.explainability.exact import linear,distance,importance,sigmoid,verify_linear

class ExactExplanationTests(unittest.TestCase):
    def test_linear_raw_and_centered(self):
        raw=linear([2.,-3.],1.,[4.,2.]);centered=linear([2.,-3.],1.,[4.,2.],[1.,1.])
        self.assertEqual(raw['contributions'],[8.,-6.]);self.assertEqual(raw['logit'],3.)
        self.assertEqual(centered['logit'],3.);self.assertEqual(centered['baseline'],0.)
        verify_linear(raw,3.,sigmoid(3.))
        with self.assertRaises(ValueError):verify_linear(raw,4.,.5)

    def test_saturation_and_invalid_schema(self):
        self.assertEqual(sigmoid(-1000.),0.);self.assertEqual(sigmoid(1000.),1.)
        for values in ([],[1.,2.],[float('nan')]):
            with self.assertRaises(ValueError):linear([1.],0.,values)

    def test_distance_and_importance(self):
        self.assertEqual(distance([1.,4.],[0.,2.]),{'contributions':[1.,4.],'squared_distance':5.})
        self.assertEqual(importance(['a','b'],[.25,.75]),{'a':.25,'b':.75})
        with self.assertRaises(ValueError):importance(['a'],[.5,.5])
        with self.assertRaises(ValueError):distance([float('inf')],[0.])
