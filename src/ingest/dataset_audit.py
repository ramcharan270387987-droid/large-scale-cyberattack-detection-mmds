"""Measure the MMDS source without changing or exporting traffic records."""

import argparse
from collections import Counter
import csv
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import time
import unicodedata


LABEL_NAMES = {"label", "traffic_label", "class", "attack_type"}
TIME_NAMES = {"timestamp", "time_stamp", "flow_timestamp"}
IDENTIFIER_NAMES = {"flow_id", "src_ip", "dst_ip", "source_ip", "destination_ip"}
NONNEGATIVE = re.compile(r"duration|length|(?:^|_)len(?:_|$)|pkts?|packets?|bytes?|byts?|count|(?:^|_)iat(?:_|$)|flags?|active|idle|(?:^|_)rate(?:_|$)|(?:^|_)ps$")
SENTINELS = {"infinity", "+infinity", "-infinity", "inf", "+inf", "-inf"}
BENIGN = "BENIGN"
# The quantized comparison is limited to these non-identity flow measurements.
NEAR_FIELDS = {
    "flow_duration", "tot_fwd_pkts", "tot_bwd_pkts",
    "totlen_fwd_pkts", "totlen_bwd_pkts", "flow_iat_mean",
}


def normalize_column(value):
    value = unicodedata.normalize("NFKC", value).lstrip("\ufeff").strip().casefold()
    return re.sub(r"[^\w]+", "_", value, flags=re.UNICODE).strip("_")


def normalize_label(value):
    return " ".join(unicodedata.normalize("NFKC", value).split()).casefold() if value is not None else None


def proposed_binary(value):
    """Only BENIGN has a default mapping; observed attack families need review."""
    return "benign" if normalize_label(value) == BENIGN.casefold() else "unmapped"


def capture_day(name):
    match = re.search(r"-(\d{2}-\d{2}-\d{4})_", name)
    return datetime.strptime(match.group(1), "%d-%m-%Y").date().isoformat() if match else None


def inspect_schema(header):
    names = [normalize_column(col) for col in header]
    original_counts = Counter(header)
    normalized_counts = Counter(names)
    return {
        "original": header,
        "normalized": names,
        "exact_duplicates": sorted(k for k, n in original_counts.items() if n > 1),
        "normalized_duplicates": sorted(k for k, n in normalized_counts.items() if n > 1),
        "whitespace_columns": [i for i, raw in enumerate(header) if raw != raw.strip()],
        "encoding_columns": [i for i, raw in enumerate(header) if any(ord(c) > 127 for c in raw)],
        "unsupported_indices": [i for i, name in enumerate(names) if not name or normalized_counts[name] > 1],
        "label_indices": [i for i, name in enumerate(names) if name in LABEL_NAMES],
        "timestamp_indices": [i for i, name in enumerate(names) if name in TIME_NAMES],
    }


def compare_schema(reference, candidate):
    left, right = reference["normalized"], candidate["normalized"]
    return {
        "same_order": left == right,
        "same_original_header": reference["original"] == candidate["original"],
        "missing": list((Counter(left) - Counter(right)).elements()),
        "extra": list((Counter(right) - Counter(left)).elements()),
        "compatible": Counter(left) == Counter(right)
        and not reference["unsupported_indices"] and not candidate["unsupported_indices"],
    }


def read_inventory(root, config):
    root = Path(root)
    expected = {f'{config["directory"]}/{name}': size for name, size in config["files"].items()}
    available = {p.relative_to(root).as_posix(): p for p in root.rglob("*") if p.is_file()}
    names = Counter(path.rsplit("/", 1)[-1] for path in available)
    items = []
    for rel in sorted(expected.keys() | available.keys()):
        path = available.get(rel)
        name = rel.rsplit("/", 1)[-1]
        size = None
        access = "missing"
        if path is not None:
            try:
                size = path.stat().st_size
                with path.open("rb") as source:
                    source.read(1)
                access = "readable"
            except OSError:
                access = "unreadable"
        items.append({
            "path": rel, "name": name, "capture_day": capture_day(name) if rel in expected else None,
            "bytes": size, "expected_bytes": expected.get(rel), "access": access,
            "unexpected": rel not in expected, "duplicate_basename": names[name] > 1,
            "size_matches": size == expected[rel] if rel in expected else None,
        })
    return items


