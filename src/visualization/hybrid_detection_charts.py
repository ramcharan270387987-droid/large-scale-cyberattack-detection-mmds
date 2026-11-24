"""Render compact Phase 8 aggregate evidence without collecting traffic."""

import csv
from itertools import cycle

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter


FRACTIONS = {"recall", "precision", "fpr", "automatic_coverage", "automatic_error_rate", "attack_rate",
             "mean_probability", "validation_recall", "validation_budget"}
LABELS = {"fpr": "Benign false-positive rate", "rows_per_second": "Flows per second",
          "false_per_1000000": "False alarms per million benign flows",
          "review_per_100000": "Referrals per 100,000 flows", "recall": "Attack recall"}


def build(reports, populations):
    def read(name):
        with (reports / f"phase8_{name}.csv").open(newline="") as handle:
            return list(csv.DictReader(handle))

    figures = reports / "figures"
    figures.mkdir(exist_ok=True)
    names = []

    def finish(fig, name):
        path = figures / f"phase8_{name}.png"
        fig.savefig(path, dpi=125, metadata={"Software": "MMDS Phase 8"})
        names.append(f"figures/{path.name}")
        plt.close(fig)

    def lines(name, title, x, y, rows, group, fmt=lambda x: x, ideal=False, marks=None):
        fig, ax = plt.subplots(figsize=(8.6, 4.6), layout="constrained")
        colors = cycle(("#17696e", "#bd4d3b", "#5852a7", "#87662c", "#487d3a", "#3d75a8", "#8b4574", "#474b58"))
        for key in sorted({group(r) for r in rows}):
            points = [(float(r[x]), float(r[y])) for r in rows if group(r) == key and r[x] != "" and r[y] != ""]
            if points:
                color = next(colors)
                ax.plot([p[0] for p in points], [p[1] for p in points], marker=".", color=color, alpha=.86, label=fmt(key))
                if marks and key in marks:
                    ax.scatter(*marks[key], color=color, marker="D", edgecolors="white", linewidths=.7, zorder=5)
        if ideal:
            ax.plot([0, 1], [0, 1], "--", color="#858587", linewidth=1)
        ax.set(title=title, xlabel=LABELS.get(x, x.replace("_", " ").capitalize()),
               ylabel=LABELS.get(y, y.replace("_", " ").capitalize()))
        for axis, variable in ((ax.xaxis, x), (ax.yaxis, y)):
            if variable in FRACTIONS:
                axis.set_major_formatter(PercentFormatter(1))
        ax.grid(alpha=.18)
        if ax.get_legend_handles_labels()[0]:
            ax.legend(fontsize=7, ncols=2, loc="best")
        finish(fig, name)

    def bars(name, title, rows, value, label, width=8.6):
        samples = [(label(r), float(r[value])) for r in rows if r[value] != ""]
        fig, ax = plt.subplots(figsize=(width, max(3.4, len(samples) * .25)), layout="constrained")
        heights = [r[1] for r in samples]
        bars = ax.barh([r[0] for r in samples], heights, color="#17696e", alpha=.87)
        if heights and not any(heights):
            ax.set_xlim(0, .01 if value in FRACTIONS else 1)
            ax.bar_label(bars, labels=["0%" if value in FRACTIONS else "0"]*len(heights), padding=4, fontsize=8)
        ax.invert_yaxis()
        ax.set(title=title, xlabel=LABELS.get(value, value.replace("_", " ").capitalize()))
        if value in FRACTIONS:
            ax.xaxis.set_major_formatter(PercentFormatter(1))
        ax.grid(axis="x", alpha=.18)
        finish(fig, name)

    summary = read("score_curves")
    comparison = read("model_comparison")
    reference = "B" if "B" in populations else next(iter(populations))
    base, winner = populations[reference]["supervised_base"], populations[reference]["selected"]
    population_title = "B retrospective chronological test" if reference == "B" else f"{reference} test"
    subset = [r for r in summary if r["population"] == reference and r["partition"] == "test" and
              r["method"] in {base, "random_forest", "platt", "isotonic", "novelty", winner}]
    for short, x, y, desc in (("precision_recall", "recall", "precision", "Precision versus recall"),
                              ("roc", "fpr", "recall", "Binned ROC with frozen points marked"),
                              ("threshold_recall", "threshold", "recall", "Threshold and attack recall"),
                              ("threshold_fpr", "threshold", "fpr", "Threshold and benign false-positive rate")):
        marks = {r["method"]: (float(r[x]), float(r[y])) for r in comparison if r["population"] == reference
                 and r.get(x) and r.get(y)} if short == "roc" else None
        lines(short, f"{population_title} · {desc}", x, y, subset, lambda r: r["method"], marks=marks)

    reliability = [r for r in read("reliability") if r["population"] == reference and r["partition"] == "test"]
    lines("reliability", f"{reference} test · Reliability by probability bin", "mean_probability", "attack_rate",
          reliability, lambda r: r["method"], ideal=True)
    bars("brier", "Held-out probability reliability", [r for r in read("calibration_metrics") if r["partition"] == "test"],
         "brier", lambda r: f"{r['population']} · {r['method']}")
    costs = [r for r in read("cost_sensitive_results") if r["population"] == reference]
    lines("class_weights", f"{reference} operating split · Recall at the 1% FPR ceiling", "weight", "recall",
          sorted(costs, key=lambda r: float(r["weight"])), lambda r: r["model"].split("_", 1)[0])
    fusion = [r for r in read("fusion_selection") if r["method"].startswith("blend_")]
    for row in fusion:
        row["supervised_weight"] = row["method"].split("_", 1)[1].replace("_", ".")
    lines("fusion_weights", "Operating-split recall across supervised blend weights", "supervised_weight", "validation_recall",
          sorted(fusion, key=lambda r: float(r["supervised_weight"])), lambda r: r["population"])
    budgets = [r | {"validation_budget": r["policy"].removeprefix("budget_")} for r in read("false_positive_budgets")
               if r["population"] == reference and r["policy"].startswith("budget_") and
               r["method"] in {base, "supervised", "novelty", winner}]
    lines("validation_budgets", f"{reference} test · Realized recall at validation-selected budgets", "validation_budget", "recall",
          sorted(budgets, key=lambda r: float(r["validation_budget"])), lambda r: r["method"])
    families = [r for r in read("family_recall") if r["method"] == populations[r["population"]]["selected"]]
    bars("family_recall", "Selected fusion · Observed family recall", families, "recall",
         lambda r: f"{r['population']} · {r['family']} (n={r['support']})")
    methods = [r for r in comparison if r["method"] in
               {populations[r["population"]]["selected"], "supervised", "novelty"}]
    bars("false_alarms", "False alarms per million held-out benign flows", methods, "false_per_1000000",
         lambda r: f"{r['population']} · {r['method']}")
    triage = read("triage_metrics")
    lines("risk_coverage", "Selective prediction · Error among automatically classified flows", "automatic_coverage",
          "automatic_error_rate", sorted(triage, key=lambda r: float(r["automatic_coverage"])), lambda r: r["population"])
    bars("review_workload", "Primary triage · Referrals per 100,000 held-out flows",
         [r for r in triage if r["policy"] == "primary"], "review_per_100000", lambda r: r["population"])
    ablation = [r for r in read("ablation_results") if r["population"] == reference]
    bars("ablation", f"{reference} test · Component ablations and recall", ablation, "recall",
         lambda r: f"{r['component']} · {r['method']} (FPR {float(r['fpr']):.2%})")
    bars("overhead", "Matched single-node scoring workload", [r for r in read("performance") if r["stage"].endswith("_matched")],
         "rows_per_second", lambda r: f"{r['population']} · {r['stage'].split('_')[0]}")
    rolling = [r for r in methods if r["population"].startswith("R")]
    if rolling:
        bars("rolling_folds", "Rolling holdouts · Recall at frozen thresholds", rolling, "recall",
             lambda r: f"{r['population']} · {r['method']} (FPR {float(r['fpr']):.2%})")
    return names
