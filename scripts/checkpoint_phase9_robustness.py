"""Reconcile the grouped-random robustness artifacts and checkpoint them."""
import argparse
import csv
from hashlib import sha256
import json
import math
from pathlib import Path

from kaggle_web_api import download_archive
from src.ml.phase9_evaluation import multiclass


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ROOT = "mmds_phase9_sensitivity"
REQUIRED = ("phase9_sensitivity_receipt.json", "phase9_sensitivity_metrics.csv",
            "phase9_sensitivity_confusion.csv", "phase9_sensitivity_day.csv")
VARIANTS = {"frozen_seed_23013", "unweighted", "inverse", "duplicate_group_weight", "second_seed"}


def rows(payload):
    return list(csv.DictReader(payload.decode().splitlines()))


def checkpoint(version, log, notebook):
    if "PHASE9 grouped-random sensitivity complete" not in log.read_text(errors="replace"):
        raise ValueError("Missing successful worker log marker")
    with download_archive(version, 2 * 1024 * 1024) as archive:
        evidence = {name: archive.read(f"{ARCHIVE_ROOT}/{name}") for name in REQUIRED}
        high = "phase9_sensitivity_high_confidence_errors.csv"
        if f"{ARCHIVE_ROOT}/{high}" in archive.namelist():
            evidence[high] = archive.read(f"{ARCHIVE_ROOT}/{high}")
    receipt = json.loads(evidence[REQUIRED[0]])
    original = json.loads((ROOT / "manifests/phase9_A.json").read_text())
    metrics = rows(evidence[REQUIRED[1]])
    confusion = rows(evidence[REQUIRED[2]])
    per_day = rows(evidence[REQUIRED[3]])
    if ((receipt["status"], receipt["scenario"]) != ("validated", "A") or
            receipt["classes"] != original["classes"] or receipt["training_support"] != original["training_support"] or
            receipt["matched_test_rows"] != original["test"]["rows"]):
        raise ValueError("Sensitivity population differs from the verified grouped-random stage")
    if {row["variant"] for row in metrics} != VARIANTS or len(metrics) != 2 * len(VARIANTS):
        raise ValueError("Missing or duplicate robustness variants")
    for row in metrics:
        variant, weighting = row["variant"], row["weighting"]
        pairs = {(int(cell["actual"]), int(cell["predicted"])): float(cell["count"]) for cell in confusion
                 if cell["variant"] == variant and cell["weighting"] == weighting}
        expected, _ = multiclass(pairs, range(len(receipt["classes"])))
        for metric, value in expected.items():
            if (value is None and row[metric]) or (value is not None and not math.isclose(value, float(row[metric]), abs_tol=1e-12)):
                raise ValueError(f"Sensitivity metric {metric} does not reconcile for {variant}")
        if weighting == "flow":
            days = [day for day in per_day if day["variant"] == variant]
            if sum(int(day["rows"]) for day in days) != receipt["matched_test_rows"]:
                raise ValueError("Sensitivity capture-day counts differ")
            if sum(int(day["correct"]) for day in days) != sum(n for (a, p), n in pairs.items() if a == p):
                raise ValueError("Sensitivity capture-day correct counts differ")
            if variant == "frozen_seed_23013":
                for key in ("accuracy", "macro_f1"):
                    if not math.isclose(expected[key], original["test"][key], abs_tol=1e-12):
                        raise ValueError("Frozen baseline metrics differ")
    destination = ROOT / "reports/phase9_sensitivity"
    destination.mkdir(parents=True, exist_ok=True)
    for name, data in evidence.items():
        (destination / name).write_bytes(data)
    manifest_path = ROOT / "manifests/phase9_experiments.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["grouped_random_sensitivity"] = {
        "status": "validated", "worker_status": "COMPLETE", "kernel_version": int(version.rsplit("/", 1)[-1]),
        "log_sha256": sha256(log.read_bytes()).hexdigest(), "notebook_sha256": sha256(notebook.read_bytes()).hexdigest(),
        "artifacts": {str((destination / name).relative_to(ROOT)): sha256(data).hexdigest() for name, data in evidence.items()},
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print("Reconciled all grouped-random sensitivity variants")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version")
    parser.add_argument("log", type=Path)
    parser.add_argument("notebook", type=Path)
    args = parser.parse_args()
    checkpoint(args.version, args.log, args.notebook)