def counts_reconcile(counts, labels=None):
    return (
        counts["physical_lines"] == sum(counts[key] for key in ("blank", "headers", "malformed", "parsed"))
        and counts["malformed"] == sum(counts[key] for key in ("bad_width_or_quotes", "spark_corrupt"))
        and counts["data_records"] == counts["parsed"] + counts["malformed"]
        and (labels is None or sum(row["count"] for row in labels) == counts["parsed"])
    )


def stable_sample(raw, seed, modulus):
    from pyspark.sql import functions as F

    return F.pmod(F.xxhash64(F.lit(seed), raw), F.lit(modulus)) == 0


def timestamp_columns(raw, formats):
    from pyspark.sql import functions as F

    value = F.trim(raw)
    primary_options = [F.try_to_timestamp(value, F.lit(fmt)) for fmt in formats]
    shadow_options = [
        F.try_to_timestamp(value, F.lit(fmt.replace("d/M/yyyy", "M/d/yyyy")))
        for fmt in formats if fmt.startswith("d/M/yyyy")
    ]
    primary = F.coalesce(*primary_options)
    shadow = F.coalesce(*shadow_options)
    matched = F.coalesce(*[F.when(expr.isNotNull(), F.lit(fmt)) for fmt, expr in zip(formats, primary_options)])
    return primary, shadow, matched


def numeric_fields(value):
    from pyspark.sql import functions as F

    stripped = F.trim(value)
    present = value.isNotNull() & (stripped != "")
    number = stripped.try_cast("double")
    nan = present & F.isnan(number)
    inf = present & (
        F.lower(stripped).isin(*sorted(SENTINELS)) | F.coalesce(F.abs(number) == float("inf"), F.lit(False))
    )
    finite = present & number.isNotNull() & ~nan & ~inf
    failed = present & number.isNull() & ~inf
    return present, number, nan, inf, finite, failed


def atomic_json(path, value):
    stage = path.with_suffix(".tmp")
    stage.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    stage.replace(path)


def spark_session(config, scratch):
    from pyspark.sql import SparkSession

    spark_config = config["spark"]
    os.environ.setdefault("SPARK_LOCAL_IP", "127.0.0.1")
    return (
        SparkSession.builder.appName("mmds-phase-1-dataset-audit")
        .master(spark_config["master"])
        .config("spark.driver.memory", spark_config["driver_memory"])
        .config("spark.local.dir", str(scratch))
        .config("spark.sql.shuffle.partitions", spark_config["shuffle_partitions"])
        .config("spark.sql.files.maxPartitionBytes", spark_config["input_partition_bytes"])
        .config("spark.sql.files.openCostInBytes", 4194304)
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.timestampType", "TIMESTAMP_NTZ")
        .config("spark.sql.legacy.timeParserPolicy", "CORRECTED")
        .config("spark.sql.csv.parser.columnPruning.enabled", "false")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )


