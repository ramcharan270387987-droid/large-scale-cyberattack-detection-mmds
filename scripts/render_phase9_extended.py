"""Render hierarchy, sensitivity and score-distribution figures from receipts."""

from collections import Counter
import csv
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports"
MANIFEST = ROOT / "manifests/phase9_experiments.json"


def evidence(manifest, name):
    value = (ROOT / name).read_bytes()
    if sha256(value).hexdigest() != manifest[name]:
        raise ValueError(f"Evidence checksum mismatch for {name}")
    return value


def table(manifest, name):
    return list(csv.DictReader(StringIO(evidence(manifest, name).decode())))


def save(figures, name, fig):
    relative = f"figures/phase9_{name}.png"
    path = REPORT / relative
    fig.savefig(path, dpi=125, bbox_inches="tight", metadata={"Software": "MMDS Phase 9"})
    plt.close(fig)
    figures[relative] = sha256(path.read_bytes()).hexdigest()


def archived_classification(figures, manifest):
    stages = manifest["stages"]
    catalog = ("A", "B", "Web", "Bot", "Infiltration", "DDoS")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), layout="constrained")
    left, right = axes
    scores = [stages[scenario]["test"]["macro_f1"] for scenario in catalog]
    left.bar(catalog, [value or 0 for value in scores], color="#276687")
    left.annotate("No known attacks", xy=(1, .03), ha="center", rotation=90)
    left.set(ylabel="Known-family macro F1", ylim=(0, 1), title="Closed-set performance")
    right.bar(catalog, [stages[scenario]["seconds"] for scenario in catalog], color="#66a892")
    right.set(ylabel="Recorded execution seconds", title="Archived family-stage runtime")
    for ax in axes:
        ax.tick_params(axis="x", rotation=15)
    save(figures, "macro_f1_runtime", fig)

    relative = "reports/phase9_per_family.csv"
    rows = table({relative: manifest["tables_sha256"]["phase9_per_family.csv"]}, relative)
    selected = {int(row["class_id"]): row for row in rows if row["scenario"] == "A"}
    classes = sorted(stages["A"]["classes"].items(), key=lambda item: item[1])
    fig, ax = plt.subplots(figsize=(8.5, 4.3), layout="constrained")
    for offset, metric, color in ((-0.16, "precision", "#276687"), (0.16, "recall", "#66a892")):
        measured = [(class_id + offset, float(selected[class_id][metric])) for _, class_id in classes
                    if selected[class_id][metric]]
        ax.bar([i for i, _ in measured], [value for _, value in measured], width=.30, label=metric.title(), color=color)
    ax.set(xticks=range(len(classes)), xticklabels=[name for name, _ in classes], ylim=(0, 1),
           title="Grouped-random per-family precision and recall")
    ax.tick_params(axis="x", rotation=15)
    ax.legend()
    save(figures, "grouped_random_family_precision_recall", fig)


def hierarchies(figures, manifest):
    scenarios = manifest.get("hierarchy", {})
    if not scenarios:
        return
    fig, axes = plt.subplots(len(scenarios), 1, figsize=(9, 3.2 * len(scenarios)), squeeze=False)
    gates = {"phase4_rf": "Phase 4 RF", "phase8_supervised": "Phase 8 supervised",
             "phase8_hybrid": "Phase 8 hybrid", "oracle": "Oracle diagnostic"}
    outcomes = {"missed_attack": ("Missed by detector", "#c75236"),
                "unknown_false_accept": ("Passed and named as known", "#d6ad36"),
                "unknown_rejected": ("Passed and rejected as UNKNOWN", "#26806f")}
    for ax, (scenario, stage) in zip(axes[:, 0], scenarios.items()):
        counts = table(stage["artifacts"], f"reports/phase9_hierarchy/{scenario}/phase9_hierarchical_counts.csv")
        summary = Counter()
        for row in counts:
            if row["binary_label"] == "1":
                summary[row["gate"], row["outcome"]] += int(row["count"])
        left = [0.0] * len(gates)
        for outcome, (label, color) in outcomes.items():
            fractions = [summary[gate, outcome] / sum(summary[gate, key] for key in outcomes) for gate in gates]
            ax.barh(list(gates.values()), fractions, left=left, label=label, color=color)
            left = [a + b for a, b in zip(left, fractions)]
        ax.set(title=f"{scenario} · retained attack outcomes", xlabel="Share of all retained attacks", xlim=(0, 1))
        ax.xaxis.set_major_formatter(PercentFormatter(1))
        ax.invert_yaxis()
    axes[-1, 0].legend(loc="upper center", bbox_to_anchor=(0.5, -0.3), ncol=2)
    fig.tight_layout()
    save(figures, "hierarchical_attack_outcomes", fig)


