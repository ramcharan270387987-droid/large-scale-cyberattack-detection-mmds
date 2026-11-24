"""Final Phase 11 invariants for validity, clocks, agreement and recovery."""
import json,math
from pathlib import Path
import unittest
from src.drift.advanced_detectors import create,update,divergences
from src.drift.drift_state import DetectorState
from src.drift.finalization import agreement,correlation,ranks,supported_alert,tolerance_matches,NATIVE_WARMUP


class FinalDriftTests(unittest.TestCase):
    def test_invalid_update_is_unavailable(self):
        detector=create('ADWIN');width=detector.width
        for value in (None,float('nan'),float('inf'),-float('inf')):self.assertIsNone(update(detector,value))
        self.assertEqual(detector.width,width)
        self.assertIsNotNone(update(detector,.5))

    def test_binary_error_contract(self):
        with self.assertRaises(ValueError):update(create('DDM'),.25,True)
        self.assertFalse(update(create('DDM'),0,True))

    def test_support_is_not_negative(self):
        self.assertIsNone(supported_alert(.2,99,100,.1))
        self.assertIsNone(supported_alert(None,100,100,.1))
        self.assertTrue(supported_alert(.2,100,100,.1))
        self.assertFalse(supported_alert(.05,100,100,.1))

    def test_zero_agreement_edges(self):
        row=agreement([False]*3,[False]*3)
        self.assertEqual(row['intervals'],3);self.assertEqual(row['agreement'],1)
        self.assertIsNone(row['jaccard']);self.assertIsNone(row['kappa']);self.assertIsNone(row['positive_agreement'])
        self.assertEqual(row['negative_agreement'],1)

    def test_agreement_confusion(self):
        row=agreement([True,True,False,False],[True,False,True,False])
        self.assertEqual(row['shared_positive'],1);self.assertEqual(row['first_only'],1);self.assertEqual(row['shared_negative'],1)
        self.assertAlmostEqual(row['jaccard'],1/3);self.assertEqual(row['kappa'],0)
        with self.assertRaises(ValueError):agreement([],[])

    def test_tolerance_one_to_one(self):
        self.assertEqual(tolerance_matches({4,5},{5}),1)
        self.assertEqual(tolerance_matches({4},{6}),0)
        self.assertEqual(tolerance_matches({4},{5}),1)

    def test_descriptive_correlation(self):
        self.assertEqual(correlation([1,2,3],[3,2,1]),-1)
        self.assertIsNone(correlation([1,1,1],[1,2,3]))
        self.assertIsNone(correlation([1,2],[1,2]))
        self.assertEqual(ranks([4,2,2]),[2,.5,.5])

    def test_native_eligibility(self):
        self.assertEqual(NATIVE_WARMUP['KSWIN'],100)
        self.assertEqual(max(64,NATIVE_WARMUP['KSWIN']),100)
        self.assertEqual(max(512,NATIVE_WARMUP['ADWIN']),512)

    def test_reference_histogram_stability(self):
        self.assertEqual(divergences([10,0],[10,0]),(0,0))
        self.assertTrue(all(math.isfinite(v) for v in divergences([10,0],[0,10])))
        with self.assertRaises(ValueError):divergences([0,0],[1,1])

    def test_snapshot_idempotence(self):
        state=DetectorState('PageHinkley');state.batch('first',[.1]*40)
        restored=DetectorState.restore(state.snapshot())
        self.assertEqual(state.batch('next',[.9]*100),restored.batch('next',[.9]*100))
        self.assertEqual(restored.batch('next',[.9]*100),[])
        self.assertEqual(restored.observations,140)

    def test_reset_reconstruction(self):
        detector=create('PageHinkley')
        for value in [.1]*100+[.9]*200:update(detector,value)
        fresh=create('PageHinkley');self.assertEqual(fresh._x_mean.n,0)
        self.assertEqual(create('KSWIN').window_size,100)

    def test_frozen_primary_preserved(self):
        primary=json.loads(Path('reports/phase11_synthetic/frozen.json').read_text())
        self.assertEqual(primary['window_size'],64)
        self.assertIn(primary['KSWIN'],('conservative','sensitive'))
        self.assertTrue(Path('docs/phase11_research_protocol.md').exists())