def record_frame(spark, path, header_line, width):
    from pyspark.sql import functions as F

    raw = F.col("raw")
    blank = raw.rlike(r"^\s*$")
    header = raw == header_line
    comma_width = F.length(raw) - F.length(F.replace(raw, F.lit(","), F.lit(""))) + 1
    quoted = F.instr(raw, '"') > 0
    field = r'(?:"(?:[^"]|"")*"|[^",]*)'
    quote_grammar = "^" + field + "(?:," + field + ")*$"
    masked = F.regexp_replace(raw, r'"(?:[^"]|"")*"', '""')
    quoted_width = F.length(masked) - F.length(F.replace(masked, F.lit(","), F.lit(""))) + 1
    valid = F.when(quoted, raw.rlike(quote_grammar) & (quoted_width == width)).otherwise(comma_width == width)
    status = F.when(blank, "blank").when(header, "headers").when(~valid, "bad_width_or_quotes")
    ddl = ", ".join([f"c{i} STRING" for i in range(width)] + ["_corrupt STRING"])
    options = {
        "mode": "PERMISSIVE", "columnNameOfCorruptRecord": "_corrupt",
        "quote": '"', "escape": '"', "nullValue": "\u0000", "ignoreLeadingWhiteSpace": "false",
        "ignoreTrailingWhiteSpace": "false", "unescapedQuoteHandling": "RAISE_ERROR",
    }
    physical = spark.read.text(str(path)).toDF("raw")
    parsed = physical.withColumn("csv", F.when(status.isNull(), F.from_csv(raw, ddl, options)))
    kind = F.coalesce(status, F.when(F.col("csv._corrupt").isNotNull(), "spark_corrupt"), F.lit("parsed"))
    return parsed.select("raw", kind.alias("kind"), *[F.col(f"csv.c{i}").alias(f"c{i}") for i in range(width)])


def count_records(frame):
    counts = {row["kind"]: row["count"] for row in frame.groupBy("kind").count().collect()}
    summary = {k: counts.get(k, 0) for k in ("blank", "headers", "bad_width_or_quotes", "spark_corrupt", "parsed")}
    summary["malformed"] = summary["bad_width_or_quotes"] + summary["spark_corrupt"]
    summary["data_records"] = summary["parsed"] + summary["malformed"]
    summary["physical_lines"] = summary["data_records"] + summary["headers"] + summary["blank"]
    summary["repeated_header_lines"] = max(0, summary["headers"] - 1)
    return summary


def count_if(condition):
    from pyspark.sql import functions as F

    return F.count(F.when(condition, 1))


def profile_columns(frame, schema, config):
    from pyspark.sql import functions as F

    sampled = frame.where(stable_sample(F.col("raw"), config["sample_seed"], config["sample_modulus"]))
    sample_count = sampled.count()
    # Exact value counts within the small sample; collect only a row per column.
    elements = [
        F.struct(F.lit(i).alias("index"), F.col(f"c{i}").alias("value"))
        for i in range(len(schema["original"]))
    ]
    sample_summary = (
        sampled.select(F.explode(F.array(*elements)).alias("cell")).select("cell.*")
        .where(F.col("value").isNotNull() & (F.trim("value") != ""))
        .groupBy("index", "value").count()
        .groupBy("index").agg(F.sum("count").alias("present"), F.max("count").alias("dominant"))
    )
    sample_counts = {row["index"]: (row["present"], row["dominant"]) for row in sample_summary.collect()}
    profiles = []
    # Limit the size of each aggregate projection and reuse the on-disk parse.
    for start in range(0, len(schema["original"]), 24):
        full = []
        stop = min(start + 24, len(schema["original"]))
        for i in range(start, stop):
            col = F.col(f"c{i}")
            present, number, nan, inf, finite, failed = numeric_fields(col)
            measures = {
                "null": count_if(col.isNull()), "empty_or_whitespace": count_if(col.isNotNull() & (F.trim(col) == "")),
                "present": count_if(present), "finite_numeric": count_if(finite),
                "nan": count_if(nan), "infinite": count_if(inf), "numeric_conversion_failures": count_if(failed),
                "negative": count_if(finite & (number < 0)),
                "lexical_min": F.min(F.when(present, col)), "lexical_max": F.max(F.when(present, col)),
            }
            full.extend(expr.alias(f"c{i}_{key}") for key, expr in measures.items())
        full_result = frame.agg(*full).first().asDict()
        for i in range(start, stop):
            prefix = f"c{i}_"
            row = {key[len(prefix):]: value for key, value in full_result.items() if key.startswith(prefix)}
            low, high = row.pop("lexical_min"), row.pop("lexical_max")
            row["constant_nonempty"] = low == high if row["present"] else None
            row["sample_present"], top_count = sample_counts.get(i, (0, 0))
            row["sample_dominant_count"] = top_count
            row["sample_dominant_fraction"] = top_count / row["sample_present"] if row["sample_present"] else None
            row["near_constant_sample"] = row["sample_dominant_fraction"] >= 0.99 if row["sample_present"] else None
            name = schema["normalized"][i]
            support = row["finite_numeric"] + row["nan"] + row["infinite"]
            identifier = name in IDENTIFIER_NAMES
            numeric = support > 0 and support / row["present"] >= 0.95
            row["type_candidate"] = (
                "label" if i in schema["label_indices"] else "timestamp" if i in schema["timestamp_indices"]
                else "unsupported" if i in schema["unsupported_indices"]
                else "identifier" if identifier else "categorical" if name in {"protocol", "protocol_number"}
                else "numeric" if numeric else "categorical" if row["present"] else "unobserved"
            )
            row["invalid_negative"] = (
                row["negative"] if numeric and NONNEGATIVE.search(name) and not name.startswith("init_") else None
            )
            if row["type_candidate"] != "numeric":
                row["numeric_conversion_failures"] = None
            profiles.append(dict(row, index=i, original=schema["original"][i], normalized=name, sample_rows=sample_count))
    return profiles


