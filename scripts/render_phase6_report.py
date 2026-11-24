"""Reconcile the retrieved historical replay against Kaggle and upstream evidence."""

from argparse import ArgumentParser
from collections import Counter
import csv
from hashlib import sha256
import json
from math import isclose
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
TABLES = ("replay_batches", "window_metrics", "shift_metrics", "alerts", "recovery_tests", "performance")


def require(condition, problem):
    if not condition:
        raise ValueError(problem)


def read(path):
    return json.loads(path.read_text())


def csv_rows(path):
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def table(columns, items):
    return ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |",
            *["| " + " | ".join(map(str, item)) + " |" for item in items]]


def pct(value):
    return f"{100 * float(value):.4f}%" if value is not None else "—"


def verify_figures(source, figures):
    from PIL import Image

    sys.path.insert(0, str(ROOT))
    from src.streaming.replay_charts import draw

    with TemporaryDirectory() as temporary:
        regenerated = Path(temporary)
        for name in TABLES:
            file = f"phase6_{name}.csv"
            shutil.copyfile(source / file, regenerated / file)
        require(draw(regenerated) == figures, "Recreated figure catalog differs")
        for name in figures:
            with Image.open(source / "figures" / name) as original, Image.open(regenerated / "figures" / name) as rebuilt:
                require(original.size == rebuilt.size and original.convert("RGBA").tobytes() == rebuilt.convert("RGBA").tobytes(),
                        f"Recreated pixels differ for {name}")


def check_upstream(summary, windows, shifts):
    phase2 = read(ROOT / "manifests/parquet_layers.json")
    phase4 = read(ROOT / "manifests/phase4_models.json")["protocols"]["B"]
    phase5 = read(ROOT / "manifests/phase5_clustering_models.json")["experiments"]["B"]
    require(summary["input"]["receipt_sha256"] == phase2["independent_mount"]["summary_sha256"], "Phase 2 receipt differs")
    require(summary["features"] == phase4["registered_predictors"] == phase5["features"], "Feature order differs")
    for name, model in summary["supervised"].items():
        expected = next(item for item in phase4["models"] if item["model"] == name and item["training_cohort"] == "group_sample")
        require(model["sha256"] == expected["sha256"] and model["probe_rows"] == 3, f"{name} verification differs")
    require(summary["clustering"]["sha256"] == phase5["model"]["sha256"] and summary["clustering"]["probe_rows"] == 3
            and summary["clustering"]["p99"] == phase5["calibration"]["cutoffs"]["0.99"], "K-Means identity or threshold differs")
    require(summary["reference_cluster_occupancy"] == phase5["reference_occupancy"], "Frozen cluster reference differs")
    require(summary["staging"]["rows"] == phase5["retained_rows"] and
            summary["staging"]["purged_rows"] == phase5["purge"]["rows"], "B replay population differs")
    for rank, name in enumerate(("train", "validation", "test")):
        scope, expected = summary["scopes"][name], phase4["split_support"][name]["labels"]
        require((scope["benign"], scope["attacks"]) == (expected["0"], expected["1"]), f"{name} support differs")
        if rank:
            training_cohorts = {"random_forest": "group_sample", "logistic_regression": "group_sample",
                               "duration_rule": "full_train_baseline"}
            expected_models = {
                r["model"]: r for r in csv_rows(ROOT / "reports/phase4_metrics.csv") if r["protocol"] == "B" and r["split"] == name
                and r["training_cohort"] == training_cohorts.get(r["model"])
            }
            for model, metrics in scope["models"].items():
                previous = expected_models[model]
                require(all(metrics[key] == int(previous[key]) for key in ("tp", "tn", "fp", "fn")) and
                        isclose(metrics["pr_auc"], float(previous["pr_auc"]), abs_tol=1e-12),
                        f"{model} {name} differs from Phase 4")
        earlier = next(r for r in csv_rows(ROOT / "reports/phase5_novelty_metrics.csv")
                       if r["experiment"] == "B" and r["split_rank"] == str(rank) and r["percentile"] == "0.99" and r["scope"] == "binary")
        require(all(scope["novelty"][key] == int(earlier[key]) for key in ("rows", "tp", "fp", "flags")), "Phase 5 novelty differs")
    expected_windows = {(r["source_day"], r["window_hour"]): r for r in csv_rows(ROOT / "reports/phase5_temporal_shift.csv")
                        if r["experiment"] == "B"}
    observed_windows = {(r["source_day"], r["window_hour"] or "-1"): int(r["rows"]) for r in windows if r["scope"] != "capture_only"}
    require(observed_windows == {key: int(r["rows"]) for key, r in expected_windows.items()}, "Phase 5 window support differs")
    for row in shifts:
        if row["category"] == "CLUSTER_SHIFT" and row["scope"] != "capture_only":
            want = expected_windows[row["source_day"], row["window_hour"] or "-1"]
            require(isclose(float(row["value"]), float(want["js_divergence_bits"]), abs_tol=1e-12), "Cluster Jensen–Shannon differs")


