import unittest
from src.explainability.permutation import permute,evaluate

class PermutationTests(unittest.TestCase):
    def test_grouped_and_capture_reproducibility(self):
        rows=[dict(source_day='a' if i<5 else 'b',x=i,y=10*i,binary_label=i%2) for i in range(10)]
        a=permute(rows,['x','y'],23013,True)
        self.assertEqual(a,permute(rows,['x','y'],23013,True))
        self.assertTrue(all(r['y']==10*r['x'] for r in a))
        self.assertTrue(all((r['x']<5)==(r['source_day']=='a') for r in a))
        self.assertEqual([r['binary_label'] for r in a],[r['binary_label'] for r in rows])
        self.assertEqual(rows[0]['x'],0)

    def test_histogram_metrics_and_undefined(self):
        r=evaluate({0:[3,1],2047:[1,3]})
        self.assertEqual((r['tp'],r['fp'],r['tn'],r['fn']),(3,1,3,1))
        self.assertEqual(r['pr_auc'],.75*.75+.25*.5)
        self.assertIsNone(evaluate({0:[5,0]})['recall'])
        self.assertIsNone(evaluate({0:[5,0]})['roc_auc'])