def summarize_time(frame, schema, formats, day):
    from pyspark.sql import functions as F

    results = []
    for i in schema["timestamp_indices"]:
        raw = F.col(f"c{i}")
        primary, shadow, matched = timestamp_columns(raw, formats)
        stamped = frame.select(raw.alias("source"), primary.alias("parsed"), shadow.alias("shadow"), matched.alias("format"))
        parsed, shadow, source = F.col("parsed"), F.col("shadow"), F.col("source")
        present = source.isNotNull() & (F.trim(source) != "")
        date = F.to_date(parsed)
        aggregates = stamped.agg(
            F.count("*").alias("rows"), count_if(~present).alias("missing"), count_if(present & parsed.isNull()).alias("invalid"),
            count_if(parsed.isNotNull()).alias("parsed"), F.min(parsed).alias("earliest"), F.max(parsed).alias("latest"),
            count_if(shadow.isNotNull() & parsed.isNull()).alias("mdy_only"),
            count_if(shadow.isNotNull() & parsed.isNotNull() & (F.to_date(shadow) != date)).alias("ambiguous"),
            count_if(date == F.lit(day)).alias("date_matches"),
            count_if(date.isNotNull() & (date != F.lit(day))).alias("date_mismatches"),
            count_if(F.to_date(shadow) == F.lit(day)).alias("mdy_date_matches"),
        ).first().asDict()
        dates = [row.asDict() for row in stamped.where(parsed.isNotNull()).groupBy(date.alias("date"), "format").count().limit(501).collect()]
        if len(dates) <= 500:
            aggregates["date_formats"] = sorted(dates, key=lambda row: (row["date"], row["format"]))
        results.append(dict(aggregates, index=i, original=schema["original"][i]))
    return results


def fingerprint_frame(frame, schema, path, config):
    from pyspark.sql import functions as F

    label = schema["label_indices"]
    if len(label) != 1:
        return None
    columns = sorted(
        (name, i) for i, name in enumerate(schema["normalized"])
        if name not in LABEL_NAMES | TIME_NAMES | IDENTIFIER_NAMES and i not in schema["unsupported_indices"]
    )
    schema_key = hashlib.sha256(json.dumps([name for name, _ in columns]).encode()).hexdigest()[:16]
    selected = [(name, i) for name, i in columns if name in NEAR_FIELDS]
    raw = F.col("raw")
    near = F.lit(None).cast("string")
    if len(selected) >= 3:
        buckets = [F.floor(F.col(f"c{i}").try_cast("double") / (1000 if "duration" in name or "iat" in name else 10))
                   for name, i in selected]
        complete = F.lit(True)
        for bucket in buckets:
            complete = complete & bucket.isNotNull()
        near = F.when(stable_sample(raw, config["sample_seed"], config["sample_modulus"]) & complete,
                      F.sha2(F.to_json(F.array(*buckets)), 256))
    return frame.select(
        F.sha2(raw, 256).alias("row_hash"),
        F.sha2(F.to_json(F.array(*[F.col(f"c{i}") for _, i in columns])), 256).alias("feature_hash"),
        F.col(f"c{label[0]}").alias("label"), near.alias("near_hash"),
        F.lit(schema_key).alias("schema_key"), F.lit(path).alias("source"),
    )