def validate(run, source, version):
    summary = read(source / "phase6_summary.json")
    require(summary["mode"] == "full" and summary["status"] == "validated", "Kaggle replay is incomplete")
    require(summary["spark"] == "4.3.0", "Unexpected Spark version")
    status = (run / "status-history.txt").read_text().splitlines()[-1]
    require(f'/{version} has status "KernelWorkerStatus.COMPLETE"' in status, "Kaggle terminal status differs")
    logs = read(run / "kaggle.log")
    text = "".join(event["data"] for event in logs).replace("–".encode().decode("latin-1"), "–")
    stats = summary["staging"]
    require(f"PHASE6 complete {stats['rows']} retained flows in {stats['chunks']} streaming batches" in text
            and "PHASE6 planned stop after atomic sink publish" in text
            and "PHASE6 pinned inputs and three frozen pipelines validated" in text, "Terminal log markers differ")
    rows = {name: csv_rows(source / f"phase6_{name}.csv") for name in TABLES}
    batches, windows, shifts, alerts = (rows[name] for name in TABLES[:4])
    check_upstream(summary, windows, shifts)
    progress = read(source / "phase6_stream_progress.json")
    run_data = progress["historical"]
    attempts = run_data["attempts"]
    require([row["outcome"] for row in attempts] == ["planned_interruption", "terminated"]
            and attempts[0]["query_id"] == attempts[1]["query_id"] and attempts[0]["run_id"] != attempts[1]["run_id"],
            "Checkpoint restart identity differs")
    require({row["batchId"] for row in run_data["progress"] if row["numInputRows"] > 0} == set(range(len(batches))),
            "Progress events differ from batch IDs")
    for name, evidence in progress.items():
        total = next(x["batches"] for x in summary["configurations"] if x["configuration"] == name)
        require({p["batchId"] for p in evidence["progress"] if p["numInputRows"] > 0} == set(range(total)),
                f"Progress mismatch for {name}")
    require(all(r["passed"] == "True" for r in rows["recovery_tests"]) and len(rows["recovery_tests"]) == 5, "Recovery evidence is incomplete")
    require([int(r["replay_seq"]) for r in batches] == [int(r["batch_id"]) for r in batches] == list(range(stats["chunks"])),
            "Streaming sequence differs")
    require([(r["source_day"], int(r["window_hour"])) for r in batches] ==
            sorted((r["source_day"], int(r["window_hour"])) for r in batches), "Capture ordering differs")
    require(sum(int(r["rows"]) for r in batches) == stats["rows"] and
            sum(int(r["temporally_eligible"]) for r in batches) == stats["rows"] - stats["ineligible_retained"] and
            sum(int(r["bytes"]) for r in batches) == stats["bytes"], "Batch accounting differs")
    require(all(f"PHASE6 stream batch {r['batch_id']} committed sink sequences {r['replay_seq']}–{r['replay_seq']} rows {r['rows']}" in text
                for r in batches), "Batch output disagrees with log")
    for row in windows:
        totals = int(row["rows"])
        require(int(row["benign"]) + int(row["attacks"]) == totals and sum(json.loads(row["cluster_counts"])) == totals
                and sum(json.loads(row["rf_score_counts_32"])) == totals, "Window totals differ")
        require(all(m["rows"] == totals for m in json.loads(row["classifier_metrics"]).values()), "Model totals differ by window")
    ref = read(source / "phase6_reference.json")
    require(ref["rows"] == summary["scopes"]["train"]["rows"] and ref["histograms"]["cluster"] == summary["reference_cluster_occupancy"],
            "Reference aggregates differ")
    require(all(sum(values) == ref["rows"] for values in ref["histograms"].values()) and
            all(sum(sum(values) for values in bins.values()) == ref["rows"] for bins in ref["scores"].values()),
            "Reference histogram denominators differ")
    lookup = {name: {} for name in ("expected", "actual")}
    keys = ("scope", "source_day", "window_hour", "category", "detector")
    for row in shifts:
        if row["support"] == "supported" and row["split_rank"] != "0" and float(row["delta"]) > float(row["threshold"]):
            lookup["expected"][tuple(row[k] for k in keys)] = "high" if float(row["delta"]) >= 2 * float(row["threshold"]) else "warning"
    for row in alerts:
        lookup["actual"][tuple(row[k] for k in keys)] = row["severity"]
        require((row["labels_used"] == "True") == (row["category"] == "PERFORMANCE_WARNING"), "Alert label provenance differs")
    require(lookup["expected"] == lookup["actual"] and len(alerts) == summary["alerts"]["count"], "Alert decisions differ")
    require(len(summary["figures"]) == 11 and all((source / "figures" / name).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
                                                  for name in summary["figures"]), "Figure evidence is incomplete")
    return summary, rows, {"version": version, "status": "COMPLETE", "log_events": len(logs),
                           "log_sha256": sha256((run / "kaggle.log").read_bytes()).hexdigest(),
                           "query_attempts": attempts, "data_progress_events": len(batches),
                           "spark_offset_and_commit_ms": {
                               name: sum(sum(event["durationMs"].get(key, 0) for key in ("walCommit", "commitOffsets"))
                                         for event in evidence["progress"] if event["numInputRows"] > 0)
                               for name, evidence in progress.items()
                           }}


