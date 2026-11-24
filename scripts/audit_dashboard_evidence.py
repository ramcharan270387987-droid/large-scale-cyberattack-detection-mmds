"""Reconcile published dashboard evidence without rerunning research workloads."""

from collections import Counter, defaultdict
import csv
import json
from math import isclose, log2
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dashboard.validation import require, verify_package


def report(name):
    with (ROOT / "reports" / f"{name}.csv").open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def manifest(name):
    return json.loads((ROOT / "manifests" / f"{name}.json").read_text())


def scalar(value):
    return None if value in ("", None) else float(value)


def equal(actual, expected):
    actual, expected = scalar(actual), scalar(expected)
    return actual is expected if actual is None or expected is None else isclose(actual, expected, abs_tol=1e-12)


def rate(numerator, denominator):
    return numerator / denominator if denominator else None


def totals(rows, name, field):
    grouped = Counter()
    for row in rows:
        grouped[row[name]] += int(row[field])
    return grouped


def confusion_rates(row):
    tp, tn, fp, fn = (int(row[name]) for name in ("tp", "tn", "fp", "fn"))
    require(min(tp, tn, fp, fn) >= 0 and int(row["rows"]) == tp + tn + fp + fn, "Invalid confusion counts")
    recall, specificity = rate(tp, tp + fn), rate(tn, tn + fp)
    return {"accuracy": rate(tp + tn, tp + tn + fp + fn), "recall": recall,
            "precision": rate(tp, tp + fp), "specificity": specificity,
            "f1": rate(2 * tp, 2 * tp + fp + fn),
            "balanced_accuracy": (recall + specificity) / 2 if recall is not None and specificity is not None else None}


def require_fields(row, expected, message):
    require(all(equal(row[key], value) for key, value in expected.items()), message)


def novelty_rates(row, family=False):
    attack, benign, tp, fp, flags, n = (int(row[k]) for k in ("attacks", "benign", "tp", "fp", "flags", "rows"))
    require(0 <= tp <= attack and 0 <= fp <= benign and flags == tp + fp and n == attack + benign,
            "Invalid novelty counts")
    require_fields(row, {"flag_rate": rate(flags, n), "benign_fpr": rate(fp, benign),
                         "attack_recall": rate(tp, attack), "precision": None if family else rate(tp, flags)},
                   "Incorrect novelty percentage")


def js_bits(left, right):
    n, m = sum(left), sum(right)
    require(n > 0 and m > 0 and len(left) == len(right), "Invalid JS comparison populations")
    answer = 0
    for count_a, count_b in zip(left, right):
        a, b = count_a / n, count_b / m
        for mass in (a, b):
            if mass:
                answer += .5 * mass * log2(2 * mass / (a + b))
    return answer


def audit_dataset(summary):
    raw = report("dataset_file_statistics")
    labels = report("dataset_label_distribution")
    processed = report("phase2_count_reconciliation")
    daily = report("phase3_daily_traffic")
    require(totals(raw, "capture_day", "parsed") == totals(processed, "source_day", "canonical") ==
            totals(daily, "source_day", "records"), "Phase 1–3 capture totals differ")
    require(totals(labels, "proposed_family", "count") == totals(report("phase3_original_labels"), "attack_family", "records"),
            "Audited family totals differ")
    binary = totals(labels, "proposed_binary", "count")
    t = summary["dataset"]["totals"]
    require(binary == {"benign": t["benign"], "attack": t["attack"]}, "Audited class counts differ")
    require(all(int(r["canonical"]) == int(r["clean"]) == int(r["feature_ready"]) for r in processed),
            "Parquet layers differ")
    require(sum(int(r["timestamp_outlier"]) for r in processed) == int(report("phase3_duplicate_quality")[0]["temporal_ineligible"]),
            "Anomaly counts differ")
    for row in daily:
        n = int(row["records"])
        require(n == int(row["benign"]) + int(row["attacks"]), "Capture labels do not reconcile")
        require_fields(row, {"attack_share": int(row["attacks"])/n}, "Attack prevalence differs")
    for name, capture_field in (("packet_count", "packet_count"), ("byte_count", "byte_count")):
        require(equal(sum(float(r[capture_field]) for r in daily),
                      sum(float(r[name]) for r in report("phase3_traffic_totals"))), "Traffic volume differs")
    for row in report("phase3_feature_missingness"):
        require(0 <= int(row["missing"]) <= int(row["records"]) == sum(binary.values()), "Missingness denominator differs")
    for row in report("phase3_feature_statistics"):
        qs = json.loads(row["quantiles"])
        require(float(row["min"]) <= min(qs) and max(qs) <= float(row["max"]) and qs == sorted(qs)
                and 0 < int(row["valid"]) <= int(row["population_count"]), "Invalid feature distribution")
    for row in report("phase3_correlations"):
        require(-1 <= float(row["pearson"]) <= 1 and 0 < int(row["pairs"]) <= sum(binary.values()), "Invalid correlation")
    for row in report("phase3_destination_ports"):
        require(0 <= int(row["records"]) <= int(row["population_records"]) <= sum(binary.values()) and
                0 <= float(row["dst_port"]) <= 65535, "Invalid port summary")


