import json
import unittest
from pathlib import Path
from src.patterns.support import score

class PatternRegistryTests(unittest.TestCase):
    def test_frozen_registry_round_trip_and_inference(self):
        root=Path(__file__).resolve().parents[1]
        policy=json.loads((root/'reports/phase10_detection/frozen.json').read_text())
        restored=json.loads(json.dumps(policy))
        self.assertEqual(restored,policy)
        cases=[[],['flow_duration=MISSING'],policy['patterns'][0]]
        self.assertEqual([score(c,policy['patterns']) for c in cases],[score(c,restored['patterns']) for c in cases])
        self.assertEqual(policy['training_rows'],13191622)
        self.assertEqual(policy['validation_fpr_budget'],.01)
        self.assertTrue(all(len(p) in (2,3) for p in policy['patterns']))
        self.assertTrue(all('source_day' not in item and 'attack_family' not in item for p in policy['patterns'] for item in p))
