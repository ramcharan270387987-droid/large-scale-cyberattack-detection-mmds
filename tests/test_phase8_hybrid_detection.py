"""Verify Phase 8 numerical policy and time boundaries without complete captures."""

import json
from math import isclose
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.ingest.dataset_audit import spark_session
from src.ml.cost_sensitive_training import weights
from src.ml.hybrid_detection import blend_name, chronology, split_validation
from src.ml.novelty_normalization import percentile
from src.ml.operational_metrics import burden, scenario_ppv
from src.ml.phase8_evaluation import choose_method, eligible
from src.ml.probability_calibration import isotonic, platt, probability, reliability
from src.ml.risk_triage import risk_category, summary
from src.ml.score_fusion import learned, learned_score, weighted
from src.ml.threshold_calibration import at_threshold, choose, curves, metrics, thresholds, threshold_value


class ThresholdTests(unittest.TestCase):
    def test_tied_bins_excluded_as_a_group(self):
        scores = {0: [997, 20], 1: [2, 30], 2: [1, 10], 3: [0, 40]}
        points = curves(scores, 4)
        self.assertEqual(choose(points, .001)[0], 2)
        self.assertEqual(choose(points, .0001)[0], 3)
        frozen = at_threshold(scores, 2, 4)
        self.assertEqual((frozen["tp"], frozen["tn"], frozen["fp"], frozen["fn"]), (50, 999, 1, 50))
        self.assertEqual(choose(curves({3: [100, 100]}, 4), .001)[0], 4)
        self.assertGreater(threshold_value(4, 4), 1)

    def test_confusion_and_single_class(self):
        record = metrics(3, 8, 2, 1)
        self.assertAlmostEqual(record["f2"], 15/21)
        self.assertAlmostEqual(record["fpr"], .2)
        only = at_threshold({0: [4, 0]}, 1, 4)
        self.assertIsNone(only["pr_auc"])
        self.assertIsNone(only["recall"])
        self.assertIsNone(only["precision"])
        with self.assertRaises(ValueError):
            thresholds({0: [4, 0]}, {"score_bins": 4, "budgets": [.01], "false_negative_cost": 5})

    def test_model_selection_tie_breaks_on_cost(self):
        m = {"recall": .4, "fpr": .01, "precision": .5}
        self.assertEqual(choose_method({"costly": (m, 5, 1), "short": (m, 2, 3)}), "short")


class CalibrationTests(unittest.TestCase):
    def test_platt_calibrates_bin_midpoints(self):
        calibration = {0: [40, 2], 2: [21, 13], 3: [2, 40]}
        fitted = platt(calibration, 4)
        self.assertLess(probability(fitted, 0, 4), probability(fitted, 3, 4))
        self.assertEqual(fitted, platt(calibration, 4))

    def test_isotonic_pools_decreasing_blocks(self):
        spec = isotonic({0: [9, 1], 1: [2, 8], 3: [7, 3]})
        self.assertEqual(spec["upper_bins"], [0, 3])
        self.assertAlmostEqual(probability(spec, 2, 4), .55)
        with self.assertRaises(ValueError):
            isotonic({0: [10, 0], 1: [10, 0]})

    def test_weighted_reliability_math(self):
        values, bins = reliability({0: [9, 1], 3: [1, 9]}, 4, 2, 1e-6)
        self.assertEqual(values["rows"], 20)
        self.assertAlmostEqual(values["brier"], .090625)
        self.assertAlmostEqual(values["ece"], .025)
        self.assertEqual(sum(group[0] for group in bins), 20)

    def test_novelty_ties_and_fusion(self):
        self.assertEqual(percentile([0, 2, 2, 8], 2), .25)
        self.assertEqual(percentile([0, 2, 2, 8], 6), .75)
        self.assertEqual(percentile([1, 1, 1], 1), 0)
        self.assertIsNone(percentile([], 2))
        self.assertEqual(weighted(.8, .4, .5), .6000000000000001)
        self.assertEqual(blend_name(.25), "blend_0_25")
        self.assertTrue(isclose(learned_score({"intercept": -1, "coefficients": [2, 0]}, .5, .2), .5))


