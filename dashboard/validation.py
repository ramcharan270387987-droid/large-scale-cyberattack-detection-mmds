"""Validate the aggregate package without requiring the research runtime."""

import csv
from hashlib import sha256
from io import StringIO
import json
from math import isclose
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "dashboard-v1"


class EvidenceError(ValueError):
    """A missing, altered or inconsistent research artifact."""


def require(condition, message):
    if not condition:
        raise EvidenceError(message)


def digest(content):
    return sha256(content).hexdigest()


def parse_table(content, fields, name):
    reader = csv.DictReader(StringIO(content.decode("utf-8")), strict=True)
    require(reader.fieldnames == fields and len(fields) == len(set(fields)), f"Schema mismatch in {name}")
    rows = list(reader)
    require(rows and all(None not in row and None not in row.values() for row in rows), f"Invalid rows in {name}")
    return rows


def reconcile(summary, tables):
    dataset = summary["dataset"]
    daily = tables["phase3_daily_traffic"]
    require(len({r["source_day"] for r in daily}) == len(daily) == len(dataset["days"]), "Capture days differ")
    require({r["source_day"] for r in daily} == set(dataset["days"]), "Capture provenance differs")
    for col, key in (("records", "canonical_rows"), ("benign", "benign"), ("attacks", "attack")):
        require(sum(int(r[col]) for r in daily) == dataset["totals"][key], f"Dataset {col} differ")
    for name in ("attack_families", "family_by_day", "original_labels"):
        observations = tables[f"phase3_{name}"]
        require(sum(int(r["records"]) for r in observations if r["attack_family"] != "Benign") ==
                dataset["totals"]["attack"], f"Attack totals differ in {name}")
    for row in tables["phase4_metrics"]:
        total = sum(int(row[k]) for k in ("tp", "tn", "fp", "fn"))
        require(total == int(row["rows"]), "Model confusion counts differ")
        support = summary["model_support"][row["protocol"]][row["split"]]["labels"]
        require(int(row["tp"]) + int(row["fn"]) == support.get("1", 0) and
                int(row["tn"]) + int(row["fp"]) == support.get("0", 0), "Model support differs")
    for code, spec in summary["clusters"].items():
        profiles = [r for r in tables["phase5_cluster_profiles"] if r["experiment"] == code]
        require(len(profiles) == spec["selected_k"] and sum(int(r["records"]) for r in profiles) == spec["retained_rows"],
                f"Cluster experiment {code} differs")
    for row in tables["phase5_novelty_metrics"]:
        require(float(row["threshold"]) == summary["clusters"][row["experiment"]]["cutoffs"][row["percentile"]],
                "Novelty threshold differs")
        require(int(row["flags"]) == int(row["tp"]) + int(row["fp"]), "Novelty flag counts differ")
        for key, a, b in (("flag_rate", "flags", "rows"), ("benign_fpr", "fp", "benign"),
                          ("attack_recall", "tp", "attacks")):
            if int(row[b]):
                require(isclose(float(row[key]), int(row[a])/int(row[b]), abs_tol=1e-12), f"Invalid novelty {key}")
    replay = summary["replay"]
    batches = tables["phase6_replay_batches"]
    require([int(r["batch_id"]) for r in batches] == list(range(replay["batches"])), "Batch sequence differs")
    require(sum(int(r["rows"]) for r in batches) == replay["rows"], "Replay counts differ")
    require(sum(int(r["temporally_eligible"]) for r in batches)+replay["ineligible"] == replay["rows"],
            "Replay eligibility differs")
    require(sum(int(r["rows"]) for r in tables["phase6_window_metrics"] if r["scope"] == "daily") ==
            replay["rows"], "Daily replay totals differ")
    alerts = tables["phase6_alerts"]
    require(len(alerts) == replay["alerts"]["count"] and sum(r["severity"] == "high" for r in alerts) ==
            replay["alerts"]["high"], "Alert counts differ")
    require(all(float(r["delta"]) > float(r["threshold"]) and r["support"] == "supported" for r in alerts),
            "Unsupported alert")


def verify_package(root=ROOT, *, sources=False):
    try:
        config = json.loads((root / "configs/dashboard.yaml").read_text())
        manifest = json.loads((root / "manifests/dashboard_package.json").read_text())
        require(config["schema_version"] == manifest["schema_version"] == SCHEMA and
                manifest["source_revision"] == config["source_revision"], "Unsupported dashboard schema or source revision")
        require(set(manifest["tables"]) == set(config["tables"]), "Incomplete dashboard table inventory")
        require(digest((root / "configs/dashboard.yaml").read_bytes()) == manifest["config_sha256"],
                "Dashboard contract checksum differs")
        tables = {}
        for name, spec in manifest["tables"].items():
            content = (root / "dashboard/data" / f"{name}.csv").read_bytes()
            require(digest(content) == spec["sha256"], f"Checksum mismatch in {name}")
            tables[name] = parse_table(content, config["tables"][name]["columns"], name)
            require(len(tables[name]) == spec["rows"], f"Row count differs in {name}")
        overview = (root / "dashboard/data/summary.json").read_bytes()
        require(digest(overview) == manifest["summary_sha256"], "Summary checksum mismatch")
        if sources:
            for path, spec in manifest["inputs"].items():
                require(digest((root / path).read_bytes()) == spec["sha256"], f"Source checksum mismatch in {path}")
            for name, spec in manifest["tables"].items():
                require(spec["sha256"] == manifest["inputs"][config["tables"][name]["source"]]["sha256"],
                        f"Packaged table differs from its source in {name}")
        summary = json.loads(overview)
        reconcile(summary, tables)
        return manifest, summary
    except EvidenceError:
        raise
    except (OSError, ValueError, KeyError, TypeError, csv.Error) as exc:
        raise EvidenceError(f"Cannot validate dashboard evidence. {exc}") from exc
