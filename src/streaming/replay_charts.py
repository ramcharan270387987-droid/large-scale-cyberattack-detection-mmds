"""Render historical replay evidence from its bounded CSV tables."""

import csv
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def draw(folder):
    def read(name):
        with (folder / f"phase6_{name}.csv").open(newline="", encoding="utf-8") as file:
            return list(csv.DictReader(file))

    batches, windows, shifts, alerts = (read(name) for name in ("replay_batches", "window_metrics", "shift_metrics", "alerts"))
    days = [row for row in windows if row["scope"] == "daily"]
    dates = [r["source_day"][5:] for r in days]
    output = folder / "figures"
    output.mkdir(exist_ok=True)
    names = []
    plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "font.size": 9})

    def chart(name, title, xlabel, ylabel, x, series, kind="line"):
        figure, ax = plt.subplots(figsize=(8.7, 3.8), layout="constrained")
        for label, values in series:
            if kind == "bar":
                ax.bar(x, values, color="#127e89")
            else:
                ax.plot(x, values, label=label, marker="." if len(x) <= 70 else None)
        if len(series) > 1:
            ax.legend(fontsize=8, ncols=2)
        ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
        ax.grid(axis="y", alpha=.21)
        target = f"phase6_{name}.png"
        figure.savefig(output / target, dpi=120, metadata={"Software": "MMDS Phase 6"})
        plt.close(figure)
        names.append(target)

    batch_ids = [int(r["batch_id"]) for r in batches]
    source_days = {day: i for i, day in enumerate(sorted({r["source_day"] for r in batches}))}
    chart("timeline", "Chronological release of historical captures", "Structured Streaming batch", "Capture-day order",
          batch_ids, [("Capture order", [source_days[r["source_day"]] + 1 for r in batches])])
    chart("batch_rows", "Microbatch size", "Structured Streaming batch", "Flows", batch_ids,
          [("rows", [int(r["rows"]) for r in batches])], "bar")
    chart("batch_latency", "Batch processing time", "Structured Streaming batch", "Seconds", batch_ids,
          [("Callback", [float(r["processing_seconds"]) for r in batches]),
           ("Scoring and cache materialization", [float(r["scoring_seconds"]) for r in batches])])

    models = [json.loads(r["classifier_metrics"]) for r in days]
    chart("predicted_attack", "Frozen classifier positive rates by capture day", "Capture day", "Positive flows (%)",
          dates, [(name.replace("_", " ").title(), [100 * x[name]["predicted_rate"] for x in models]) for name in models[0]])
    chart("novelty", "Flows above the saved K-Means P99 cutoff", "Capture day", "Flagged flows (%)",
          dates, [("P99", [100 * json.loads(r["novelty_metrics"])["flag_rate"] for r in days])], "bar")
    clusters = np.array([json.loads(r["cluster_counts"]) for r in days], dtype=float)
    clusters /= clusters.sum(axis=1)[:, None]
    figure, ax = plt.subplots(figsize=(8.7, 3.8), layout="constrained")
    ax.stackplot(dates, (100 * clusters).T, labels=[str(i) for i in range(clusters.shape[1])], colors=plt.get_cmap("tab20").colors[:clusters.shape[1]])
    ax.set(title="Frozen K-Means occupancy by capture day", xlabel="Capture day", ylabel="Cluster share (%)")
    ax.legend(ncols=6, fontsize=7, title="Cluster", loc="upper left")
    figure.savefig(output / "phase6_occupancy.png", dpi=120, metadata={"Software": "MMDS Phase 6"})
    plt.close(figure)
    names.append("phase6_occupancy.png")

    daily = [r for r in shifts if r["scope"] == "daily"]
    for category, name, title in (("CLUSTER_SHIFT", "cluster_shift", "Cluster occupancy divergence"),
                                   ("INPUT_SHIFT", "input_shift", "Raw feature divergence"),
                                   ("SCORE_SHIFT", "score_shift", "Frozen classifier score divergence")):
        series = [r for r in daily if r["category"] == category]
        detectors = sorted({r["detector"] for r in series})
        chart(name, title + " versus historical reference", "Capture day", "Jensen–Shannon bits", dates,
              [(name, [float(r["value"]) for r in series if r["detector"] == name]) for name in detectors])
    flagged = {day: sum(row["source_day"] == day for row in alerts) for day in source_days}
    chart("alerts", "Window and daily alerts by capture day", "Capture day", "Alert records", dates,
          [("alerts", [flagged[r["source_day"]] for r in days])], "bar")
    chart("performance", "Retrospective attack recall at the frozen thresholds", "Capture day", "Recall (%)", dates,
          [(name.replace("_", " ").title(), [100 * x[name]["recall"] if x[name]["recall"] is not None else np.nan for x in models])
           for name in models[0]])
    return names
