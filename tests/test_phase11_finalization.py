"""Final Phase 11 invariants for validity, clocks, agreement and recovery."""
import json,math
from pathlib import Path
import unittest
import csv


def table(path):
    with open(path,newline='') as file:
        return list(csv.DictReader(file))
from src.drift.advanced_detectors import create,update,divergences
from src.drift.drift_state import DetectorState
from src.drift.finalization import agreement,correlation,ranks,supported_alert,tolerance_matches,NATIVE_WARMUP
from src.drift.signal_registry import historical_availability


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

    def test_legacy_emissions_have_separate_availability(self):
        rows=[{'signal':'x','label_delay':float('nan'),'detector':'PageHinkley','evaluation':True,'alert':False} for _ in range(31)]
        derived=historical_availability(rows,{'PageHinkley':30})
        self.assertTrue(all(r['alert'] is None for r in derived[:29]))
        self.assertFalse(derived[29]['alert'])
        self.assertTrue(derived[29]['available'])
        self.assertFalse(rows[0]['alert'])

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

    def test_arrival_and_valid_clocks(self):
        state=DetectorState('ADWIN');state.batch('missing',[.1,None,float('nan'),.9])
        self.assertEqual((state.observations,state.valid_updates,state.suppressed_updates),(4,2,2))
        state.batch('missing',[.1])
        self.assertEqual((state.observations,state.valid_updates,state.suppressed_updates),(4,2,2))

    def test_legacy_snapshot_counters_remain_unknown(self):
        state=DetectorState('ADWIN');state.batch('old',[.2]*20)
        del state.valid_updates;del state.suppressed_updates
        opened=DetectorState.restore(state.snapshot())
        self.assertIsNone(opened.valid_updates);self.assertIsNone(opened.suppressed_updates)
        opened.batch('new',[.3,None]);self.assertEqual(opened.observations,22)

    def test_failed_batch_restores_state_before_retry(self):
        state=DetectorState('DDM')
        with self.assertRaises(ValueError):state.batch('retry',[0,1,.2])
        self.assertEqual(state.observations,0)
        self.assertNotIn('retry',state.batch_ids)
        fresh=DetectorState('DDM')
        self.assertEqual(state.batch('retry',[0,1,0]),fresh.batch('retry',[0,1,0]))
        self.assertEqual(state.observations,fresh.observations)
        self.assertEqual(state.valid_updates,fresh.valid_updates)
        self.assertEqual(state.batch('future',[0]*100+[1]*100),fresh.batch('future',[0]*100+[1]*100))

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


class FinalEvidenceTests(unittest.TestCase):
    def test_historical_agreement_excludes_native_warmup(self):
        import csv
        rows=list(table('reports/phase11_finalization/agreement.csv'))
        mean=next(r for r in rows if r['population']=='historical' and r['signal']=='RF score mean')
        raw=[r for r in table('reports/phase6_window_metrics.csv') if r['scope'] in ('intraday','capture_only')]
        raw.sort(key=lambda r:json.loads(r['batch_ids'])[0])
        count=0;eligible=0
        for i,row in enumerate(raw):
            if int(row['rows'])<100:continue
            count+=1
            eligible+=int(i>=10 and count>=30)
        self.assertEqual(int(mean['intervals']),eligible)
        self.assertFalse(any(r['population']=='historical' and 'KSWIN' in (r['first'],r['second']) for r in rows))

    def test_paired_outcomes_release_before_analysis(self):
        import csv
        for row in table('reports/phase11_finalization/association_pairs.csv'):
            self.assertEqual(int(row['outcome_batch'])-int(row['drift_batch']),int(row['lag_windows']))
            self.assertEqual(int(row['label_release_batch']),int(row['outcome_batch'])+int(row['label_delay_windows']))
            self.assertGreaterEqual(int(row['analysis_asof_batch']),int(row['label_release_batch']))
            self.assertGreaterEqual(int(row['outcome_rows']),100)

    def test_suppression_and_native_label_clock(self):
        import csv
        for row in table('reports/phase11_finalization/native_support.csv'):
            if row['eligible']=='False':self.assertEqual(row['alert'],'')
            if row['label_release_batch']:
                self.assertLessEqual(int(row['label_release_batch']),int(row['update_batch']))
                self.assertEqual(int(row['label_release_batch'])-int(row['source_batch']),int(row['label_delay_windows']))

    def test_registry_actual_parameters(self):
        from collections import deque
        registry=json.loads(Path('manifests/phase11_detectors.json').read_text())
        primary=json.loads(Path('reports/phase11_synthetic/frozen.json').read_text())
        self.assertEqual(len(registry['detectors']),6)
        for entry in registry['detectors']:
            name=entry['identifier']
            if name in NATIVE_WARMUP:
                actual={k:list(v) if isinstance(v,deque) else v for k,v in create(name,primary[name])._get_params().items()}
                self.assertEqual(entry['primary_synthetic_configuration'],actual)
        self.assertFalse(registry['phase12_started'])

    def test_final_manifest_gate_if_closed(self):
        manifest=json.loads(Path('manifests/phase11_experiments.json').read_text())
        if manifest['complete']:
            self.assertEqual(manifest['pending'],[])
            self.assertTrue(all(stage['status']=='COMPLETE AND VERIFIED' for stage in manifest['stages'].values()))
            self.assertFalse(manifest['phase12_started'])
        else:
            self.assertTrue(manifest['pending'])
