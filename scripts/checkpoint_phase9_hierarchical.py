"""Verify and checkpoint the chronological B hierarchical run."""
import argparse
import csv
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re

GATES = ("phase4_rf", "phase8_supervised", "phase8_hybrid", "oracle")
FILES = ("phase9_hierarchical_receipt.json", "phase9_hierarchical_counts.csv", "phase8_split_diagnostics.csv")
ARCHIVE_ROOT = "mmds_phase9_hierarchy"


def table(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def summarize(rows):
    for row in rows:
        if row["gate"] not in GATES or row["binary_label"] not in {"0", "1"} or int(row["count"]) <= 0:
            raise ValueError("Invalid gate or count")
    result = {}
    for gate in GATES:
        observed = [row for row in rows if row["gate"] == gate]
        counts = Counter()
        matrix = Counter()
        for row in observed:
            n = int(row["count"])
            actual = "Benign" if row["binary_label"] == "0" else "UNKNOWN"
            prediction = row["decision"]
            if actual == "Benign":
                expected = "correct_benign" if prediction == "Benign" else "benign_false_alarm"
            elif prediction == "Benign":
                expected = "missed_attack"
            else:
                expected = "unknown_rejected" if prediction == "UNKNOWN" else "unknown_false_accept"
            if row["outcome"] != expected:
                raise ValueError("Inconsistent B outcome and final decision")
            counts[expected] += n
            matrix[(actual, prediction)] += n
        total = counts.total()
        if not total:
            raise ValueError("Missing gate")
        review = sum(n for (_, prediction), n in matrix.items() if prediction == "UNKNOWN")
        detected = counts["unknown_rejected"] + counts["unknown_false_accept"]
        unknown = counts["missed_attack"] + detected
        supported_f1 = []
        for label in ("Benign", "UNKNOWN"):
            support = sum(n for (actual, _), n in matrix.items() if actual == label)
            predicted = sum(n for (_, prediction), n in matrix.items() if prediction == label)
            if support:
                supported_f1.append(2 * matrix[label, label] / (support + predicted))
        result[gate] = {"counts": dict(counts), "rows": total,
                        "supported_target_macro_f1": sum(supported_f1) / len(supported_f1),
                        "accuracy": (counts["correct_benign"] + counts["unknown_rejected"]) / total,
                        "review_rows": review, "automatic_coverage": 1 - review / total,
                        "unknown_rejection_recall": counts["unknown_rejected"] / unknown if unknown else None,
                        "conditional_unknown_rejection_recall": counts["unknown_rejected"] / detected if detected else None,
                        "known_family_recall": None, "known_family_macro_f1": None}
    return result


def expected_binary(root):
    rows4 = table(root / "reports/phase4_metrics.csv")
    rows8 = table(root / "reports/phase8_model_comparison.csv")
    rf = next(row for row in rows4 if (row["protocol"], row["model"], row["training_cohort"], row["split"]) ==
              ("B", "random_forest", "group_sample", "test"))
    supervised = next(row for row in rows8 if row["population"] == "B" and row["method"] == "supervised")
    hybrid = next(row for row in rows8 if row["population"] == "B" and row["selected_hybrid"] == "True")
    return dict(zip(GATES, (rf, supervised, hybrid)))


def checkpoint(root, version, log, notebook):
    from kaggle_web_api import download_archive

    if not re.search(r"PHASE9 hierarchical B complete", log.read_text(errors="replace")):
        raise ValueError("Missing successful end-of-stage log marker")
    with download_archive(version, 2 * 1024 * 1024) as archive:
        evidence = {name: archive.read(f"{ARCHIVE_ROOT}/{name}") for name in FILES}
    receipt = json.loads(evidence[FILES[0]])
    if (receipt["status"], receipt["population"]) != ("validated", "B"):
        raise ValueError("Unexpected worker receipt")
    rows = list(csv.DictReader(evidence[FILES[1]].decode().splitlines()))
    results = summarize(rows)
    if {gate: r["rows"] for gate, r in results.items()} != receipt["gate_rows"]:
        raise ValueError("Worker and independent gate totals differ")
    for gate, previous in expected_binary(root).items():
        counts = Counter(results[gate]["counts"])
        actual = (counts["unknown_rejected"] + counts["unknown_false_accept"], counts["correct_benign"],
                  counts["benign_false_alarm"], counts["missed_attack"])
        if actual != tuple(int(previous[key]) for key in ("tp", "tn", "fp", "fn")):
            raise ValueError(f"Historical binary confusion differs for {gate}")
    oracle = Counter(results["oracle"]["counts"])
    known_zero = json.loads((root / "manifests/phase9_B.json").read_text())["test"]["rows"]
    if oracle["benign_false_alarm"] or oracle["missed_attack"] or known_zero:
        raise ValueError("Invalid chronological oracle accounting")
    destination = root / "reports/phase9_hierarchy/B"
    destination.mkdir(parents=True, exist_ok=True)
    for name, payload in evidence.items():
        (destination / name).write_bytes(payload)
    manifest_path = root / "manifests/phase9_experiments.json"
    manifest = json.loads(manifest_path.read_text())
    manifest.setdefault("hierarchy", {})["B"] = {
        "status": "validated", "worker_status": "COMPLETE", "kernel_version": int(version.rsplit("/", 1)[-1]),
        "log_sha256": sha256(log.read_bytes()).hexdigest(), "notebook_sha256": sha256(notebook.read_bytes()).hexdigest(),
        "artifacts": {str((destination / name).relative_to(root)): sha256(payload).hexdigest()
                      for name, payload in evidence.items()},
        "results": results,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version")
    parser.add_argument("log", type=Path)
    parser.add_argument("notebook", type=Path)
    args = parser.parse_args()
    checkpoint(Path(__file__).resolve().parents[1], args.version, args.log, args.notebook)
