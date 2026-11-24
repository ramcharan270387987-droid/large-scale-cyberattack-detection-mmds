"""Training-only model selection and permutation-invariant robustness metrics."""

import math
import time

from pyspark.ml.clustering import KMeans
from pyspark.ml.evaluation import ClusteringEvaluator
from pyspark.sql import functions as F

from src.ingest.parquet_pipeline import driver_peak_bytes


def fit_kmeans(vectors, k, config, seed):
    if vectors.columns != ["features"]:
        raise ValueError("K-Means receives only the fitted feature vector")
    start = time.monotonic()
    model = KMeans(k=k, seed=seed, initMode="k-means||", initSteps=config["init_steps"],
                   maxIter=config["max_iter"], tol=config["tolerance"], featuresCol="features",
                   predictionCol="cluster", distanceMeasure="euclidean").fit(vectors)
    elapsed = round(time.monotonic() - start, 3)
    summary = model.summary
    sizes = [int(v) for v in summary.clusterSizes]
    fraction = min(sizes) / sum(sizes) if sizes and sum(sizes) else 0.0
    return model, {
        "k": k, "seed": seed, "initialization": "k-means||", "budget": config["max_iter"], "iterations": summary.numIter,
        "wssse": summary.trainingCost, "cluster_sizes": sizes, "training_rows": sum(sizes),
        "empty_clusters": k - sum(size > 0 for size in sizes), "smallest_share": fraction, "fit_seconds": elapsed,
        "jvm_peak_rss_bytes": driver_peak_bytes(vectors.sparkSession),
    }


def silhouette(model, probe):
    predictions = model.transform(probe)
    if predictions.select("cluster").distinct().count() < 2:
        return None
    value = ClusteringEvaluator(featuresCol="features", predictionCol="cluster",
                                metricName="silhouette", distanceMeasure="squaredEuclidean").evaluate(predictions)
    return value if math.isfinite(value) else None


def choose_k(rows):
    eligible = [row for row in rows if not row["empty_clusters"] and row["smallest_share"] >= 0.001
                and row["silhouette"] is not None]
    if not eligible:
        raise ValueError("All candidates are degenerate or lack silhouette support")
    return max(eligible, key=lambda row: (row["silhouette"], -row["k"]))


def adjusted_rand(contingency):
    n = sum(n for _, _, n in contingency)
    if n < 2:
        return None
    left, right = {}, {}
    for a, b, count in contingency:
        left[a] = left.get(a, 0) + count
        right[b] = right.get(b, 0) + count
    observed = sum(math.comb(count, 2) for _, _, count in contingency)
    a, b = (sum(math.comb(count, 2) for count in side.values()) for side in (left, right))
    expected = a * b / math.comb(n, 2)
    denominator = (a + b) / 2 - expected
    return (observed - expected) / denominator if denominator else 1.0


def compare_assignments(standard, alternative, probe):
    pairs = (alternative.transform(probe.withColumnRenamed("features", "primary_features")
                                   .withColumnRenamed("alternate_features", "features"))
             .withColumnRenamed("cluster", "other_cluster").drop("features")
             .withColumnRenamed("primary_features", "features"))
    counts = standard.transform(pairs).groupBy("cluster", "other_cluster").count().collect()
    return adjusted_rand([(r.cluster, r.other_cluster, r["count"]) for r in counts]), sum(row["count"] for row in counts)


def centroid_dominance(centers, sizes, features):
    normalized = [n / sum(sizes) for n in sizes]
    sums = []
    for j, feature in enumerate(features):
        mean = sum(weight * float(c[j]) for weight, c in zip(normalized, centers))
        sums.append((feature, sum(weight * (float(c[j]) - mean) ** 2 for weight, c in zip(normalized, centers))))
    total = sum(v for _, v in sums)
    return [{"feature": name, "share_between_centroids": share / total if total else 0.0}
            for name, share in sorted(sums, key=lambda item: (-item[1], item[0]))]
