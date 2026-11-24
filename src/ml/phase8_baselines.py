"""Reconcile retrospective baselines from the original saved pipelines."""

import csv
import json
import math
from pathlib import Path

from pyspark import StorageLevel
from pyspark.ml import PipelineModel
from pyspark.ml.functions import vector_to_array
from pyspark.sql import functions as F

from src.ml.baselines import baseline_score
from src.ml.evaluate_supervised import evaluate
from src.ml.novelty_scoring import novelty_metrics
from src.ml.split_protocols import assign_population, crossing_groups, group_summary, mark_retention
from src.ml.train_clustering import split_counts, verify_phase4_match
from src.sql.traffic_analytics import require, write_rows
from src.streaming.cluster_scoring import cluster_scores
from src.streaming.model_scoring import mounted_summary, probe, verified_model


def json_file(project, name):
    return json.loads((project / name).read_text())


def rows_file(project, name):
    with (project / name).open(newline="") as handle:
        return list(csv.DictReader(handle))


def retain(assigned):
    crossings = crossing_groups(assigned, "predictor_key").persist(StorageLevel.DISK_ONLY)
    try:
        before = group_summary(crossings)
        after_assignment = mark_retention(assigned, crossings, before["groups"])
        # Materialize the small predictor projection before releasing the group join.
        retained = after_assignment.where("retained").drop("retained").persist(StorageLevel.DISK_ONLY)
        retained.count()
        return retained, before
    finally:
        crossings.unpersist()


def benchmark_population(data, protocol, design, days, previous, output):
    assigned = assign_population(data, protocol, design, days)
    active, crossing = retain(assigned)
    counts = split_counts(active)
    verify_phase4_match(counts, protocol, previous)
    excluded = data.count() - sum(row["count"] for row in counts)
    require(excluded == previous["protocols"][protocol]["overlap"]["purged_rows"], "Benchmark population differs")
    write_rows(output / "phase8_split_diagnostics.csv", counts)
    return active, {"purged_rows": excluded, "prepurge_predictor_groups": crossing}


def load_models(spark, input_root, protocol, names, previous, clustering):
    directory, receipt = mounted_summary(input_root, "phase4_summary.json", protocol, "protocol")
    require(receipt["baselines"] == previous["baselines"] and receipt["registered_predictors"] == names and
            receipt["input"]["receipt_sha256"] == previous["input"]["receipt_sha256"], "Phase 4 identity differs")
    models, manifest = {}, {}
    for item in previous["models"]:
        if item["training_cohort"] != "group_sample":
            continue
        name = item["model"]
        saved = next(meta for meta in receipt["models"] if meta["model"] == name and meta["training_cohort"] == "group_sample")
        require(saved["sha256"] == item["sha256"], "Phase 4 receipt checksums differ")
        models[name] = verified_model(spark, directory / "models" / Path(item["path"]).name, item["sha256"], names)
        scores = models[name].transform(probe(spark, names)).select(vector_to_array("probability")[1]).collect()
        require(len(scores) == 3 and all(math.isfinite(r[0]) and 0 <= r[0] <= 1 for r in scores), "Probability probe failed")
        manifest[name] = {"files": item["model_files"], "sha256": item["sha256"], "probe_rows": len(scores)}
    directory, receipt = mounted_summary(input_root, "phase5_summary.json", protocol, "experiment")
    require(receipt["features"] == names and receipt["model"]["sha256"] == clustering["model"]["sha256"] and
            receipt["calibration"] == clustering["calibration"], "Phase 5 receipt differs")
    pipeline = verified_model(spark, directory / "model", clustering["model"]["sha256"], names, "_valid", "_filled")
    km = (PipelineModel(stages=pipeline.stages[:-1]), pipeline.stages[-1], clustering["calibration"]["cutoffs"]["0.99"])
    scores = cluster_scores(probe(spark, names), *km).select("cluster", "distance").collect()
    k = len(km[1].clusterCenters())
    require(k == clustering["selected_k"] and len(scores) == 3 and
            all(0 <= r.cluster < k and math.isfinite(r.distance) for r in scores), "K-Means synthetic probe failed")
    return models, km, manifest | {"kmeans": {"sha256": clustering["model"]["sha256"], "p99": km[2], "probe_rows": len(scores)}}


def reconcile(project, protocol, active, models, km, before, design, output):
    expected = rows_file(project, "reports/phase4_metrics.csv")
    expected_novelty = rows_file(project, "reports/phase5_novelty_metrics.csv")
    result = []
    for rank, partition in ((1, "validation"), (2, "test")):
        frame = active.where(F.col("split_rank") == rank)
        scores = {name: models[name].transform(frame).withColumn("score", vector_to_array("probability")[1]) for name in models}
        scores.update({name: baseline_score(frame, name, params) for name, params in before["baselines"].items()})
        for name, scored in scores.items():
            current, _ = evaluate(scored, design)
            earlier = next(r for r in expected if r["protocol"] == protocol and r["split"] == partition and
                           r["model"] == name and r["training_cohort"] != "full_train_refit")
            checks = ("rows", "tp", "tn", "fp", "fn", "pr_auc", "roc_auc")
            agree = all(current[k] is not None and math.isclose(float(earlier[k]), current[k], abs_tol=1e-12)
                        if earlier[k] else current[k] is None for k in checks)
            result.append({"population": protocol, "partition": partition, "baseline": name, "matches": agree,
                           "rows": current["rows"], "tp": current["tp"], "fp": current["fp"],
                           "pr_auc": current["pr_auc"], "roc_auc": current["roc_auc"], "seconds": current["prediction_seconds"]})
            write_rows(output / "phase8_baseline_reconciliation.csv", result)
            require(agree, f"Phase 4 baseline discrepancy: {protocol}/{partition}/{name}")
            print(f"PHASE8 {protocol} reconciled {partition} {name} {current['rows']}", flush=True)
        measured = novelty_metrics(cluster_scores(frame, *km).withColumnRenamed("distance", "score"), {"0.99": km[2]}, [], 100)
        require(len(measured) == 1, "Unexpected novelty result groups")
        current = measured[0]
        earlier = next(r for r in expected_novelty if r["experiment"] == protocol and int(r["split_rank"]) == rank and
                       r["percentile"] == "0.99" and r["scope"] == "binary")
        agree = all(current[k] == int(earlier[k]) for k in ("rows", "tp", "fp", "flags"))
        result.append({"population": protocol, "partition": partition, "baseline": "kmeans_p99", "matches": agree,
                       "rows": current["rows"], "tp": current["tp"], "fp": current["fp"],
                       "pr_auc": None, "roc_auc": None, "seconds": None})
        write_rows(output / "phase8_baseline_reconciliation.csv", result)
        require(agree, f"Phase 5 baseline discrepancy: {protocol}/{partition}")
        print(f"PHASE8 {protocol} reconciled {partition} K-Means P99 {current['rows']}", flush=True)
    return result
