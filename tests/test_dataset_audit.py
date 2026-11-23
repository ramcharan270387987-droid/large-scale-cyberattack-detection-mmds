"""Synthetic checks for the Phase 1 audit, independent of Kaggle and the dataset."""

import json
from pathlib import Path
import tempfile
import unittest

from src.ingest import dataset_audit as audit


class AuditHelpersTest(unittest.TestCase):
    def test_column_name_normalization(self):
        self.assertEqual(audit.normalize_column("\ufeff Flow Bytes/s  "), "flow_bytes_s")
        self.assertEqual(audit.normalize_column("Ｓｒｃ—IP"), "src_ip")

    def test_label_normalization_and_default_mapping(self):
        self.assertEqual(audit.normalize_label("  Web\t Attack "), "web attack")
        self.assertEqual(audit.proposed_binary("  BEＮIGN"), "benign")
        self.assertEqual(audit.proposed_binary("Unknown"), "unmapped")
        self.assertIsNone(audit.normalize_label(None))

    def test_schema_mismatch(self):
        first = audit.inspect_schema(["Timestamp", "Flow Bytes/s", "Label"])
        reorder = audit.compare_schema(first, audit.inspect_schema(["Label", " Timestamp ", "Flow Bytes/s"]))
        self.assertTrue(reorder["compatible"])
        self.assertFalse(reorder["same_order"])
        extra = audit.compare_schema(first, audit.inspect_schema(["Timestamp", "Other", "Label"]))
        self.assertFalse(extra["compatible"])
        self.assertEqual(extra["missing"], ["flow_bytes_s"])
        dup = audit.inspect_schema(["Foo", " Foo "])
        self.assertEqual(dup["normalized_duplicates"], ["foo"])
        self.assertEqual(dup["unsupported_indices"], [0, 1])

    def test_inventory_flags_missing_size_extra_and_duplicate(self):
        filename = "Friday-02-03-2018_sample.csv"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "nested" / "raw").mkdir(parents=True)
            (root / "nested" / "raw" / filename).write_bytes(b"abc")
            (root / filename).write_bytes(b"x")
            inventory = audit.read_inventory(root, {
                "directory": "nested/raw",
                "files": {filename: 4, "Friday-16-02-2018_missing.csv": 5},
            })
            records = {item["path"]: item for item in inventory}
            mounted = records[f"nested/raw/{filename}"]
            self.assertEqual(mounted["capture_day"], "2018-03-02")
            self.assertFalse(mounted["size_matches"])
            self.assertTrue(mounted["duplicate_basename"])
            self.assertTrue(records[filename]["unexpected"])
            self.assertEqual(records["nested/raw/Friday-16-02-2018_missing.csv"]["access"], "missing")

    def test_count_reconciliation(self):
        counts = dict(physical_lines=7, blank=1, headers=2, malformed=1, parsed=3,
                      data_records=4, spark_corrupt=0, bad_width_or_quotes=1)
        self.assertTrue(audit.counts_reconcile(counts, [{"count": 2}, {"count": 1}]))
        self.assertFalse(audit.counts_reconcile(counts, [{"count": 2}]))
        self.assertFalse(audit.counts_reconcile(dict(counts, physical_lines=8)))


class SparkAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pyspark.sql import functions as F

        cls.F = F
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.config = json.loads(Path("configs/dataset.yaml").read_text())
        cls.config["spark"].update(driver_memory="2g", shuffle_partitions=4)
        cls.spark = audit.spark_session(cls.config, cls.temp.name)
        cls.addClassCleanup(cls.spark.stop)
        cls.spark.sparkContext.setLogLevel("ERROR")

    def test_timestamp_explicit_dmy_and_shadow(self):
        data = self.spark.createDataFrame(
            [(0, "02/03/2018 08:31:01"), (1, "14/02/2018 9:30 PM"), (2, "31/02/2018 08:00"), (3, None)],
            ["i", "value"],
        )
        primary, mdy, fmt = audit.timestamp_columns(self.F.col("value"), self.config["timestamp_formats"])
        rows = data.select("i", primary.alias("t"), mdy.alias("m"), fmt.alias("format")).orderBy("i").collect()
        self.assertEqual(rows[0].t.isoformat(), "2018-03-02T08:31:01")
        self.assertEqual(rows[0].m.isoformat(), "2018-02-03T08:31:01")
        self.assertEqual(rows[1].t.hour, 21)
        self.assertIsNone(rows[2].t)
        self.assertIsNone(rows[3].t)

    def test_numeric_invalid_values(self):
        data = self.spark.createDataFrame([(v,) for v in ("NaN", "Infinity", "-inf", "x", "-2", "", None)], ["value"])
        _, number, nan, inf, finite, failed = audit.numeric_fields(self.F.col("value"))
        rows = {r.value: r for r in data.select("value", number.alias("number"), nan.alias("nan"), inf.alias("inf"),
                                                finite.alias("finite"), failed.alias("failed")).collect()}
        self.assertTrue(rows["NaN"].nan)
        self.assertTrue(rows["Infinity"].inf)
        self.assertTrue(rows["-inf"].inf)
        self.assertTrue(rows["x"].failed)
        self.assertFalse(rows[""].failed)
        self.assertFalse(rows[None].finite)
        self.assertEqual(rows["-2"].number, -2)

    def test_deterministic_sampling(self):
        f = self.F
        data = self.spark.range(1000).select(f.col("id").cast("string").alias("raw"))
        keep = audit.stable_sample(f.col("raw"), 23013, 10)
        first = {r.raw for r in data.where(keep).collect()}
        second = {r.raw for r in data.repartition(4).where(keep).collect()}
        self.assertEqual(first, second)
        self.assertGreater(len(first), 0)
        self.assertLess(len(first), 1000)

    def test_spark_csv_profiles_and_fingerprints(self):
        root = Path(self.temp.name)
        name = "Friday-02-03-2018_sample.csv"
        path = root / name
        path.write_text(
            'Timestamp,Flow Duration,Note,Label\n'
            '02/03/2018 10:00,10,"part,one",Benign\n'
            '02/03/2018 10:01,10,"part,one",ATTACK\n'
            '02/03/2018 10:00,10,"part,one",Benign\n'
            '02/03/2018 10:05,-1,"", ATTACK\n'
            'Timestamp,Flow Duration,Note,Label\n'
            '1,2\n'
            '\n',
            encoding="utf-8",
        )
        item = {"name": name, "path": name, "capture_day": "2018-03-02"}
        result = {"stage_seconds": {}}
        out = root / "synthetic"
        out.mkdir()
        opts = dict(self.config, sample_modulus=1)
        parquet = audit.measure_file(self.spark, path, item, out, out, opts, result)
        self.assertEqual(result["counts"]["physical_lines"], 8)
        self.assertEqual(result["counts"]["parsed"], 4)
        self.assertEqual(result["counts"]["malformed"], 1)
        self.assertEqual(result["counts"]["repeated_header_lines"], 1)
        self.assertEqual(result["timestamps"][0]["date_matches"], 4)
        self.assertEqual(result["quality"][1]["invalid_negative"], 1)
        self.assertEqual(result["quality"][2]["empty_or_whitespace"], 1)
        fingerprints = audit.summarize_fingerprints(self.spark, [parquet])
        self.assertEqual(fingerprints["raw_line_duplicates_sha256"]["excess"], 1)
        self.assertEqual(fingerprints["label_conflicting_features_sha256"]["groups"], 1)
        self.assertTrue(audit.counts_reconcile(result["counts"], result["labels"]))

    def test_exact_duplicates_compare_field_values(self):
        root = Path(self.temp.name) / "exact"
        root.mkdir()
        first = "Friday-02-03-2018_test.csv"
        second = "Thursday-01-03-2018_test.csv"
        (root / first).write_text('Flow Duration,Label\n3,Benign\n1,Attack\n')
        (root / second).write_text('Flow Duration,Label\n"3",Benign\n2,Attack\n')
        inventory = [{"name": name, "path": name, "capture_day": audit.capture_day(name),
                      "unexpected": False, "access": "readable", "size_matches": True}
                     for name in (first, second)]
        result = audit.exact_duplicate_summary(self.spark, root, inventory)
        self.assertEqual(result["parsed_rows"], 4)
        self.assertEqual(result["distinct_rows"], 3)
        self.assertEqual(result["duplicate_groups"], 1)
        self.assertEqual(result["excess_copies"], 1)
        self.assertEqual(result["cross_day_groups"], 1)


if __name__ == "__main__":
    unittest.main()
