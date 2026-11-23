"""Execute, reconcile and checkpoint the Phase 2 data layers."""

import argparse
from collections import Counter
import csv
import json
import os
from pathlib import Path
import shutil
import time

from pyspark import StorageLevel
from pyspark.sql import Observation, functions as F

from src.ingest.cleaning import apply_duplicate_policy, canonical_frame, clean_frame, conflict_groups, exact_groups, feature_frame
from src.ingest.dataset_audit import atomic_json, count_if, read_inventory, spark_session
from src.ingest.schema_contract import DataContract, SOURCE_COUNTS, reconcile_source, source_records
from src.sql.aggregation_demo import run_aggregation_demo


LAYERS = ("raw_aligned", "clean", "feature_ready")
KINDS = ("nan", "positive_infinity", "negative_infinity", "invalid_negative", "sentinel", "cast_failure", "source_null")


def canonical_metrics():
    issues = F.col("quality_issues")
    metrics = [
        F.count("*").alias("canonical_rows"),
        count_if(F.col("binary_label") == 0).alias("benign"),
        count_if(F.col("binary_label") == 1).alias("attack"),
        count_if(F.col("binary_label").isNull()).alias("unknown_labels"),
        count_if(F.col("timestamp_parse_status") == "outside_capture_day").alias("timestamp_outlier"),
        count_if(F.col("timestamp_parse_status") == "unparseable").alias("timestamp_unparseable"),
        count_if(F.col("timestamp_parse_status") == "missing").alias("timestamp_missing"),
        count_if(F.col("temporal_eligibility")).alias("temporal_eligible"),
        count_if(F.size(issues) > 0).alias("quality_affected_rows"),
        F.coalesce(F.sum(F.size(issues)), F.lit(0)).alias("quality_affected_cells"),
        count_if(F.size("structural_missing_fields") > 0).alias("structural_missing_rows"),
        F.coalesce(F.sum(F.size("structural_missing_fields")), F.lit(0)).alias("structural_missing_cells"),
    ]
    for reason in KINDS:
        selected = F.size(F.filter(issues, lambda issue: issue["reason"] == reason))
        metrics.extend([
            count_if(selected > 0).alias(reason + "_rows"),
            F.coalesce(F.sum(selected), F.lit(0)).alias(reason + "_cells"),
        ])
    return metrics


def parquet_footers(path):
    """Verify files and row counts via footer metadata only."""
    import pyarrow.parquet as parquet

    files = sorted(path.rglob("part-*.parquet"))
    if not files:
        raise ValueError(f"No Parquet data files under {path.name}")
    rows, size = 0, 0
    codecs = set()
    for file in files:
        metadata = parquet.read_metadata(file)
        rows += metadata.num_rows
        size += file.stat().st_size
        for group in range(metadata.num_row_groups):
            row_group = metadata.row_group(group)
            codecs.update(row_group.column(i).compression for i in range(row_group.num_columns))
    if codecs != {"SNAPPY"}:
        raise ValueError(f"Parquet compression mismatch in {path.name}: {sorted(codecs)}")
    return {"records": rows, "bytes": size, "files": len(files), "compression": "SNAPPY"}


def write_day(frame, path, number_of_files, expected_rows):
    started = time.monotonic()
    (frame.drop("source_day").coalesce(number_of_files).write.mode("overwrite")
     .option("compression", "snappy").parquet(str(path)))
    write_s = round(time.monotonic() - started, 3)
    observed = parquet_footers(path)
    if observed["records"] != expected_rows:
        raise ValueError(f"Parquet row-count mismatch at {path.name}")
    return observed | {"write_seconds": write_s}


def driver_peak_bytes(spark):
    pid = spark._jvm.java.lang.ProcessHandle.current().pid()
    status = Path(f"/proc/{pid}/status")
    if status.is_file():
        line = next((line for line in status.read_text().splitlines() if line.startswith("VmHWM:")), None)
        if line is not None:
            return int(line.split()[1]) * 1024
    return None


