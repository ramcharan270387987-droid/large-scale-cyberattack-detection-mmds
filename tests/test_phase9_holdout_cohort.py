"""Confirm that holdout projection excludes all collisions with held-out families."""

import unittest

from pyspark.sql import SparkSession

from src.ml.phase9_open_set_evidence import population


class HoldoutCohortTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spark = SparkSession.builder.master("local[2]").appName("phase9-holdout-test").getOrCreate()

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def test_holdout_group_is_exclusively_unknown_and_test_only(self):
        inputs = [(0, 1, "Bot", "collision"), (1, 1, "DoS", "collision"), (2, 0, "Benign", "collision"),
                  (3, 1, "DDoS", "known"), (4, 1, "DoS", "known"), (5, 1, "Bot", "another")]
        data = self.spark.createDataFrame(inputs, "id LONG, binary_label INT, attack_family STRING, predictor_key STRING")
        design = {"random_permyriad": {"train": 7000, "validation": 1500, "test": 1500}, "seed": 23013}
        active, overlap = population(data, "Bot", design, [])
        try:
            rows = active.collect()
        finally:
            active.unpersist()
        self.assertEqual({row.id for row in rows}, {0, 3, 4, 5})
        self.assertEqual({row.split_rank for row in rows if row.attack_family == "Bot"}, {2})
        self.assertEqual(len({row.split_rank for row in rows if row.predictor_key == "known"}), 1)
        self.assertEqual(overlap, {"groups": 0, "rows": 0})
