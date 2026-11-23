"""Synthetic split, transform, metric and serialization checks."""

from collections import Counter
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pyspark.sql import functions as F

from src.ingest.dataset_audit import spark_session
from src.ml.evaluate_supervised import binned_auc, confusion_metrics, estimator_score, evaluate, family_recall
from src.ml.feature_registry import finite, registry
from src.ml.preprocessing import fit_preprocessing, verify_vectors
from src.ml.split_protocols import assign_population, check_days, crossing_groups, group_sample, group_summary, mark_retention
from src.ml.train_supervised import create_estimator, save_and_reload, select_trial


CONFIG = json.loads(Path("configs/ml_experiments.yaml").read_text())


class SupervisedMetricsTest(unittest.TestCase):
    def test_confusion(self):
        metrics = confusion_metrics(18, 24, 8, 6)
        self.assertAlmostEqual(metrics["accuracy"], 42 / 56)
        self.assertAlmostEqual(metrics["recall"], .75)
        self.assertAlmostEqual(metrics["specificity"], .75)
        self.assertAlmostEqual(metrics["precision"], 18 / 26)
        self.assertIsNone(confusion_metrics(0, 10, 0, 0)["precision"])

    def test_auc_edges_and_ties(self):
        self.assertEqual(binned_auc({0: Counter({0: 8, 1: 2})}), {"roc_auc": .5, "pr_auc": .2})
        self.assertEqual(binned_auc({1: Counter({0: 8})}), {"roc_auc": None, "pr_auc": None})
        self.assertEqual(binned_auc({1: Counter({1: 8})}), {"roc_auc": None, "pr_auc": None})
        self.assertEqual(binned_auc({0: Counter({0: 2}), 1: Counter({1: 2})}), {"roc_auc": 1.0, "pr_auc": 1.0})
        self.assertEqual(binned_auc({1: Counter({0: 2}), 0: Counter({1: 2})}), {"roc_auc": 0.0, "pr_auc": .5})

    def test_family_support(self):
        rows = family_recall({(1, "Web attack", "XSS"): Counter({1: 5, 0: 5}), (0, "Benign", "Benign"): Counter({1: 3, 0: 7})},
                             {"Benign": 30}, {"Benign": 30},
                             {"Benign": 0, "Web attack": 1, "Bot": 1}, {"Benign": 0, "XSS": 1}, 100)
        family = {row["category"]: row for row in rows if row["level"] == "family"}
        self.assertEqual(family["Web attack"]["recall"], .5)
        self.assertEqual(family["Web attack"]["support_status"], "low")
        self.assertFalse(family["Web attack"]["seen_in_training"])
        self.assertIsNone(family["Bot"]["recall"])
        self.assertEqual(family["Benign"]["benign_false_positive_rate"], .3)

    def test_registry_chronology_and_selection(self):
        upstream = json.loads(Path("manifests/parquet_layers.json").read_text())["feature_columns"]
        self.assertEqual(len(registry(CONFIG, upstream)), 18)
        for forbidden in ("binary_label", "source_day", "dst_port", "split_feature_key", "protocol", "init_bwd_win_byts"):
            with self.assertRaises(ValueError):
                registry(CONFIG | {"numerical_features": [forbidden]}, [forbidden])
        design = CONFIG["protocols"]["B"]
        days = [day for key in ("train", "validation", "test") for day in design[key]]
        check_days("B", design, days)
        with self.assertRaisesRegex(ValueError, "strictly ordered"):
            check_days("B", design | {"train": design["test"], "test": design["train"]}, days)
        self.assertEqual(select_trial([{"trial": 2, "pr_auc": .7}, {"trial": 1, "pr_auc": .7}])["trial"], 1)


class SparkSupervisedTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.path = Path(cls.temp.name)
        cls.spark = spark_session({"spark": {"master": "local[2]", "driver_memory": "2g", "shuffle_partitions": 3,
                                             "input_partition_bytes": 67108864}}, cls.path)
        cls.addClassCleanup(cls.spark.stop)
        cls.spark.sparkContext.setLogLevel("ERROR")

    def test_groups_deterministic_and_purged(self):
        data = self.spark.createDataFrame([
            (b"a", "2020-01-01"), (b"a", "2020-01-03"), (b"b", "2020-01-02"),
            (b"b", "2020-01-03"), (b"c", "2020-01-03"),
        ], ["predictor_key", "source_day"])
        a = group_sample(assign_population(data, "A", CONFIG, []), CONFIG)
        b = group_sample(assign_population(data.repartition(3), "A", CONFIG, []), CONFIG)
        self.assertEqual(sorted(tuple(r) for r in a.collect()), sorted(tuple(r) for r in b.collect()))
        self.assertEqual(group_summary(crossing_groups(a, "predictor_key"))["groups"], 0)
        days = ["2020-01-01", "2020-01-02", "2020-01-03"]
        config = CONFIG | {"protocols": {"B": dict(zip(("train", "validation", "test"), [[d] for d in days]))}}
        assigned = assign_population(data, "B", config, days)
        groups = crossing_groups(assigned, "predictor_key")
        self.assertEqual(group_summary(groups)["groups"], 2)
        kept = mark_retention(assigned, groups, 2).where("retained")
        self.assertEqual(kept.count(), 3)
        self.assertEqual(group_summary(crossing_groups(kept, "predictor_key"))["groups"], 0)

    def test_train_only_finite_and_model_reload(self):
        rows = [(i, int(i >= 5), 0, float(i), 1.0, "Bot" if i >= 5 else "Benign",
                 "Bot" if i >= 5 else "Benign") for i in range(10)]
        schema = ["id", "binary_label", "split_rank", "value", "constant", "attack_family", "original_label"]
        train = self.spark.createDataFrame(rows, schema).withColumn("predictor_key", F.col("id").cast("string"))
        test = self.spark.createDataFrame([
            (11, 1, 2, float("inf"), 1.0, "Bot", "Bot"), (12, 0, 2, 100.0, 1.0, "Benign", "Benign"),
        ], schema).withColumn("value", finite("value"))
        common, scaled, evidence = fit_preprocessing(train, ["value", "constant"])
        self.assertEqual(evidence["active"], ["value"])
        self.assertEqual(evidence["training_medians"], {"value": 4.0})
        with self.assertRaisesRegex(ValueError, "train rows only"):
            fit_preprocessing(test, ["value"])
        test_vectors = scaled.transform(test)
        verify_vectors(test_vectors, 1)
        self.assertEqual(test_vectors.where("id = 11").first().value_imputed, 4.0)
        params = {"maxIter": 3, "regParam": 0.05, "elasticNetParam": 0.0}
        fitted = create_estimator("logistic_regression", params, CONFIG).fit(scaled.transform(train))
        metrics, groups = evaluate(estimator_score(fitted, test_vectors), CONFIG)
        self.assertEqual(metrics["rows"], 2)
        self.assertEqual(set(groups), {(1, "Bot", "Bot"), (0, "Benign", "Benign")})
        self.assertTrue({"accuracy", "specificity", "pr_auc", "roc_auc", "prediction_seconds"} <= set(metrics))
        evidence = save_and_reload(fitted, scaled, "logistic_regression", train, self.path / "test_model")
        self.assertEqual(evidence["reload_probe_rows"], 10)
        self.assertGreater(evidence["model_files"], 0)
