"""Drive historical traffic through bounded file-backed Spark Structured Streaming."""

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import time

from pyspark.sql import functions as F
from pyspark.sql.streaming import StreamingQueryException

from src.ingest.dataset_audit import atomic_json
from src.ingest.parquet_pipeline import driver_peak_bytes, resource_limits
from src.sql.traffic_analytics import require
from src.streaming.checkpoint_recovery import (
    ReplayInterruption, commit_aggregate, commit_file, committed_ids, load_commits,
)
from src.streaming.replay_source import CAPTURE_ONLY, chunk_file, stage
from src.streaming.shift_metrics import aggregate, combine


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def query_stream(spark, source, schema, calendar, checkpoint, sink, files, process, inject=False):
    started = time.monotonic()
    receipt = {"attempts": [], "progress": [], "recovery": []}
    failure = {"injected": False}
    recovery_batch = 1
    batches = (len(calendar) + files - 1) // files
    require(batches > recovery_batch or not inject, "Need at least two batches to test recovery")
    observed = spark.readStream.schema(schema).option("maxFilesPerTrigger", files).parquet(str(source))
    require(observed.isStreaming, "A Structured Streaming DataFrame is required")

    def callback(frame, batch_id):
        entered = time.monotonic()
        when = utc_now()
        expected = calendar[batch_id * files:(batch_id + 1) * files]
        require(bool(expected), "Spark delivered an unexpected extra batch")
        file_counts = frame.select(F.col("replay_seq").alias("seq"), F.input_file_name().alias("file")).groupBy("seq", "file").count().collect()
        actual = sorted((row.seq, Path(row.file).name, row["count"]) for row in file_counts)
        require(actual == [(item["replay_seq"], chunk_file(item["replay_seq"]), item["rows"]) for item in expected],
                f"Spark file release order differs at batch {batch_id}")
        payload = {"batch_id": batch_id, "source": expected}
        exists = commit_file(sink, batch_id).exists()
        if exists:
            require(not commit_aggregate(sink, batch_id, payload), "Retried batch overwrote its sink commit")
            receipt["recovery"].append({"test": "replayed_committed_sink_batch", "batch_id": batch_id, "passed": True})
            return
        items, scoring_seconds = process(frame)
        require([(i["replay_seq"], i["source_day"], i["window_hour"], i["split_rank"], i["rows"]) for i in items] ==
                [(i["replay_seq"], i["source_day"], i["window_hour"], i["split_rank"], i["rows"]) for i in expected],
                "Scored chunk does not match its manifest entry")
        payload.update(chunks=items, entered_utc=when, finished_utc=utc_now(),
                       scoring_seconds=round(scoring_seconds, 6), processing_seconds=round(time.monotonic() - entered, 6))
        require(commit_aggregate(sink, batch_id, payload), "Uncommitted batch already had output")
        print(f"PHASE6 stream batch {batch_id} committed sink sequences "
              f"{expected[0]['replay_seq']}–{expected[-1]['replay_seq']} rows {sum(i['rows'] for i in expected)}", flush=True)
        if inject and batch_id == recovery_batch and not failure["injected"]:
            failure["injected"] = True
            raise ReplayInterruption("PHASE6 planned stop after atomic sink publish")

    def attempt(expected_error):
        query = (observed.writeStream.option("checkpointLocation", str(checkpoint)).outputMode("append")
                 .trigger(availableNow=True).foreachBatch(callback).start())
        try:
            query.awaitTermination()
            require(not expected_error, "Expected planned interruption did not occur")
        except StreamingQueryException as exc:
            if not expected_error or not failure["injected"] or "PHASE6 planned stop" not in str(exc):
                raise
        finally:
            if query.isActive:
                query.stop()
        receipt["attempts"].append({"query_id": str(query.id), "run_id": str(query.runId),
                                    "outcome": "planned_interruption" if expected_error else "terminated"})
        for progress in query.recentProgress:
            receipt["progress"].append(json.loads(progress.json))

    attempt(inject)
    if inject:
        path = commit_file(sink, recovery_batch)
        checksum = sha256(path.read_bytes()).hexdigest()
        require(committed_ids(checkpoint) == list(range(recovery_batch)), "Checkpoint advanced beyond injected failure")
        partial = path.with_suffix(".partial")
        partial.write_text('{"interrupted":')
        receipt["recovery"].append({"test": "partial_aggregate_ignored", "batch_id": recovery_batch, "passed":
                                    len(load_commits(sink)) == recovery_batch + 1})
        attempt(False)
        require(checksum == sha256(path.read_bytes()).hexdigest(), "Idempotent retry changed an aggregate")
        require(receipt["attempts"][0]["query_id"] == receipt["attempts"][1]["query_id"] and
                receipt["attempts"][0]["run_id"] != receipt["attempts"][1]["run_id"], "Restart did not use the same checkpoint")
        receipt["recovery"].append({"test": "restart_same_query_new_run", "batch_id": recovery_batch, "passed": True})
        receipt["recovery"].append({"test": "durable_sink_hash_unchanged", "batch_id": recovery_batch, "passed": True})
        partial.unlink()
    documents = load_commits(sink)
    expected_ids = list(range(batches))
    require([x["batch_id"] for x in documents] == committed_ids(checkpoint) == expected_ids,
            "Checkpoint and aggregate sink accounting differ")
    require([i for doc in documents for i in doc["source"]] == calendar, "Replay duplicated or lost source chunks")
    require({p["batchId"] for p in receipt["progress"] if p["numInputRows"] > 0} == set(expected_ids),
            "Actual Structured Streaming progress does not cover all data batches")
    require(all(row["passed"] for row in receipt["recovery"]), "An interruption check failed")
    receipt["recovery"].append({"test": "checkpoint_and_sink_reconcile", "batch_id": batches - 1, "passed": True})
    receipt["checkpoint_bytes"] = sum(path.stat().st_size for path in checkpoint.rglob("*") if path.is_file())
    receipt["elapsed_seconds"] = round(time.monotonic() - started, 3)
    return documents, receipt


