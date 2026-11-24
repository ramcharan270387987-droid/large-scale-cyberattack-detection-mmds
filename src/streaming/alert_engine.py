"""Versioned, support-aware alert decisions over frozen reference aggregates."""

from src.streaming.shift_metrics import distribution_shifts, model_metrics, novelty


def signals(item, reference, context, config):
    """Emit monitoring measures for all windows and alerts only for held-out evidence."""
    unsupported = item["rows"] < config["minimum_window"]
    candidates = [(kind, name, value, baseline, False, unsupported)
                  for kind, name, value, baseline in distribution_shifts(item, reference, config)]
    candidates.append(("NOVELTY_RATE", "kmeans_p99", novelty(item)["flag_rate"], novelty(reference)["flag_rate"],
                       False, unsupported))
    scoring = config["score_bins"]
    current = model_metrics(item["scores"]["random_forest"], scoring)
    historical = model_metrics(reference["scores"]["random_forest"], scoring)
    rare = min(item["attacks"], item["benign"], reference["attacks"], reference["benign"]) < config["minimum_per_class"]
    candidates.append(("PERFORMANCE_WARNING", "random_forest_recall", current["recall"], historical["recall"],
                       True, unsupported or rare))
    shifts, alerts = [], []
    for kind, detector, value, baseline, labels, too_small in candidates:
        threshold = config["alert_thresholds"][kind]
        support = "insufficient" if too_small or value is None or baseline is None else "supported"
        delta = None if value is None or baseline is None else (baseline - value if labels else value - baseline)
        row = context | {"category": kind, "detector": detector, "value": value, "reference_value": baseline,
                         "delta": delta, "threshold": threshold, "rows": item["rows"], "support": support,
                         "labels_used": labels, "version": config["version"]}
        shifts.append(row)
        if context["split_rank"] > 0 and support == "supported" and delta > threshold:
            alerts.append(row | {"severity": "high" if delta >= 2 * threshold else "warning",
                                 "evidence": "retrospective_labels" if labels else "distribution"})
    return shifts, alerts
