"""Bounded Spark aggregation for candidate ranking and matched evaluation."""

from collections import defaultdict
from time import monotonic

from pyspark.sql import functions as F

from src.sql.traffic_analytics import compact, require


def bucket(column, bins):
    return F.when(column.between(0.0, 1.0) & ~F.isnan(column),
                  F.least(F.floor(column * bins).cast("int"), F.lit(bins - 1))).otherwise(-1)


def histograms(frame, names, bins, sliced=False):
    started = monotonic()
    keys = ["source_day", "attack_family"] if sliced else []
    entries = [F.struct(F.lit(name).alias("method"), bucket(F.col(name), bins).alias("bucket")) for name in names]
    data = frame.select("binary_label", *keys, F.explode(F.array(*entries)).alias("score"))
    rows = compact(data.groupBy("binary_label", *keys, "score.method", "score.bucket").count(), 300000)
    full = {name: defaultdict(lambda: [0, 0]) for name in names}
    parts = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for row in rows:
        require(row["binary_label"] in (0, 1) and row["bucket"] >= 0, "Invalid probability, distance score or label")
        method, index, label = row["method"], row["bucket"], row["binary_label"]
        full[method][index][label] += row["count"]
        for key in keys:
            parts[method, key, row[key]][index][label] += row["count"]
    return full, parts, monotonic()-started


def supports(frame):
    output = defaultdict(dict)
    for row in compact(frame.groupBy("role", "binary_label").count(), 40):
        output[row["role"]][row["binary_label"]] = row["count"]
    return dict(output)


def eligible(support, minimum):
    return min(support.get(k, 0) for k in (0, 1)) >= minimum


def choose_method(candidates):
    def key(item):
        name, (row, cost, complexity) = item
        return (row["recall"], row["precision"] if row["precision"] is not None else -1,
                -row["fpr"], -cost, -complexity, name)
    return max(candidates.items(), key=key)[0]
