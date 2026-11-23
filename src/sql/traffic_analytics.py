"""Validated input and reusable SQL aggregations for Phase 3."""

from collections import Counter
import csv
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import time

from pyspark.sql import functions as F

from src.ingest.dataset_audit import atomic_json
from src.ingest.parquet_pipeline import parquet_footers
from src.ingest.schema_contract import FEATURE_CONTEXT, TARGETS


def identifier(name):
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        raise ValueError(f"Invalid configured SQL identifier {name!r}")
    return name


def locate_producer(input_root, expected_sha):
    relative = "mmds_phase2/evidence/validation_summary.json"
    root = Path(input_root)
    candidates = set(root.rglob(relative))
    for depth in (1, 2, 3, 4):
        candidates.update(root.glob("*/" * depth + relative))
    matched = {path.resolve(): path for path in sorted(candidates)
               if sha256(path.read_bytes()).hexdigest() == expected_sha}
    if len(matched) != 1:
        raise ValueError("Expected one mounted input matching the Phase 2 receipt")
    return next(iter(matched.values()))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def label_grouping(frame):
    return frame.groupBy("source_day", *TARGETS, "temporal_eligibility").count()


def compact(frame, maximum):
    rows = frame.limit(maximum + 1).collect()
    require(len(rows) <= maximum, "Aggregate exceeds compact output limit")
    def scalar(value):
        if isinstance(value, float):
            return value if math.isfinite(value) else None
        return value

    return [{k: scalar(v) for k, v in row.asDict().items()} for row in rows]


def validate_input(spark, receipt, manifest, policy):
    summary = json.loads(receipt.read_text())
    expected_sha = manifest["independent_mount"]["summary_sha256"]
    require(sha256(receipt.read_bytes()).hexdigest() == expected_sha, "Phase 2 receipt checksum differs")
    require(summary["status"] == "validated" and summary["dataset"] == manifest["dataset"], "Wrong producer dataset")
    require(summary["policy_version"] == manifest["policy_version"] == policy["version"], "Wrong cleaning policy")
    require(summary["totals"] == manifest["totals"], "Wrong producer totals")
    root = receipt.parent.parent / summary["policy_version"]
    frames = {}
    evidence = {}
    for name in ("feature_ready", "clean", "raw_aligned"):
        directory = root / name
        actual = parquet_footers(directory)
        expected = manifest["layers"][name]
        days = sorted(path.name.split("=", 1)[1] for path in directory.glob("source_day=*") if path.is_dir())
        require(all(expected[key] == value for key, value in actual.items()), f"{name} is unreadable or differs from manifest")
        require(len(days) == expected["partitions"] == 10, f"{name} partition count differs")
        require(days == sorted(row["source_day"] for row in summary["completed_files"]), f"{name} day list differs")
        frames[name] = spark.read.parquet(str(directory))
        evidence[name] = actual | {"path": str(directory), "partitions": len(days)}
    features, clean = frames["feature_ready"], frames["clean"]
    require(set(features.columns) == set(manifest["feature_columns"]) | set(FEATURE_CONTEXT) | set(TARGETS), "Feature schema differs")
    for frame in (features, clean):
        types = dict(frame.dtypes)
        require(all(types.get(name) == "double" for name in manifest["feature_columns"]), "Feature types differ")
        require(types.get("source_day") == "string" and types.get("binary_label") == "tinyint", "Target or partition type differs")
        require(types.get("record_fingerprint") == "binary" and types.get("temporal_eligibility") == "boolean", "Provenance types differ")
    require(dict(clean.dtypes).get("parsed_event_time") == "timestamp_ntz", "Wall-clock timestamp is unavailable")
    require({row[0] for row in clean.select("cleaning_policy_version").distinct().collect()} == {policy["version"]}, "Stored cleaning policy differs")
    clean_groups = compact(label_grouping(clean).orderBy("source_day", "original_label", "temporal_eligibility"), 500)
    feature_groups = compact(label_grouping(features).orderBy("source_day", "original_label", "temporal_eligibility"), 500)
    require(clean_groups == feature_groups, "Layer targets or temporal flags differ")
    expected_totals = summary["totals"]
    labels, day_counts = Counter(), Counter()
    ineligible = 0
    for row in clean_groups:
        label = policy["label_mapping"].get(row["original_label"])
        require(label is not None and (row["normalized_label"], row["binary_label"], row["attack_family"]) ==
                (label["normalized"], label["binary"], label["family"]), "Observed label mapping differs")
        require(row["temporal_eligibility"] in (True, False), "Null temporal flag")
        labels[row["binary_label"]] += row["count"]
        day_counts[row["source_day"]] += row["count"]
        if not row["temporal_eligibility"]:
            ineligible += row["count"]
    require(dict(labels) == {0: expected_totals["benign"], 1: expected_totals["attack"]}, "Binary counts differ")
    require(sum(labels.values()) == expected_totals["canonical_rows"] == 16232943 and ineligible == 14, "Row or temporal counts differ")
    require(dict(day_counts) == {row["source_day"]: row["counts"]["canonical_rows"] for row in summary["completed_files"]}, "Per-day counts differ")
    bad_time = clean.where(
        ~F.col("temporal_eligibility").eqNullSafe(
            F.col("parsed_event_time").isNotNull() & (F.to_date("parsed_event_time") == F.col("source_day").cast("date"))))
    require(bad_time.limit(1).count() == 0, "Temporal eligibility disagrees with stored event time")
    return frames, root, {
        "status": "validated", "dataset": summary["dataset"], "phase2_receipt_sha256": expected_sha,
        "policy_version": summary["policy_version"], "producer": manifest["producer"], "layers": evidence,
        "records": sum(labels.values()), "benign": labels[0], "attack": labels[1], "temporal_ineligible": ineligible,
        "source_days": sorted(day_counts), "features": manifest["feature_columns"],
    }


