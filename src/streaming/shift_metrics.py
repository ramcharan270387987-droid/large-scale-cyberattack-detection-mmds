"""Compute compact replay histograms, retrospective metrics and shift distances."""

from collections import Counter
import math
import time

from pyspark import StorageLevel
from pyspark.sql import functions as F

from src.ml.cluster_evolution import divergence
from src.ml.evaluate_supervised import binned_auc, confusion_metrics, rate
from src.ml.novelty_scoring import novelty_row
from src.sql.traffic_analytics import require
from src.streaming.cluster_scoring import cluster_scores
from src.streaming.model_scoring import SUPERVISED, supervised_scores


def fixed_bin(name, bounds):
    value = F.col(name)
    return F.when(value.isNull(), len(bounds) + 1).otherwise(
        sum((F.when(value >= edge, 1).otherwise(0) for edge in bounds), F.lit(0)))


def score_bin(name, bins):
    score = F.col(name)
    return F.when(score.between(0, 1), F.least(F.floor(score * bins), F.lit(bins - 1))).otherwise(-1)


def aggregate(batch, models, duration, cluster, config):
    started = time.monotonic()
    aligned = supervised_scores(batch, models, duration)
    scored = (cluster_scores(aligned, *cluster).select("replay_seq", "window_hour", "audit", "cluster", "distance", "novel",
                                                       *SUPERVISED, *config["features"])
              .persist(StorageLevel.MEMORY_AND_DISK))
    try:
        rows = scored.count()
        scoring_seconds = time.monotonic() - started
        observed = {}
        label = F.col("audit.binary_label")
        count = lambda condition: F.count(F.when(condition, 1))
        histograms = {name: (fixed_bin(name, edges), len(edges) + 2) for name, edges in config["features"].items()}
        histograms["cluster"] = F.col("cluster"), len(cluster[1].clusterCenters())
        histograms["distance"] = fixed_bin("distance", config["distance_bounds"]), len(config["distance_bounds"]) + 2
        fields = [
            F.count("*").alias("rows"), count(F.col("audit.temporal_eligibility")).alias("eligible"),
            count(label == 1).alias("attacks"), count(label == 0).alias("benign"),
            count(F.col("novel") & (label == 1)).alias("novel_attack"),
            count(F.col("novel") & (label == 0)).alias("novel_benign"),
            F.sum("distance").alias("distance_sum"),
            F.countDistinct(F.struct("audit.source_day", "window_hour", "audit.split_rank")).alias("groups"),
            F.first("audit.source_day").alias("source_day"), F.first("window_hour").alias("window_hour"),
            F.first("audit.split_rank").alias("split_rank"),
            count(F.col("distance").isNull() | F.isnan("distance") | (F.col("distance") < 0) |
                  (F.col("distance") == float("inf"))).alias("bad_distance"),
        ]
        fields.extend(count(column == i).alias(f"{name}_{i}") for name, (column, size) in histograms.items() for i in range(size))
        for row in scored.groupBy("replay_seq").agg(*fields).collect():
            item = row.asDict()
            require(item.pop("groups") == 1 and item.pop("bad_distance") == 0, "Replay chunk identity or distance is invalid")
            item["histograms"] = {name: [item.pop(f"{name}_{i}") for i in range(size)]
                                  for name, (_, size) in histograms.items()}
            require(item["rows"] == item["attacks"] + item["benign"] and
                    all(sum(values) == item["rows"] for values in item["histograms"].values()), "Chunk totals do not reconcile")
            item["scores"] = {name: {} for name in SUPERVISED}
            observed[row.replay_seq] = item
        labels = scored.select("replay_seq", label.alias("label"), F.posexplode(F.array(*[
            score_bin(name, config["score_bins"]) for name in SUPERVISED
        ])).alias("model", "bin"))
        for row in labels.groupBy("replay_seq", "model", "bin", "label").count().collect():
            require(row.bin >= 0 and row.label in (0, 1), "Invalid classifier score or evaluation label")
            buckets = observed[row.replay_seq]["scores"][SUPERVISED[row.model]]
            buckets.setdefault(str(row.bin), [0, 0])[row.label] = row["count"]
        for item in observed.values():
            for buckets in item["scores"].values():
                require(sum(x[0] for x in buckets.values()) == item["benign"] and
                        sum(x[1] for x in buckets.values()) == item["attacks"], "Classifier score support differs")
        require(rows == sum(item["rows"] for item in observed.values()), "Microbatch accounting differs")
        return [observed[seq] for seq in sorted(observed)], scoring_seconds
    finally:
        scored.unpersist(blocking=True)


def combine(items):
    n = {key: sum(item[key] for item in items) for key in
         ("rows", "eligible", "attacks", "benign", "novel_attack", "novel_benign", "distance_sum")}
    n["histograms"] = {name: list(map(sum, zip(*(x["histograms"][name] for x in items)))) for name in items[0]["histograms"]}
    scores = {}
    for name in SUPERVISED:
        negative, positive = Counter(), Counter()
        for item in items:
            for bucket, (left, right) in item["scores"][name].items():
                negative[bucket] += left
                positive[bucket] += right
        scores[name] = {bucket: [negative[bucket], positive[bucket]] for bucket in sorted(negative.keys() | positive.keys(), key=int)}
    n["scores"] = scores
    return n


def model_metrics(scores, bins):
    hits = [0, 0]
    misses = [0, 0]
    for bucket, counts in scores.items():
        population = hits if int(bucket) >= bins // 2 else misses
        population[0] += counts[0]
        population[1] += counts[1]
    result = confusion_metrics(hits[1], misses[0], hits[0], misses[1])
    return result | binned_auc({int(key): value for key, value in scores.items()}) | {"predicted_positive": sum(hits), "predicted_rate": rate(sum(hits), result["rows"])}


def unsupervised_vectors(item, bins):
    result = dict(item["histograms"])
    for name, scores in item["scores"].items():
        result[name] = [sum(scores.get(str(i), (0, 0))) for i in range(bins)]
    return result


def distribution_shifts(item, reference, config):
    current = unsupervised_vectors(item, config["score_bins"])
    baseline = unsupervised_vectors(reference, config["score_bins"])
    for name in (*config["features"], *SUPERVISED, "cluster"):
        metric = "CLUSTER_SHIFT" if name == "cluster" else "SCORE_SHIFT" if name in SUPERVISED else "INPUT_SHIFT"
        yield metric, name, divergence(current[name], baseline[name]), 0.0


def tail_upper(item, edges, percentile=0.95):
    target = math.ceil(percentile * item["rows"])
    accrued = 0
    for i, count in enumerate(item["histograms"]["distance"]):
        accrued += count
        if target and accrued >= target:
            return edges[i] if i < len(edges) else None
    return None


def novelty(item):
    return novelty_row(item["attacks"], item["benign"], item["novel_attack"], item["novel_benign"])