def audit_supervised():
    models = report("phase4_metrics")
    families = report("phase4_family_recall")
    for row in models:
        require_fields(row, confusion_rates(row), "Phase 4 confusion-derived metric differs")
        require(all(0 <= float(row[key]) <= 1 for key in ("roc_auc", "pr_auc") if row[key]), "Invalid ranking metric")
        match = [r for r in families if all(r[k] == row[k] for k in ("protocol", "split", "model", "training_cohort"))
                 and r["level"] == "family"]
        require(sum(int(r["evaluated_rows"]) for r in match) == int(row["rows"]), "Family coverage differs")
        require(sum(int(r["tp"] or 0) for r in match) == int(row["tp"]) and
                sum(int(r["fp"] or 0) for r in match) == int(row["fp"]), "Family confusion differs")
    for row in families:
        if row["binary_label"] == "1":
            require_fields(row, {"recall": rate(int(row["tp"]), int(row["evaluated_rows"]))}, "Family recall differs")
        else:
            require_fields(row, {"benign_false_positive_rate": rate(int(row["fp"]), int(row["evaluated_rows"]))},
                           "Family FPR differs")
    return models


def audit_clustering():
    experiments = manifest("phase5_clustering_models")["experiments"]
    occupancy = defaultdict(Counter)
    for row in report("phase5_cluster_occupancy"):
        key = (row["experiment"], row["source_day"], row["window_hour"])
        occupancy[key][int(row["cluster"])] = int(row["records"])
    for row in report("phase5_cluster_occupancy"):
        key = (row["experiment"], row["source_day"], row["window_hour"])
        require_fields(row, {"occupancy": int(row["records"]) / sum(occupancy[key].values())}, "Occupancy share differs")
    for row in report("phase5_temporal_shift"):
        exp, day, window = (row[k] for k in ("experiment", "source_day", "window_hour"))
        ref = experiments[exp]["reference_occupancy"]
        window_counts = occupancy[exp, day, window]
        require_fields(row, {"js_divergence_bits": js_bits([window_counts[i] for i in range(len(ref))], ref),
                             "reference_rows": sum(ref), "rows": sum(window_counts.values())}, "Phase 5 window shift differs")
    for row in report("phase5_model_selection"):
        spec = experiments[row["experiment"]]
        sizes = json.loads(row["cluster_sizes"])
        require_fields(row, {"training_rows": sum(sizes), "smallest_share": min(sizes)/sum(sizes),
                             "empty_clusters": sizes.count(0)}, "Fit cluster counts differ")
        require((row["selected"] == "True") == (int(row["k"]) == spec["selected_k"]), "Selected fit differs")
        result = next(trial for trial in spec["trials"] if trial["k"] == int(row["k"]))
        require_fields(row, {k: result[k] for k in ("training_rows", "silhouette", "wssse")}, "Fit statistic differs")
    for row in report("phase5_cluster_profiles"):
        require_fields(row, {"attack_share": int(row["attacks"])/int(row["records"])}, "Cluster attack prevalence differs")
    novel = report("phase5_novelty_metrics")
    histograms = Counter()
    for row in report("phase5_score_histogram"):
        histograms[row["experiment"], row["split_rank"], row["binary_label"]] += int(row["count"])
    for row in novel:
        novelty_rates(row, row["scope"] == "family")
        if row["scope"] == "binary":
            prefix = (row["experiment"], row["split_rank"])
            require(int(row["attacks"]) == histograms[prefix + ("1",)] and
                    int(row["benign"]) == histograms[prefix + ("0",)], "Distance histogram support differs")
    return novel