def finite(column):
    name = identifier(column)
    return f"CASE WHEN {name} IS NOT NULL AND NOT isnan({name}) AND abs({name}) < CAST('Infinity' AS DOUBLE) THEN {name} END"


def register_traffic(clean, metrics):
    """Project only the columns needed by exploratory queries."""
    selected = set(metrics) - {"total_packets", "total_bytes"}
    columns = ["source_day", *TARGETS, "temporal_eligibility", "parsed_event_time",
               *sorted(selected | {"protocol", "dst_port", "fin_flag_cnt"})]
    projected = (clean.select(*columns, "quality_issues")
                 .withColumn("quality_cells", F.size("quality_issues"))
                 .withColumn("invalid_cells", F.size(F.filter("quality_issues", lambda issue: issue["reason"] != "sentinel")))
                 .drop("quality_issues"))
    return (
        projected.withColumn("population", F.when(F.col("binary_label") == 0, "benign").otherwise("attack"))
        .withColumn("total_packets", F.col("tot_fwd_pkts") + F.col("tot_bwd_pkts"))
        .withColumn("total_bytes", F.col("totlen_fwd_pkts") + F.col("totlen_bwd_pkts"))
    )


DAILY_SQL = """SELECT source_day, count(*) AS records, count_if(binary_label = 0) AS benign,
 count_if(binary_label = 1) AS attacks, avg(CAST(binary_label AS DOUBLE)) AS attack_share,
 sum(total_packets) AS packet_count, sum(total_bytes) AS byte_count
 FROM traffic GROUP BY source_day ORDER BY source_day"""

TOTAL_SQL = """SELECT population, count(*) AS records, sum(total_packets) AS packet_count,
 sum(total_bytes) AS byte_count, count(total_packets) AS packet_observations,
 count(total_bytes) AS byte_observations FROM traffic GROUP BY population ORDER BY population"""

FAMILY_SQL = """SELECT attack_family, count(*) AS records, count(*) / sum(count(*)) OVER () AS share_of_attacks,
 count(DISTINCT source_day) AS capture_days,
 count_if(quality_cells > 0) AS quality_affected_rows, avg(CAST(quality_cells > 0 AS DOUBLE)) AS quality_affected_share,
 count_if(invalid_cells > 0) AS invalid_affected_rows, avg(CAST(invalid_cells > 0 AS DOUBLE)) AS invalid_affected_share
 FROM traffic WHERE binary_label = 1 GROUP BY attack_family ORDER BY records DESC, attack_family"""

