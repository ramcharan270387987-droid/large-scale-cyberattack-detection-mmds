"""Nearest-centroid squared distances and reference-only score calibration."""

from pyspark.ml.functions import vector_to_array
from pyspark.sql import functions as F


def squared_distance(model, data):
    centers = F.array(*[F.array(*[F.lit(float(x)) for x in center]) for center in model.clusterCenters()])
    prediction = model.transform(data)
    assigned = F.element_at(centers, (F.col("cluster") + 1).cast("int"))
    deltas = F.zip_with(vector_to_array("features"), assigned, lambda x, y: (x - y) * (x - y))
    return prediction.withColumn("score", F.aggregate(deltas, F.lit(0.0), lambda acc, value: acc + value))


def calibrate(reference_scores, percentiles, accuracy):
    if set(reference_scores.columns) != {"split_rank", "score"} or reference_scores.where("split_rank <> 0 OR split_rank IS NULL").limit(1).count():
        raise ValueError("Threshold calibration requires reference score rows only")
    row = reference_scores.agg(F.count("*").alias("rows"),
                               F.percentile_approx("score", percentiles, accuracy).alias("cutoffs")).first()
    if not row.rows or row.cutoffs is None:
        raise ValueError("Empty novelty calibration population")
    cutoffs = dict(zip(map(str, percentiles), row.cutoffs))
    exceedance = reference_scores.agg(*[
        F.count(F.when(F.col("score") > value, 1)).alias(p) for p, value in cutoffs.items()
    ]).first().asDict()
    return {"rows": row.rows, "cutoffs": cutoffs, "accuracy": accuracy, "reference_flags": exceedance}


def safe_div(a, b):
    return a / b if b else None


def novelty_row(positive, negative, tp, fp):
    count = positive + negative
    return {"rows": count, "attacks": positive, "benign": negative, "tp": tp, "fp": fp,
            "flags": tp + fp, "flag_rate": safe_div(tp + fp, count),
            "benign_fpr": safe_div(fp, negative), "attack_recall": safe_div(tp, positive),
            "precision": safe_div(tp, tp + fp)}


def novelty_metrics(data, cutoffs, catalog, minimum):
    rows = []
    for p, cutoff in cutoffs.items():
        flag = F.col("score") > cutoff
        projection = data.withColumn("flag", flag)
        measured = projection.groupBy("split_rank", "binary_label", "attack_family").agg(
            F.count("*").alias("records"), F.count(F.when(F.col("flag"), 1)).alias("flagged")).collect()
        totals, support = {}, {}
        for row in measured:
            totals.setdefault(row.split_rank, [0, 0, 0, 0])
            totals[row.split_rank][0 if row.binary_label else 1] += row.records
            totals[row.split_rank][2 if row.binary_label else 3] += row.flagged
            support[row.split_rank, row.attack_family] = (row.records, row.flagged)
        for rank, counts in sorted(totals.items()):
            rows.append({"split_rank": rank, "percentile": p, "threshold": cutoff, "scope": "binary", "family": "All",
                         **novelty_row(*counts), "support_status": "observed"})
            for family in catalog:
                s, hit = support.get((rank, family), (0, 0))
                rows.append({"split_rank": rank, "percentile": p, "threshold": cutoff, "scope": "family", "family": family,
                             **(novelty_row(s, 0, hit, 0) | {"precision": None}),
                             "support_status": "absent" if not s else "low" if s < minimum else "observed"})
    return rows
