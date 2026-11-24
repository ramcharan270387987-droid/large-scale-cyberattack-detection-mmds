"""Tie-preserving histogram thresholds and validation-only selection."""

from math import sqrt

from src.ml.evaluate_supervised import binned_auc, confusion_metrics, rate


def metrics(tp, tn, fp, fn):
    result = confusion_metrics(tp, tn, fp, fn)
    denom = sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return result | {"fpr": rate(fp, fp + tn), "fnr": rate(fn, tp + fn),
                     "f2": rate(5 * tp, 5 * tp + fp + 4 * fn),
                     "mcc": rate(tp * tn - fp * fn, denom)}


def curves(hist, bins):
    negative = sum(x[0] for x in hist.values())
    positive = sum(x[1] for x in hist.values())
    tp = fp = 0
    result = {bins: metrics(0, negative, 0, positive)}
    for index in reversed(range(bins)):
        no, yes = hist.get(index, (0, 0))
        tp += yes
        fp += no
        result[index] = metrics(tp, negative - fp, fp, positive - tp)
    return result


def objective(row, key):
    value = row[key]
    return -1.0 if value is None else value


def choose(points, budget):
    feasible = [(i, row) for i, row in points.items() if row["fpr"] is not None and row["fpr"] <= budget]
    if not feasible:
        raise ValueError("No benign support for operating threshold selection")
    return max(feasible, key=lambda item: (objective(item[1], "recall"), objective(item[1], "precision"),
                                           -item[1]["fpr"], item[0]))


def thresholds(hist, config):
    bins = config["score_bins"]
    series = curves(hist, bins)
    if not any(row["recall"] is not None for row in series.values()):
        raise ValueError("No attack support for operating threshold selection")
    choices = {"fixed_0.5": (bins // 2, series[bins // 2])}
    choices.update({f"budget_{budget:g}": choose(series, budget) for budget in config["budgets"]})
    for name in ("f1", "f2", "balanced_accuracy"):
        choices[name] = max(series.items(), key=lambda item: (objective(item[1], name), item[0]))
    choices["cost"] = min(series.items(), key=lambda item: (
        item[1]["fp"] + config["false_negative_cost"] * item[1]["fn"], -item[0]))
    return choices


def at_threshold(hist, index, bins):
    negatives = sum(x[0] for x in hist.values())
    positives = sum(x[1] for x in hist.values())
    tn_fp, tp = (sum(x[position] for key, x in hist.items() if key >= index) for position in (0, 1))
    return metrics(tp, negatives - tn_fp, tn_fp, positives - tp) | binned_auc(hist)


def threshold_value(index, bins):
    """One step above 1 represents the explicit never-positive threshold."""
    return (index if index < bins else bins + 1) / bins