def audit_replay(models, novel):
    replay = manifest("phase6_replay_runs")
    reference = replay["scopes"]["train"]
    config = replay["config"]
    windows = {(r["scope"], r["source_day"], r["window_hour"]): r for r in report("phase6_window_metrics")}
    for row in windows.values():
        n = int(row["rows"])
        require(sum(json.loads(row["cluster_counts"])) == sum(json.loads(row["rf_score_counts_32"])) ==
                int(row["attacks"]) + int(row["benign"]) == n, "Replay window counts differ")
        for model in json.loads(row["classifier_metrics"]).values():
            require_fields(model, confusion_rates(model) | {"predicted_positive": model["tp"] + model["fp"],
                                                            "predicted_rate": (model["tp"] + model["fp"])/n},
                           "Replay classifier rates differ")
        novelty_rates(json.loads(row["novelty_metrics"]))
    for row in report("phase6_performance"):
        require_fields(row, {"rows_per_second": int(row["rows"])/float(row["elapsed_seconds"])}, "Replay throughput differs")
    candidates = []
    for row in report("phase6_shift_metrics"):
        window = windows[row["scope"], row["source_day"], row["window_hour"]]
        kind = row["category"]
        threshold = config["alert_thresholds"][kind]
        expected = {"threshold": threshold, "rows": window["rows"]}
        labels_used = kind == "PERFORMANCE_WARNING"
        require((row["labels_used"] == "True") == labels_used, "Alert label provenance differs")
        if kind == "CLUSTER_SHIFT":
            expected["value"] = js_bits(json.loads(window["cluster_counts"]), replay["reference_cluster_occupancy"])
        elif kind == "NOVELTY_RATE":
            expected.update(value=json.loads(window["novelty_metrics"])["flag_rate"], reference_value=reference["novelty"]["flag_rate"])
        elif kind == "PERFORMANCE_WARNING":
            expected.update(value=json.loads(window["classifier_metrics"])["random_forest"]["recall"],
                            reference_value=reference["models"]["random_forest"]["recall"])
        if kind in ("INPUT_SHIFT", "SCORE_SHIFT", "CLUSTER_SHIFT"):
            expected["reference_value"] = 0
        enough_labels = min(int(window["attacks"]), int(window["benign"]), reference["attacks"], reference["benign"]) >= config["minimum_per_class"]
        supported = (int(window["rows"]) >= config["minimum_window"] and bool(row["value"]) and
                     bool(row["reference_value"]) and (not labels_used or enough_labels))
        require((row["support"] == "supported") == supported, "Alert minimum support differs")
        if row["value"] and row["reference_value"]:
            expected["delta"] = float(row["reference_value"])-float(row["value"]) if kind == "PERFORMANCE_WARNING" else float(row["value"])-float(row["reference_value"])
        require_fields(row, expected, "Shift metric differs")
        if int(row["split_rank"]) > 0 and row["support"] == "supported" and float(row["delta"]) > threshold:
            candidates.append(row | {"severity": "high" if float(row["delta"]) >= 2 * threshold else "warning",
                                     "evidence": "retrospective_labels" if row["labels_used"] == "True" else "distribution"})
    require(candidates == report("phase6_alerts"), "Severity rules do not reproduce the alert table")
    for model, actual in replay["scopes"]["test"]["models"].items():
        previous = next(r for r in models if r["protocol"] == "B" and r["split"] == "test" and r["model"] == model
                        and r["training_cohort"] != "full_train_refit")
        require_fields(actual, {k: previous[k] for k in ("tp", "tn", "fp", "fn", "roc_auc", "pr_auc")}, "Phase 4 and 6 results differ")
    previous = next(r for r in novel if (r["experiment"], r["split_rank"], r["percentile"], r["scope"]) == ("B", "2", "0.99", "binary"))
    require_fields(replay["scopes"]["test"]["novelty"], {k: previous[k] for k in ("tp", "fp", "flags", "precision", "attack_recall")},
                   "Phase 5 and 6 novelty results differ")


def audit():
    package, summary = verify_package(sources=True)
    audit_dataset(summary)
    models = audit_supervised()
    novel = audit_clustering()
    audit_replay(models, novel)
    r = summary["replay"]
    t = summary["dataset"]["totals"]
    expected = (16232943, 13484708, 2748235, 15322987, 49, 102, 62, 17770)
    observed = (t["canonical_rows"], t["benign"], t["attack"], r["rows"], r["batches"],
                r["alerts"]["count"], r["alerts"]["high"], round(r["rows_per_second"]))
    require(observed == expected, "Key dashboard totals differ from verified expectations")
    print(f"PASS: {len(package['tables'])} source tables, {len(models)} supervised results, {len(novel)} novelty rows and {r['alerts']['count']} alert decisions.")


if __name__ == "__main__":
    audit()