def render(output, source, summary, rows, execution, url, mirror_url):
    reports, docs, manifests = (output / path for path in ("reports", "docs", "manifests"))
    for directory in (reports / "figures", docs, manifests):
        directory.mkdir(parents=True, exist_ok=True)
    for name in TABLES:
        file = f"phase6_{name}.csv"
        shutil.copyfile(source / file, reports / file)
    for name in summary["figures"]:
        shutil.copyfile(source / "figures" / name, reports / "figures" / name)
    for file in ("phase6_stream_progress.json", "phase6_reference.json"):
        shutil.copyfile(source / file, manifests / file)
    registry = summary | {"kaggle": execution | {"url": url, "mirror_url": mirror_url},
                         "artifact_sha256": {str(p.relative_to(source)): sha256(p.read_bytes()).hexdigest()
                                             for p in sorted(source.rglob("*")) if p.is_file()}}
    (manifests / "phase6_replay_runs.json").write_text(json.dumps(registry, indent=2) + "\n")
    test, train = (summary["scopes"][key] for key in ("test", "train"))
    sc = summary["staging"]
    result = ["# Phase 6 historical Structured Streaming replay", "",
              "**READY FOR PHASE 7.** The replay covered the complete chronological B population. The frozen supervised confusion counts, "
              "binned PR-AUCs, K-Means novelty counts and window occupancy distances reconcile to Phases 4 and 5. "
              f"[Private Kaggle notebook]({url}) · [Run evidence](../manifests/phase6_replay_runs.json)", "",
              "## Input, replay and recovery", "",
              f"The Phase 2 receipt covers 16,232,943 original flows and 14 timestamp anomalies. The overlap purge removed "
              f"{sc['purged_rows']:,} rows. Spark processed {sc['rows']:,} retained flows in {sc['chunks']} replay microbatches. "
              f"{sc['ineligible_retained']:,} retained anomaly rows contribute only to their capture day. "
              "The saved Phase 4 and Phase 5 B pipelines and their original preprocessing passed hash and synthetic scoring checks. "
              "The direct version-qualified preflight could not locate Phase 4 B. The completed notebook mounted a byte-verified private mirror "
              f"of the exact version 2 files. [Private model mirror]({mirror_url})", "",
              "The query used available-now and a one-file trigger. A planned failure at batch 1 left its atomic aggregate intact and its "
              "Spark checkpoint uncommitted. Restart reused the query ID with a new run ID, replayed batch 1 without rewriting its aggregate, "
              "ignored a partial sink file, and matched the complete batch and checkpoint ranges. [Spark progress](../manifests/phase6_stream_progress.json) "
              "· [Recovery evidence](phase6_recovery_tests.csv)", "", "## Frozen later-capture performance", ""]
    result += table(["Model", "TP", "TN", "FP", "FN", "Precision", "Recall", "F1", "PR-AUC"], [
        (name, *(f"{m[k]:,}" for k in ("tp", "tn", "fp", "fn")), pct(m["precision"]), pct(m["recall"]),
         f"{m['f1']:.5f}", f"{m['pr_auc']:.6f}") for name, m in test["models"].items()
    ])
    n = test["novelty"]
    result += ["", f"At the saved P99 distance of {summary['clustering']['p99']:.6f}, K-Means flagged {n['flags']:,} "
               f"test flows, including {n['tp']:,} attack-labeled and {n['fp']:,} benign-labeled flows. Attack recall was "
               f"{pct(n['attack_recall'])} and benign false-positive rate was {pct(n['benign_fpr'])}. "
               f"The unlabelled flag rate was {pct(n['flag_rate'])}, compared with {pct(train['novelty']['flag_rate'])} in training. "
               "[Window metrics](phase6_window_metrics.csv)", "", "## Alert and performance evidence", ""]
    counts = Counter((a["category"], a["severity"]) for a in rows["alerts"])
    result += table(["Alert category", "Warning", "High"], [(a, counts[a, "warning"], counts[a, "high"])
                                                           for a in summary["config"]["alert_thresholds"]])
    result += ["", "[Alert records](phase6_alerts.csv) · [Shift measures](phase6_shift_metrics.csv) · "
               "[Interpretation](../docs/phase6_drift_interpretation.md)", ""]
    result += table(["Configuration", "Files per trigger", "Batches", "Rows", "Elapsed (s)", "Rows/s", "Checkpoint bytes"], [
        (m["configuration"], m["files_per_trigger"], m["batches"], f"{m['rows']:,}", f"{m['elapsed_seconds']:.2f}",
         f"{m['rows_per_second']:,.0f}", f"{m['checkpoint_bytes']:,}") for m in summary["configurations"]
    ])
    result += ["", f"Staging used {sc['bytes']:,} bytes and took {sc['seconds']:.2f} seconds. "
               f"The Spark JVM peaked at {summary['driver_peak_rss_bytes'] / 1024**3:.2f} GiB RSS. "
               f"The historical query recorded {execution['spark_offset_and_commit_ms']['historical'] / 1000:.3f} seconds "
               "in Spark's offset and commit timing counters. "
               "Each comparison used the same four chunks on the same local CPU session with a separate checkpoint. "
               "[Batch timings](phase6_replay_batches.csv) · [Performance metrics](phase6_performance.csv)", "", "## Figures", ""]
    result += [f"- [{name.removeprefix('phase6_').removesuffix('.png').replace('_', ' ').capitalize()}](figures/{name})"
               for name in summary["figures"]]
    (reports / "phase6_streaming_results.md").write_text("\n".join(result) + "\n")
    discussion = ["# Phase 6 interpretation", "",
                  "Six raw feature histograms, three classifier score distributions and cluster occupancy use frozen training-capture aggregates. "
                  "Jensen–Shannon divergence is in bits. The novelty comparison uses strict exceedance of the saved K-Means cutoff. "
                  "Only retrospective performance warnings use binary labels. Random Forest recall was "
                  f"{pct(train['models']['random_forest']['recall'])} across the retained training captures and "
                  f"{pct(test['models']['random_forest']['recall'])} across the later captures. The training baseline includes rows used "
                  "to fit the model and can overstate generalization.", "", "## Later daily shifts", ""]
    for_plot = []
    for day in sorted({r["source_day"] for r in rows["shift_metrics"] if r["split_rank"] == "2"}):
        daily = [r for r in rows["shift_metrics"] if r["source_day"] == day and r["scope"] == "daily"]
        feature = max((r for r in daily if r["category"] == "INPUT_SHIFT"), key=lambda r: float(r["value"]))
        rf = next(r for r in daily if r["category"] == "SCORE_SHIFT" and r["detector"] == "random_forest")
        cluster = next(r for r in daily if r["category"] == "CLUSTER_SHIFT")
        for_plot.append((day, feature["detector"], f"{float(feature['value']):.5f}", f"{float(rf['value']):.5f}",
                         f"{float(cluster['value']):.5f}", sum(a["source_day"] == day for a in rows["alerts"])))
    discussion += table(["Day", "Largest raw feature shift", "Feature JS", "Random Forest score JS", "Cluster JS", "Alert records"], for_plot)
    discussion += ["", "Alerts can reflect changing traffic mix or capture conditions. The replay measures observed labeled performance, "
                   "and establishes neither a change in the predictor–label relationship nor discovery of a novel attack. "
                   "Daily and intraday alerts can describe the same flows and are counted as separate records. "
                   "Capture-only rows preserve the observed multiplicity of timestamp anomalies without assigning them an intraday window.", "",
                   "Offline refresh was omitted. Phase 6 preserves both March captures as final holdout, and the collection has no verified schedule "
                   "for the release of analyst-confirmed labels. Processing timestamps measure the Kaggle run. Original event timestamps remain "
                   "wall-clock values with unverified timezone.", "", "[Protocol](phase6_replay_protocol.md) · "
                   "[Streaming results](../reports/phase6_streaming_results.md)"]
    (docs / "phase6_drift_interpretation.md").write_text("\n".join(discussion) + "\n")


if __name__ == "__main__":
    p = ArgumentParser(description=__doc__)
    p.add_argument("run", type=Path)
    p.add_argument("--kernel-url", required=True)
    p.add_argument("--mirror-url", required=True)
    p.add_argument("--output-root", type=Path, default=ROOT)
    p.add_argument("--verify-figures", action="store_true", help="Regenerate charts and compare decoded pixels")
    args = p.parse_args()
    source = args.run / "results"
    summary, rows, evidence = validate(args.run, source, int((args.run / "version").read_text()))
    if args.verify_figures:
        verify_figures(source, summary["figures"])
        evidence["recreated_figures_pixel_identical"] = len(summary["figures"])
    render(args.output_root, source, summary, rows, evidence, args.kernel_url, args.mirror_url)
    print("Phase 6 reports reconciled with archived streaming progress, Spark logs, and Phase 2–5 metrics.")
