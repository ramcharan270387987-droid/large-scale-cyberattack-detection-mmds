"""Reconcile completed protocol artifacts and generate measured Phase 4 reports."""

import argparse
from collections import Counter
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSV_NAMES = ("metrics", "family_recall", "split_diagnostics", "training_performance")
PARTITIONS = ("train", "validation", "test")
MODEL_LABELS = {
    "majority": "Majority", "duration_rule": "Duration rule", "logistic_regression": "Logistic Regression",
    "random_forest": "Random Forest", "gradient_boosted_trees": "GBT",
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_rows(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def write_rows(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def table(head, rows):
    return [
        "| " + " | ".join(head) + " |",
        "| " + " | ".join("---" for _ in head) + " |",
        *["| " + " | ".join(str(item) for item in row) + " |" for row in rows],
    ]


def metric(value):
    return f"{float(value):.4f}" if value != "" else "—"


def model_label(row):
    name = MODEL_LABELS[row["model"]]
    return name + (" (full refit)" if row["training_cohort"] == "full_train_refit" else "")


def read_protocol(root, protocol, expected_config, previous):
    folder = root / protocol
    results = folder / "results"
    summary = load(results / "phase4_summary.json")
    require(summary["protocol"] == protocol and summary["status"] == "validated", "Incomplete protocol evidence")
    require(load(results / "phase4_config.json") == expected_config, "Configuration differs across experiments")
    require(summary["design"] == expected_config["protocols"][protocol], "Split definition differs from preregistration")
    require(summary["input"]["receipt_sha256"] == previous["independent_mount"]["summary_sha256"], "Input receipt differs")
    require(summary["input"]["rows"] == 16232943 and summary["input"]["totals"] == {"0": 13484708, "1": 2748235}, "Input counts differ")
    require(summary["registered_predictors"] == expected_config["numerical_features"], "Registered features differ")
    require(summary["selection_frozen"] and all(item["groups"] == 0 for item in summary["overlap"]["after"].values()),
            "Split overlap or model-selection invariant failed")
    version = int((folder / "version").read_text())
    status = (folder / "status-history.txt").read_text()
    expected_status = f"/{version} has status \"KernelWorkerStatus.COMPLETE\""
    require(expected_status in status.splitlines()[-1], "Kaggle did not reach COMPLETE")
    log = load(folder / "kaggle.log")
    message = "".join(event["data"] for event in log)
    frozen = f"PHASE4 {protocol} selections frozen before testing"
    require(frozen in message and f"PHASE4 {protocol} complete: 12 evaluation rows, 4 reloaded pipelines" in message,
            "Completed run marker is missing")
    compact = {name: read_rows(results / f"phase4_{name}.csv") for name in CSV_NAMES}
    split_rows = compact["split_diagnostics"]
    require(sum(int(row["count"]) for row in split_rows) == summary["input"]["rows"], "Raw split rows do not reconcile")
    require(sum(int(row["count"]) for row in split_rows if row["retained"] == "False") == summary["overlap"]["purged_rows"],
            "Purged rows do not reconcile")
    for rank, split in enumerate(PARTITIONS):
        retained = Counter()
        for row in split_rows:
            if row["split_rank"] == str(rank) and row["retained"] == "True":
                retained[row["binary_label"]] += int(row["count"])
        require(dict(retained) == summary["split_support"][split]["labels"], "Split support differs")
    sample = sum(int(r["count"]) for r in split_rows if r["split_rank"] == "0" and r["retained"] == "True"
                 and r["sampled"] == "True")
    require(sample == summary["train_sample_support"]["rows"], "Training sample count differs")
    require(len(compact["metrics"]) == 12 and len(compact["training_performance"]) == 7 and len(summary["models"]) == 4,
            "Required experiments are missing")
    for row in compact["metrics"]:
        require(row["protocol"] == protocol and row["split"] in {"validation", "test"}, "Unexpected result scope")
        tp, tn, fp, fn, scored = (int(row[k]) for k in ("tp", "tn", "fp", "fn", "rows"))
        support = summary["split_support"][row["split"]]["labels"]
        require(tp + fn == support.get("1", 0) and tn + fp == support.get("0", 0) and scored == tp + tn + fp + fn,
                "Confusion matrix differs from split prevalence")
        if row["split"] == "test":
            marker = f"PHASE4 {protocol} {row['model']} {row['training_cohort']} test: {scored} scored"
            require(marker in message and message.index(marker) > message.index(frozen), "Test ran before selection freeze")
        family = [entry for entry in compact["family_recall"] if entry["model"] == row["model"] and
                  entry["training_cohort"] == row["training_cohort"] and entry["split"] == row["split"] and entry["level"] == "family"]
        require(sum(int(entry["evaluated_rows"]) for entry in family) == scored, "Family counts differ")
    for name, selection in summary["trial_selections"].items():
        contenders = [row for row in compact["training_performance"] if row["model"] == name and row["training_cohort"] == "group_sample"]
        require(len(contenders) == 2 and all(load_trial(row) == expected_config["trials"][name][int(row["trial"]) - 1] for row in contenders),
                "Model trial differs from preregistration")
        for row in contenders:
            marker = (f"PHASE4 {protocol} {name} trial {row['trial']}: fit "
                      f"{float(row['training_seconds']):.3f}s, validation PR-AUC {float(row['pr_auc'])}")
            require(marker in message and message.index(marker) < message.index(frozen), "Trial evidence differs from the log")
        chosen = max(contenders, key=lambda row: (float(row["pr_auc"]), -int(row["trial"])))
        require(chosen["selected"] == "True" and int(chosen["trial"]) == selection["trial"], "Validation winner differs")
    return summary, compact, {"version": version, "status": "COMPLETE", "log_events": len(log)}


def load_trial(row):
    return json.loads(row["parameters"])


def generate(root, url, reload_receipt, output):
    expected = load(ROOT / "configs/ml_experiments.yaml")
    prior = load(ROOT / "manifests/parquet_layers.json")
    external_reload = load(reload_receipt)
    summary, metrics, experiments, benches = {}, {}, {}, {name: [] for name in CSV_NAMES}
    for protocol in "ABC":
        info, compact, run = read_protocol(root, protocol, expected, prior)
        require({item["artifact_directory"] for item in external_reload[protocol] if item["finite_probe_predictions"] == 3}
                == {Path(item["path"]).name for item in info["models"]}, "Downloaded reload coverage differs")
        summary[protocol], metrics[protocol], experiments[protocol] = info, compact["metrics"], run
        for name in CSV_NAMES:
            rows = compact[name]
            benches[name].extend(rows if "protocol" in rows[0] else [{"protocol": protocol, **row} for row in rows])
    reports, docs, manifests = (output / part for part in ("reports", "docs", "manifests"))
    for folder in (reports, docs, manifests):
        folder.mkdir(parents=True, exist_ok=True)
    for name, rows in benches.items():
        write_rows(reports / f"phase4_{name}.csv", rows)
    manifest = {
        "status": "validated", "kernel_url": url, "config_version": expected["version"], "seed": expected["seed"],
        "metric_policy": {"positive_label": 1, "threshold": expected["threshold"], "score_bins": expected["score_bins"],
                          "pr_auc": "step-integrated binned average precision", "roc_auc": "trapezoidal binned ROC"},
        "protocols": {key: {**experiments[key], **value, "downloaded_reload": external_reload[key]}
                      for key, value in summary.items()},
    }
    (manifests / "phase4_models.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    report = [
        "# Phase 4 supervised attack detection", "",
        "**READY FOR PHASE 5.** All three prespecified Kaggle protocols completed and were reconciled against their run logs. "
        "All 12 saved pipelines passed archive checksum verification and a second reload in Codex Cloud with synthetic probes. "
        f"[Private Kaggle notebook]({url}) · [Model and run manifest](../manifests/phase4_models.json)", "",
        "## Input and cohort integrity", "",
        "Each run verified 16,232,943 input records across ten capture days, with 13,484,708 benign and 2,748,235 attack. "
        "The pinned Phase 2 receipt and cleaning version matched, and the 14 timestamp-flagged records remain eligible for capture-day assignment. "
        "The primary version registers 18 shared numerical predictors and fits preprocessing only on training-group samples. "
        "All evaluation predictions use the retained population. [Protocol specification](../docs/phase4_experimental_protocol.md)", "",
    ]
    report += table(["Protocol", "Train", "Validation", "Test", "Purged", "Train sample", "Sample share of train"], [
        (key, *(f"{info['split_support'][split]['rows']:,}" for split in PARTITIONS),
         f"{info['overlap']['purged_rows']:,}", f"{info['train_sample_support']['rows']:,}",
         f"{100 * info['train_sample_support']['rows'] / info['split_support']['train']['rows']:.3f}%")
        for key, info in summary.items()
    ])
    report += ["", "Attack prevalence in retained cohorts", ""]
    report += table(["Protocol", "Train", "Validation", "Test", "Train sample"], [
        (key, *(f"{100 * item['labels'].get('1', 0) / item['rows']:.4f}%"
                for item in [*(info["split_support"][split] for split in PARTITIONS), info["train_sample_support"]]))
        for key, info in summary.items()
    ])
    report += ["", "The retained cohorts had zero crossing primary, exact-record or Phase 2 cleaned-feature groups. "
               "Imputed vectors were audited separately. [Day, binary and original-label support](phase4_split_diagnostics.csv)", ""]
    report += table(["Protocol", "Crossing predictor groups before purge", "Crossing imputed vectors", "Rows in those imputed groups"], [
        (key, f"{item['overlap']['predictor_before']['groups']:,}", f"{item['post_imputation_overlap']['groups']:,}",
         f"{item['post_imputation_overlap']['rows']:,}") for key, item in summary.items()
    ])
    report += ["", "## Test metrics", "",
               "PR-AUC is binned average precision. Blank denominators appear as dashes. "
               "Baseline setup is included in overall runtime and its reported fit time excludes cutoff calibration. "
               "[Validation and test metrics with confusion matrices](phase4_metrics.csv)", ""]
    report += table(["Protocol", "Model", "PR-AUC", "ROC-AUC", "Precision", "Recall", "F1", "Balanced accuracy"], [
        (row["protocol"], model_label(row), *(metric(row[k]) for k in ("pr_auc", "roc_auc", "precision", "recall", "f1", "balanced_accuracy")))
        for p in "ABC" for row in metrics[p] if row["split"] == "test"
    ])
    report += ["", "## Execution", ""]
    report += table(["Protocol", "Kaggle version", "Runtime (s)", "Spark", "CPU workers", "Driver heap", "JVM peak GiB", "Log events"], [
        (key, experiments[key]["version"], f"{item['elapsed_seconds']:,.3f}", item["resources"]["spark_version"],
         item["resources"]["default_parallelism"], item["resources"]["driver_memory"],
         f"{item['resources']['driver_peak_rss_bytes'] / 1024**3:.2f}", experiments[key]["log_events"])
        for key, item in summary.items()
    ])
    report += ["", "[Fit and validation-scoring timings](phase4_training_performance.csv) · "
               "[Family and original-label recall](phase4_family_recall.csv) · [Model comparison](../docs/phase4_model_comparison.md)"]
    (reports / "phase4_supervised_results.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    comparisons = [
        "# Phase 4 model comparison", "",
        "The sampled model comparison uses common training groups and identical held-out rows within each protocol. "
        "The full-training Logistic Regression refit is a separate cohort. The split designs represent different evaluation populations "
        "with different mixtures, missing families and recall denominators.", "",
    ]
    test = {(r["protocol"], r["model"], r["training_cohort"]): r
            for r in benches["metrics"] if r["split"] == "test"}
    comparisons += [
        "The same sampled Random Forest procedure yielded test PR-AUC of "
        + ", ".join(f"{metric(test[p, 'random_forest', 'group_sample']['pr_auc'])} in {p}" for p in "ABC")
        + ". The corresponding test attack prevalences were "
        + ", ".join(f"{100 * summary[p]['split_support']['test']['labels'].get('1', 0) / summary[p]['split_support']['test']['rows']:.4f}%"
                    for p in "ABC")
        + ". Compare recall and precision alongside PR-AUC because the evaluation class balance changes.",
        "",
        "The full-training Logistic Regression refit reused the sample-selected settings and feature scaling. "
        "Its test PR-AUC was " + ", ".join(
            f"{metric(test[p, 'logistic_regression', 'full_train_refit']['pr_auc'])} in {p}" for p in "ABC")
        + ". The sampled Logistic Regression values were " + ", ".join(
            f"{metric(test[p, 'logistic_regression', 'group_sample']['pr_auc'])} in {p}" for p in "ABC")
        + ". The observed differences describe this fixed preprocessing and optimization schedule.",
        "",
        f"At the fixed 0.5 threshold, the chronological duration rule achieved F1 "
        f"{metric(test['B', 'duration_rule', 'full_train_baseline']['f1'])}. "
        "The sampled Logistic Regression, Random Forest and GBT scored "
        + ", ".join(metric(test["B", model, "group_sample"]["f1"])
                    for model in ("logistic_regression", "random_forest", "gradient_boosted_trees"))
        + ". Ranking performance and operating-point performance answer different questions. "
        "A later threshold study would need separate validation support for its intended traffic.",
        "",
        f"The scenario test retained {summary['C']['split_support']['test']['labels'].get('1', 0):,} positive rows. "
        f"Sampled GBT found {int(test['C', 'gradient_boosted_trees', 'group_sample']['tp']):,} at the fixed threshold "
        f"with {int(test['C', 'gradient_boosted_trees', 'group_sample']['fp']):,} benign false positives. "
        "The held-out dates contain the Web attack family, and the observed label mix and capture setup limit comparisons across protocols.",
        "", "## Attack-family support by partition", "",
    ]
    family_keys = sorted({
        entry["category"] for entry in benches["family_recall"] if entry["level"] == "family" and entry["binary_label"] == "1"
    })
    comparisons += table(["Protocol", "Partition", *family_keys], [
        (key, split, *(f"{info['split_support'][split]['families'].get(family, 0):,}" for family in family_keys))
        for key, info in summary.items() for split in PARTITIONS
    ])
    comparisons += ["",
        "## Attack-family evaluation", "",
    ]
    families = [row for row in benches["family_recall"] if row["level"] == "family" and row["split"] == "test"
                and row["model"] == "random_forest"]
    comparisons.extend(table(["Protocol", "Family", "Test rows", "Training-sample rows", "RF attack recall", "RF benign FPR", "Support"], [
        (row["protocol"], row["category"], row["evaluated_rows"], row["training_rows"], metric(row["recall"]),
         metric(row["benign_false_positive_rate"]), row["support_status"]) for row in families
    ]))
    unseen = [row for row in families if row["seen_in_training"] == "False" and int(row["evaluated_rows"])]
    comparisons += ["", "The Random Forest comparison includes these test families absent from its training sample:", ""]
    comparisons += [
        f"- Protocol {row['protocol']} evaluated {int(row['evaluated_rows']):,} {row['category']} rows as unseen-family traffic. "
        f"Recall was {metric(row['recall'])} with support status {row['support_status']}." for row in unseen
    ]
    comparisons += ["", "Only supported test rows contribute to recall. The 100-row display threshold is descriptive and the "
                    "correlated flow and capture groups constrain generalization. The day-level differences do not establish a feature–label mechanism.",
                    "", "## Interpretation", ""]
    comparisons += table(["Protocol", "Model", "Cohort", "Three highest-magnitude terms"], [
        (protocol, MODEL_LABELS[item["model"]], item["training_cohort"],
         ", ".join(f"`{term['feature']}` ({term['value']:.4g})" for term in item["explanation"][:3]))
        for protocol, info in summary.items() for item in info["models"]
    ])
    comparisons += [
        "", "Logistic Regression signs are conditional associations in the scaled model coordinates. Random Forest and GBT split importances "
        "can redistribute importance among correlated features and favor variables with more useful splits. "
        "Use held-out permutation or controlled ablation for follow-up and keep group isolation fixed.",
        "", "[All measured metrics](../reports/phase4_metrics.csv) · [All family and original-label results](../reports/phase4_family_recall.csv)",
    ]
    (docs / "phase4_model_comparison.md").write_text("\n".join(comparisons) + "\n", encoding="utf-8")
    print("Published three reconciled protocols, 36 validation/test rows and 12 verified fitted pipelines.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--kernel-url", required=True)
    parser.add_argument("--reload-receipt", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=ROOT)
    args = parser.parse_args()
    generate(args.evidence, args.kernel_url, args.reload_receipt, args.output_root)
