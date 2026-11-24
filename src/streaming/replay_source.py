"""Build bounded chronological Parquet files and attest their release sequence."""

from pathlib import Path
import os
import time

from pyspark import StorageLevel
from pyspark.sql import functions as F

from src.ingest.parquet_pipeline import parquet_footers
from src.ml.split_protocols import crossing_groups, group_summary, mark_retention
from src.ml.train_clustering import cohorts, split_counts, verify_phase4_match
from src.sql.traffic_analytics import require


AUDIT_FIELDS = (
    "source_day", "split_rank", "original_timestamp", "parsed_event_time", "temporal_eligibility",
    "timestamp_parse_status", "source_file", "record_fingerprint", "predictor_key",
    "binary_label", "attack_family", "original_label",
)
CAPTURE_ONLY = 24


def window_key(hours):
    return F.when(F.col("temporal_eligibility"),
                  (F.floor(F.hour("parsed_event_time") / hours) * hours).cast("int")).otherwise(CAPTURE_ONLY)


def replay_calendar(rows, config):
    keys = sorted((row["source_day"], row["window_hour"], row["split_rank"], row["count"]) for row in rows)
    require(0 < len(keys) <= config["max_chunks"] and len(set((day, hour) for day, hour, _, _ in keys)) == len(keys),
            "Unexpected number or identity of historical replay chunks")
    return [{"replay_seq": i, "source_day": day, "window_hour": hour, "split_rank": split, "rows": count}
            for i, (day, hour, split, count) in enumerate(keys)]


def chunk_file(seq):
    return f"chunk-{seq:03}.parquet"


def publish(directory, src, seq):
    target = directory / chunk_file(seq)
    os.replace(src, target)
    # FileStreamSource sorts by modification time. Unique times avoid relying on directory order.
    stamp = 946684800 + 2 * seq
    os.utime(target, (stamp, stamp))
    return target.stat().st_size


def stage(spark, receipt, upstream, design, phase4, phase5, names, config, scratch):
    started = time.monotonic()
    clean_path = receipt.parent.parent / upstream["policy_version"] / "clean"
    require(all(upstream["layers"]["clean"][key] == value for key, value in parquet_footers(clean_path).items()),
            "Unverified clean input")
    clean = spark.read.parquet(str(clean_path))
    require(dict(clean.dtypes).get("parsed_event_time") == "timestamp_ntz", "Unexpected timestamp type")
    extra = ("original_timestamp", "source_file", "timestamp_parse_status")
    base = cohorts(clean, names, design, "B", phase5["input"]["days"], extra).persist(StorageLevel.DISK_ONLY)
    cross = crossing_groups(base, "predictor_key").persist(StorageLevel.DISK_ONLY)
    retained = mark_retention(base, cross, group_summary(cross)["groups"]).where("retained").drop("retained").persist(StorageLevel.DISK_ONLY)
    try:
        raw_rows = base.count()
        pre_anomalies = base.where(~F.col("temporal_eligibility")).count()
        require(raw_rows == phase5["input"]["rows"] and pre_anomalies == 14, "Original temporal support differs")
        observed = split_counts(retained)
        verify_phase4_match(observed, "B", {"protocols": {"B": phase4}})
        total = sum(row["count"] for row in observed)
        removed = raw_rows - total
        require(total == phase5["retained_rows"] and removed == phase5["purge"]["rows"] == 909956,
                "Chronological retained population differs")
        require(group_summary(crossing_groups(retained, "predictor_key"))["groups"] == 0, "Retained predictor overlap")
        cross.unpersist(blocking=True)
        base.unpersist(blocking=True)
        staged = retained.withColumn("window_hour", window_key(config["window_hours"]))
        require(staged.where("window_hour IS NULL OR temporal_eligibility IS NULL OR record_fingerprint IS NULL "
                             "OR (temporal_eligibility AND CAST(parsed_event_time AS DATE) <> CAST(source_day AS DATE))")
                .limit(1).count() == 0, "Invalid event window or provenance")
        calendar = replay_calendar(staged.groupBy("source_day", "window_hour", "split_rank").count().collect(), config)
        require(all(item["rows"] <= config["max_chunk_rows"] for item in calendar), "Replay chunk exceeds the row budget")
        lookup = spark.createDataFrame([(item["source_day"], item["window_hour"], item["replay_seq"]) for item in calendar],
                                       "source_day STRING, window_hour INT, replay_seq INT")
        packed = (staged.join(F.broadcast(lookup), ["source_day", "window_hour"])
                  .select(*names, "replay_seq", "window_hour", F.struct(*AUDIT_FIELDS).alias("audit"))
                  .withColumn("shard", F.col("replay_seq")))
        schema = packed.drop("shard").schema
        temporary, directory = scratch / "ordered", scratch / "available"
        directory.mkdir()
        (packed.repartition(config["spark"]["shuffle_partitions"], "shard")
         .sortWithinPartitions("shard", "audit.parsed_event_time", "audit.record_fingerprint", "audit.predictor_key")
         .write.partitionBy("shard").parquet(str(temporary)))
        for item in calendar:
            sequence = item["replay_seq"]
            paths = list((temporary / f"shard={sequence}").glob("*.parquet"))
            require(len(paths) == 1, "Replay staging must have exactly one file per sequence")
            item["bytes"] = publish(directory, paths[0], sequence)
        total_bytes = sum(item["bytes"] for item in calendar)
        require(total_bytes <= config["max_staging_bytes"], "Replay staging exceeded the configured size limit")
        require(sum(item["rows"] for item in calendar) == total, "Replay staging lost records")
        return directory, schema, calendar, {"rows": total, "purged_rows": removed, "source_anomalies": pre_anomalies,
                                            "ineligible_retained": sum(x["rows"] for x in calendar if x["window_hour"] == CAPTURE_ONLY),
                                            "bytes": total_bytes, "seconds": round(time.monotonic() - started, 3),
                                            "chunks": len(calendar), "cohorts": observed}
    finally:
        for data in (base, cross, retained):
            data.unpersist()
