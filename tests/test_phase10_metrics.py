import unittest
from src.patterns.metrics import association,contrast,emergence,jaccard


class PatternMetricsTests(unittest.TestCase):
    def test_association(self):
        r=association(20,40,25,100)
        self.assertEqual(r['confidence'],.5)
        self.assertEqual(r['lift'],2)
        self.assertAlmostEqual(r['leverage'],.1)
        self.assertEqual(r['conviction'],1.5)
        self.assertEqual(association(20,20,25,100)['conviction'],float('inf'))
        self.assertIsNone(association(20,20,100,100)['conviction'])

    def test_contrast_and_temporal(self):
        r=contrast(20,10,100,100)
        self.assertEqual(r['support_ratio'],2)
        self.assertEqual(r['attack_given_pattern'],2/3)
        self.assertEqual(emergence(0,100,1000,1000)['category'],'newly_observed')
        self.assertEqual(emergence(100,0,1000,1000)['category'],'disappearing')
        self.assertIsNone(emergence(0,0,1000,1000)['growth'])
        self.assertEqual(jaccard([1,2],[2,3]),1/3)
        self.assertIsNone(jaccard([],[]))