def process_capture(spark, root, stores, contract, source, formats):
    source_name, day = source["name"], source["capture_day"]
    path = root / source["path"]
    expected = source["counts"]
    start = time.monotonic()
    variant, frame = source_records(spark, contract, path, day)
    physical = Observation()
    measured = frame.observe(
        physical, F.count("*").alias("physical_lines"),
        *[count_if(F.col("kind") == name).alias(name) for name in SOURCE_COUNTS],
    )
    normalized = Observation()
    canonical = (canonical_frame(measured, contract, variant, source_name, day, formats)
                 .observe(normalized, *canonical_metrics()).persist(StorageLevel.DISK_ONLY))
    target = contract.policy["target_source_bytes_per_part"]
    parts = max(1, (source["bytes"] + target - 1) // target)
    try:
        materialized = canonical.count()
        parse_seconds = round(time.monotonic() - start, 3)
        reconciliation = reconcile_source(physical.get, expected)
        stats = normalized.get
        if stats["canonical_rows"] != expected["parsed"] or materialized != expected["parsed"]:
            raise ValueError("Canonical rows failed reconciliation")
        if stats["unknown_labels"] or stats["benign"] + stats["attack"] != materialized:
            raise ValueError(f"Unmapped labels in {source_name}: {stats['unknown_labels']}")
        if stats["timestamp_outlier"] + stats["timestamp_missing"] + stats["timestamp_unparseable"] + stats["temporal_eligible"] != materialized:
            raise ValueError("Canonical timestamp statuses failed reconciliation")
        raw_output = write_day(canonical, stores["raw_aligned"] / f"source_day={day}", parts, materialized)
        clean_output = write_day(clean_frame(canonical, contract), stores["clean"] / f"source_day={day}", parts, materialized)
    finally:
        canonical.unpersist(blocking=True)
    # The third layer is built from the persisted clean data.
    clean_path = stores["clean"] / f"source_day={day}"
    feature_source = spark.read.parquet(str(clean_path)).withColumn("source_day", F.lit(day))
    feature_output = write_day(feature_frame(feature_source, contract), stores["feature_ready"] / f"source_day={day}", parts, materialized)
    return {
        "source_file": source_name, "source_day": day, "schema_variant": variant,
        "source_bytes": source["bytes"], "expected_records": expected["parsed"],
        "expected_headers": expected["headers"], "read_transform_seconds": parse_seconds,
        "effective_read_mib_s": round(source["bytes"] / (1024 ** 2) / max(parse_seconds, 0.001), 3),
        "driver_peak_rss_bytes": driver_peak_bytes(spark),
        "counts": reconciliation | stats,
        "layers": dict(zip(LAYERS, (raw_output, clean_output, feature_output))),
    }


def reconcile_full(summary, expected):
    counts = summary["totals"]
    observed = {key: counts[key] for key in ("benign", "attack", "timestamp_outlier")}
    observed.update(nan=counts["nan_cells"], infinity=counts["positive_infinity_cells"] + counts["negative_infinity_cells"],
                    invalid_negative=counts["invalid_negative_cells"])
    if any(observed[key] != expected[key] for key in observed):
        raise ValueError(f"Phase 1 totals disagree: {observed}")
    if counts["canonical_rows"] != counts["parsed"] or any(counts["canonical_rows"] != summary["layers"][name]["records"] for name in LAYERS):
        raise ValueError("Layer totals do not reconcile")


def layer_summary(files, data_root):
    output = {}
    for name in LAYERS:
        metrics = [row["layers"][name] for row in files]
        output[name] = {
            "path": (data_root / name).as_posix(), "partition_column": "source_day",
            "partitions": len(metrics), "format": "parquet", "compression": "SNAPPY",
            **{key: sum(item[key] for item in metrics) for key in ("records", "bytes", "files")},
            "write_seconds": round(sum(item["write_seconds"] for item in metrics), 3),
        }
    return output


def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_evidence(evidence, summary, policy):
    atomic_json(evidence / "validation_summary.json", summary)
    atomic_json(evidence / "parquet_layers.json", {
        key: summary[key] for key in ("status", "dataset", "policy_version", "layers", "duplicate_policy", "duplicate_diagnostics")
        if key in summary
    })
    captured = summary["completed_files"]
    counts = [{
        "source_file": item["source_file"], "source_day": item["source_day"],
        "expected_records": item["expected_records"], "observed_records": item["counts"]["parsed"],
        "physical_lines": item["counts"]["physical_lines"], "expected_headers": item["expected_headers"],
        "headers": item["counts"]["headers"], "repeated_headers": item["counts"]["repeated_headers"],
        "canonical": item["counts"]["canonical_rows"], "clean": item["layers"]["clean"]["records"],
        "feature_ready": item["layers"]["feature_ready"]["records"], "benign": item["counts"]["benign"],
        "attack": item["counts"]["attack"], "timestamp_outlier": item["counts"]["timestamp_outlier"],
    } for item in captured]
    timing = [{
        "source_file": item["source_file"], "source_bytes": item["source_bytes"],
        "read_transform_seconds": item["read_transform_seconds"], "effective_read_mib_s": item["effective_read_mib_s"],
        "driver_peak_rss_bytes": item["driver_peak_rss_bytes"],
        **{name + "_write_seconds": item["layers"][name]["write_seconds"] for name in LAYERS},
    } for item in captured]
    quality = [{
        "source_file": item["source_file"], "reason": reason,
        "affected_rows": item["counts"][reason + "_rows"], "affected_cells": item["counts"][reason + "_cells"],
        "action": policy["numeric_actions"].get(reason, "structural_null" if reason == "structural_missing" else "all_quality_issues"),
    } for item in captured for reason in (*KINDS, "structural_missing", "quality_affected")]
    if counts:
        write_csv(evidence / "phase2_count_reconciliation.csv", counts, list(counts[0]))
        write_csv(evidence / "phase2_performance.csv", timing, list(timing[0]))
        write_csv(evidence / "phase2_quality_actions.csv", quality, list(quality[0]))


def run_duplicate_mode(spark, stores, policy, data_root, expected_excess):
    mode = policy["duplicate_policy"]
    if mode == "preserve_all":
        return {"records_removed_primary": 0}
    if mode not in {"diagnostic", "exact_representative"}:
        raise ValueError(f"Unknown duplicate policy {mode}")
    started = time.monotonic()
    folder = data_root / "diagnostics"
    folder.mkdir(exist_ok=True)
    aligned = spark.read.parquet(str(stores["raw_aligned"])).select("record_fingerprint", "source_file")
    keys = folder / "exact_groups"
    exact_groups(aligned).write.mode("overwrite").option("compression", "snappy").parquet(str(keys))
    exact = spark.read.parquet(str(keys)).agg(F.count("*").alias("groups"),
                                              F.coalesce(F.sum(F.col("multiplicity") - 1), F.lit(0)).alias("excess")).first().asDict()
    if expected_excess is not None and exact["excess"] != expected_excess:
        raise ValueError("Exact raw-line duplicate excess differs from Phase 1")
    features = spark.read.parquet(str(stores["feature_ready"])).select("split_feature_key", "original_label")
    conflicts_path = folder / "label_conflicts"
    conflict_groups(features).write.mode("overwrite").option("compression", "snappy").parquet(str(conflicts_path))
    conflicts = spark.read.parquet(str(conflicts_path)).agg(F.count("*").alias("groups"),
        F.coalesce(F.sum("rows"), F.lit(0)).alias("participating_rows")).first().asDict()
    result = {"records_removed_primary": 0, "exact": exact, "cleaned_feature_conflicts": conflicts,
              "diagnostics_path": folder.as_posix()}
    if mode == "exact_representative":
        clean = spark.read.parquet(str(stores["clean"]))
        target = data_root / "exact_representatives"
        (apply_duplicate_policy(clean, mode).write.mode("overwrite").option("compression", "snappy")
         .partitionBy("source_day").parquet(str(target)))
        measured = parquet_footers(target)
        if measured["records"] != sum(parquet_footers(p)["records"] for p in stores["clean"].glob("source_day=*")) - exact["excess"]:
            raise ValueError("Representative output failed multiplicity reconciliation")
        result["representatives"] = measured | {"path": target.as_posix()}
    return result | {"seconds": round(time.monotonic() - started, 3)}


def resource_limits(spark, policy, path):
    metrics = {"spark_version": spark.version, **policy["spark"], "default_parallelism": spark.sparkContext.defaultParallelism,
               "cpu_affinity": len(os.sched_getaffinity(0)), "scratch_output_free_bytes_start": shutil.disk_usage(path).free}
    for name in ("memory.max", "cpu.max"):
        resource = Path("/sys/fs/cgroup") / name
        if resource.exists():
            metrics[name] = resource.read_text().strip()
    return metrics


def run_pipeline(contract, source_config, phase1, root, output, scratch, only_days=None):
    root, output, scratch = map(Path, (root, output, scratch))
    if not root.is_dir() or any(p.resolve().is_relative_to(root.resolve()) for p in (output, scratch)):
        raise ValueError("The verified mount and writable outputs must be separate")
    output.mkdir(parents=True, exist_ok=True)
    scratch.mkdir(parents=True, exist_ok=True)
    actual = read_inventory(root, source_config)
    audited = {row["path"]: row for row in phase1["files"]}
    if len(actual) != len(audited) or any(
        row["path"] not in audited or row["bytes"] != audited[row["path"]]["bytes"]
        or row["access"] != "readable" or row["unexpected"] or row["duplicate_basename"] for row in actual
    ):
        raise ValueError("Mounted inventory differs from Phase 1")
    policy = contract.policy
    data_root = output / policy["version"]
    stores = {name: data_root / name for name in LAYERS}
    evidence = output / "evidence"
    evidence.mkdir(exist_ok=True)
    spark = spark_session({"spark": policy["spark"]}, scratch)
    spark.conf.set("spark.sql.sources.partitionColumnTypeInference.enabled", "false")
    spark.sparkContext.setLogLevel("WARN")
    summary = {
        "status": "running", "dataset": phase1["dataset"], "policy_version": policy["version"],
        "duplicate_policy": policy["duplicate_policy"], "expected_files": len(audited),
        "resources": resource_limits(spark, policy, output), "completed_files": [], "failures": [],
        "phase1_conflict_groups": 22129,
    }
    started = time.monotonic()
    totals = Counter()
    try:
        sources = sorted(audited.values(), key=lambda file: file["bytes"])
        for source in sources:
            day = source["capture_day"]
            if only_days is not None and day not in only_days:
                continue
            try:
                marker = evidence / f"capture-{day}.json"
                if marker.is_file():
                    result = json.loads(marker.read_text())
                    for name in LAYERS:
                        metrics = parquet_footers(stores[name] / f"source_day={day}")
                        if any(result["layers"][name][key] != value for key, value in metrics.items()):
                            raise ValueError("Existing checkpoint no longer matches its data files")
                else:
                    print(f"PHASE2 start {day} {source['bytes']} bytes", flush=True)
                    result = process_capture(spark, root, stores, contract, source, source_config["timestamp_formats"])
                    atomic_json(marker, result)
                summary["completed_files"].append(result)
                totals.update(result["counts"])
                print(f"PHASE2 completed {day} {result['counts']['canonical_rows']} rows "
                      f"in {result['read_transform_seconds']} s read and transform", flush=True)
            except Exception as error:
                summary["failures"].append({"source_day": day, "stage": "capture", "type": type(error).__name__})
                print(f"PHASE2 failed {day}: {type(error).__name__}: {str(error)[:1000]}", flush=True)
            summary.update(totals=dict(totals), layers=layer_summary(summary["completed_files"], data_root))
            write_evidence(evidence, summary, policy)
        full = len(summary["completed_files"]) == len(sources)
        if full:
            reconcile_full(summary, policy["expected_full"])
            stored = stores["feature_ready"] / f"source_day={sources[0]['capture_day']}"
            summary["aggregation_demo"] = run_aggregation_demo(spark.read.parquet(str(stored)))
            summary["duplicate_diagnostics"] = run_duplicate_mode(
                spark, stores, policy, data_root, policy["expected_full"]["duplicate_excess"])
        summary["status"] = "validated" if full else "partial"
    except Exception as error:
        summary["status"] = "partial"
        summary["failures"].append({"stage": "global_validation", "type": type(error).__name__})
        print(f"PHASE2 validation failed: {type(error).__name__}: {str(error)[:1000]}", flush=True)
    finally:
        summary["elapsed_seconds"] = round(time.monotonic() - started, 3)
        summary["resources"]["driver_peak_rss_bytes"] = driver_peak_bytes(spark)
        write_evidence(evidence, summary, policy)
        print(f"PHASE2 final {summary['status']} in {summary['elapsed_seconds']} seconds", flush=True)
        # Persist compact evidence in logs as well as the notebook output.
        print("PHASE2_EVIDENCE " + json.dumps(summary, separators=(",", ":")), flush=True)
        spark.stop()
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--day", action="append")
    args = parser.parse_args()
    contract = DataContract.load("configs/cleaning.yaml")
    load = lambda path: json.loads(Path(path).read_text())
    summary = run_pipeline(contract, load("configs/dataset.yaml"), load("manifests/dataset_inventory.json"),
                           args.root, args.output, args.scratch, args.day)
    raise SystemExit(0 if summary["status"] == "validated" else 1)


if __name__ == "__main__":
    main()
