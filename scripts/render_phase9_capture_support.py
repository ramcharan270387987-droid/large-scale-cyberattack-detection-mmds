"""Render capture-family confounding from the verified input audit."""
import csv
from hashlib import sha256
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np


def render(root):
    source = root / "reports/phase9_family_support.csv"
    manifest = json.loads((root / "manifests/phase9_experiments.json").read_text())
    if sha256(source.read_bytes()).hexdigest() != manifest["tables_sha256"][source.name]:
        raise ValueError("Phase 9 support table was modified")
    with source.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    days = sorted({row["source_day"] for row in rows})
    families = sorted({row["attack_family"] for row in rows if row["binary_label"] == "1"})
    counts = np.zeros((len(families), len(days)), dtype=np.int64)
    for row in rows:
        if row["binary_label"] == "1":
            counts[families.index(row["attack_family"]), days.index(row["source_day"])] += int(row["count"])
    audit = json.loads((root / "manifests/phase9_input_audit.json").read_text())
    if int(counts.sum()) != audit["input"]["totals"]["1"]:
        raise ValueError("Capture support does not match the input receipt")
    fig, ax = plt.subplots(figsize=(11, 4))
    image = ax.imshow(np.ma.masked_equal(counts, 0), aspect="auto", cmap="Blues",
                      norm=LogNorm(vmin=1, vmax=int(counts.max())))
    ax.set(xticks=range(len(days)), xticklabels=[day[5:] for day in days],
           yticks=range(len(families)), yticklabels=families, xlabel="2018 capture day",
           title="Attack-family support by capture day")
    for (row, col), count in np.ndenumerate(counts):
        if count:
            ax.text(col, row, f"{count:,}", ha="center", va="center", fontsize=7,
                    color="white" if count > 40_000 else "black")
    fig.colorbar(image, ax=ax, label="Flows (log scale)")
    target = root / "reports/figures/phase9_capture_family_support.png"
    fig.savefig(target, dpi=125, bbox_inches="tight", metadata={"Software": "MMDS Phase 9"})
    plt.close(fig)
    for name, values in zip(families, counts):
        print(name, "days", int(np.count_nonzero(values)), "flows", int(values.sum()),
              "largest_day_share", f"{values.max() / values.sum():.3%}")


if __name__ == "__main__":
    render(Path(__file__).resolve().parents[1])
