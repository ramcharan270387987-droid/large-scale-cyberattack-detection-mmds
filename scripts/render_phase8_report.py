"""Reconcile independent Kaggle receipts and publish compact Phase 8 evidence."""

import argparse
from collections import Counter, defaultdict
import csv
from hashlib import sha256
import json
from math import isclose, sqrt
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.visualization.hybrid_detection_charts import build


def require(verified, message):
    if not verified:
        raise ValueError(message)


def read(path):
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


def js(path):
    return json.loads(path.read_text())


def pct(text):
    return f"{float(text):.3%}" if text not in ("", None) else "NA"


def dec(text):
    return f"{float(text):.5f}" if text not in ("", None) else "NA"


def write(path, rows):
    keys = dict.fromkeys(key for row in rows for key in row)
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=keys, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def table(columns, values):
    return ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |",
            *["| " + " | ".join(map(str, row)) + " |" for row in values]]


def check_confusion(row):
    tp, tn, fp, fn = (int(row[key]) for key in ("tp", "tn", "fp", "fn"))
    total = tp+tn+fp+fn
    require(total == int(row["rows"]) and min(tp, tn, fp, fn) >= 0, "Confusion counts differ")
    for key, num, den in (("fpr", fp, fp+tn), ("recall", tp, tp+fn), ("precision", tp, tp+fp),
                          ("f1", 2*tp, 2*tp+fp+fn), ("accuracy", tp+tn, total),
                          ("specificity", tn, tn+fp), ("fnr", fn, tp+fn), ("f2", 5*tp, 5*tp+fp+4*fn),
                          ("mcc", tp*tn-fp*fn, sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn)))):
        require(isclose(float(row[key]), num/den, abs_tol=1e-12) if den else row[key] == "", f"Wrong {key}")
    balanced = row["balanced_accuracy"]
    require(isclose(float(balanced), (tp/(tp+fn) + tn/(tn+fp))/2, abs_tol=1e-12)
            if (tp+fn)*(tn+fp) else balanced == "", "Wrong balanced accuracy")
    return tp, tn, fp, fn


def evaluate(config, known, path, summary, frozen):
    population = summary["population"]
    expected_test = sum(summary["roles"]["test"].values())
    require(expected_test == summary["scored_rows"] and summary["inference_reload_probes"] == 3, "Test and reload counts differ")
    require(all(min(summary["roles"][role].values()) >= config["minimum_per_class"] for role in ("train", "probability", "operating", "test")),
            "An indispensable role lacks sufficient support")
    require(not any(item["groups"] for item in summary["postpurge_overlap"].values()), "Source roles overlap")
    comparison = read(path / "phase8_model_comparison.csv")
    policies = read(path / "phase8_false_positive_budgets.csv")
    require(any(row["selected_hybrid"] == "True" and row["method"] == frozen["selected_hybrid"] for row in comparison),
            "Selected hybrid is not registered")
    for row in comparison:
        tp, tn, fp, fn = check_confusion(row)
        require(tp+fn == summary["roles"]["test"]["1"] and tn+fp == summary["roles"]["test"]["0"], "Population differs between methods")
        winner = next(r for r in policies if r["method"] == row["method"] and r["policy"] == row["selection"])
        require(int(winner["tp"]) == tp and int(winner["fp"]) == fp, "Frozen threshold counts differ")
    for row in policies:
        check_confusion(row)
        if row["policy"].startswith("budget_"):
            require(float(row["validation_fpr"]) <= float(row["policy"].removeprefix("budget_")), "Validation FPR over budget")
    for stem in ("ablation_results", "cost_sensitive_results", "robustness", "threshold_selection"):
        for row in read(path / f"phase8_{stem}.csv"):
            check_confusion(row)
    for row in read(path / "phase8_triage_metrics.csv"):
        counts = json.loads(row["category_counts"])
        require(sum(sum(pair) for pair in counts.values()) == expected_test, "Triage lost test rows")
        low = counts.get("LOW_RISK", [0, 0])
        high = counts.get("HIGH_RISK", [0, 0])
        require(isclose(float(row["automatic_coverage"]), (sum(low)+sum(high))/expected_test, abs_tol=1e-12),
                "Triage automatic coverage differs")
    support = Counter()
    for row in read(path / "phase8_family_recall.csv"):
        support[row["method"]] += int(row["support"])
    require(all(total == summary["roles"]["test"]["1"] for total in support.values()), "Families lost test attacks")
    paired = read(path / "phase8_paired_disagreement.csv")
    require(sum(int(row["count"]) for row in paired) == expected_test, "Paired disagreement lost rows")
    if population in ("B", "C"):
        fixed = next(r for r in policies if r["method"] == "random_forest" and r["policy"] == "fixed_0.5")
        previous = known[population, "test", "random_forest"]
        require(all(isclose(float(fixed[key]), float(previous[key]), abs_tol=1e-12)
                    for key in ("tp", "tn", "fp", "fn", "pr_auc")), "Frozen Phase 4 RF discrepancy")


