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
    for version, stage in stages.items():
        for scenario in stage["scenarios"]:
            path = f"reports/phase9_open_set_evidence/{version}/{scenario}/score_histograms.csv"
            rows = table(stage["artifacts"], path)
            curves = rejection_curves(rows)
            for ax, values in zip(axes, curves):
                if values is not None:
                    ax.plot(*values, label=scenario)
    for ax in axes:
        ax.legend(fontsize=8)
    fig.suptitle("Open-set discrimination using frozen classifier confidence")
    save(figures, "risk_coverage_roc_pr", fig)


if __name__ == "__main__":
    manifest = json.loads(MANIFEST.read_text())
    figures = manifest.setdefault("extended_figures_sha256", {})
    hierarchies(figures, manifest)
    sensitivities(figures, manifest)
    open_set(figures, manifest)
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
