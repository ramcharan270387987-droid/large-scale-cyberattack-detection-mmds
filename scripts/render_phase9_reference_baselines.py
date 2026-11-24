"""Derive closed-set reference baselines on the archived evaluation support."""

import csv
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path

from src.ml.phase9_evaluation import multiclass


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests/phase9_experiments.json"


def render(manifest):
    stages = manifest["stages"]
    source = ROOT / "reports/phase9_per_family.csv"
    data = source.read_bytes()
    if sha256(data).hexdigest() != manifest["tables_sha256"][source.name]:
        raise ValueError("Archived per-family support hash differs")
    measured = list(csv.DictReader(StringIO(data.decode())))
    output = []
    for scenario, stage in stages.items():
        classes = stage["classes"]
        ids = range(len(classes))
        train = {classes[family]: count for family, count in stage["training_support"].items()}
        test = {int(row["class_id"]): int(row["support"]) for row in measured if row["scenario"] == scenario}
        if sum(test.values()) != stage["test"]["rows"]:
            raise ValueError(f"Archived test support differs for {scenario}")
        majority = min(train, key=lambda idx: (-train[idx], idx))
        train_total = sum(train.values())
        majority_counts = {(idx, majority): test[idx] for idx in ids}
        prior_counts = {(idx, pred): test[idx] * train[pred] / train_total for idx in ids for pred in ids}
        for name, counts in (("majority", majority_counts), ("training_prior_expected", prior_counts)):
            metrics, _ = multiclass(counts, ids)
            output.append({"scenario": scenario, "model": name, **metrics})
    directory = ROOT / "reports/phase9_reference_baselines"
    directory.mkdir(exist_ok=True)
    target = directory / "phase9_reference_baselines.csv"
    with target.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(output[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(output)
    return {target.relative_to(ROOT).as_posix(): sha256(target.read_bytes()).hexdigest()}


if __name__ == "__main__":
    manifest = json.loads(MANIFEST.read_text())
    manifest["reference_baselines_sha256"] = render(manifest)
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