def summarize_fingerprints(spark, paths):
    from pyspark.sql import functions as F

    rows = spark.read.parquet(*[str(path) for path in paths])
    duplicate_groups = rows.groupBy("row_hash").count().where(F.col("count") > 1)
    duplicates = duplicate_groups.agg(F.count("*").alias("groups"), F.sum(F.col("count") - 1).alias("excess")).first().asDict()
    known = rows.where(F.col("label").isNotNull() & (F.trim(F.col("label")) != ""))
    conflicts = (known.groupBy("schema_key", "feature_hash")
                 .agg(F.min("label").alias("first"), F.max("label").alias("last"), F.count("*").alias("rows"))
                 .where(F.col("first") != F.col("last"))
                 .agg(F.count("*").alias("groups"), F.sum("rows").alias("rows")).first().asDict())
    near_sample = rows.where(F.col("near_hash").isNotNull())
    near = (near_sample.groupBy("schema_key", "near_hash")
            .agg(F.min("feature_hash").alias("first"), F.max("feature_hash").alias("last"), F.count("*").alias("rows"))
            .where(F.col("first") != F.col("last"))
            .agg(F.count("*").alias("groups"), F.sum("rows").alias("rows")).first().asDict())
    near["eligible_sample_rows"] = near_sample.count()
    return {
        "raw_line_duplicates_sha256": {key: value or 0 for key, value in duplicates.items()},
        "label_conflicting_features_sha256": {key: value or 0 for key, value in conflicts.items()},
        "near_sample_buckets": {key: value or 0 for key, value in near.items()},
    }


def exact_duplicate_summary(spark, root, inventory):
    """Group full parsed string arrays within identical original headers."""
    from pyspark.sql import functions as F

    schemas = {}
    complete = []
    for item in inventory:
        if item["unexpected"] or item["access"] != "readable" or not item["size_matches"]:
            raise ValueError("Exact duplicate measurement requires the verified inventory.")
        path = root / item["path"]
        with path.open("rb") as source:
            header_line = source.readline(65536).decode("utf-8").rstrip("\r\n").lstrip("\ufeff")
        header = tuple(next(csv.reader([header_line], strict=True)))
        schema_key = schemas.setdefault(header, len(schemas))
        frame = record_frame(spark, path, header_line, len(header))
        complete.append(frame.where(F.col("kind") == "parsed").select(
            F.lit(schema_key).alias("schema"),
            F.array(*[F.col(f"c{i}") for i in range(len(header))]).alias("values"),
            F.lit(item["capture_day"]).alias("day"),
        ))
    combined = complete[0]
    for frame in complete[1:]:
        combined = combined.unionByName(frame)
    groups = combined.groupBy("schema", "values").agg(
        F.count("*").alias("count"), F.min("day").alias("first_day"), F.max("day").alias("last_day"),
    )
    result = groups.agg(
        F.sum("count").alias("parsed_rows"),
        F.count("*").alias("distinct_rows"),
        count_if(F.col("count") > 1).alias("duplicate_groups"),
        F.sum(F.col("count") - 1).alias("excess_copies"),
        count_if(F.col("first_day") != F.col("last_day")).alias("cross_day_groups"),
    ).first().asDict()
    return result | {"files": len(complete), "original_schemas": len(schemas)}


