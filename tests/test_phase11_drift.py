import unittest
from src.drift.label_availability import LabelSchedule
from src.drift.synthetic_generators import generate
from src.drift.drift_evaluation import evaluate

class DriftContracts(unittest.TestCase):
    def test_label_release(self):
        labels=LabelSchedule(3);labels.predict(0,'a',1)
        self.assertEqual(labels.release(2),[])
        self.assertEqual(labels.release(3),[('a',1,3)])
        self.assertEqual(labels.release(4),[])

    def test_unique_episode_matching(self):
        result=evaluate([100,2050,2051,3000],[2048],4096)
        self.assertEqual((result['detected_episodes'],result['repeated_episode_alerts'],result['false_alarms']),(1,1,1))
        self.assertIsNone(evaluate([], [2048],4096)['mean_delay_observations'])

    def test_synthetic_determinism(self):
        self.assertEqual(list(generate('abrupt',1)),list(generate('abrupt',1)))
        concept=list(generate('concept',1));self.assertFalse(any(r['error'] for r in concept[:2048]));self.assertTrue(all(r['error'] for r in concept[2048:]))
