"""Validate and report matched Phase 5 artifacts, figures and cohort counts."""

import argparse
from collections import Counter
import csv
from itertools import combinations
import json
import math
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.ml.cluster_diagnostics import choose_k
from src.ml.cluster_evolution import divergence
from src.ml.novelty_scoring import novelty_row


EXPERIMENTS = ("G", "B", "C")
NAMES = {
    "cohorts", "model_selection", "transform_diagnostics", "cluster_profiles", "centroids", "composition",
    "window_family", "cluster_occupancy", "temporal_shift", "novelty_metrics", "score_histogram",
}


def read(path):
    return json.loads(path.read_text())


def records(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def write(path, entries):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, list(entries[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(entries)


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def table(headers, rows):
    return [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
        *["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows],
    ]


def pct(value):
    return f"{100 * float(value):.4f}%" if value not in (None, "") else "—"


def strongest_centroid_pair(centroids, trial):
    profiles = {}
    for row in centroids:
        profiles.setdefault(row["feature"], {})[int(row["cluster"])] = float(row["center"])
    weights = [n / trial["training_rows"] for n in trial["cluster_sizes"]]
    residuals = {}
    for name, profile in profiles.items():
        mean = sum(weight * profile[i] for i, weight in enumerate(weights))
        values = [math.sqrt(weight) * (profile[i] - mean) for i, weight in enumerate(weights)]
        norm = math.hypot(*values)
        if norm:
            residuals[name] = [value / norm for value in values]
    pairs = [(a, b, sum(x * y for x, y in zip(residuals[a], residuals[b])))
             for a, b in combinations(residuals, 2)]
    return max(pairs, key=lambda pair: abs(pair[2]))


def read_experiment(root, experiment, config, manifest, previous):
    folder = root / experiment
    source = folder / "results"
    summary = read(source / "phase5_summary.json")
    require(summary["experiment"] == experiment and summary["status"] == "validated", "Incomplete experiment")
    require(summary["config"] == config and summary["input"]["rows"] == 16232943, "Unexpected config or input")
    require(summary["input"]["receipt_sha256"] == manifest["independent_mount"]["summary_sha256"], "Wrong Phase 2 output")
    require(summary["input"]["totals"] == {"0": 13484708, "1": 2748235} and len(summary["input"]["days"]) == 10,
            "Input totals differ")
    require(summary["features"] == summary["preprocessing"]["fit_columns"] == previous["protocols"]["A"]["registered_predictors"],
            "Unapproved predictors reached the fit")
    require(summary["purge"]["groups_after"] == 0, "Retained group overlap")
    version = int((folder / "version").read_text())
    require(f'/{version} has status "KernelWorkerStatus.COMPLETE"' in (folder / "status-history.txt").read_text().splitlines()[-1],
            "Kaggle terminal status differs")
    log = read(folder / "kaggle.log")
    message = "".join(row["data"] for row in log)
    require(f"PHASE5 {experiment} complete k={summary['selected_k']} trained {summary['training']['fit_rows']}, scored {summary['retained_rows']}" in message,
            "Run log does not match completion receipt")
    rows = {name: records(source / f"phase5_{name}.csv") for name in NAMES | ({"duplicate_sensitivity"} if experiment == "G" else set())}
    require([row["k"] for row in summary["trials"]] == config["candidate_k"], "Missing K-Means trials")
    require(choose_k(summary["trials"])["k"] == summary["selected_k"], "Reference silhouette selection differs")
    for trial, entry in zip(summary["trials"], rows["model_selection"]):
        require(f"PHASE5 {experiment} k={trial['k']} trained {trial['training_rows']} rows, silhouette {trial['silhouette']}" in message,
                "Training evidence differs from logs")
        require(int(entry["k"]) == trial["k"] and float(entry["wssse"]) == trial["wssse"]
                and trial["training_rows"] == summary["training"]["fit_rows"], "Training aggregates differ")
    require(summary["calibration"]["rows"] == summary["training"]["internal_rows"] and summary["calibration"]["rows"] <= config["max_internal_rows"],
            "Reference calibration rows differ")
    require(set(summary["calibration"]["cutoffs"]) == set(map(str, config["reference_percentiles"])), "Threshold list differs")
    population = summary["retained_rows"]
    require(population + summary["purge"]["rows"] == summary["input"]["rows"], "Retention did not reconcile")
    for section in ("cohorts", "composition", "score_histogram"):
        require(sum(int(row["count"]) for row in rows[section]) == population, f"{section} totals differ")
    require(sum(int(row["records"]) for row in rows["cluster_profiles"]) == population, "Cluster profile counts differ")
    cohort, families = Counter(), Counter()
    for row in rows["cohorts"]:
        rank, support = row["split_rank"], int(row["count"])
        cohort[rank, row["binary_label"]] += support
        families[rank, row["attack_family"]] += support
    require(cohort["0", "0"] + cohort["0", "1"] == summary["training"]["reference_rows"], "Reference population differs")
    if experiment != "G":
        expected = previous["protocols"][experiment]
        require(summary["matched_phase4"]["purged_rows"] == expected["overlap"]["purged_rows"] and
                summary["matched_phase4"]["kaggle_version"] == expected["version"], "Phase 4 comparison differs")
        for i, split in enumerate(("train", "validation", "test")):
            require(all(cohort[str(i), label] == expected["split_support"][split]["labels"].get(label, 0)
                        for label in ("0", "1")), "Phase 4 binary support differs")
    for row in rows["novelty_metrics"]:
        rank = row["split_rank"]
        attacks, benign, hits, false_alarms = (int(row[key]) for key in ("attacks", "benign", "tp", "fp"))
        recomputed = novelty_row(attacks, benign, hits, false_alarms)
        if row["scope"] == "binary":
            require(benign == cohort[rank, "0"] and attacks == cohort[rank, "1"], "Novelty binary support differs")
        else:
            require(attacks == families[rank, row["family"]] and benign == false_alarms == 0,
                    "Novelty family support differs")
            recomputed["precision"] = None
        require(0 <= hits <= attacks and 0 <= false_alarms <= benign, "Novelty confusion counts differ")
        require(all(row[key] == "" if value is None else math.isclose(float(row[key]), value, abs_tol=1e-12)
                    for key, value in recomputed.items()), "Novelty scores do not reconcile")
        require(float(row["threshold"]) == summary["calibration"]["cutoffs"][row["percentile"]], "Novelty threshold differs")
    k = summary["selected_k"]
    grouped, reference = {}, [0] * k
    for row in rows["cluster_occupancy"]:
        key = row["source_day"], row["split_rank"], row["window_hour"]
        index = int(row["cluster"])
        n = int(row["records"])
        grouped.setdefault(key, [0] * k)[index] += n
        if key[1:] == ("0", "-1"):
            reference[index] += n
    require(reference == summary["reference_occupancy"], "Frozen reference occupancy differs")
    require(sum(sum(v) for k, v in grouped.items() if k[2] == "-1") == population, "Daily occupancy does not reconcile")
    require(sum(sum(v) for k, v in grouped.items() if k[2] != "-1") == sum(int(row["count"]) for row in rows["window_family"]),
            "Eligible window counts differ")
    for row in rows["cluster_occupancy"]:
        key = row["source_day"], row["split_rank"], row["window_hour"]
        require(math.isclose(float(row["occupancy"]), int(row["records"]) / sum(grouped[key]), abs_tol=1e-12),
                "Cluster occupancy share differs")
    for row in rows["temporal_shift"]:
        counts = grouped[row["source_day"], row["split_rank"], row["window_hour"]]
        require(sum(counts) == int(row["rows"]) and abs(divergence(reference, counts) - float(row["js_divergence_bits"])) <= 1e-12,
                "Temporal shift disagrees with cluster occupancy")
    require(len(summary["figures"]) == (9 if experiment == "G" else 10) and
            all((source / "figures" / name).read_bytes().startswith(b"\x89PNG\r\n\x1a\n") for name in summary["figures"]),
            "Missing or corrupt figures")
    require(summary["model"]["reload_rows"] == 32, "Saved model reload evidence differs")
    return summary, rows, {"version": version, "log_events": len(log), "status": "COMPLETE"}


def generate(root, url, reload, output):
    config = read(ROOT / "configs/clustering_experiments.yaml")
    upstream = read(ROOT / "manifests/parquet_layers.json")
    previous = read(ROOT / "manifests/phase4_models.json")
    reloaded = read(reload)
    soups, results, experiments, combined = {}, {}, {}, {}
    reports, docs, manifests = (output / name for name in ("reports", "docs", "manifests"))
    for directory in (reports, docs, manifests, reports / "figures"):
        directory.mkdir(parents=True, exist_ok=True)
    for e in EXPERIMENTS:
        summary, tables, run = read_experiment(root, e, config, upstream, previous)
        require(reloaded[e]["verified"] and reloaded[e]["probes"] == 3, "Independent reload missing")
        soups[e], results[e], experiments[e] = summary, tables, run
        for name, rows in tables.items():
            combined.setdefault(name, []).extend({"experiment": e, **item} for item in rows)
        for figure in summary["figures"]:
            shutil.copyfile(root / e / "results" / "figures" / figure, reports / "figures" / figure)
    for name, rows in combined.items():
        write(reports / f"phase5_{name}.csv", rows)
    manifest = {"status": "validated", "kernel_url": url, "experiments": {
        e: soups[e] | experiments[e] | {"downloaded_reload": reloaded[e]} for e in EXPERIMENTS}}
    (manifests / "phase5_clustering_models.json").write_text(json.dumps(manifest, indent=2) + "\n")

    report = [
        "# Phase 5 clustering and pattern evolution", "",
        "**READY FOR PHASE 6.** All three Spark 4.3.0 Kaggle runs completed. The saved pipelines passed archive checksum and independent reload checks. "
        "The frozen models were fitted on predictor-only data and evaluated using post-fit labels. "
        f"[Kaggle notebook]({url}) · [Full manifests](../manifests/phase5_clustering_models.json)", "",
        "## Input and cohorts", "",
        "Each run validated the Phase 2 version 1 receipt, cleaning policy, ten dates and 16,232,943 flows, including 13,484,708 benign and "
        "2,748,235 attack. The 18-feature registry contains no labels, identifiers, ports, protocol or day fields. "
        "The historical and scenario cohorts match the corresponding Phase 4 retained binary and family counts. "
        "[Cohort evidence](phase5_cohorts.csv)", "",
    ]
    report += table(["Experiment", "Retained rows", "Overlap rows purged", "Fit rows", "Fit share", "Silhouette/calibration rows"],
                    [(e, f"{s['retained_rows']:,}", f"{s['purge']['rows']:,}", f"{s['training']['fit_rows']:,}",
                      pct(s["training"]["share_of_reference"]), f"{s['training']['internal_rows']:,}") for e, s in soups.items()])
    report += ["", "## K-Means and robustness", ""]
    report += table(["Experiment", "Selected k", "Probe silhouette", "Fit WSSSE", "Fit time (s)", "Seed ARI", "Linear vs log ARI"],
                    [(e, s["selected_k"], f"{t['silhouette']:.4f}", f"{t['wssse']:,.1f}", f"{t['fit_seconds']:.3f}",
                      f"{s['robustness']['seed_ari']:.4f}", f"{s['robustness']['scale_ari']:.4f}") for e, s in soups.items()
                     for t in s["trials"] if t["k"] == s["selected_k"]])
    report += ["", "The bounded silhouette selected among k = 3, 5, 8 and 12 on a disjoint reference probe. "
               "WSSSE is the fitted sample objective. ARI uses the same probe and compares label-free assignments. "
               "The linear and signed-log objectives are measured in different feature spaces. "
               "[All trial sizes, iterations and memory snapshots](phase5_model_selection.csv)", "",
               "## External label composition", ""]
    report += table(["Experiment", "Largest cluster", "Records", "Attack share", "Highest attack-share cluster", "Attack share"], [
        (e, a["cluster"], f"{int(a['records']):,}", pct(a["attack_share"]), b["cluster"], pct(b["attack_share"]))
        for e in EXPERIMENTS
        for a, b in [(max(results[e]["cluster_profiles"], key=lambda r: int(r["records"])),
                      max(results[e]["cluster_profiles"], key=lambda r: float(r["attack_share"])))]
    ])
    report += ["", "Cluster IDs are specific to each fit. Means, distance summaries, external purity, family and original-label counts "
               "describe the retained traffic. Global exact-content sensitivity removes 410,707 excess copies only from the representative count. "
               "[Cluster profiles](phase5_cluster_profiles.csv) · [Family and original-label composition](phase5_composition.csv) · "
               "[Centroids](phase5_centroids.csv)", "", "## Reference-calibrated novelty", ""]
    primary = {e: next(row for row in results[e]["novelty_metrics"] if row["split_rank"] == ("0" if e == "G" else "2")
                       and row["scope"] == "binary" and row["percentile"] == "0.99") for e in EXPERIMENTS}
    source_counts = {r["capture_day"]: r["counts"]["parsed"]
                     for r in read(ROOT / "manifests/dataset_inventory.json")["files"]}
    phase4_design = read(ROOT / "configs/ml_experiments.yaml")["protocols"]
    coverage = {e: sum(source_counts[day] for day in phase4_design[e]["test"]) if e != "G" else 16232943
                for e in EXPERIMENTS}
    report += table(["Experiment", "Scored rows", "Coverage of original population", "P99 squared distance", "Flag rate",
                    "Benign false-positive rate", "Attack recall", "Precision"], [
        (e, f"{int(r['rows']):,}", pct(int(r["rows"]) / coverage[e]), f"{float(r['threshold']):.3f}", pct(r["flag_rate"]),
         pct(r["benign_fpr"]), pct(r["attack_recall"]), pct(r["precision"])) for e, r in primary.items()
    ])
    report += ["", "The primary rule flags strict exceedance of the disjoint reference probe P99. G is an all-day retrospective "
               "description. B scores later captures and C tests unseen Web attack captures. A flag describes distance in this feature space. "
               "[P95, P99 and P99.9 results with family support](phase5_novelty_metrics.csv)", "",
               "## Execution", ""]
    report += table(["Experiment", "Kaggle version", "Through model save (s)", "Local workers", "Driver heap", "JVM peak GiB", "Log events"], [
        (e, experiments[e]["version"], f"{s['elapsed_seconds']:.3f}", s["resources"]["default_parallelism"],
         s["resources"]["driver_memory"], f"{s['resources']['driver_peak_rss_bytes'] / 1024 ** 3:.2f}", experiments[e]["log_events"])
        for e, s in soups.items()
    ])
    report += ["", "Each run used 48 shuffle partitions and 64 MiB input splits. Figures and summaries were retrieved from the "
               "saved notebook outputs. [Pattern evolution and comparison](../docs/phase5_pattern_evolution.md)", "", "## Figures", ""]
    report += [f"- [{e} · {name.removesuffix('.png').split('_', 2)[-1].replace('_', ' ')}](figures/{name})"
               for e, s in soups.items() for name in s["figures"]]
    (reports / "phase5_clustering_results.md").write_text("\n".join(report) + "\n")

    rf = {(r["protocol"], r["category"]): r for r in records(ROOT / "reports/phase4_family_recall.csv")
          if r["protocol"] in {"B", "C"} and r["level"] == "family" and r["split"] == "test"
          and r["model"] == "random_forest" and r["training_cohort"] == "group_sample"}
    discussion = [
        "# Phase 5 pattern evolution", "",
        "## Retrospective behavior and capture composition", "",
        "The global clusters combine behavioral summaries and post-fit capture context. "
        "Reported feature means use the available clean values in each assigned cluster.", "",
    ]
    global_profiles = results["G"]["cluster_profiles"]
    day_cluster = Counter()
    rare_cluster = Counter()
    rare_labels = {"SQL Injection", "Brute Force -XSS", "Brute Force -Web"}
    for row in results["G"]["composition"]:
        n = int(row["count"])
        day_cluster[row["cluster"], row["source_day"]] += n
        if row["original_label"] in rare_labels:
            rare_cluster[row["original_label"], row["cluster"]] += n
    discussion += table(["Cluster", "Rows", "Attack share", "Mean duration (µs)", "Mean forward packets",
                         "Mean backward packets", "Largest day contribution"], [
        (r["cluster"], f"{int(r['records']):,}", pct(r["attack_share"]), f"{float(r['mean_duration_us']):,.1f}",
         f"{float(r['mean_forward_packets']):,.2f}", f"{float(r['mean_backward_packets']):,.2f}",
         day + " · " + pct(n / int(r["records"])))
        for r in global_profiles
        for n, day in [max((n, day) for (cluster, day), n in day_cluster.items() if cluster == r["cluster"])]
    ])
    raw = [int(r["records"]) for r in results["G"]["duplicate_sensitivity"]]
    representatives = [int(r["exact_digest_representatives"]) for r in results["G"]["duplicate_sensitivity"]]
    discussion += [
        "",
        f"Counting one representative per exact source digest yields {sum(representatives):,} records. "
        f"Global cluster occupancy changes by {divergence(raw, representatives):.6f} Jensen–Shannon bits under that count.",
        "",
    ]
    discussion += table(["Rare original label", "Records", "Observed cluster distribution"], [
        (label, f"{sum(n for (name, _), n in rare_cluster.items() if name == label):,}",
         ", ".join(f"{cluster} ({n:,})" for (name, cluster), n in sorted(rare_cluster.items()) if name == label))
        for label in sorted(rare_labels)
    ])
    discussion += ["", "Those rare-label counts describe recorded support. Repeated or related flows can reduce effective sample size.", "",
        "## Capture-day occupancy", "",
        "Jensen–Shannon values compare the full retained reference occupancy with each observed day or three-hour wall-clock bin. "
        "The source timezone is unverified. The model is frozen within each experiment. Labels provide post-fit composition only.", "",
    ]
    discussion += table(["Experiment", "Largest described daily shift", "Rows", "Jensen–Shannon bits", "Occupied clusters"], [
        (e, r["source_day"], f"{int(r['rows']):,}", f"{float(r['js_divergence_bits']):.5f}", r["occupied_clusters"])
        for e in EXPERIMENTS for r in [max(
            (r for r in results[e]["temporal_shift"] if r["window_hour"] == "-1" and (e == "G" or r["split_rank"] == "2")),
            key=lambda row: float(row["js_divergence_bits"]))]
    ])
    discussion += ["", "### Held-out dates", ""]
    for_holdout = []
    for e in ("B", "C"):
        for row in results[e]["temporal_shift"]:
            if row["split_rank"] != "2" or row["window_hour"] != "-1":
                continue
            day = row["source_day"]
            counts = [r for r in results[e]["cluster_occupancy"] if r["source_day"] == day and r["window_hour"] == "-1"]
            dominant = max(counts, key=lambda r: int(r["records"]))
            total = int(row["rows"])
            for_holdout.append((e, day, f"{total:,}", f"{float(row['js_divergence_bits']):.5f}",
                                dominant["cluster"] + " · " + pct(dominant["occupancy"]),
                                pct(sum(int(r["flags"]) for r in counts) / total)))
    discussion += table(["Experiment", "Capture day", "Rows", "Jensen–Shannon bits", "Largest cluster and share", "P99 flag rate"],
                        for_holdout)
    discussion += ["", "The day and window summaries also retain mean flow attributes, distance tails, flag counts and an explicit cohort "
                   "denominator. Day-specific behavior and attack composition can change together. The observed contrasts describe the "
                   "capture collection and do not identify a feature-to-label mechanism. [Occupancy](../reports/phase5_cluster_occupancy.csv) · "
                   "[Shifts](../reports/phase5_temporal_shift.csv) · [Window family support](../reports/phase5_window_family.csv)", "",
                   "## Phase 4 generalization cases", ""]
    families = []
    for e, names in (("B", ("Bot", "Infiltration")), ("C", ("Web attack",))):
        for name in names:
            r = next(row for row in results[e]["novelty_metrics"] if row["split_rank"] == "2" and
                     row["percentile"] == "0.99" and row["scope"] == "family" and row["family"] == name)
            s = rf[e, name]
            require(int(r["attacks"]) == int(s["evaluated_rows"]), "Family comparison denominators differ")
            families.append((e, name, f"{int(r['attacks']):,}", f"{int(r['tp']):,}", pct(r["attack_recall"]), pct(s["recall"])))
    discussion += table(["Cohort", "Family", "Matched test rows", "P99 flags", "P99 flag recall", "Phase 4 RF recall"], families)
    discussion += [
        "", f"The historical P99 flagged {pct(primary['B']['attack_recall'])} of attacks and {pct(primary['B']['benign_fpr'])} of benign flows. "
        f"In the Web capture holdout, {pct(primary['C']['attack_recall'])} of attacks exceeded P99. Only {pct(primary['C']['precision'])} "
        "of flagged flows carried an attack label in that low-prevalence cohort.", "",
        "The comparison recreates Phase 4's retained cohorts and checks support. It uses aggregate metrics because Phase 4 preserved no "
        "row-level predictions. Random Forest operates at a 0.5 classification threshold, and the centroid rule uses a reference P99 cutoff. "
        "Compare benign false positives and precision before considering either signal for a detection decision. "
        "Distance can complement model review by identifying unusual traffic for inspection. These experiments neither establish that flagged rows "
        "represent new attacks nor demonstrate an improvement at matched operating points.", "",
        "## Stability and feature influence", "",
    ]
    discussion += table(["Experiment", "Paired probe rows", "Alternative-seed ARI", "Linear-scaling ARI", "Largest between-centroid contribution"], [
        (e, f"{s['robustness']['paired_rows']:,}", f"{s['robustness']['seed_ari']:.4f}", f"{s['robustness']['scale_ari']:.4f}",
         s["robustness"]["dominance"][0]["feature"] + " (" + pct(s["robustness"]["dominance"][0]["share_between_centroids"]) + ")")
        for e, s in soups.items()
    ])
    trial_diagnostics = []
    for e, summary in soups.items():
        best = next(row for row in summary["trials"] if row["k"] == summary["selected_k"])
        a, b, correlation = strongest_centroid_pair(results[e]["centroids"], best)
        n_near = sum(row.get("near_constant", False) for row in summary["preprocessing"]["reference_stats"].values())
        trial_diagnostics.append((e, sum(row["empty_clusters"] for row in summary["trials"]),
                                  pct(best["smallest_share"]), len(summary["preprocessing"]["dropped"]), n_near,
                                  f"{a} / {b} ({correlation:+.3f})"))
    discussion += [""] + table(["Experiment", "Empty clusters across grid", "Smallest selected cluster share",
                                "Predictors dropped", "Near-constant predictors", "Strongest weighted centroid correlation"],
                               trial_diagnostics)
    discussion += ["", "ARI is invariant to cluster ID permutations. The contribution statistic is the fitted-cluster-size-weighted "
                   "between-centroid variance share in the scaled space. Correlations use the selected cluster centers, weighted by training counts. "
                   "They indicate where features describe similar centroid profiles. Per-flow redundancy would require within-cluster covariance. "
                   "[Full results and figures](../reports/phase5_clustering_results.md)"]
    (docs / "phase5_pattern_evolution.md").write_text("\n".join(discussion) + "\n")
    print("Published three validated experiments, three saved model receipts and 29 figures.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", type=Path)
    parser.add_argument("--kernel-url", required=True)
    parser.add_argument("--reload", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=ROOT)
    args = parser.parse_args()
    generate(args.runs, args.kernel_url, args.reload, args.output_root)
