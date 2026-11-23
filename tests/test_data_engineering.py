"""Synthetic Phase 2 coverage, including layered Parquet verification."""

from collections import Counter
import csv
import json
import math
from pathlib import Path
import tempfile
import unittest

from pyspark.sql import functions as F

from src.ingest.cleaning import (
    apply_duplicate_policy, canonical_frame, clean_frame, conflict_groups, exact_groups, feature_frame,
)
from src.ingest.dataset_audit import spark_session
from src.ingest.parquet_pipeline import LAYERS, process_capture
from src.ingest.schema_contract import DataContract, reconcile_source, safe_union, source_records
from src.ingest.storage_validation import verify_published_layers
from src.sql.aggregation_demo import run_aggregation_demo
from scripts.retrieve_phase2_evidence import log_summary


class EngineeringTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.directory = Path(cls.temp.name)
        cls.contract = DataContract.load("configs/cleaning.yaml")
        cls.contract.policy["spark"].update(driver_memory="2g", master="local[2]", shuffle_partitions=4)
        cls.spark = spark_session(cls.contract.policy, cls.directory)
        cls.addClassCleanup(cls.spark.stop)
        cls.spark.sparkContext.setLogLevel("ERROR")
        cls.formats = json.loads(Path("configs/dataset.yaml").read_text())["timestamp_formats"]
        cls.common = cls.directory / "common.csv"
        cls.extended = cls.directory / "extended.csv"
        cls.write_csv(cls.common, "common_80", [
            {"Timestamp": "14/02/2018 01:00:00", "Label": "Benign", "Flow Byts/s": "NaN",
             "Flow Pkts/s": "Infinity", "Flow Duration": "-2", "Init Fwd Win Byts": "-1"},
            {"Timestamp": "14/02/2018 01:00:00", "Label": "Benign", "Flow Byts/s": "NaN",
             "Flow Pkts/s": "Infinity", "Flow Duration": "-2", "Init Fwd Win Byts": "-1"},
            {"Timestamp": "05/01/1970 03:01:17", "Label": "Bot", "Flow Byts/s": "-Infinity",
             "Flow Pkts/s": "Infinity", "Flow Duration": "-2", "Init Fwd Win Byts": "-1"},
            {"Timestamp": "15/02/2018 02:00:00", "Label": "SQL Injection", "Flow Byts/s": "bad"},
        ], repeat=True)
        cls.write_csv(cls.extended, "extended_84", [
            {"Timestamp": "20/02/2018 01:00:00", "Label": "Benign", "Flow ID": "flow",
             "Src IP": "192.0.2.1", "Dst IP": "192.0.2.2", "Src Port": "12345"},
        ])

    @classmethod
    def write_csv(cls, path, variant, rows, repeat=False):
        header = cls.contract.policy["headers"][variant]
        with path.open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(header)
            for row in rows:
                writer.writerow([row.get(name, "1") for name in header])
            if repeat:
                writer.writerow(header)

    def canonical(self, path=None, day="2018-02-14"):
        path = path or self.common
        variant, data = source_records(self.spark, self.contract, path, day)
        return canonical_frame(data, self.contract, variant, path.name, day, self.formats)

    def test_schema_normalization_and_safe_union(self):
        common = self.canonical()
        extended = self.canonical(self.extended, "2018-02-20")
        union = safe_union([common, extended])
        self.assertEqual(union.count(), 5)
        rows = {row.schema_variant: row for row in union.select("schema_variant", "src_ip", "src_port", "structural_missing_fields").distinct().collect()}
        self.assertIsNone(rows["common_80"].src_ip)
        self.assertEqual(len(rows["common_80"].structural_missing_fields), 4)
        self.assertEqual(rows["extended_84"].src_port, 12345.0)
        self.assertEqual(rows["extended_84"].structural_missing_fields, [])
        with self.assertRaisesRegex(ValueError, "Unexpected original header"):
            source_records(self.spark, self.contract, self.extended, "2018-02-14")
        with self.assertRaisesRegex(ValueError, "different columns"):
            safe_union([common, extended.drop("src_ip")])

    def test_mapping_and_timestamp_flags(self):
        items = {row.original_label: row for row in self.canonical().select(
            "original_label", "normalized_label", "binary_label", "attack_family",
            "timestamp_parse_status", "temporal_eligibility", "parsed_event_time", "original_timestamp").collect()}
        self.assertEqual(items["Benign"].binary_label, 0)
        self.assertEqual(items["SQL Injection"].attack_family, "Web attack")
        self.assertEqual(items["Bot"].normalized_label, "bot")
        self.assertEqual(items["Bot"].binary_label, 1)
        self.assertEqual(items["Bot"].original_timestamp, "05/01/1970 03:01:17")
        self.assertEqual(items["Bot"].parsed_event_time.year, 1970)
        self.assertEqual(items["Bot"].timestamp_parse_status, "outside_capture_day")
        self.assertTrue(items["Benign"].temporal_eligibility)
        self.assertFalse(items["Bot"].temporal_eligibility)
        raw = self.spark.createDataFrame([(" Benign",)], ["label"])
        self.assertIsNone(raw.select(self.contract.label_lookup()[F.col("label")]).first()[0])

    def test_invalid_values_and_sentinels(self):
        raw = self.canonical()
        before = raw.where("binary_label = 0").first()
        self.assertTrue(math.isnan(before.flow_byts_s))
        self.assertEqual(before.flow_pkts_s, math.inf)
        self.assertEqual(before.init_fwd_win_byts, -1)
        after = {row.original_label: row for row in clean_frame(raw, self.contract).collect()}
        clean = after["Benign"]
        for name in ("flow_byts_s", "flow_pkts_s", "flow_duration", "init_fwd_win_byts"):
            self.assertIsNone(clean[name])
        reasons = {issue.reason: issue.source_text for issue in clean.quality_issues}
        self.assertEqual(reasons, {"nan": "NaN", "positive_infinity": "Infinity",
                                   "invalid_negative": "-2", "sentinel": "-1"})
        self.assertTrue(any(i.reason == "negative_infinity" for i in after["Bot"].quality_issues))
        self.assertTrue(any(i.reason == "cast_failure" for i in after["SQL Injection"].quality_issues))

    def test_fingerprint_multiplicity_and_conflicting_labels(self):
        raw = self.canonical()
        actual = Counter(row.record_fingerprint for row in raw.select("record_fingerprint").collect())
        stable = Counter(row.record_fingerprint for row in raw.repartition(3).select("record_fingerprint").collect())
        self.assertEqual(actual, stable)
        self.assertEqual(sorted(actual.values()), [1, 1, 2])
        self.assertEqual(exact_groups(raw).first().multiplicity, 2)
        self.assertEqual(apply_duplicate_policy(raw, "diagnostic").count(), 4)
        self.assertEqual(apply_duplicate_policy(raw, "preserve_all").count(), 4)
        self.assertEqual(apply_duplicate_policy(raw, "exact_representative").count(), 3)
        features = feature_frame(clean_frame(raw, self.contract), self.contract)
        conflict = conflict_groups(features).first()
        self.assertEqual((conflict.label_count, conflict.rows), (2, 3))
        self.assertEqual(features.select("original_label").distinct().count(), 3)

    def test_leakage_feature_exclusions(self):
        features = feature_frame(clean_frame(self.canonical(self.extended, "2018-02-20"), self.contract), self.contract)
        for name in ("flow_id", "src_ip", "dst_ip", "src_port", "dst_port", "parsed_event_time",
                     "original_timestamp", "source_file", "schema_variant", "quality_issues"):
            self.assertNotIn(name, features.columns)
        for name in ("source_day", "binary_label", "record_fingerprint", "split_feature_key"):
            self.assertIn(name, features.columns)
            self.assertNotIn(name, self.contract.feature_names)
        self.assertEqual(len(self.contract.feature_names), 77)

    def test_sql_dataframe_and_rdd_parity(self):
        subset = self.spark.range(4096).select(
            F.pmod("id", F.lit(3)).cast("double").alias("protocol"),
            F.pmod("id", F.lit(2)).cast("byte").alias("binary_label"),
            F.unhex(F.sha2(F.col("id").cast("string"), 256)).alias("record_fingerprint"),
        )
        result = run_aggregation_demo(subset)
        self.assertGreater(result["rows"], 0)
        self.assertEqual(result["rows"], sum(row["records"] for row in result["groups"]))
        self.assertIn("Aggregate", result["sql_plan"])
        self.assertIn("ShuffledRDD", result["rdd_dag"])

    def test_producer_receipt_recovery_from_split_logs(self):
        receipt = {"status": "validated", "counts": {"rows": 15}}
        serialized = json.dumps(receipt)
        log = self.directory / "fixture.log"
        log.write_text(json.dumps([
            {"data": "Spark output"},
            {"data": "PHASE2_EVIDENCE " + serialized[:15]},
            {"data": serialized[15:] + "\n"},
        ]))
        self.assertEqual(log_summary(log), receipt)

    def test_layer_round_trip_and_count_reconciliation(self):
        published = self.directory / "published"
        stores = {layer: published / self.contract.policy["version"] / layer for layer in LAYERS}
        counts = {"parsed": 4, "headers": 2, "physical_lines": 6, "blank": 0,
                  "bad_width_or_quotes": 0, "spark_corrupt": 0}
        item = {"name": self.common.name, "path": self.common.name, "capture_day": "2018-02-14",
                "bytes": self.common.stat().st_size, "counts": counts}
        result = process_capture(self.spark, self.directory, stores, self.contract, item, self.formats)
        self.assertEqual(result["counts"]["repeated_headers"], 1)
        self.assertEqual(result["counts"]["canonical_rows"], 4)
        for entry in result["layers"].values():
            self.assertEqual(entry["records"], 4)
            self.assertEqual(entry["compression"], "SNAPPY")
        clean = self.spark.read.parquet(str(stores["clean"]))
        feature = self.spark.read.parquet(str(stores["feature_ready"]))
        self.assertEqual(clean.select("record_fingerprint").exceptAll(feature.select("record_fingerprint")).count(), 0)
        self.assertEqual(clean.where("original_label = 'Bot'").first().original_timestamp, "05/01/1970 03:01:17")
        self.assertEqual(dict(clean.dtypes)["parsed_event_time"], "timestamp_ntz")
        verification = verify_published_layers({
            "policy_version": self.contract.policy["version"],
            "totals": result["counts"],
            "layers": {name: info | {"partitions": 1} for name, info in result["layers"].items()},
        }, published)
        self.assertEqual(verification["clean_cells_verified_null"], 12)
        self.assertEqual(verification["clean_timestamp_outliers"], 2)
        self.assertEqual(verification["layers"]["feature_ready"]["attack"], 2)
        with self.assertRaisesRegex(ValueError, "Source count mismatch"):
            reconcile_source(counts | {"parsed": 3}, counts)


if __name__ == "__main__":
    unittest.main()