class DesignAndDecisionTests(unittest.TestCase):
    def test_rolling_boundaries_and_minimum_support(self):
        config = json.loads(Path("configs/phase8_hybrid_experiments.yaml").read_text())
        for plan in config["rolling"].values():
            self.assertTrue(chronology(plan))
            self.assertFalse(chronology(plan | {"test": plan["operating"]}))
        self.assertFalse(eligible({0: 10000, 1: 99}, 100))
        self.assertFalse(eligible({1: 100}, 100))
        self.assertTrue(eligible({0: 1000, 1: 123}, 100))

    def test_weights_are_train_class_ratios(self):
        self.assertEqual(weights({0: 40, 1: 10}, [1, 5, "inverse"]), {"1": 1.0, "5": 5.0, "inverse": 4.0})
        with self.assertRaises(ValueError):
            weights({0: 40}, ["inverse"])

    def test_triage_preserves_review_and_abstentions(self):
        self.assertEqual(risk_category(.8, .8, .3), "HIGH_RISK")
        self.assertEqual(risk_category(.3, .8, .3), "REVIEW_REQUIRED")
        self.assertEqual(risk_category(.29, .8, .3), "LOW_RISK")
        self.assertEqual(risk_category(float("nan"), .8, .3), "ABSTAIN")
        result = summary({"HIGH_RISK": (1, 5), "LOW_RISK": (4, 1),
                          "REVIEW_REQUIRED": (2, 3), "ABSTAIN": (2, 2)})
        self.assertEqual(result["rows"], 20)
        self.assertAlmostEqual(result["automatic_coverage"], .55)
        self.assertAlmostEqual(result["automatic_error_rate"], 2/11)
        self.assertAlmostEqual(result["review_per_100000"], 25000)

    def test_hypothetical_ppv_and_operational_rate(self):
        self.assertAlmostEqual(scenario_ppv(.5, .01, .001), .0005/.01049)
        self.assertIsNone(scenario_ppv(0, 0, .1))
        result = burden(metrics(50, 990, 10, 50), [.001])
        self.assertAlmostEqual(result["false_per_1000000"], 10000)


class SparkRoleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = TemporaryDirectory()
        cls.addClassCleanup(temporary.cleanup)
        cls.spark = spark_session({"spark": {"master": "local[2]", "driver_memory": "2g", "shuffle_partitions": 2,
                                           "input_partition_bytes": 16777216}}, Path(temporary.name))
        cls.addClassCleanup(cls.spark.stop)
        cls.spark.sparkContext.setLogLevel("ERROR")

    def test_role_hash_keeps_groups_and_is_repartition_invariant(self):
        records = [(f"validation-{index}", 1) for index in range(60)] * 2
        records += [("train", 0), ("operating", 2), ("test", 3)]
        frame = self.spark.createDataFrame(records, "predictor_key string, split_rank int")
        first = split_validation(frame, True, 23013).collect()
        second = split_validation(frame.repartition(3), True, 23013).collect()
        self.assertEqual(sorted(first), sorted(second))
        roles = dict((row.predictor_key, row.role) for row in first)
        self.assertTrue(all(roles[row.predictor_key] == row.role for row in first))
        self.assertEqual({roles[key] for key in ("train", "operating", "test")}, {"train", "operating", "test"})
        self.assertEqual({row.role for row in first if row.split_rank == 1}, {"probability", "meta"})

    def test_learned_fusion_rejects_other_roles(self):
        frame = self.spark.createDataFrame([("meta", .2, .1, 0), ("test", .8, .6, 1)],
                                           "role string, supervised double, novelty double, binary_label int")
        with self.assertRaisesRegex(ValueError, "disjoint meta-training"):
            learned(frame)


if __name__ == "__main__":
    unittest.main()
