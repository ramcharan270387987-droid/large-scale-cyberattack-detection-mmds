"""Run the Phase 3 notebook stages against the verified Phase 2 output."""

import json
from pathlib import Path
import time

from pyspark import StorageLevel

from src.ingest.dataset_audit import atomic_json, spark_session
from src.ingest.parquet_pipeline import driver_peak_bytes, resource_limits
from src.sql.aggregation_demo import run_aggregation_demo
from src.sql.attack_patterns import FLAGS_SQL, benign_thresholds_sql, patterns_sql, sensitivity_sql
from src.sql.query_benchmarks import compare_workload
from src.sql.temporal_analytics import FAMILY_DAY_SQL, HOURLY_SQL, WINDOW_SQL
from src.sql.traffic_analytics import (
    DAILY_SQL, FAMILY_SQL, LABEL_SQL, PORT_SQL, PROTOCOL_SQL, TOTAL_SQL, correlations_sql,
    feature_statistics_sql, locate_producer, missing_sql, register_traffic, require, timed_sql,
    validate_input, write_checkpoint, write_rows,
)
from src.visualization.eda_charts import draw, load_inputs


def read(path):
    return json.loads(path.read_text())


def verify_aggregates(data, expected):
    total = expected["records"]
    require(sum(row["records"] for row in data["daily_traffic"]) == total, "Capture-day counts do not reconcile")
    require({row["population"]: row["records"] for row in data["traffic_totals"]} ==
            {"benign": expected["benign"], "attack": expected["attack"]}, "Binary counts do not reconcile")
    require(sum(row["records"] for row in data["attack_families"]) == expected["attack"], "Attack-family counts do not reconcile")
    require(sum(row["records"] for row in data["original_labels"]) == total, "Original-label counts do not reconcile")
    require(sum(row["records"] for row in data["family_by_day"]) == expected["attack"], "Family-day counts do not reconcile")
    eligible = total - expected["temporal_ineligible"]
    require(sum(row["records"] for row in data["hourly_traffic"]) == eligible, "Hourly counts do not reconcile")
    require(sum(row["records"] for row in data["time_windows"]) == eligible, "Time-window counts do not reconcile")


def run(project, input_root, output, scratch):
    output.mkdir(parents=True, exist_ok=True)
    scratch.mkdir(parents=True, exist_ok=True)
    config = read(project / "configs/analytics.yaml")
    manifest = read(project / "manifests/parquet_layers.json")
    policy = read(project / "configs/cleaning.yaml")
    spark = spark_session(config, scratch)
    spark.conf.set("spark.sql.sources.partitionColumnTypeInference.enabled", "false")
    spark.sparkContext.setLogLevel("WARN")
    started = time.monotonic()
    view = None
    timings, data = [], {}
    try:
        receipt = locate_producer(input_root, manifest["independent_mount"]["summary_sha256"])
        frames, root, validation = validate_input(spark, receipt, manifest, policy)
        validation.update(status="running", records_ready=True, validation_seconds=round(time.monotonic() - started, 3),
                          resources=resource_limits(spark, config, output))
        write_checkpoint(output, validation, [], [])
        print(f"PHASE3 validated input: {validation['records']} rows, {len(validation['source_days'])} days", flush=True)
        clean, features = frames["clean"], frames["feature_ready"]
        for name, frame in frames.items():
            frame.createOrReplaceTempView(name)
        features.createOrReplaceTempView("features")
        view = register_traffic(clean, config["flow_statistics"]).persist(StorageLevel.DISK_ONLY)
        view.createOrReplaceTempView("traffic")
        settings = config["quantile_accuracy"]
        metrics = config["flow_statistics"]
        queries = [
            ("traffic_totals", TOTAL_SQL), ("daily_traffic", DAILY_SQL),
            ("attack_families", FAMILY_SQL), ("original_labels", LABEL_SQL),
            ("protocols", PROTOCOL_SQL), ("destination_ports", PORT_SQL.format(limit=config["top_ports"])),
            ("family_by_day", FAMILY_DAY_SQL), ("hourly_traffic", HOURLY_SQL),
            ("time_windows", WINDOW_SQL.format(accuracy=settings)),
            ("feature_statistics", feature_statistics_sql(metrics, "population", settings)),
            ("family_feature_statistics", feature_statistics_sql(metrics, "attack_family", settings)),
            ("feature_missingness", missing_sql(manifest["feature_columns"])),
            ("correlations", correlations_sql(config["correlations"])), ("tcp_flags", FLAGS_SQL),
            ("raw_sensitivity", sensitivity_sql("raw_aligned")), ("clean_sensitivity", sensitivity_sql("clean")),
            ("reference_thresholds", benign_thresholds_sql(settings)),
        ]

        def execute(name, query):
            data[name] = timed_sql(spark, query, config["max_compact_rows"], name, output, timings)
            write_checkpoint(output, validation, data, timings)

        for name, query in queries:
            execute(name, query)
        execute("candidate_patterns", patterns_sql(data["reference_thresholds"][0]))
        for table in ("exact_groups", "label_conflicts"):
            spark.read.parquet(str(root / "diagnostics" / table)).createOrReplaceTempView(table)
        execute("duplicate_quality", """SELECT
 (SELECT count(*) FROM exact_groups) AS exact_groups,
 (SELECT sum(multiplicity - 1) FROM exact_groups) AS excess_copies,
 (SELECT sum(multiplicity) FROM exact_groups) AS rows_in_exact_groups,
 (SELECT count(*) FROM label_conflicts) AS feature_label_conflict_groups,
 (SELECT sum(rows) FROM label_conflicts) AS rows_in_feature_label_conflicts,
 (SELECT count(*) FROM traffic WHERE NOT temporal_eligibility) AS temporal_ineligible""")
        quality = data["duplicate_quality"][0]
        production = manifest["duplicate_diagnostics"]
        require(quality["excess_copies"] == production["exact"]["excess"], "Duplicate diagnostics differ")
        require(quality["feature_label_conflict_groups"] == production["cleaned_feature_conflicts"]["groups"], "Conflict diagnostics differ")
        require(quality["rows_in_feature_label_conflicts"] == production["cleaned_feature_conflicts"]["participating_rows"], "Conflict rows differ")
        require(quality["temporal_ineligible"] == validation["temporal_ineligible"], "Timestamp anomaly count differs")
        verify_aggregates(data, validation)
        validation["duplicate_aware_records"] = validation["records"] - quality["excess_copies"]
        benchmark, plans, counts = compare_workload(view.select("source_day", "binary_label"), config["benchmark_repeats"])
        require(sum(row["records"] for row in counts) == validation["records"], "Benchmark skipped records")
        timings.extend(benchmark)
        rdd = run_aggregation_demo(features.where("source_day = '2018-03-01'"))
        atomic_json(output / "phase3_execution_plans.json", {"day_label_benchmark": plans, "bounded_rdd": rdd})
        figures = draw(load_inputs(output), output / "figures")
        validation.update(status="validated", elapsed_seconds=round(time.monotonic() - started, 3),
                          figures=[item.name for item in figures], rdd_sample_rows=rdd["rows"],
                          benchmark_repeats=config["benchmark_repeats"], quantile_accuracy=settings)
        validation["resources"]["driver_peak_rss_bytes"] = driver_peak_bytes(spark)
        write_checkpoint(output, validation, data, timings)
        print(f"PHASE3 complete: {len(data)} queries, {len(figures)} charts; {validation['elapsed_seconds']} s", flush=True)
    finally:
        if view is not None:
            view.unpersist(blocking=True)
        spark.stop()
