"""Exercise replay chronology, frozen scoring boundaries and actual checkpoint restart."""

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from pyspark.ml import Pipeline
from pyspark.ml.feature import Imputer, VectorAssembler
from pyspark.sql import functions as F

from src.ingest.dataset_audit import spark_session
from src.streaming.alert_engine import signals
from src.streaming.checkpoint_recovery import commit_aggregate, commit_file, load_commits
from src.streaming.model_scoring import verified_model
from src.streaming.replay_source import CAPTURE_ONLY, publish, replay_calendar, window_key
from src.streaming.shift_metrics import fixed_bin, model_metrics, novelty
from src.streaming.structured_replay import query_stream


class Phase6StreamingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(Path("configs/streaming_experiments.yaml").read_text())
        cls.temp = TemporaryDirectory()
        config = cls.config | {"spark": {"master": "local[2]", "driver_memory": "2g", "shuffle_partitions": 2,
                                        "input_partition_bytes": 16777216}}
        cls.spark = spark_session(config, cls.temp.name)
        cls.spark.sparkContext.setLogLevel("FATAL")

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()
        cls.temp.cleanup()

    def test_replay_order_and_timestamp_quarantine(self):
        events = self.spark.createDataFrame([
            ("2018-03-02", "2018-03-02 10:00:00", True, 2),
            ("2018-03-01", "2018-02-28 08:00:00", False, 2),
            ("2018-03-01", "2018-03-01 05:59:59", True, 2),
            ("2018-03-01", None, False, 2),
        ], "source_day STRING, event STRING, temporal_eligibility BOOLEAN, split_rank INT")
        rows = (events.withColumn("parsed_event_time", F.col("event").cast("timestamp_ntz"))
                .withColumn("window_hour", window_key(3)).groupBy("source_day", "window_hour", "split_rank").count().collect())
        actual = replay_calendar(rows, self.config)
        self.assertEqual([(r["source_day"], r["window_hour"], r["rows"]) for r in actual],
                         [("2018-03-01", 3, 1), ("2018-03-01", CAPTURE_ONLY, 2), ("2018-03-02", 9, 1)])
        self.assertEqual(actual, replay_calendar(list(reversed(rows)), self.config))

    def test_fixed_bins_and_retrospective_support(self):
        frame = self.spark.createDataFrame([(None,), (-1.0,), (0.0,), (2.0,), (3.0,)], "value DOUBLE")
        self.assertEqual([r[0] for r in frame.select(fixed_bin("value", [0, 2])).collect()], [3, 0, 1, 2, 2])
        model = model_metrics({"0": [9, 0], "1024": [1, 0]}, 2048)
        self.assertIsNone(model["recall"])
        self.assertIsNone(model["pr_auc"])
        self.assertEqual(model["predicted_positive"], 1)
        self.assertEqual(model["fp"], 1)
        self.assertIsNone(novelty({"attacks": 0, "benign": 10, "novel_attack": 0, "novel_benign": 0})["precision"])

    def test_alert_labels_support_and_reference(self):
        def frame(left, right, hit, novel):
            score = {"0": [left, right - hit]}
            if hit:
                score["1024"] = [0, hit]
            return {"rows": left + right, "attacks": right, "benign": left, "novel_attack": novel, "novel_benign": 0,
                    "histograms": {name: [left, right] for name in (*self.config["features"], "cluster")},
                    "scores": {name: score
                               for name in ("random_forest", "logistic_regression", "duration_rule")}}
        baseline = frame(20000, 10000, 8000, 0)
        future = frame(20000, 10000, 1000, 700)
        _, alerts = signals(future, baseline, {"split_rank": 2}, self.config)
        self.assertTrue(any(r["category"] == "NOVELTY_RATE" and not r["labels_used"] for r in alerts))
        self.assertTrue(any(r["category"] == "PERFORMANCE_WARNING" and r["labels_used"] and r["severity"] == "high"
                            for r in alerts))
        self.assertEqual(signals(future, baseline, {"split_rank": 0}, self.config)[1], [])
        self.assertEqual(signals(frame(1, 1, 0, 1), baseline, {"split_rank": 2}, self.config)[1], [])

    def test_partial_and_duplicate_sink_writes(self):
        with TemporaryDirectory() as tmp:
            target = Path(tmp)
            commit_file(target, 0).with_suffix(".partial").write_text("{")
            payload = {"batch_id": 0, "source": [3], "rows": 2}
            self.assertEqual(load_commits(target), [])
            self.assertTrue(commit_aggregate(target, 0, payload))
            self.assertFalse(commit_aggregate(target, 0, payload | {"rows": 99}))
            self.assertEqual(load_commits(target), [payload])
            with self.assertRaises(ValueError):
                commit_aggregate(target, 0, {"batch_id": 0, "source": [6]})

    def test_frozen_preprocessing_check_hash_order_and_spark_metadata(self):
        fixture = self.spark.createDataFrame([(1.0, 2.0), (2.0, 4.0)], "f DOUBLE, g DOUBLE")
        pipeline = Pipeline(stages=[Imputer(inputCols=["f", "g"], outputCols=["f_imputed", "g_imputed"]),
                                    VectorAssembler(inputCols=["f_imputed", "g_imputed"], outputCol="features")]).fit(fixture)
        with TemporaryDirectory() as tmp:
            target = Path(tmp) / "pipeline"
            pipeline.write().save(str(target))
            hashes = {p.relative_to(target).as_posix(): sha256(p.read_bytes()).hexdigest()
                      for p in target.rglob("*") if p.is_file() and not p.name.endswith(".crc")}
            self.assertTrue(any(name.endswith("/_SUCCESS") for name in hashes))
            self.assertEqual(verified_model(self.spark, target, hashes, ["f", "g"]).transform(fixture).count(), 2)
            with self.assertRaisesRegex(ValueError, "predictor order"):
                verified_model(self.spark, target, hashes, ["g", "f"])
            with self.assertRaisesRegex(ValueError, "checksum"):
                verified_model(self.spark, target, {}, ["f", "g"])

    def test_structured_streaming_checkpoint_and_multifile(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "ready"
            source.mkdir()
            calendar = []
            schema = None
            for seq in range(3):
                expected = {"replay_seq": seq, "source_day": f"2018-03-0{seq + 1}", "window_hour": 3,
                            "split_rank": 2, "rows": seq + 1}
                frame = self.spark.createDataFrame([(seq,)] * (seq + 1), "replay_seq INT")
                schema = frame.schema
                spool = root / f"spool{seq}"
                frame.coalesce(1).write.parquet(str(spool))
                expected["bytes"] = publish(source, next(spool.glob("*.parquet")), seq)
                calendar.append(expected)

            def process(frame):
                rows = frame.groupBy("replay_seq").count().orderBy("replay_seq").collect()
                return [calendar[r.replay_seq] | {"rows": r["count"]} for r in rows], 0.0

            documents, evidence = query_stream(self.spark, source, schema, calendar, root / "checkpoint", root / "sink",
                                               1, process, inject=True)
            self.assertEqual(sum(item["rows"] for doc in documents for item in doc["chunks"]), 6)
            self.assertEqual(len(documents), 3)
            self.assertEqual(len(evidence["attempts"]), 2)
            self.assertTrue(all(item["passed"] for item in evidence["recovery"]))
            merged, _ = query_stream(self.spark, source, schema, calendar, root / "checkpoint2", root / "sink2", 2, process)
            self.assertEqual([len(doc["chunks"]) for doc in merged], [2, 1])
