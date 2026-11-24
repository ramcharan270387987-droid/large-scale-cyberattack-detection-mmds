"""Independent accounting checks for the chronological hierarchy."""

import unittest

from scripts.checkpoint_phase9_hierarchical import GATES, summarize


class HierarchyCheckpointTests(unittest.TestCase):
    def test_complete_traffic_accounting_and_conditional_denominators(self):
        cases = [
            ("0", "Benign", "correct_benign", 10),
            ("0", "UNKNOWN", "benign_false_alarm", 2),
            ("1", "Benign", "missed_attack", 5),
            ("1", "UNKNOWN", "unknown_rejected", 2),
            ("1", "DoS", "unknown_false_accept", 1),
        ]
        rows = [dict(gate=gate, binary_label=label, decision=decision, outcome=outcome, count=n)
                for gate in GATES for label, decision, outcome, n in cases]
        result = summarize(rows)["phase8_hybrid"]
        self.assertEqual(result["rows"], 20)
        self.assertEqual(result["accuracy"], 0.60)
        self.assertEqual(result["review_rows"], 4)
        self.assertEqual(result["automatic_coverage"], 0.80)
        self.assertEqual(result["unknown_rejection_recall"], 0.25)
        self.assertEqual(result["conditional_unknown_rejection_recall"], 2 / 3)
        self.assertIsNone(result["known_family_macro_f1"])

    def test_rejects_inconsistent_error_category(self):
        with self.assertRaisesRegex(ValueError, "Inconsistent"):
            summarize([dict(gate="phase4_rf", binary_label="1", decision="Benign",
                            outcome="unknown_rejected", count=1)])

    def test_zero_attack_support_is_undefined(self):
        rows = [dict(gate=gate, binary_label="0", decision="Benign", outcome="correct_benign", count=1)
                for gate in GATES]
        result = summarize(rows)["oracle"]
        self.assertIsNone(result["unknown_rejection_recall"])
        self.assertIsNone(result["conditional_unknown_rejection_recall"])
