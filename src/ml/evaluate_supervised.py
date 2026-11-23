"""Distributed exact confusion counts and bounded score-bin AUC estimates."""

from collections import Counter
import time

from pyspark.ml.functions import vector_to_array
from pyspark.sql import functions as F


def rate(numerator, denominator):
    return numerator / denominator if denominator else None


def confusion_metrics(tp, tn, fp, fn):
    recall, specificity = rate(tp, tp + fn), rate(tn, tn + fp)
    return {"tp": tp, "tn": tn, "fp": fp, "fn": fn, "rows": tp + tn + fp + fn,
            "accuracy": rate(tp + tn, tp + tn + fp + fn), "precision": rate(tp, tp + fp), "recall": recall,
            "specificity": specificity, "f1": rate(2 * tp, 2 * tp + fp + fn),
            "balanced_accuracy": (recall + specificity) / 2 if recall is not None and specificity is not None else None}


def binned_auc(histogram):
    positives = sum(counts[1] for counts in histogram.values())
    negatives = sum(counts[0] for counts in histogram.values())
    if not positives or not negatives:
        return {"roc_auc": None, "pr_auc": None}
    grown_pos = grown_neg = 0
    last_tpr = last_fpr = 0.0
    roc = pr = 0.0
    for score_bin in sorted(histogram, reverse=True):
        counts = histogram[score_bin]
        grown_neg += counts[0]
        grown_pos += counts[1]
        tpr, fpr = grown_pos / positives, grown_neg / negatives
        precision = grown_pos / (grown_pos + grown_neg)
        roc += (fpr - last_fpr) * (tpr + last_tpr) / 2
        pr += (tpr - last_tpr) * precision
        last_tpr, last_fpr = tpr, fpr
    return {"roc_auc": roc, "pr_auc": pr}


def estimator_score(model, frame):
    return model.transform(frame).withColumn("score", vector_to_array("probability")[1])


def evaluate(scored, config):
    """One Spark action scores rows and gathers only small aggregated histograms."""
    started = time.monotonic()
    value = F.col("score")
    bins = config["score_bins"]
    invalid = value.isNull() | F.isnan(value) | (value < 0.0) | (value > 1.0)
    rows = (scored.select("binary_label", "attack_family", "original_label",
                         F.when(invalid, -1).otherwise(F.least(F.floor(value * bins), F.lit(bins - 1))).alias("score_bin"),
                         F.when(value >= config["threshold"], 1).otherwise(0).alias("pred"))
            .groupBy("binary_label", "attack_family", "original_label", "score_bin", "pred").count()
            .limit(65001).collect())
    seconds = round(time.monotonic() - started, 3)
    if len(rows) >= 65001 or any(row.score_bin < 0 or row.binary_label not in (0, 1) for row in rows):
        raise ValueError("Invalid model scores or aggregate exceeded the compact limit")
    histogram, conf, groups = {}, Counter(), {}
    for row in rows:
        histogram.setdefault(row.score_bin, Counter())[row.binary_label] += row["count"]
        conf[row.binary_label, row.pred] += row["count"]
        groups.setdefault((row.binary_label, row.attack_family, row.original_label), Counter())[row.pred] += row["count"]
    metrics = confusion_metrics(conf[1, 1], conf[0, 0], conf[0, 1], conf[1, 0])
    return metrics | binned_auc(histogram) | {"prediction_seconds": seconds}, groups


def family_recall(groups, train_families, train_labels, families, original_labels, minimum):
    observed = {}
    for (binary, family, label), pred in groups.items():
        observed.setdefault(("family", family, binary), Counter()).update(pred)
        observed.setdefault(("original_label", label, binary), Counter()).update(pred)
    rows = []
    for level, catalog, train in (("family", families, train_families), ("original_label", original_labels, train_labels)):
        for name, binary in sorted(catalog.items()):
            counts = observed.get((level, name, binary), Counter())
            support = counts[0] + counts[1]
            rows.append({"level": level, "category": name, "binary_label": binary,
                         "evaluated_rows": support, "tp": counts[1] if binary else None,
                         "fn": counts[0] if binary else None, "fp": counts[1] if not binary else None,
                         "recall": rate(counts[1], support) if binary else None,
                         "benign_false_positive_rate": rate(counts[1], support) if not binary else None,
                         "seen_in_training": train.get(name, 0) > 0, "training_rows": train.get(name, 0),
                         "support_status": "absent" if not support else "low" if support < minimum else "reported"})
    return rows