def sensitivities(figures, manifest):
    stage = manifest.get("grouped_random_sensitivity")
    if stage is None:
        return
    rows = table(stage["artifacts"], "reports/phase9_sensitivity/phase9_sensitivity_metrics.csv")
    labels = ["Frozen seed", "Unweighted", "Inverse", "Duplicate-weighted", "Second seed"]
    variants = ("frozen_seed_23013", "unweighted", "inverse", "duplicate_group_weight", "second_seed")
    values = {(r["variant"], r["weighting"]): float(r["macro_f1"]) for r in rows}
    fig, ax = plt.subplots(figsize=(8.8, 4))
    for offset, measure, label, color in ((-0.16, "flow", "Flow weighted", "#276687"),
                                         (0.16, "predictor_group_equal", "Group weighted", "#66a892")):
        ax.bar([i + offset for i in range(len(labels))], [values[v, measure] for v in variants], 0.3,
               label=label, color=color)
    ax.set(xticks=range(len(labels)), xticklabels=labels, ylabel="Macro F1", ylim=(0, 1),
           title="Grouped-random sensitivity on matched evaluation rows")
    ax.tick_params(axis="x", rotation=12)
    ax.legend()
    save(figures, "grouped_random_sensitivity", fig)


def rejection_curves(rows):
    profile = Counter()
    for row in rows:
        if row["method"] == "maximum":
            profile[int(row["bin"]), row["known"].lower() == "true", row["correct"].lower() == "true"] += int(row["count"])
    known = sum(n for (_, k, _), n in profile.items() if k)
    unknown = sum(n for (_, k, _), n in profile.items() if not k)
    num_correct = sum(n for (_, _, correct), n in profile.items() if correct)
    rejected_known = rejected_unknown = rejected_correct = 0
    coverage, risk = [1.0], [1 - num_correct / (known + unknown)]
    tpr, fpr, precision = [0.0], [0.0], [1.0]
    for bin_num in sorted({b for b, _, _ in profile}, reverse=True):
        rejected_known += profile[bin_num, True, False] + profile[bin_num, True, True]
        rejected_unknown += profile[bin_num, False, False]
        rejected_correct += profile[bin_num, True, True]
        remaining = known + unknown - rejected_known - rejected_unknown
        if remaining:
            coverage.append(remaining / (known + unknown))
            risk.append(1 - (num_correct - rejected_correct) / remaining)
        if known and unknown:
            tpr.append(rejected_unknown / unknown)
            fpr.append(rejected_known / known)
            precision.append(rejected_unknown / (rejected_unknown + rejected_known))
    return (coverage, risk), (fpr, tpr) if known and unknown else None, (tpr, precision) if known and unknown else None


