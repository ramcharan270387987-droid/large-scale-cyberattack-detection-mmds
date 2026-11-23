"""Render compact PNGs from Phase 3 aggregate CSVs."""

import argparse
from collections import Counter
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


COLORS = ("#007f83", "#b94c1d", "#5267a0", "#6b7e2e", "#955eb0", "#ba8275")
FIGURES = (
    "binary_distribution", "attack_family_frequencies", "daily_traffic_volume", "daily_attack_prevalence",
    "family_by_capture_day", "flow_duration_comparison", "packet_byte_distributions", "protocol_distribution",
    "destination_ports", "temporal_feature_changes",
)


def read_table(root, name):
    with (root / f"phase3_{name}.csv").open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_inputs(root):
    tables = {name: read_table(root, name) for name in (
        "traffic_totals", "attack_families", "daily_traffic", "family_by_day",
        "feature_statistics", "protocols", "destination_ports", "time_windows",
    )}
    totals = {row["population"]: int(row["records"]) for row in tables["traffic_totals"]}
    require(set(totals) == {"attack", "benign"}, "Expected both populations")
    daily = tables["daily_traffic"]
    require(sum(int(row["records"]) for row in daily) == sum(totals.values()), "Daily traffic total differs")
    require(all(int(row["benign"]) + int(row["attacks"]) == int(row["records"]) for row in daily), "Daily label counts differ")
    require(sum(int(row["records"]) for row in tables["attack_families"]) == totals["attack"], "Attack family total differs")
    require(sum(int(row["records"]) for row in tables["family_by_day"]) == totals["attack"], "Family/day total differs")
    require(sum(int(row["records"]) for row in tables["protocols"]) == sum(totals.values()), "Protocol total differs")
    stats = tables["feature_statistics"]
    required = {(name, population) for name in ("flow_duration", "total_packets", "total_bytes") for population in totals}
    available = {(row["feature"], row["population"]) for row in stats if row["valid"] and row["quantiles"]}
    require(required <= available, "Quantile chart input is incomplete")
    return tables