def audit_exact_duplicates(config, root, output, scratch):
    root, output, scratch = map(Path, (root, output, scratch))
    if not root.is_dir() or any(path.resolve().is_relative_to(root.resolve()) for path in (output, scratch)):
        raise ValueError("Use a mounted dataset root and separate writable output and scratch directories")
    output.mkdir(parents=True, exist_ok=True)
    scratch.mkdir(parents=True, exist_ok=True)
    inventory = read_inventory(root, config)
    atomic_json(output / "inventory.json", {
        "dataset": {key: config[key] for key in ("owner", "slug", "version")},
        "expected_bytes": sum(config["files"].values()),
        "actual_total_bytes": sum(item["bytes"] or 0 for item in inventory),
        "files": inventory,
    })
    spark = spark_session(config, scratch)
    spark.sparkContext.setLogLevel("WARN")
    try:
        started = time.monotonic()
        print("Measuring exact duplicate field arrays across the mounted captures.", flush=True)
        result = exact_duplicate_summary(spark, root, inventory)
        result["elapsed_seconds"] = round(time.monotonic() - started, 3)
        result["spark_version"] = spark.version
        result["spark"] = config["spark"]
        atomic_json(output / "exact_duplicates.json", result)
        print(f"Exact duplicate aggregation completed in {result['elapsed_seconds']} s", flush=True)
    finally:
        spark.stop()


def measure_file(spark, path, item, output, cache_dir, config, result):
    from pyspark import StorageLevel
    from pyspark.sql import functions as F

    with path.open("rb") as source:
        header_bytes = source.readline(65536)
    if not header_bytes.endswith(b"\n"):
        raise ValueError("Missing header newline or header exceeds 64 KiB")
    header_line = header_bytes.decode("utf-8").rstrip("\r\n")
    schema = inspect_schema(next(csv.reader([header_line.lstrip("\ufeff")], strict=True)))
    schema["utf8_bom"] = header_bytes.startswith(b"\xef\xbb\xbf")
    result["schema"] = schema
    cache_path = cache_dir / (item["name"] + ".parquet")
    stage = output / (item["name"] + ".json")
    frame = record_frame(spark, path, header_line.lstrip("\ufeff"), len(schema["original"])).persist(StorageLevel.DISK_ONLY)
    try:
        started = time.monotonic()
        counts = count_records(frame)
        if not counts_reconcile(counts) or not counts["headers"]:
            raise ValueError("Header or row counts failed reconciliation")
        result["counts"] = counts
        result["stage_seconds"]["parse_and_count"] = round(time.monotonic() - started, 3)
        atomic_json(stage, result)
        valid = frame.where(F.col("kind") == "parsed")
        started = time.monotonic()
        if len(schema["label_indices"]) == 1:
            label_col = F.col(f'c{schema["label_indices"][0]}')
            labels = valid.groupBy(label_col.alias("label")).count().orderBy("label").limit(501).collect()
            if len(labels) > 500:
                raise ValueError("Label cardinality exceeds compact audit limit")
            result["labels"] = [row.asDict() for row in labels]
            if not counts_reconcile(counts, result["labels"]):
                raise ValueError("Label counts do not reconcile")
        result["timestamps"] = summarize_time(valid, schema, config["timestamp_formats"], item["capture_day"])
        result["stage_seconds"]["labels_and_time"] = round(time.monotonic() - started, 3)
        atomic_json(stage, result)
        started = time.monotonic()
        result["quality"] = profile_columns(valid, schema, config)
        result["stage_seconds"]["quality"] = round(time.monotonic() - started, 3)
        atomic_json(stage, result)
        started = time.monotonic()
        fingerprints = fingerprint_frame(valid, schema, item["path"], config)
        if fingerprints is not None:
            fingerprints.write.mode("overwrite").parquet(str(cache_path))
            result["fingerprints"] = True
        result["stage_seconds"]["fingerprints"] = round(time.monotonic() - started, 3)
        return cache_path if fingerprints is not None else None
    finally:
        frame.unpersist(blocking=True)


