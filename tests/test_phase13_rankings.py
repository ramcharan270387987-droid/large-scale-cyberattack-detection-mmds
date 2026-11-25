import unittest
from src.explainability.rankings import ranks,agreement

class RankingTests(unittest.TestCase):
    def test_average_ties_and_reverse_order(self):
        self.assertEqual(ranks({'a':1,'b':1,'c':2}),{'a':1.5,'b':1.5,'c':3.})
        self.assertAlmostEqual(agreement({'a':1,'b':2,'c':3},{'a':3,'b':2,'c':1},1)['spearman'],-1.)
        self.assertEqual(agreement({'a':1,'b':2,'c':3},{'a':3,'b':2,'c':1},1)['top_jaccard'],0.)
        self.assertIsNone(agreement({'a':1,'b':1},{'a':1,'b':2})['spearman'])
