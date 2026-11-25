import unittest,json
from pathlib import Path
from src.scalability.benchmark_runner import equivalent
class ScalabilityContractTests(unittest.TestCase):
    def test_correctness_rejects_count_changes(self):
        self.assertTrue(equivalent([{'rows':100,'value':1.}], [{'rows':100,'value':1.+1e-10}]))
        self.assertFalse(equivalent([{'rows':100}], [{'rows':101}]))
        self.assertFalse(equivalent({'a':1},{'b':1}))
    def test_frozen_nested_matrix_and_repetitions(self):
        c=json.loads((Path(__file__).resolve().parents[1]/'configs/phase14_scalability.yaml').read_text())
        self.assertEqual(c['workers'],[1,2,4]);self.assertEqual(c['repetitions'],3);self.assertEqual(c['volumes'][-1],16232943)
        self.assertEqual(c['fractions'],sorted(c['fractions']));self.assertEqual(c['fractions'][-1],1.)
        self.assertEqual(len(c['core_workloads']),3);self.assertFalse(c['aqe'])
    def test_speedup_requires_matched_positive_times(self):
        from src.scalability.results import speedup
        self.assertEqual(speedup(10.,4.,2),{'speedup':2.5,'efficiency':1.25})
        with self.assertRaises(ValueError):speedup(0.,4.,2)
        with self.assertRaises(ValueError):speedup(10.,0.,2)
