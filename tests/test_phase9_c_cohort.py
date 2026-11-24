"""Verify the C family cohort amendment on a synthetic Spark frame."""

import unittest

from pyspark.sql import SparkSession

from src.ml.train_multiclass import earlier_c_attacks


class EarlierCohortTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spark = SparkSession.builder.master("local[2]").appName("phase9-C-test").getOrCreate()

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def test_earlier_group_disjoint_fit_and_calibration_keep_exact_test(self):
        train = [(i, "2018-02-21", "DDoS", f"group-{i}", 0) for i in range(200)]
        train += [(200, "2018-02-20", "DDoS", "group-0", 0)]
        inputs = train + [
            (201, "2018-02-21", "Web attack", "held-out", 0),
            (202, "2018-03-02", "Bot", "later", 0),
            (203, "2018-02-28", "Infiltration", "original-validation", 1),
            (204, "2018-02-22", "Web attack", "test-1", 2),
            (205, "2018-02-23", "Web attack", "test-2", 2),
        ]
        frame = self.spark.createDataFrame(inputs, "id LONG, source_day STRING, attack_family STRING, predictor_key STRING, split_rank INT")
        cfg = {"seed": 23013, "protocols": {"C": {"test": ["2018-02-22", "2018-02-23"]}}}
        result = earlier_c_attacks(frame, cfg).collect()
        self.assertEqual({r.id for r in result if r.split_rank == 2}, {204, 205})
        self.assertEqual({r.id for r in result if r.split_rank < 2}, set(range(201)))
        self.assertEqual({r.split_rank for r in result if r.split_rank < 2}, {0, 1})
        self.assertEqual(len({r.split_rank for r in result if r.predictor_key == "group-0"}), 1)
