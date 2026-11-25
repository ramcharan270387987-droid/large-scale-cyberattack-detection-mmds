import unittest
from pathlib import Path
from src.scalability.acceptance import volume,same
class BenchmarkEvidenceTests(unittest.TestCase):
    def test_recovered_volume_repetitions_and_checksums(self):
        r=volume(Path(__file__).resolve().parents[1]/'reports/phase14_14D')
        self.assertEqual(r['measured_runs'],48)
    def test_numerical_equivalence_preserves_exact_integer_counts(self):
        self.assertFalse(same({'rows':12},{'rows':13}))
        self.assertTrue(same([{'sum':1.}],[{'sum':1.+1e-10}]))
