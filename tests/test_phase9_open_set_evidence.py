"""Check the aggregate open-set evidence reconciliation."""

import json
import unittest

from scripts.checkpoint_phase9_open_set_evidence import METHODS, validate


def fixture():
    thresholds = {method: {"0.05": 20} for method in METHODS}
    hist = ["method,bin,known,correct,count"]
    days = ["method,known,rejected,count"]
    historical = {}
    for method in sorted(METHODS):
        hist.extend([f"{method},20,False,False,3", f"{method},21,False,False,1"])
        days.extend([f"{method},False,False,3", f"{method},False,True,1"])
        historical[method, "0.05"] = {"known_false_rejection": "", "unknown_rejection_recall": "0.25"}
    tables = {"score_histograms.csv": "\n".join(hist).encode(), "day_rejection.csv": "\n".join(days).encode(),
              "thresholds.json": json.dumps({"reproduction": thresholds}).encode()}
    return {"support": {"false": 4}}, tables, historical


class OpenSetEvidenceTests(unittest.TestCase):
    def test_tied_rows_and_zero_known_support_reconcile(self):
        validate(*fixture())

    def test_mismatched_day_counts_fail(self):
        receipt, tables, historical = fixture()
        tables["day_rejection.csv"] = tables["day_rejection.csv"].replace(b"maximum,False,True,1", b"maximum,False,True,2")
        with self.assertRaisesRegex(ValueError, "Per-day rejection"):
            validate(receipt, tables, historical)
