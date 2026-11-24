"""Validate bounded rejection aggregates and private novelty model hashes."""

import argparse
import csv
from collections import Counter
from hashlib import sha256
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = "mmds_phase9_open_set"
METHODS = {"maximum", "margin", "entropy", "novelty", "combined"}
FILES = ("receipt.json", "thresholds.json", "score_histograms.csv", "day_rejection.csv", "capture_feature_quantiles.csv")


def read_csv(payload):
    return list(csv.DictReader(payload.decode().splitlines()))


def flag(value):
    if value.lower() not in {"true", "false"}:
        raise ValueError("Expected a Boolean evidence field")
    return value.lower() == "true"


def validate(receipt, tables, old):
    hist = read_csv(tables["score_histograms.csv"])
    days = read_csv(tables["day_rejection.csv"])
    thresholds = json.loads(tables["thresholds.json"])
    if {r["method"] for r in hist} != METHODS or {r["method"] for r in days} != METHODS:
        raise ValueError("Missing rejection score")
    for method in METHODS:
        rows = [row for row in hist if row["method"] == method]
        support = Counter()
        for row in rows:
            support[flag(row["known"])] += int(row["count"])
        if dict(support) != {flag(k): v for k, v in receipt["support"].items()}:
            raise ValueError(f"{method} score population differs")
        for budget, threshold in thresholds["reproduction"][method].items():
            rejected = Counter()
            for row in rows:
                if int(row["bin"]) > threshold:
                    rejected[flag(row["known"])] += int(row["count"])
            if budget == "0.05":
                day_counts = Counter()
                for row in days:
                    if row["method"] == method:
                        day_counts[flag(row["known"]), flag(row["rejected"])] += int(row["count"])
                for known in (False, True):
                    if (day_counts[known, True], day_counts[known, False]) != (rejected[known], support[known] - rejected[known]):
                        raise ValueError("Per-day rejection counts differ from the histogram")
            if method in {"maximum", "margin", "entropy"}:
                historical = old[method, budget]
                for known, metric in ((True, "known_false_rejection"), (False, "unknown_rejection_recall")):
                    expected = rejected[known] / support[known] if support[known] else None
                    if (expected is None and historical[metric]) or (
                            expected is not None and not math.isclose(expected, float(historical[metric]), abs_tol=1e-12)):
                        raise ValueError(f"Historical {method} {metric} differs")


def checkpoint(version, log, notebook):
    from kaggle_web_api import download_archive

    if "PHASE9 open-set evidence complete" not in log.read_text(errors="replace"):
        raise ValueError("Missing successful open-set log marker")
    with download_archive(version, 12 * 1024 * 1024) as archive:
        receipt_data = archive.read(f"{ARCHIVE}/receipt.json")
        aggregate = json.loads(receipt_data)
        if aggregate["status"] != "validated":
            raise ValueError("Open-set receipt is not validated")
        evidence = {"receipt.json": receipt_data}
        for scenario in aggregate["scenarios"]:
            tables = {name: archive.read(f"{ARCHIVE}/{scenario}/{name}") for name in FILES}
            examples = "rejection_error_groups.csv"
            if f"{ARCHIVE}/{scenario}/{examples}" in archive.namelist():
                tables[examples] = archive.read(f"{ARCHIVE}/{scenario}/{examples}")
            receipt = json.loads(tables["receipt.json"])
            if receipt["status"] != "validated" or receipt["scenario"] != scenario:
                raise ValueError("Unexpected scenario receipt")
            old = read_csv((ROOT / "reports/phase9_stages" / scenario / "phase9_open_set_metrics.csv").read_bytes())
            validate(receipt, tables, {(r["method"], r["budget"]): r for r in old})
            model = receipt["model"]
            for name, expected in model["sha256"].items():
                content = archive.read(f"{ARCHIVE}/{scenario}/{model['artifact']}/{name}")
                if sha256(content).hexdigest() != expected:
                    raise ValueError(f"{scenario} model component checksum differs")
            evidence.update({f"{scenario}/{name}": payload for name, payload in tables.items()})
    release = int(version.rsplit("/", 1)[-1])
    destination = ROOT / "reports/phase9_open_set_evidence" / str(release)
    for name, payload in evidence.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    manifest_path = ROOT / "manifests/phase9_experiments.json"
    manifest = json.loads(manifest_path.read_text())
    manifest.setdefault("open_set_evidence", {})[str(release)] = {
        "status": "validated", "worker_status": "COMPLETE", "kernel_version": release,
        "scenarios": aggregate["scenarios"], "log_sha256": sha256(log.read_bytes()).hexdigest(),
        "notebook_sha256": sha256(notebook.read_bytes()).hexdigest(),
        "artifacts": {str((destination / name).relative_to(ROOT)): sha256(payload).hexdigest()
                      for name, payload in evidence.items()},
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print("Reconciled open-set evidence for", ", ".join(aggregate["scenarios"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version")
    parser.add_argument("log", type=Path)
    parser.add_argument("notebook", type=Path)
    args = parser.parse_args()
    checkpoint(args.version, args.log, args.notebook)
