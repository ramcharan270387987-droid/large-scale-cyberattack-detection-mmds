import itertools
import unittest
from src.explainability.exact import linear

class LinearShapTests(unittest.TestCase):
    def test_closed_form_matches_all_coalition_orders(self):
        beta=[2.,-3.,.5];x=[4.,2.,-1.];background=[[1.,0.,2.],[-1.,2.,0.]]
        reference=[sum(row[i] for row in background)/len(background) for i in range(3)]
        exact=linear(beta,1.,x,reference)
        shap=[0.,0.,0.]
        for order in itertools.permutations(range(3)):
            current=list(reference)
            before=linear(beta,1.,current)['logit']
            for index in order:
                current[index]=x[index]
                after=linear(beta,1.,current)['logit']
                shap[index]+=(after-before)/6
                before=after
        for actual,expected in zip(shap,exact['contributions']):self.assertAlmostEqual(actual,expected)
        self.assertAlmostEqual(exact['baseline']+sum(shap),linear(beta,1.,x)['logit'])
