"""Capture-day and three-hour occupancy comparisons on a frozen model."""

import math

from pyspark.sql import functions as F

from src.sql.traffic_analytics import compact


def divergence(left, right):
    if sum(left) == 0 or sum(right) == 0 or len(left) != len(right):
        return None
    p = [value / sum(left) for value in left]
    q = [value / sum(right) for value in right]
    distance = sum(
        (a * math.log2(2 * a / (a + b)) if a else 0.0)
        + (b * math.log2(2 * b / (a + b)) if b else 0.0) for a, b in zip(p, q)
    ) / 2
    return max(0.0, distance)


def occupancy(data, k, config, cutoff):
    hours = config["window_hours"]
    bins = F.floor(F.hour("parsed_event_time") / hours) * hours
    day = data.withColumn("window_hour", F.lit(-1))
    window = data.where("temporal_eligibility").withColumn("window_hour", bins.cast("int"))
    fields = ("source_day", "split_rank", "window_hour", "cluster", "score", "binary_label", "flow_duration", "tot_fwd_pkts", "totlen_fwd_pkts")
    scoped = day.select(*fields).unionByName(window.select(*fields))
    raw = compact(scoped.groupBy("source_day", "split_rank", "window_hour", "cluster").agg(
        F.count("*").alias("records"), F.count(F.when(F.col("binary_label") == 1, 1)).alias("attacks"),
        F.count(F.when(F.col("score") > cutoff, 1)).alias("flags"),
        F.avg("score").alias("mean_score"), F.percentile_approx("score", 0.95, config["quantile_accuracy"]).alias("score_p95"),
        F.avg("flow_duration").alias("mean_duration_us"), F.avg("tot_fwd_pkts").alias("mean_forward_packets"),
        F.avg("totlen_fwd_pkts").alias("mean_forward_bytes")
    ).orderBy("source_day", "window_hour", "cluster"), 2000)
    reference = [0] * k
    for row in raw:
        if row["split_rank"] == 0 and row["window_hour"] == -1:
            reference[row["cluster"]] += row["records"]
    cohorts = {}
    for row in raw:
        key = row["source_day"], row["split_rank"], row["window_hour"]
        cohorts.setdefault(key, [0] * k)[row["cluster"]] += row["records"]
    rows = [row | {"occupancy": row["records"] / sum(cohorts[row["source_day"], row["split_rank"], row["window_hour"]])} for row in raw]
    shifts = [{"source_day": day, "split_rank": rank, "window_hour": hour, "rows": sum(counts),
               "occupied_clusters": sum(n > 0 for n in counts), "js_divergence_bits": divergence(reference, counts),
               "reference_rows": sum(reference)} for (day, rank, hour), counts in sorted(cohorts.items())]
    return rows, shifts, reference
