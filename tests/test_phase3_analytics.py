"""Synthetic query, reconciliation and chart tests."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.ingest.dataset_audit import spark_session
from src.sql.attack_patterns import benign_thresholds_sql, patterns_sql, sensitivity_sql
from src.sql.phase3_pipeline import verify_aggregates
from src.sql.query_benchmarks import compare_workload
from src.sql.temporal_analytics import FAMILY_DAY_SQL, HOURLY_SQL, WINDOW_SQL
from src.sql.traffic_analytics import (
    DAILY_SQL, FAMILY_SQL, LABEL_SQL, PORT_SQL, PROTOCOL_SQL, TOTAL_SQL,
    compact, correlations_sql, feature_statistics_sql, missing_sql, write_rows,
)
from src.visualization.eda_charts import draw, load_inputs


class AnalyticsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.path = Path(cls.temp.name)
        cls.spark = spark_session({"spark": {
            "driver_memory": "2g", "master": "local[2]", "shuffle_partitions": 2,
            "input_partition_bytes": 67108864,
        }}, cls.path)
        cls.addClassCleanup(cls.spark.stop)
        cls.spark.sparkContext.setLogLevel("ERROR")
        cls.data = cls.spark.sql("""SELECT * FROM VALUES
        ('2018-03-01', 'benign', 'Benign', 'Benign', 0, true, TIMESTAMP '2018-03-01 02:00:00', 6D, 443D, 1, 0, 10D, 1D, 2D, 6D, 3D),
        ('2018-03-01', 'attack', 'Bot', 'Bot', 1, true, TIMESTAMP '2018-03-01 02:02:00', 6D, 80D, 2, 1, 20D, 2D, 20D, 20D, 12D),
        ('2018-03-02', 'attack', 'Web attack', 'SQL Injection', 1, false, TIMESTAMP '1970-01-01 00:00:00', 6D, 80D, 2, 0, NULL, 3D, 30D, 30D, 40D),
        ('2018-03-02', 'benign', 'Benign', 'Benign', 0, true, TIMESTAMP '2018-03-02 05:00:00', 17D, 53D, 0, 0, 100D, 4D, 40D, 10D, 20D)
        AS t(source_day, population, attack_family, original_label, binary_label, temporal_eligibility,
        parsed_event_time, protocol, dst_port, quality_cells, invalid_cells, flow_duration, total_packets, total_bytes,
        flow_pkts_s, flow_iat_mean)""")
        cls.data.createOrReplaceTempView("traffic")

    def query(self, code):
        return compact(self.spark.sql(code), 500)

    def test_sql_grouping_and_reconciliation(self):
        queries = {"daily_traffic": DAILY_SQL, "traffic_totals": TOTAL_SQL, "attack_families": FAMILY_SQL,
                   "original_labels": LABEL_SQL, "family_by_day": FAMILY_DAY_SQL, "hourly_traffic": HOURLY_SQL,
                   "time_windows": WINDOW_SQL.format(accuracy=4096)}
        data = {key: self.query(sql) for key, sql in queries.items()}
        verify_aggregates(data, {"records": 4, "benign": 2, "attack": 2, "temporal_ineligible": 1})
        self.assertEqual([row["records"] for row in data["daily_traffic"]], [2, 2])
        self.assertEqual(sum(row["records"] for row in data["hourly_traffic"]), 3)
        self.assertEqual(sum(row["local_hour"] == 0 for row in data["hourly_traffic"]), 0)
        self.assertEqual(len([row for row in data["family_by_day"] if not row["records"]]), 2)
        self.assertEqual([row["share_of_attacks"] for row in data["attack_families"]], [0.5, 0.5])
        with self.assertRaisesRegex(ValueError, "Hourly counts"):
            verify_aggregates(data, {"records": 4, "benign": 2, "attack": 2, "temporal_ineligible": 0})

    def test_benchmark_equivalence(self):
        timings, plans, counts = compare_workload(self.data.select("source_day", "binary_label"), 2)
        self.assertEqual([row["api"] for row in timings], ["SQL", "DataFrame", "DataFrame", "SQL"])
        self.assertEqual(sum(row["records"] for row in counts), 4)
        self.assertIn("Aggregate", plans["SQL"])

    def test_distributions_and_exploratory_rules(self):
        stats = self.query(feature_statistics_sql(["flow_duration", "total_bytes"], "population", 4096))
        durations = next(r for r in stats if r["population"] == "attack" and r["feature"] == "flow_duration")
        self.assertEqual((durations["valid"], durations["population_count"], durations["mean"]), (1, 2, 20))
        correlation = self.query(correlations_sql([["total_packets", "total_bytes"]]))
        self.assertEqual(correlation[0]["pairs"], 2)
        thresholds = self.query(benign_thresholds_sql(4096))[0]
        rules = self.query(patterns_sql(thresholds))
        self.assertEqual(len(rules), 12)
        self.data.createOrReplaceTempView("features")
        missing = self.query(missing_sql(["flow_duration"]))
        self.assertEqual(missing[0]["missing"], 1)

    def test_sensitivity_duplicate_counts_preserve_label_rows(self):
        raw = self.spark.sql("""SELECT * FROM VALUES
         (0, CAST('NaN' AS DOUBLE), CAST('Infinity' AS DOUBLE), -1D, -1D, 10D),
         (0, CAST('NaN' AS DOUBLE), CAST('Infinity' AS DOUBLE), -1D, -1D, 10D),
         (1, 50D, 60D, 100D, 100D, 20D)
         AS t(binary_label, flow_byts_s, flow_pkts_s, init_fwd_win_byts, init_bwd_win_byts, flow_duration)""")
        raw.createOrReplaceTempView("raw_aligned")
        values = self.query(sensitivity_sql("raw_aligned"))
        rows = {r["feature"]: r for r in values if r["binary_label"] == 0}
        self.assertEqual(rows["flow_byts_s"]["nan"], 2)
        self.assertEqual(rows["flow_pkts_s"]["infinities"], 2)
        self.assertEqual(rows["init_fwd_win_byts"]["minus_one"], 2)
        self.assertEqual(raw.count(), 3)
        self.assertEqual(raw.distinct().count(), 2)

    def test_aggregate_csv_and_charts_are_deterministic(self):
        tables = {"traffic_totals": TOTAL_SQL, "attack_families": FAMILY_SQL, "daily_traffic": DAILY_SQL,
                  "family_by_day": FAMILY_DAY_SQL, "protocols": PROTOCOL_SQL, "destination_ports": PORT_SQL.format(limit=8),
                  "time_windows": WINDOW_SQL.format(accuracy=4096),
                  "feature_statistics": feature_statistics_sql(["flow_duration", "total_packets", "total_bytes"], "population", 4096)}
        for name, code in tables.items():
            file = self.path / f"phase3_{name}.csv"
            result = self.query(code)
            write_rows(file, result)
            payload = file.read_bytes()
            write_rows(file, result)
            self.assertEqual(payload, file.read_bytes())
        inputs = load_inputs(self.path)
        first = draw(inputs, self.path / "first")
        second = draw(inputs, self.path / "second")
        self.assertEqual(len(first), 10)
        for left, right in zip(first, second):
            self.assertEqual(left.read_bytes(), right.read_bytes())
        different = self.query(DAILY_SQL)
        different[0]["records"] += 1
        write_rows(self.path / "phase3_daily_traffic.csv", different)
        with self.assertRaisesRegex(ValueError, "Daily traffic total"):
            load_inputs(self.path)


if __name__ == "__main__":
    unittest.main()