LABEL_SQL = """SELECT attack_family, original_label, count(*) AS records, count(DISTINCT source_day) AS capture_days
 FROM traffic GROUP BY attack_family, original_label ORDER BY attack_family, original_label"""

PROTOCOL_SQL = """SELECT population, attack_family, protocol, count(*) AS records
 FROM traffic GROUP BY population, attack_family, protocol ORDER BY population, attack_family, protocol"""

PORT_SQL = """WITH grouped AS (
 SELECT population, coalesce(attack_family, 'All families') AS attack_family,
 CASE WHEN grouping(attack_family) = 1 THEN 'population' ELSE 'family' END AS scope,
 dst_port, count(*) AS records FROM traffic
 GROUP BY GROUPING SETS ((population, attack_family, dst_port), (population, dst_port))),
 ranked AS (SELECT *, row_number() OVER (PARTITION BY scope, population, attack_family ORDER BY records DESC, dst_port) AS rank,
 sum(records) OVER (PARTITION BY scope, population, attack_family) AS population_records FROM grouped)
 SELECT * FROM ranked WHERE rank <= {limit} ORDER BY scope, population, attack_family, rank"""

def feature_statistics_sql(features, group, accuracy):
    group = identifier(group)
    terms = []
    for feature in features:
        x = finite(feature)
        terms.append(
            f"named_struct('feature', '{feature}', 'valid', count({x}), 'population_count', count(*), "
            f"'mean', avg({x}), 'stddev', stddev_samp({x}), 'min', min({x}), 'max', max({x}), "
            f"'quantiles', percentile_approx({x}, array(0.1D, 0.5D, 0.9D, 0.99D), {int(accuracy)}))"
        )
    return (f"SELECT {group}, m.* FROM (SELECT {group}, explode(array({', '.join(terms)})) AS m "
            f"FROM traffic GROUP BY {group}) ORDER BY {group}, m.feature")


def missing_sql(features):
    terms = [
        f"named_struct('feature', '{name}', 'missing', count(*) - count({finite(name)}), 'records', count(*))"
        for name in features
    ]
    return f"SELECT m.* FROM (SELECT explode(array({', '.join(terms)})) AS m FROM features) ORDER BY m.feature"


def correlations_sql(pairs):
    terms = []
    for x, y in pairs:
        a, b = finite(x), finite(y)
        terms.append(
            f"named_struct('x', '{x}', 'y', '{y}', 'pairs', count_if(({a}) IS NOT NULL AND ({b}) IS NOT NULL), "
            f"'pearson', corr({a}, {b}))"
        )
    return (f"SELECT population, m.* FROM (SELECT population, explode(array({', '.join(terms)})) AS m "
            "FROM traffic GROUP BY population) ORDER BY population, m.x, m.y")


def write_rows(destination, rows):
    if not rows:
        raise ValueError(f"Unexpected empty result {destination.name}")
    stage = destination.with_suffix(".tmp")
    with stage.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows({key: json.dumps(value, separators=(",", ":")) if isinstance(value, (list, dict)) else value
                          for key, value in row.items()} for row in rows)
    stage.replace(destination)


def timed_sql(spark, query, limit, name, output, performance):
    started = time.monotonic()
    rows = compact(spark.sql(query), limit)
    seconds = round(time.monotonic() - started, 6)
    write_rows(output / f"phase3_{name}.csv", rows)
    performance.append({"workload": name, "api": "SQL", "iteration": 1, "seconds": seconds, "result_rows": len(rows)})
    print(f"PHASE3 query {name}: {len(rows)} result rows in {seconds:.3f} s", flush=True)
    return rows


def write_checkpoint(output, validation, completed, performance):
    atomic_json(output / "phase3_validation.json", validation | {"completed_queries": list(completed)})
    if performance:
        write_rows(output / "phase3_query_performance.csv", performance)