def audit_dataset(config, root, output, scratch, only_days=None):
    root, output, scratch = map(Path, (root, output, scratch))
    if not root.is_dir() or any(path.resolve().is_relative_to(root.resolve()) for path in (output, scratch)):
        raise ValueError("Use a mounted dataset root and separate writable output and scratch directories")
    output.mkdir(parents=True, exist_ok=True)
    scratch.mkdir(parents=True, exist_ok=True)
    fingerprints_dir = scratch / "fingerprints"
    fingerprints_dir.mkdir(exist_ok=True)
    (scratch / "spark").mkdir(exist_ok=True)
    inventory = read_inventory(root, config)
    atomic_json(output / "inventory.json", {
        "dataset": {key: config[key] for key in ("owner", "slug", "version")},
        "expected_bytes": sum(config["files"].values()),
        "actual_total_bytes": sum(item["bytes"] or 0 for item in inventory),
        "files": inventory,
    })
    spark = spark_session(config, scratch / "spark")
    spark.sparkContext.setLogLevel("WARN")
    run = {
        "spark": config["spark"] | {
            "version": spark.version, "timezone": "UTC", "timestamp_type": "TIMESTAMP_NTZ",
            "executor_cores": spark.sparkContext.defaultParallelism, "spark_application": spark.sparkContext.appName,
        },
        "timestamp_formats": config["timestamp_formats"], "files": {},
    }
    started = time.monotonic()
    atomic_json(output / "run_summary.json", run)
    fingerprints = []
    try:
        # Complete the smaller files first so expensive captures do not prevent partial findings.
        for item in sorted(inventory, key=lambda entry: entry["bytes"] or 0):
            if item["unexpected"] or (only_days is not None and item["capture_day"] not in only_days):
                continue
            name = item["name"]
            result = {"name": name, "stage_seconds": {}, "status": "partial"}
            stage = output / (name + ".json")
            print(f"Audit start {name}", flush=True)
            try:
                if item["access"] != "readable" or not item["size_matches"]:
                    raise ValueError("Missing, inaccessible or changed source file")
                path = measure_file(spark, root / item["path"], item, output, fingerprints_dir, config, result)
                if path is not None:
                    fingerprints.append(path)
                result["status"] = "complete"
            except Exception as error:
                result["error"] = f"{type(error).__name__}: {str(error)[:900]}"
                print(result["error"], flush=True)
            atomic_json(stage, result)
            run["files"][name] = {"status": result["status"], "stage_seconds": result["stage_seconds"]}
            atomic_json(output / "run_summary.json", run)
            print(f"Audit {result['status']} {name}: {result.get('counts', {}).get('parsed')} parsed", flush=True)

        if fingerprints:
            fingerprint_started = time.monotonic()
            try:
                run["fingerprint_summary"] = summarize_fingerprints(spark, fingerprints)
                run["fingerprint_files"] = len(fingerprints)
            except Exception as error:
                run["fingerprint_error"] = f"{type(error).__name__}: {str(error)[:900]}"
                print(run["fingerprint_error"], flush=True)
            run["fingerprint_seconds"] = round(time.monotonic() - fingerprint_started, 3)
    finally:
        run["elapsed_seconds"] = round(time.monotonic() - started, 3)
        atomic_json(output / "run_summary.json", run)
        spark.stop()
    return run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/dataset.yaml"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--day", action="append", help="Audit only this ISO capture day; repeat for more days.")
    parser.add_argument("--exact-duplicates", action="store_true", help="Run only the exact duplicate aggregation.")
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    if args.exact_duplicates:
        audit_exact_duplicates(config, args.root, args.output, args.scratch)
    else:
        audit_dataset(config, args.root, args.output, args.scratch, args.day)


if __name__ == "__main__":
    main()