def draw(tables, destination):
    destination.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                        "axes.grid": True, "grid.alpha": 0.20, "axes.axisbelow": True})
    outputs = []

    def save(fig, name):
        path = destination / f"phase3_{name}.png"
        fig.savefig(path, dpi=130, bbox_inches="tight", metadata={"Software": "MMDS Phase 3"})
        plt.close(fig)
        outputs.append(path)

    def bar(name, values, ylabel, title, rotation=0, horizontal=False):
        labels, numbers = zip(*values)
        fig, ax = plt.subplots(figsize=(7.0, 3.4), layout="constrained")
        if horizontal:
            ax.barh(labels, numbers, color=COLORS[0])
            ax.set_xlabel(ylabel)
            ax.invert_yaxis()
        else:
            ax.bar(labels, numbers, color=[COLORS[i % len(COLORS)] for i in range(len(labels))])
            ax.set_ylabel(ylabel)
            ax.tick_params(axis="x", labelrotation=rotation)
        ax.set_title(title, loc="left")
        save(fig, name)

    bar(FIGURES[0], [(row["population"].title(), int(row["records"])) for row in tables["traffic_totals"]],
        "Records", "All captures · binary label distribution")
    bar(FIGURES[1], [(row["attack_family"], int(row["records"])) for row in tables["attack_families"]],
        "Attack records", "All captures · attack-family frequencies", horizontal=True)
    daily = tables["daily_traffic"]
    dates = [row["source_day"][5:] for row in daily]
    bar(FIGURES[2], list(zip(dates, [int(row["records"]) for row in daily])), "Records", "Traffic volume by capture day", 30)
    bar(FIGURES[3], list(zip(dates, [100 * float(row["attack_share"]) for row in daily])), "Attack share (%)",
        "Attack prevalence by capture day", 30)

    values = {(row["source_day"][5:], row["attack_family"]): int(row["records"]) for row in tables["family_by_day"]}
    fig, ax = plt.subplots(figsize=(8.1, 4.3), layout="constrained")
    bottom = [0] * len(dates)
    for i, row in enumerate(tables["attack_families"]):
        family = row["attack_family"]
        counts = [values[(day, family)] for day in dates]
        ax.bar(dates, counts, bottom=bottom, label=family, color=COLORS[i])
        bottom = [a + b for a, b in zip(bottom, counts)]
    ax.set_ylabel("Attack records")
    ax.set_title("Attack families by capture day", loc="left")
    ax.tick_params(axis="x", labelrotation=30)
    ax.legend(ncols=2, fontsize=8)
    save(fig, FIGURES[4])

    stats = {(row["population"], row["feature"]): json.loads(row["quantiles"]) for row in tables["feature_statistics"]}

    def quantile_axis(ax, feature, ylabel):
        for i, population in enumerate(("benign", "attack")):
            ax.plot(("P10", "P50", "P90", "P99"), stats[population, feature], marker="o",
                    color=COLORS[i], label=population.title())
        ax.set_yscale("symlog", linthresh=1)
        ax.set_ylabel(ylabel)
        ax.set_xlabel("Approximate quantile")
        ax.legend()

    fig, ax = plt.subplots(figsize=(6.2, 3.6), layout="constrained")
    quantile_axis(ax, "flow_duration", "Duration (µs, symlog)")
    ax.set_title("Flow duration by binary label", loc="left")
    save(fig, FIGURES[5])

    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.8), layout="constrained")
    quantile_axis(axes[0], "total_packets", "Packets per flow (symlog)")
    quantile_axis(axes[1], "total_bytes", "Bytes per flow (symlog)")
    fig.suptitle("Packet and byte distributions by binary label")
    save(fig, FIGURES[6])

    protocols = Counter()
    for row in tables["protocols"]:
        protocols[row["protocol"]] += int(row["records"])
    bar(FIGURES[7], sorted(protocols.items()), "Records", "All captures · IP protocol codes")

    fig, axes = plt.subplots(1, 2, figsize=(9.0, 4.4), layout="constrained")
    for i, population in enumerate(("benign", "attack")):
        counts = Counter()
        for row in tables["destination_ports"]:
            if row["population"] == population and row["scope"] == "population":
                counts[row["dst_port"] or "Missing"] += int(row["records"])
        top = counts.most_common(8)
        axes[i].barh([port for port, _ in top], [count for _, count in top], color=COLORS[i])
        axes[i].invert_yaxis()
        axes[i].set_title(population.title())
        axes[i].set_xlabel("Records")
    fig.suptitle("Most frequent destination ports by label")
    save(fig, FIGURES[8])

    fig, ax = plt.subplots(figsize=(8.0, 4.0), layout="constrained")
    times = sorted({(r["source_day"], int(r["window_start_hour"])) for r in tables["time_windows"]})
    index = {key: i for i, key in enumerate(times)}
    for i, population in enumerate(("benign", "attack")):
        selected = [r for r in tables["time_windows"] if r["population"] == population and r["median_duration_us"]]
        ax.scatter([index[r["source_day"], int(r["window_start_hour"])] for r in selected],
                   [float(r["median_duration_us"]) for r in selected], s=13, color=COLORS[i], label=population.title())
    ticks = [i for i, key in enumerate(times) if i == 0 or key[0] != times[i - 1][0]]
    ax.set_xticks(ticks, [times[i][0][5:] for i in ticks], rotation=30)
    ax.set_xlabel("Observed capture days · three-hour wall-clock windows")
    ax.set_ylabel("Approximate median duration (µs, symlog)")
    ax.set_yscale("symlog", linthresh=1)
    ax.set_title("Eligible event-time flow duration summaries", loc="left")
    ax.legend()
    save(fig, FIGURES[9])
    return outputs


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tables", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    draw(load_inputs(args.tables), args.destination)