def full_replay(spark, receipt, upstream, design, phase4, phase5, names, models, duration, cluster, config, output, scratch, summary):
    started = time.monotonic()
    source, schema, calendar, staging = stage(spark, receipt, upstream, design, phase4, phase5, names, config, scratch)
    summary.update(status="staged", staging=staging, source_schema=schema.jsonValue(),
                   resources=resource_limits(spark, config, output))
    atomic_json(output / "phase6_summary.json", summary)
    print(f"PHASE6 staged {staging['chunks']} chunks and {staging['rows']} rows, {staging['bytes']} bytes", flush=True)

    def process(frame):
        require(set(frame.columns) == set(names) | {"replay_seq", "window_hour", "audit"}, "Unexpected streaming source schema")
        return aggregate(frame, models, duration, cluster, config)

    full, run = query_stream(spark, source, schema, calendar, scratch / "checkpoint", scratch / "sink",
                             config["files_per_trigger"], process, inject=True)
    reference = combine([item for doc in full for item in doc["chunks"] if item["split_rank"] == 0])
    require(reference["histograms"]["cluster"] == phase5["reference_occupancy"], "Phase 5 reference cluster occupancy differs")
    print(f"PHASE6 streaming and recovery validated over {len(full)} distinct batches", flush=True)
    subset = [item for item in calendar if item["window_hour"] != CAPTURE_ONLY][:config["comparison_chunks"]]
    comparison_source = scratch / "comparison-input"
    comparison_source.mkdir()
    for item in subset:
        path = chunk_file(item["replay_seq"])
        os.link(source / path, comparison_source / path)
    comparisons = []
    for files in (config["files_per_trigger"], config["comparison_files_per_trigger"]):
        label = f"comparison-{files}"
        docs, evidence = query_stream(spark, comparison_source, schema, subset, scratch / (label + "-checkpoint"),
                                      scratch / (label + "-sink"), files, process)
        comparisons.append((label, files, docs, evidence))
    # Metrics are reconstructed offline from completed immutable callback outputs.
    from src.streaming.replay_reporting import publish_results

    summary.update(status="validated", elapsed_seconds=round(time.monotonic() - started, 3),
                   driver_peak_rss_bytes=driver_peak_bytes(spark), reference_rows=reference["rows"],
                   reference_cluster_occupancy=reference["histograms"]["cluster"])
    publish_results(output, full, run, comparisons, summary, reference, config)
    atomic_json(output / "phase6_summary.json", summary)
    print(f"PHASE6 complete {staging['rows']} retained flows in {len(full)} streaming batches", flush=True)
