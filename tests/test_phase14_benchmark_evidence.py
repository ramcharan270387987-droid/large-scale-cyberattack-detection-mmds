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
    def test_optimization_acceptance_requires_complete_matrix(self):
        import tempfile,json
        from src.scalability.acceptance import optimization
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder);(path/'optimization_runs.json').write_text('[]');(path/'receipt.json').write_text(json.dumps({'status':'validated','stage':'14E','measured_runs':0}))
            with self.assertRaises(AssertionError):optimization(path)
