"""Verify that full curves preserve unknown and accepted-risk denominators."""

import unittest

from scripts.render_phase9_extended import rejection_curves


def row(bin_num, known, correct, count):
    return {"method": "maximum", "bin": str(bin_num), "known": str(known),
            "correct": str(correct), "count": str(count)}


class Phase9RejectionCurveTests(unittest.TestCase):
    def test_rejecting_tied_bin_keeps_both_target_populations(self):
        risk, roc, pr = rejection_curves([row(10, True, True, 3), row(20, True, False, 1),
                                          row(20, False, False, 2)])
        self.assertEqual(risk, ([1.0, 0.5], [0.5, 0.0]))
        self.assertEqual(roc, ([0.0, 0.25, 1.0], [0.0, 1.0, 1.0]))
        self.assertEqual(pr, ([0.0, 1.0, 1.0], [1.0, 2 / 3, 1 / 3]))

    def test_no_known_support_leaves_discrimination_undefined(self):
        risk, roc, pr = rejection_curves([row(10, False, False, 1), row(20, False, False, 1)])
        self.assertEqual(risk, ([1.0, 0.5], [1.0, 1.0]))
        self.assertIsNone(roc)
        self.assertIsNone(pr)
