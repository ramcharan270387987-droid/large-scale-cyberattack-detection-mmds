"""Synthetic checks for label-free clustering and descriptive evaluation."""

import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pyspark.sql import functions as F

from src.ingest.dataset_audit import spark_session
from src.ml.cluster_diagnostics import adjusted_rand, choose_k, fit_kmeans, silhouette
from src.ml.cluster_evolution import divergence
from src.ml.clustering_features import clustering_registry, fit_transform, verify_finite_vectors
from src.ml.novelty_scoring import calibrate, novelty_row, squared_distance
from src.ml.train_clustering import pick_reference, saved_pipeline, verify_phase4_match


CONFIG = json.loads(Path("configs/clustering_experiments.yaml").read_text())


class ClusteringMathTest(unittest.TestCase):
    def test_divergence_and_zero_bins(self):
        self.assertAlmostEqual(divergence([1, 0], [0, 1]), 1)
        self.assertAlmostEqual(divergence([4, 2, 0], [6, 3, 0]), 0)
        self.assertIsNone(divergence([0, 0], [1, 0]))

    def test_permutation_and_degeneracy(self):
        self.assertEqual(adjusted_rand([(0, 1, 4), (1, 0, 5)]), 1)
        self.assertLess(adjusted_rand([(0, 0, 4), (0, 1, 4), (1, 0, 4), (1, 1, 4)]), .1)
        rows = [{"k": k, "empty_clusters": empty, "smallest_share": share, "silhouette": score}
                for k, empty, share, score in [(3, 0, .2, .8), (5, 1, .2, .95), (8, 0, .0001, .9), (12, 0, .1, .8)]]
        self.assertEqual(choose_k(rows)["k"], 3)
        with self.assertRaisesRegex(ValueError, "degenerate"):
            choose_k(rows[1:3])

    def test_support_and_reconciliation(self):
        self.assertIsNone(novelty_row(0, 20, 0, 2)["attack_recall"])
        self.assertIsNone(novelty_row(3, 0, 0, 0)["benign_fpr"])
        self.assertIsNone(novelty_row(3, 0, 0, 0)["precision"])
        actual = [{"split_rank": 2, "binary_label": 1, "attack_family": "Bot", "count": 4}]
        supports = {"train": {"families": {}, "labels": {}}, "validation": {"families": {}, "labels": {}},
                    "test": {"families": {"Bot": 4}, "labels": {"1": 4}}}
        receipt = {"protocols": {"B": {"version": 2, "split_support": supports, "overlap": {"purged_rows": 2}}}}
        self.assertEqual(verify_phase4_match(actual, "B", receipt)["purged_rows"], 2)
        with self.assertRaisesRegex(ValueError, "retained cohort"):
            verify_phase4_match([actual[0] | {"count": 5}], "B", receipt)

    def test_feature_exclusions(self):
        config = json.loads(Path("configs/ml_experiments.yaml").read_text())
        names = clustering_registry(config, config["numerical_features"])
        self.assertEqual(len(names), 18)
        for name in ("binary_label", "source_day", "protocol", "dst_port", "record_fingerprint"):
            with self.assertRaises(ValueError):
                clustering_registry(config | {"numerical_features": [name]}, [name])


class ClusteringSparkTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.path = Path(cls.temp.name)
        cls.spark = spark_session({"spark": {"master": "local[2]", "driver_memory": "2g", "shuffle_partitions": 2,
                                             "input_partition_bytes": 67108864}}, cls.path)
        cls.addClassCleanup(cls.spark.stop)
        cls.spark.sparkContext.setLogLevel("ERROR")

    def test_group_sampling_is_stable_and_train_only(self):
        rows = [(bytes([i]), rank) for i in range(180) for rank in (0, 0, 2)]
        data = self.spark.createDataFrame(rows, ["predictor_key", "split_rank"])
        config = CONFIG | {"training_permyriad": 3000, "internal_permyriad": 3000}
        a, b = pick_reference(data, config)
        a2, b2 = pick_reference(data.repartition(3), config)
        for x, y in ((a, a2), (b, b2)):
            self.assertEqual(sorted(tuple(r) for r in x.collect()), sorted(tuple(r) for r in y.collect()))
            self.assertEqual({row.split_rank for row in x.collect()}, {0})
            self.assertTrue(all(r["count"] == 2 for r in x.groupBy("predictor_key").count().collect()))
        self.assertEqual(a.join(b, "predictor_key").count(), 0)

    def test_label_free_transform_distance_calibration_and_reload(self):
        train = self.spark.createDataFrame([(float(i), float(i % 3)) for i in range(18)], ["x", "y"])
        with self.assertRaisesRegex(ValueError, "approved predictor"):
            fit_transform(train.withColumn("binary_label", F.lit(1)), ["x", "y"])
        prep, details = fit_transform(train, ["x", "y"])
        self.assertEqual(details["fit_columns"], ["x", "y"])
        frozen = details["imputation_surrogates"]["x_valid"]
        self.assertLess(frozen, math.log1p(10))
        heldout = self.spark.createDataFrame([(float("inf"), 0.0), (100.0, float("nan"))], ["x", "y"])
        clean = prep.transform(heldout)
        verify_finite_vectors(clean, 2)
        self.assertAlmostEqual(clean.where("x_filled < 3").first()["x_filled"], frozen)
        vectors = prep.transform(train).select("features")
        with self.assertRaisesRegex(ValueError, "only the fitted feature"):
            fit_kmeans(vectors.withColumn("label", F.lit(1)), 2, CONFIG, 17)
        model, receipt = fit_kmeans(vectors, 2, CONFIG, 17)
        model2, _ = fit_kmeans(vectors, 2, CONFIG, 17)
        self.assertEqual(receipt["training_rows"], 18)
        self.assertIsNotNone(silhouette(model, vectors))
        self.assertEqual(model.clusterCenters()[0].tolist(), model2.clusterCenters()[0].tolist())
        scored = squared_distance(model, vectors)
        row = scored.first()
        self.assertAlmostEqual(row.score, sum((a - b) ** 2 for a, b in zip(row.features, model.clusterCenters()[row.cluster])))
        reference = scored.select(F.lit(0).alias("split_rank"), "score")
        calibration = calibrate(reference, [0.95, 0.99], 8192)
        self.assertEqual(calibration["rows"], 18)
        self.assertLessEqual(calibration["cutoffs"]["0.95"], calibration["cutoffs"]["0.99"])
        with self.assertRaisesRegex(ValueError, "reference score rows"):
            calibrate(reference.withColumn("split_rank", F.lit(2)), [0.95], 8192)
        artifact = saved_pipeline(prep, model, train, self.path / "model")
        self.assertEqual(artifact["reload_rows"], 18)
        self.assertGreater(artifact["bytes"], 0)
