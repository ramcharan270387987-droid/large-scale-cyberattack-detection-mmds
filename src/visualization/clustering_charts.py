"""Generate compact Phase 5 figures from reconciled aggregate tables."""

from collections import Counter
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np



def draw_phase5(root, experiment, supervised_csv):
    from csv import DictReader

    def read(name):
        with (root / f"phase5_{name}.csv").open(newline="", encoding="utf-8") as stream:
            return list(DictReader(stream))

    summary = json.loads((root / "phase5_summary.json").read_text())
    profiles, composition = read("cluster_profiles"), read("composition")
    occupancy, shifts, centroids = read("cluster_occupancy"), read("temporal_shift"), read("centroids")
    novelty, histogram = read("novelty_metrics"), read("score_histogram")
    total = sum(int(item["records"]) for item in profiles)
    if total != summary["retained_rows"] or sum(int(item["count"]) for item in composition) != total:
        raise ValueError("Chart totals do not match the retained population")
    folder = root / "figures"
    folder.mkdir(exist_ok=True)
    prefix = f"phase5_{experiment.lower()}"
    k = summary["selected_k"]
    ids = list(range(k))
    figures = []
    colors = plt.get_cmap("tab20")(np.linspace(0, 1, k))

    def show(fig, name):
        target = folder / f"{prefix}_{name}.png"
        fig.savefig(target, dpi=120, bbox_inches="tight", metadata={"Software": "MMDS Phase 5"})
        plt.close(fig)
        figures.append(target.name)

    def bar(name, items, label, title):
        fig, ax = plt.subplots(figsize=(6.8, 3.4), layout="constrained")
        ax.bar([str(a) for a, _ in items], [b for _, b in items], color="#087e8b")
        ax.set_ylabel(label)
        ax.set_title(title, loc="left")
        ax.grid(axis="y", alpha=.2)
        show(fig, name)

    bar("cluster_sizes", [(r["cluster"], int(r["records"])) for r in profiles], "Records",
        f"{experiment} · cluster size across retained captures")
    bar("cluster_attack_share", [(r["cluster"], 100 * float(r["attack_share"])) for r in profiles],
        "Observed attack share (%)", f"{experiment} · external label composition")
    families = sorted({r["attack_family"] for r in composition})
    matrix = Counter()
    for row in composition:
        matrix[int(row["cluster"]), row["attack_family"]] += int(row["count"])
    counts = [[matrix[i, family] for family in families] for i in ids]
    fig, ax = plt.subplots(figsize=(7.8, 3.9), layout="constrained")
    view = ax.imshow(np.log10(1 + np.array(counts)), aspect="auto", cmap="cividis")
    ax.set_xticks(range(len(families)), families, rotation=25, ha="right")
    ax.set_yticks(ids, ids)
    ax.set_ylabel("Cluster")
    ax.set_title(f"{experiment} · cluster by observed family")
    fig.colorbar(view, ax=ax, label="log10(1 + records)")
    show(fig, "family_heatmap")

    daily = [r for r in occupancy if r["window_hour"] == "-1"]
    days = sorted({r["source_day"] for r in daily})
    posts = {(r["source_day"], int(r["cluster"])): float(r["occupancy"]) for r in daily}
    if sum(int(r["records"]) for r in daily) != total or any(
        abs(sum(posts.get((day, i), 0) for i in ids) - 1) > 1e-8 for day in days
    ):
        raise ValueError("Chart occupancy partitions do not reconcile")
    fig, ax = plt.subplots(figsize=(8.1, 3.8), layout="constrained")
    bottom = np.zeros(len(days))
    for i in ids:
        y = [100 * posts.get((day, i), 0) for day in days]
        ax.bar([d[5:] for d in days], y, bottom=bottom, color=colors[i], label=str(i))
        bottom += y
    ax.set_ylabel("Cluster occupancy (%)")
    ax.set_title(f"{experiment} · occupancy by capture day")
    ax.legend(ncols=min(k, 6), title="Cluster", fontsize=7)
    show(fig, "daily_occupancy")
    bar("temporal_shift", [(r["source_day"][5:], float(r["js_divergence_bits"]))
                           for r in shifts if r["window_hour"] == "-1"], "Jensen–Shannon divergence (bits)",
        f"{experiment} · daily occupancy versus reference")

    names = summary["preprocessing"]["active"]
    positions = {(int(r["cluster"]), r["feature"]): float(r["center"]) for r in centroids}
    fig, ax = plt.subplots(figsize=(9.5, 4.6), layout="constrained")
    view = ax.imshow([[positions[i, key] for key in names] for i in ids], aspect="auto", cmap="coolwarm")
    ax.set_xticks(range(len(names)), names, rotation=60, ha="right", fontsize=7)
    ax.set_yticks(ids, ids)
    ax.set_ylabel("Cluster")
    ax.set_title(f"{experiment} · centered and scaled signed-log centroids")
    fig.colorbar(view, ax=ax, label="Reference standard deviations")
    show(fig, "centroid_profiles")

    rank = "0" if experiment == "G" else "2"
    fig, ax = plt.subplots(figsize=(7, 3.6), layout="constrained")
    for label, title, color in (("0", "Benign", "#087e8b"), ("1", "Attack", "#b44a31")):
        rows = sorted((r for r in histogram if r["split_rank"] == rank and r["binary_label"] == label),
                      key=lambda row: int(row["score_bin"]))
        if rows:
            denominator = sum(int(r["count"]) for r in rows)
            ax.plot([int(r["score_bin"]) / 4 for r in rows], [int(r["count"]) / denominator for r in rows],
                    marker=".", label=title, color=color)
    ax.set_xlabel("log1p(squared distance), 0.25-width bins")
    ax.set_ylabel("Within-label fraction per bin")
    ax.set_title(f"{experiment} · {'all retained' if rank == '0' else 'test'} distance distribution")
    ax.legend()
    show(fig, "distance_histogram")

    day_counts = Counter()
    day_flags = Counter()
    for row in daily:
        day_counts[row["source_day"]] += int(row["records"])
        day_flags[row["source_day"]] += int(row["flags"])
    bar("daily_novelty", [(day[5:], 100 * day_flags[day] / day_counts[day]) for day in days],
        "Rows above reference P99 (%)", f"{experiment} · novelty flags by capture day")

    primary = next(r for r in novelty if r["split_rank"] == rank and r["percentile"] == "0.99" and r["scope"] == "binary")
    bar("binary_novelty", [("Benign", 100 * float(primary["benign_fpr"])), ("Attack", 100 * float(primary["attack_recall"]))],
        "Within-label flag rate (%)", f"{experiment} · {'all retained' if rank == '0' else 'test'} at reference P99")
    if experiment != "G":
        with Path(supervised_csv).open(newline="", encoding="utf-8") as stream:
            rf = next(row for row in DictReader(stream) if row["protocol"] == experiment and row["split"] == "test"
                      and row["model"] == "random_forest" and row["training_cohort"] == "group_sample")
        if int(rf["tp"]) + int(rf["fn"]) != int(primary["attacks"]) or int(rf["tn"]) + int(rf["fp"]) != int(primary["benign"]):
            raise ValueError("Comparison chart test denominators differ")
        fig, ax = plt.subplots(figsize=(7.0, 3.8), layout="constrained")
        x = np.arange(2)
        ax.bar(x - .16, [100 * (1 - float(rf["specificity"])), 100 * float(rf["recall"])], width=.32, label="Phase 4 RF, 0.5")
        ax.bar(x + .16, [100 * float(primary["benign_fpr"]), 100 * float(primary["attack_recall"])], width=.32,
               label="Centroid distance, reference P99")
        ax.set_xticks(x, ["Benign false positives", "Attack recall"])
        ax.set_ylabel("Rate (%)")
        ax.set_title(f"{experiment} · cohort-matched aggregate signals")
        ax.legend()
        show(fig, "supervised_comparison")
    return figures