def render(work, output):
    config = js(ROOT / "configs/phase8_hybrid_experiments.yaml")
    design = js(ROOT / "configs/ml_experiments.yaml")
    known = {(r["protocol"], r["split"], r["model"]): r for r in read(ROOT / "reports/phase4_metrics.csv")
             if r["training_cohort"] != "full_train_refit"}
    daily = {r["source_day"]: int(r["records"]) for r in read(ROOT / "reports/phase3_daily_traffic.csv")}
    combined, receipts, registry, supported, full = defaultdict(list), {}, {}, {}, []
    upstream = js(ROOT / "manifests/parquet_layers.json")["independent_mount"]["summary_sha256"]
    kernel = "https://www.kaggle.com/code/ramcharan2345/mmds-phase-8-robust-hybrid-cyberattack-detection"
    mirror = work / "mirror"
    require('/1 has status "KernelWorkerStatus.COMPLETE"' in (mirror / "status.txt").read_text(), "Baseline mirror did not complete")
    mirror_log = mirror / "kaggle.log"
    mirror_receipt = {"kernel_url": "https://www.kaggle.com/code/ramcharan2345/mmds-phase-8-baseline-model-mirror",
                      "kernel_version": 1, "worker_status": "COMPLETE", "log_events": len(js(mirror_log)),
                      "log_sha256": sha256(mirror_log.read_bytes()).hexdigest()}
    for key in ("baseline-B", "baseline-C", "hybrid-B", "hybrid-C", "hybrid-R1", "hybrid-R2"):
        folder = work / key
        source = folder / "results"
        summary = js(source / "phase8_summary.json")
        version = int((folder / "version").read_text())
        condition = (folder / "status-history.txt").read_text().splitlines()[-1]
        require(f'/{version} has status "KernelWorkerStatus.COMPLETE"' in condition, f"{key} did not complete")
        logs = js(folder / "kaggle.log")
        text = "".join(event["data"] for event in logs)
        stage, population = key.split("-")
        require((summary["stage"], summary["population"]) == (stage, population) and
                summary["input"]["receipt_sha256"] == upstream and summary["protocol"] == config["version"], f"{key} source changed")
        require(f"PHASE8 complete {stage} {population} status {summary['status']}" in text, f"{key} terminal marker missing")
        note = folder / "submission" / "phase8_hybrid_detection.ipynb"
        metadata = js(folder / "submission" / "kernel-metadata.json")
        sources = [config["phase2"]] + (["ramcharan2345/mmds-phase-8-baseline-model-mirror/1"] if population in ("B", "C") else [])
        require(metadata["is_private"] and not metadata["enable_gpu"] and not metadata["enable_tpu"] and
                metadata["kernel_sources"] == sources, f"{key} submission configuration changed")
        receipts[key] = summary | {"kernel_version": version, "worker_status": "COMPLETE",
                                   "submitted_sources": sources, "private_cpu": True,
                                   "notebook_sha256": sha256(note.read_bytes()).hexdigest(),
                                   "log_events": len(logs), "log_sha256": sha256((folder / "kaggle.log").read_bytes()).hexdigest(),
                                   "log_markers": [line for line in text.splitlines() if line.startswith("PHASE8 ")]}
        if stage == "baseline":
            require(summary["status"] == "validated" and summary["baseline_checks"] == 12 and
                    all(r["matches"] == "True" for r in read(source / "phase8_baseline_reconciliation.csv")), "Baseline not reconciled")
        elif summary["status"] == "validated":
            frozen_file = source / "phase8_frozen.json"
            frozen = js(frozen_file)
            require(summary["frozen_sha256"] == sha256(frozen_file.read_bytes()).hexdigest(), "Frozen model metadata differs")
            require(text.find(f"PHASE8 {population} frozen ") < text.find(f"PHASE8 {population} evaluated ") and
                    f"PHASE8 {population} frozen " in text, "Evaluation did not follow freeze")
            evaluate(config, known, source, summary, frozen)
            registry[population] = frozen | {"kernel": kernel, "kernel_version": version,
                                             "validated_reload_probes": summary["inference_reload_probes"],
                                             "saved_pipelines": summary["registry"],
                                             "archived_baselines": summary.get("baseline_models"),
                                             "training_dates": (design["protocols"].get(population) or config["rolling"][population])["train"]}
            supported[population] = summary
            full.append(population)
        else:
            require(summary["status"] == "unsupported" and summary["unsupported_roles"], "Unknown stage result")
        for file in sorted(source.glob("phase8_*.csv")):
            for row in read(file):
                if file.stem == "phase8_model_comparison":
                    rows_original = sum(daily[day] for day in (design["protocols"].get(population) or config["rolling"][population])["test"])
                    row["share_of_retained_cohort"] = row["evaluation_coverage"]
                    row["evaluation_coverage"] = int(row["rows"]) / rows_original
                    row["original_test_rows"] = rows_original
                combined[file.stem].append({"population": population, "stage": stage, **row})
        if population in supported and stage == "hybrid":
            base = summary["supervised_base"]
            curve = {float(r["threshold"]): r for r in read(source / "phase8_score_curves.csv")
                     if r["partition"] == "test" and r["method"] == "supervised"}
            low, high = curve[1/16], curve[15/16]
            labels = summary["roles"]["test"]
            combined["phase8_error_audit"].append({
                "population": population, "model": base, "score": "Platt calibrated supervised",
                "low_cutoff_exclusive": 1/16, "high_cutoff_inclusive": 15/16,
                "attacks_below_low_cutoff": round(labels["1"] * (1-float(low["recall"]))),
                "benign_at_or_above_high_cutoff": round(labels["0"] * float(high["fpr"])),
                "attack_support": labels["1"], "benign_support": labels["0"],
            })

    reports, manifests = (output / p for p in ("reports", "manifests"))
    reports.mkdir(parents=True, exist_ok=True)
    manifests.mkdir(parents=True, exist_ok=True)
    family_reference = {(r["population"], r["family"]): r["recall"] for r in combined["phase8_family_recall"]
                        if r["method"] == "supervised"}
    for row in combined["phase8_family_recall"]:
        reference_recall = family_reference[row["population"], row["family"]]
        if row["recall"] != "" and reference_recall != "":
            delta = float(row["recall"])-float(reference_recall)
            row["recall_delta_vs_calibrated_supervised"] = delta
            row["relative_recall_delta_vs_calibrated_supervised"] = delta / float(reference_recall) if float(reference_recall) else None
    for name, rows in combined.items():
        write(reports / f"{name}.csv", rows)
    figures = build(reports, supported)
    common = {"protocol_version": config["version"], "evidence_schema": "phase8-aggregate-v1", "kernel_url": kernel, "figures": figures}
    (manifests / "phase8_models.json").write_text(json.dumps(common | {"populations": registry}, indent=2) + "\n")
    hashes = {p.name: sha256(p.read_bytes()).hexdigest() for p in sorted(reports.glob("phase8_*.csv"))}
    figure_hashes = {name: sha256((reports / name).read_bytes()).hexdigest() for name in figures}
    (manifests / "phase8_experiments.json").write_text(json.dumps(common | {"runs": receipts, "tables_sha256": hashes,
                                        "figures_sha256": figure_hashes, "baseline_mirror": mirror_receipt,
                                        "baseline_revision": "16ef2c23bbfe33c497d32863173455185fe868ed"}, indent=2) + "\n")

    report = ["# Phase 8 hybrid detection results", "",
              "The B and C experiments are retrospective benchmarks. The R folds use strictly earlier fit and "
              "calibration dates within the same previously examined corpus. All results below use the same retained rows within each population.",
              "", f"[Private Kaggle CPU notebook]({kernel}) · [Run receipts](../manifests/phase8_experiments.json)", "",
              "## Execution and eligibility", ""]
    report += table(("Stage", "Version", "Result", "Seconds", "JVM peak GiB"), [
        (key, s["kernel_version"], s["status"], f"{s['elapsed_seconds']:.1f}", f"{s['driver_peak_rss_bytes']/2**30:.2f}")
        for key, s in receipts.items()])
    report += ["", "Both retrospective stages verified their Phase 2 receipt and reproduced the 12 Phase 4/5 validation and test comparisons per population.",
               "[Baseline reconciliation](phase8_baseline_reconciliation.csv)", ""]
    for key, s in receipts.items():
        if s["status"] == "unsupported":
            roles = ", ".join(s["unsupported_roles"])
            report += [f"{s['population']} was unsupported for {roles}. The prespecified minimum was 100 benign and 100 attack rows "
                       "in each indispensable role after the source-key purge.", ""]
    reference = combined["phase8_model_comparison"]
    conclusions = []
    contributions = []
    for population in full:
        data = {r["method"]: r for r in reference if r["population"] == population}
        summary = supported[population]
        base, hybrid = summary["supervised_base"], summary["selected"]
        ablation = {r["component"]: r for r in combined["phase8_ablation_results"] if r["population"] == population}
        selection = [("Random Forest at 0.5", ablation["A"]), ("Budget-selected Random Forest", ablation["B"]),
                     (f"Best LR ({summary['best_lr']})", data[summary["best_lr"]]),
                     (f"Best weighted ({summary['best_weighted']})", data[summary["best_weighted"]]),
                     ("Calibrated supervised", data["supervised"]), ("Novelty only", data["novelty"]),
                     (f"Selected fusion ({hybrid})", data[hybrid])]
        report += [f"## {population} held-out evaluation", "",
                   f"The operating split selected **{base}** as its supervised base and **{hybrid}** as its fusion. "
                   f"Training used {summary['training_sample_rows']:,} grouped sample rows. "
                   f"Evaluation retained {pct(data[hybrid]['evaluation_coverage'])} of originally assigned test rows.", ""]
        if registry[population]["learned"] is None:
            meta_support = summary["roles"].get("meta", {})
            report += [f"Learned fusion was skipped. The disjoint meta-training role retained {meta_support.get('0', 0):,} benign "
                       f"flows and {meta_support.get('1', 0):,} attack flows. The minimum was {config['minimum_per_class']} per class.", ""]
        costs = {r["model"]: r for r in combined["phase8_cost_sensitive_results"] if r["population"] == population}
        archived_cost = {r["baseline"]: r["seconds"] for r in combined["phase8_baseline_reconciliation"]
                         if r["population"] == population and r["partition"] == "test" and r["seconds"]}
        timings = {r["stage"]: r for r in combined["phase8_performance"] if r["population"] == population}
        base_seconds = float(timings["supervised_matched"]["seconds"])
        hybrid_seconds = float(timings["hybrid_matched"]["seconds"])
        def scoring_cost(method):
            if method == hybrid:
                return f"{hybrid_seconds:.2f}s held out"
            if method == base:
                return f"{base_seconds:.2f}s held out (raw base)"
            if method in costs:
                return f"{float(costs[method]['scoring_seconds']):.2f}s operating"
            if method in archived_cost:
                return f"{float(archived_cost[method]):.2f}s baseline pass"
            return "Shared Spark pass"
        report += table(("Method", "Precision", "Recall", "F1", "Binned PR-AUC", "Benign FPR", "Rows", "Scoring time"),
                        [(name, pct(row["precision"]), pct(row["recall"]), dec(row["f1"]),
                          dec(row["pr_auc"]), pct(row["fpr"]), f"{int(row['rows']):,}", scoring_cost(row["method"])) for name, row in selection])
        supervised, candidate = data["supervised"], data[hybrid]
        delta_recall = float(candidate["recall"]) - float(supervised["recall"])
        delta_fpr = float(candidate["fpr"]) - float(supervised["fpr"])
        conclusions.append((population, delta_recall, delta_fpr))
        review = next(r for r in combined["phase8_triage_metrics"] if r["population"] == population and r["policy"] == "primary")
        policies = {(r["method"], r["policy"]): r for r in combined["phase8_false_positive_budgets"] if r["population"] == population}
        frozen_policy = policies[hybrid, candidate["selection"]]
        weighted = data[summary["best_weighted"]]
        unweighted = data[summary["best_weighted"].split("_", 1)[0] + "_w1"]
        def difference(a, b, metric):
            return f"{100*(float(a[metric])-float(b[metric])):+.3f} pp"
        contributions.append((population, difference(ablation["B"], ablation["A"], "recall"),
                              difference(ablation["B"], ablation["A"], "fpr"),
                              difference(weighted, unweighted, "recall"), difference(weighted, unweighted, "fpr"),
                              difference(candidate, supervised, "recall"), difference(candidate, supervised, "fpr"),
                              difference(candidate, data["novelty"], "recall"), difference(candidate, data["novelty"], "fpr"),
                              pct(1-float(candidate["accuracy"])), pct(review["automatic_error_rate"]),
                              pct(review["automatic_coverage"]), pct(review["review_rate"]),
                              f"{hybrid_seconds/base_seconds:.2f}×"))
        report += ["", f"Against calibrated supervised scoring, selected fusion changed recall by {delta_recall*100:+.3f} percentage points "
                   f"and realized benign FPR by {delta_fpr*100:+.3f} points. At its frozen operating point it produced "
                   f"{float(candidate['false_per_1000000']):,.0f} false alarms per million benign flows. Triage referred "
                   f"{float(review['review_per_100000']):,.0f} rows per 100,000 flows for review and automatically covered "
                   f"{pct(review['automatic_coverage'])}. The frozen cutoff was {dec(candidate['threshold'])} "
                   f"and the validation FPR was {pct(frozen_policy['validation_fpr'])}.", "",
                   f"The measured base and selected-fusion scoring passes took {base_seconds:.2f}s and {hybrid_seconds:.2f}s "
                   f"over the same {summary['scored_rows']:,} rows. These timings cover the selected methods and include Spark execution overhead.", ""]
        calibration = [r for r in combined["phase8_calibration_metrics"] if r["population"] == population and r["partition"] == "test"]
        report += table(("Probability method", "Rows", "Brier", "Log loss", "ECE"),
                        [(r["method"], f"{int(r['rows']):,}", dec(r["brier"]), dec(r["log_loss"]), dec(r["ece"])) for r in calibration]) + [""]
        platt = registry[population]["calibration"]["platt"]
        report += [f"The probability-split Platt fit used a slope of {platt['slope']:+.5f} and intercept of {platt['intercept']:+.5f} "
                   "on raw-score bin midpoints. A negative slope reverses the fitted score ordering before binning.", ""]
        family = {(r["method"], r["family"]): r for r in combined["phase8_family_recall"] if r["population"] == population}
        categories = [(label, r) for (method, label), r in family.items() if method == hybrid and int(r["support"]) > 0]
        report += table(("Attack family", "Support", "Seen in training", "Calibrated recall", "Weighted recall",
                         "Novelty recall", "Fusion recall", "Fusion referred or abstained"),
                        [(label, f"{int(r['support']):,}", r["seen_in_training"], pct(family["supervised", label]["recall"]),
                          pct(family[summary["best_weighted"], label]["recall"]), pct(family["novelty", label]["recall"]),
                          pct(r["recall"]), r["hybrid_referred"]) for label, r in categories]) + [""]
    gains = [(r, f) for _, r, f in conclusions if r > 1e-10 and f <= 1e-10]
    conclusion = ("Results were mixed across populations." if gains and len(gains) < len(conclusions) else
                  "Selected fusion improved the held-out recall–FPR tradeoff in each supported population." if gains else
                  "Selected fusion did not demonstrate a recall gain without added false positives in the supported populations.")
    report += ["## Scientific interpretation", "", conclusion,
               "This comparison uses validation-selected thresholds. A validation FPR ceiling can differ materially from achieved held-out FPR.",
               "The score calibration experiments use midpoint-binned probability estimates. Binned ranking metrics and capture-day comparisons "
               "do not provide row-independent uncertainty intervals. The paired disagreement table preserves same-row categorical counts.", "",
               "[Probability calibration](phase8_calibration_metrics.csv) · [Family coverage](phase8_family_recall.csv) · "
               "[Operating budgets](phase8_false_positive_budgets.csv) · [Ablations](phase8_ablation_results.csv) · "
               "[Timing](phase8_performance.csv) · [Paired disagreements](phase8_paired_disagreement.csv) · [High-confidence errors](phase8_error_audit.csv) · "
               "[Inference registry](../manifests/phase8_models.json)", "", "## Figures", ""]
    report.extend(f"- [{Path(name).stem.removeprefix('phase8_').replace('_',' ')}]({name})" for name in figures)
    (reports / "phase8_hybrid_results.md").write_text("\n".join(report) + "\n")
    contribution = ["# Phase 8 research contribution", "",
                    "Earlier supervised models ranked traffic above chance while producing very low chronological recall at 0.5. "
                    "The study adds a common validation FPR ceiling, disjoint probability and fusion calibration, "
                    "reference-normalized novelty, matched ablations and selective triage after freezing the operating policies. "
                    "The contribution is experimental methodology and engineering integration using established algorithms.", "",
                    "The deltas below use the same held-out rows. Positive recall and negative FPR deltas favor the first method. "
                    "H1 compares the same RF at the validation-selected threshold and at 0.5. H2 compares the validation-selected "
                    "weighted candidate with its unweighted algorithm. H3 compares the selected fusion with each single-signal policy. "
                    "H4 compares automatic errors before and after referrals and reports coverage.", ""]
    contribution += table(("Population", "H1 recall Δ", "H1 FPR Δ", "H2 recall Δ", "H2 FPR Δ", "H3 recall Δ vs supervised",
                           "H3 FPR Δ vs supervised", "H3 recall Δ vs novelty", "H3 FPR Δ vs novelty", "Binary error",
                           "H4 automatic error", "Automatic coverage", "Review rate", "Fusion/base time"), contributions)
    contribution += ["", conclusion,
                     "Triage conditions error on the automated subset. Review work and missed attacks remain visible in the full population. "
                     "Compute ratios come from matched single-node scoring and can vary with Spark caching and query plans.", "",
                     "Ten correlated capture days, family/day association, one training seed and retrospective access constrain inference. "
                     "An independently reserved compatible capture and a prospective comparison of frozen policies at a feasible alert workload "
                     "are needed before deployment. The literature review should investigate calibration under temporal shift, "
                     "fixed-FPR transfer, classifier–novelty complementarity and selective prediction under constrained review.", "",
                     "[Measured results](../reports/phase8_hybrid_results.md) · [Evaluation limitations](phase8_evaluation_limitations.md)"]
    (output / "docs").mkdir(exist_ok=True)
    (output / "docs/phase8_research_contribution.md").write_text("\n".join(contribution) + "\n")
    print(f"Published {len(full)} supported populations, {len(figures)} figures and two reconciled baselines.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT)
    args = parser.parse_args()
    render(args.run, args.output)
