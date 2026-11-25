import unittest
from src.explainability.components import reject,fusion

class ComponentTests(unittest.TestCase):
    def test_open_set_order_ties_and_registry(self):
        classes={'Bot':0,'DoS':1}
        self.assertFalse(reject([.75,.25],classes,512)['rejected'])
        self.assertTrue(reject([.5,.5],classes,512)['rejected'])
        self.assertEqual(reject([.5,.5],classes,1024)['predicted_family'],'Bot')
        with self.assertRaises(ValueError):reject([.5,.5],{'Bot':1,'DoS':2},512)

    def test_logical_and_weighted_components(self):
        gates={'supervised':.5,'novelty':.8}
        self.assertEqual(fusion(.3,.9,'or',gates),1.)
        self.assertEqual(fusion(.3,.9,'and',gates),0.)
        self.assertAlmostEqual(fusion(.3,.9,'blend',alpha=.25),.75)
        with self.assertRaises(ValueError):fusion(.3,.9,'blend')