def open_set(figures, manifest):
    stages = manifest.get("open_set_evidence", {})
    if not stages:
        return
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), layout="constrained")
    plots = ("Accepted coverage", "Known-family false rejection", "Unknown-family rejection recall")
    targets = ("Accepted error rate", "Unknown-family rejection recall", "Unknown-rejection precision")
    for ax, xlabel, ylabel in zip(axes, plots, targets):
        ax.set(xlabel=xlabel, ylabel=ylabel, xlim=(0, 1), ylim=(0, 1))
    score_fig, score_axes = plt.subplots(2, 3, figsize=(12, 6), layout="constrained")
    day_fig, day_axes = plt.subplots(2, 3, figsize=(12, 6), layout="constrained")
    scenarios = [(version, stage, scenario) for version, stage in stages.items() for scenario in stage["scenarios"]]
    for i, (version, stage, scenario) in enumerate(scenarios):
        prefix = f"reports/phase9_open_set_evidence/{version}/{scenario}"
        rows = table(stage["artifacts"], f"{prefix}/score_histograms.csv")
        curves = rejection_curves(rows)
        for ax, values in zip(axes, curves):
            if values is not None:
                ax.plot(*values, label=scenario)
        ax = score_axes.flat[i]
        dist = Counter()
        for row in rows:
            if row["method"] == "maximum":
                dist[min(int(row["bin"]) * 32 // 2048, 31), row["known"].lower() == "true"] += int(row["count"])
        for known, label, color in ((True, "Known", "#276687"), (False, "Unknown", "#c75236")):
            support = sum(n for (_, item), n in dist.items() if item == known)
            if support:
                ax.step([j / 32 for j in range(32)], [dist[j, known] / support for j in range(32)],
                        where="post", label=label, color=color)
        ax.set(title=scenario, xlabel="Maximum-score uncertainty", ylabel="Share within target group")
        ax.legend(fontsize=7)
        ax = day_axes.flat[i]
        day_rows = table(stage["artifacts"], f"{prefix}/day_rejection.csv")
        day_counts = Counter()
        for row in day_rows:
            if row["method"] == "maximum":
                day_counts[row["source_day"][5:], row["known"].lower() == "true", row["rejected"].lower() == "true"] += int(row["count"])
        days = sorted({day for day, _, _ in day_counts})
        for known, label, color in ((True, "Known", "#276687"), (False, "Unknown", "#c75236")):
            supported = [(i, day_counts[day, known, True] / total) for i, day in enumerate(days)
                         if (total := day_counts[day, known, True] + day_counts[day, known, False])]
            if supported:
                ax.scatter([pos for pos, _ in supported], [rate for _, rate in supported], label=label, color=color, s=16)
        ax.set(title=scenario, xticks=range(len(days)), xticklabels=days, ylabel="Rejected share", ylim=(0, 1))
        ax.tick_params(axis="x", rotation=45)
        ax.yaxis.set_major_formatter(PercentFormatter(1))
        ax.legend(fontsize=7)
    for score_ax, day_ax in zip(list(score_axes.flat)[len(scenarios):], list(day_axes.flat)[len(scenarios):]):
        score_ax.set_visible(False)
        day_ax.set_visible(False)
    score_fig.suptitle("Known and unknown score distributions")
    day_fig.suptitle("Per-day rejection at the frozen 5% validation budget")
    save(figures, "known_unknown_score_distributions", score_fig)
    save(figures, "per_day_rejection", day_fig)
    for ax in axes:
        ax.legend(fontsize=8)
    fig.suptitle("Open-set discrimination using frozen classifier confidence")
    save(figures, "risk_coverage_roc_pr", fig)


def worker_cost(figures, manifest):
    runs = []
    for population, stage in manifest.get("hierarchy", {}).items():
        path = f"reports/phase9_hierarchy/{population}/phase9_hierarchical_receipt.json"
        runs.append((stage, path, f"{population} hierarchy"))
    sensitivity = manifest.get("grouped_random_sensitivity")
    if sensitivity is not None:
        runs.append((sensitivity, "reports/phase9_sensitivity/phase9_sensitivity_receipt.json", "Sensitivity"))
    for version, stage in manifest.get("open_set_evidence", {}).items():
        path = f"reports/phase9_open_set_evidence/{version}/receipt.json"
        runs.append((stage, path, "Open-set aggregates"))
    if not runs:
        return
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), layout="constrained")
    labels, elapsed, peak = [], [], []
    for stage, path, label in runs:
        receipt = json.loads(evidence(stage["artifacts"], path))
        labels.append(f"v{stage['kernel_version']} · {label}")
        elapsed.append(receipt["elapsed_seconds"] / 60)
        peak.append(receipt["driver_peak_rss_bytes"] / 1024**3)
    axes[0].barh(labels, elapsed, color="#276687")
    axes[1].barh(labels, peak, color="#66a892")
    axes[0].set(xlabel="Elapsed minutes", title="Measured worker runtime")
    axes[1].set(xlabel="Peak RSS (GiB)", title="Measured driver memory")
    for ax in axes:
        ax.invert_yaxis()
    save(figures, "worker_resources", fig)


if __name__ == "__main__":
    manifest = json.loads(MANIFEST.read_text())
    figures = manifest.setdefault("extended_figures_sha256", {})
    archived_classification(figures, manifest)
    hierarchies(figures, manifest)
    sensitivities(figures, manifest)
    open_set(figures, manifest)
    worker_cost(figures, manifest)
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
