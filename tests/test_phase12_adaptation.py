"""Information boundaries and genuine persistence/fault-path regression tests."""
import json
import tempfile
import unittest
from pathlib import Path
from src.adaptation.lifecycle import Registry, eligible, released, training_window
from src.adaptation.evaluation import evaluate, operating, guarded, merge


class Phase12Tests(unittest.TestCase):
    def test_label_release_and_pending(self):
        self.assertEqual(released(list(range(7)),3,6),[0,1,2,3])
        self.assertEqual(released([0],1,0),[])
        with self.assertRaises(ValueError): released([0],-1,0)
    def test_window_future_exclusion(self):
        self.assertEqual(training_window([0,1],[3,4],'sliding',2),[3,4])
        self.assertEqual(training_window([0,1],[3,4],'expanding',2),[0,1,3,4])
    def test_trigger_support_budget_cooldown(self):
        self.assertEqual(eligible(True,199,200,3,0,2,0,3),(False,'insufficient-new-labels'))
        self.assertEqual(eligible(True,200,200,3,2,2,0,3),(False,'cooldown'))
        self.assertEqual(eligible(True,200,200,3,0,2,3,3),(False,'budget'))
        self.assertEqual(eligible(True,200,200,3,0,2,0,3),(True,'eligible'))
    def test_atomic_registry_and_actual_rollback(self):
        with tempfile.TemporaryDirectory() as root:
            r=Registry(root); r.register('a',{'probe':[.2,.8]}); r.register('b',{'probe':[.3,.7]}); r.activate('a')
            with self.assertRaises(RuntimeError): r.activate('b',True)
            self.assertEqual(Registry(root).active,'a')
            r.activate('b'); r.activate('a')
            self.assertEqual(Registry(root).active,'a')
            with self.assertRaises(ValueError): r.register('a',{'probe':[.4]})
            self.assertTrue(r.request('batch')); self.assertFalse(r.request('batch'))
            self.assertFalse(Registry(root).request('batch'))
    def test_threshold_ties_and_confusion(self):
        hist={0:[990,0],1500:[10,20]}
        threshold=operating(hist); m=evaluate(hist,threshold)
        self.assertLessEqual(m['fpr'],.01); self.assertEqual(m['tp']+m['fn'],20)
        self.assertEqual(m['tn']+m['fp'],1000)
        self.assertIsNone(evaluate({0:[10,0]},0)['recall'])
        self.assertEqual(merge([hist,hist])[1500],[20,40])
    def test_guard_rejection(self):
        good={'recall':.8,'pr_auc':.7,'fpr':.005}
        self.assertTrue(guarded(good,good,good,good)[0])
        self.assertFalse(guarded(good|{'recall':.7},good,good,good)[0])
    def test_synthetic_replay_persistence_and_future_activation(self):
        from src.adaptation.synthetic_benchmark import SyntheticBackend
        from src.adaptation.prequential_runner import run
        with tempfile.TemporaryDirectory() as root:
            b=SyntheticBackend('abrupt-conditional',23013,root)
            result=run(b,'P1',3,Path(root)/'registry',budget=2,period=8,sliding=8,minimum=50)
            self.assertEqual(result['summary']['pending_label_windows'],3)
            for e in result['events']:
                if e.get('accepted'):
                    self.assertGreater(e['activation_index'],e['window'])
                    self.assertGreaterEqual(e['activation_time'],e['training_complete'])
                    latest=max(map(int,e['training_days']))
                    self.assertLessEqual(latest,6+e['window']-3)
            for key in b.models: b.verify(key)
            self.assertEqual(sum(r['rows'] for r in result['windows']),result['summary']['rows'])
