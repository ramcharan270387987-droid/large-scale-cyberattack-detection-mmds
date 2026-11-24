import unittest
from src.patterns.support import counts,score,select_threshold


class SupportTests(unittest.TestCase):
    def test_counts_and_group_mass(self):
        rows=[dict(source_day='day1',binary_label=1,attack_family='Bot',items=['a','b'],count=10,group_weight=1),dict(source_day='day1',binary_label=0,attack_family='Benign',items=['a'],count=20,group_weight=2)]
        matches,totals=counts(rows,['a','b'])
        self.assertEqual(sum(matches.values()),10)
        self.assertEqual(sum(totals.values()),30)
        self.assertEqual(sum(counts(rows,['a'],'group_weight')[0].values()),3)
        self.assertEqual(score(['a','b'],[['a'],['c']]),.5)

    def test_validation_budget_and_ties(self):
        rows=[dict(score=.5,binary_label=0,count=100),dict(score=1.,binary_label=1,count=10)]
        self.assertEqual(select_threshold(rows),1.)
        with self.assertRaises(ValueError):select_threshold([rows[1]])
