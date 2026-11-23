"""Validate and publish compact Phase 2 results from downloaded Kaggle evidence."""

import argparse
from collections import Counter, defaultdict
import csv
from hashlib import sha256
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
REPORT_CSVS = ("phase2_count_reconciliation.csv", "phase2_quality_actions.csv", "phase2_performance.csv")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def rows(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def table(headers, values):
    result = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    return result + ["| " + " | ".join(str(value) for value in row) + " |" for row in values]


def check_evidence(summary, folder, mount=None):
    phase1 = read_json(ROOT / "manifests/dataset_inventory.json")
    if summary["dataset"] != phase1["dataset"]:
        raise ValueError("Unexpected dataset identity")
    phase1_files = {entry["name"]: entry for entry in phase1["files"]}
    phase1_labels = defaultdict(Counter)
    for row in rows(ROOT / "reports/dataset_label_distribution.csv"):
        phase1_labels[row["file"]][row["proposed_binary"]] += int(row["count"])
    count_rows = {row["source_file"]: row for row in rows(folder / REPORT_CSVS[0])}
    quality_rows = {(row["source_file"], row["reason"]): row for row in rows(folder / REPORT_CSVS[1])}
    perf_rows = {row["source_file"]: row for row in rows(folder / REPORT_CSVS[2])}
    files = summary["completed_files"]
    names = {row["source_file"] for row in files}
    if len(files) != len(names) or names != set(count_rows) or names != set(perf_rows):
        raise ValueError("Compact evidence does not identify the same captures")
    totals = Counter()
    for item in files:
        name = item["source_file"]
        measured = item["counts"]
        expected = phase1_files[name]["counts"]
        row = count_rows[name]
        if any(int(row[key]) != value for key, value in {
            "expected_records": expected["parsed"], "observed_records": expected["parsed"],
            "physical_lines": expected["physical_lines"], "expected_headers": expected["headers"],
            "headers": expected["headers"], "repeated_headers": expected["repeated_header_lines"],
            "canonical": expected["parsed"], "clean": expected["parsed"], "feature_ready": expected["parsed"],
            "benign": phase1_labels[name]["benign"], "attack": phase1_labels[name]["attack"],
            "timestamp_outlier": measured["timestamp_outlier"],
        }.items()):
            raise ValueError(f"Capture evidence does not reconcile for {name}")
        if measured["canonical_rows"] != expected["parsed"] or any(
            measured[key] != phase1_labels[name][key] for key in ("benign", "attack")
        ):
            raise ValueError(f"Capture marker does not reconcile for {name}")
        for reason in ("nan", "positive_infinity", "negative_infinity", "invalid_negative", "sentinel",
                       "cast_failure", "source_null", "structural_missing", "quality_affected"):
            quality = quality_rows[(name, reason)]
            if int(quality["affected_rows"]) != measured[f"{reason}_rows"] or int(quality["affected_cells"]) != measured[f"{reason}_cells"]:
                raise ValueError(f"Quality counts disagree for {name} and {reason}")
        timing = perf_rows[name]
        if int(timing["source_bytes"]) != item["source_bytes"] or float(timing["read_transform_seconds"]) != item["read_transform_seconds"]:
            raise ValueError(f"Performance evidence does not match the capture marker for {name}")
        for layer in item["layers"]:
            if float(timing[layer + "_write_seconds"]) != item["layers"][layer]["write_seconds"]:
                raise ValueError(f"Write performance differs for {name} and {layer}")
        totals.update(measured)
    if dict(totals) != summary["totals"]:
        raise ValueError("Global totals differ from capture sums")
    for name, layer in summary["layers"].items():
        for key in ("files", "bytes", "records"):
            if layer[key] != sum(item["layers"][name][key] for item in files):
                raise ValueError(f"Parquet layer aggregate differs for {name} and {key}")
    if summary["status"] == "validated":
        if names != phase1_files.keys() or not summary["aggregation_demo"]["groups"]:
            raise ValueError("A validated run must include every capture and the aggregation check")
        if summary["duplicate_policy"] != "preserve_all":
            exact = summary["duplicate_diagnostics"]["exact"]
            if exact["excess"] != phase1["audit"]["exact_duplicates"]["excess_copies"]:
                raise ValueError("Duplicate excess differs from Phase 1")
    if mount is not None:
        if mount["summary_sha256"] != sha256((folder / "validation_summary.json").read_bytes()).hexdigest():
            raise ValueError("Independent mount referred to different producer evidence")
        for name, layer in summary["layers"].items():
            for key in ("files", "bytes", "records", "partitions"):
                if mount["layers"][name][key] != layer[key]:
                    raise ValueError(f"Independent reread differs for {name} and {key}")
            for key in ("benign", "attack"):
                if mount["layers"][name][key] != totals[key]:
                    raise ValueError(f"Independent reread differs for {name} label {key}")


def write_report(folder, producer, producer_version, producer_status, probe, probe_version, output):
    summary = read_json(folder / "validation_summary.json")
    receipt = folder / "mount_verification.json"
    mount = read_json(receipt) if receipt.exists() else None
    check_evidence(summary, folder, mount)
    manifest = read_json(folder / "parquet_layers.json")
    for key, value in manifest.items():
        if summary[key] != value:
            raise ValueError(f"Producer Parquet manifest differs for {key}")
    manifest.update(producer={"url": producer, "kernel_version": producer_version, "status": producer_status},
                    resources=summary["resources"], totals=summary["totals"])
    if mount is not None:
        manifest["independent_mount"] = mount | {"url": probe, "kernel_version": probe_version, "status": "COMPLETE"}
    policy = read_json(ROOT / "configs/cleaning.yaml")
    # Import the audited normalizer without loading Spark.
    import sys
    sys.path.insert(0, str(ROOT))
    from src.ingest.dataset_audit import normalize_column

    exclusions = set(policy["excluded_shared_features"]) | {"timestamp", "label"}
    manifest["feature_columns"] = [name for name in map(normalize_column, policy["headers"]["common_80"]) if name not in exclusions]
    report_dir = output / "reports"
    manifest_dir = output / "manifests"
    report_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    for name in REPORT_CSVS:
        shutil.copyfile(folder / name, report_dir / name)
    (manifest_dir / "parquet_layers.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    full = summary["status"] == "validated" and producer_status == "COMPLETE" and mount is not None
    verdict = "READY FOR PHASE 3" if full else "PARTIALLY READY"
    counts = Counter(summary["totals"])
    files = summary["completed_files"]
    report = [
        "# Phase 2 Spark data engineering", "",
        f"**{verdict}.** Phase 2 validated {len(files)} of {summary['expected_files']} captures. "
        f"The private CPU producer reached Kaggle `{producer_status}` at version {producer_version}. [Producer notebook]({producer})", "",
        "## Input reconciliation", "",
    ]
    report += table(
        ["Capture day", "Expected records", "Canonical records", "Expected header lines", "Observed header lines", "Repeated header lines"],
        [(entry["source_day"], f"{entry['expected_records']:,}", f"{entry['counts']['canonical_rows']:,}",
          entry["expected_headers"], entry["counts"]["headers"], entry["counts"]["repeated_headers"]) for entry in files],
    )
    report += [
        "", f"The completed captures contain {counts['physical_lines']:,} physical lines and {counts['canonical_rows']:,} data records. "
        f"Spark counted {counts['headers']:,} header lines, including {counts['repeated_headers']:,} repeats, "
        f"and {counts['blank']:,} blank lines. The width/quoting and corrupt-record counters "
        f"were {counts['bad_width_or_quotes']:,} and {counts['spark_corrupt']:,}. [Count evidence](phase2_count_reconciliation.csv)",
        "", "## Cleaning and labels", "",
        f"The canonical label totals were {counts['benign']:,} benign and {counts['attack']:,} attack. "
        f"There were {counts['unknown_labels']:,} unknown labels. "
        f"{counts['timestamp_outlier']:,} records retained an outside-capture-day timestamp and were marked temporally ineligible.",
        "",
        f"Numeric diagnostics cover {counts['quality_affected_rows']:,} distinct rows and {counts['quality_affected_cells']:,} cells. "
        f"Schema-only nulls cover {counts['structural_missing_rows']:,} rows and {counts['structural_missing_cells']:,} cells.", "",
    ]
    report += table(["Reason", "Affected rows", "Affected cells", "Action"], [
        (reason, f"{counts[reason + '_rows']:,}", f"{counts[reason + '_cells']:,}", action)
        for reason, action in policy["numeric_actions"].items()
    ])
    if mount:
        report += [
            "", f"The independent mount validated {mount['clean_cells_verified_null']:,} stored policy nullifications "
            "and re-counted the benign and attack classes directly in each primary layer.",
        ]
    diagnostic = summary.get("duplicate_diagnostics", {})
    if "exact" in diagnostic:
        exact, conflicts = diagnostic["exact"], diagnostic["cleaned_feature_conflicts"]
        report += [
            "", f"The diagnostic policy kept all primary records. It measured {exact['groups']:,} exact digest groups "
            f"and {exact['excess']:,} excess copies. Cleaned shared features produced {conflicts['groups']:,} conflicting-label groups "
            f"involving {conflicts['participating_rows']:,} rows. Phase 1's {summary['phase1_conflict_groups']:,} groups refer to "
            "its own raw-feature definition. [Cell actions](phase2_quality_actions.csv)",
        ]
    report += ["", "## Parquet output", ""]
    report += table(
        ["Layer", "Producer path", "Day partitions", "Files", "Bytes", "Records"],
        [(name, f"`{item['path']}`", item["partitions"], item["files"], f"{item['bytes']:,}", f"{item['records']:,}")
         for name, item in summary["layers"].items()],
    )
    report += ["", "The worker inspected data-file footers and verified Snappy compression and row totals. "
               "[Parquet manifest](../manifests/parquet_layers.json)", "", "## Performance", ""]
    resources = summary["resources"]
    source_bytes = sum(f["source_bytes"] for f in files)
    total_transform = sum(f["read_transform_seconds"] for f in files)
    effective = source_bytes / 1024 ** 2 / total_transform if total_transform else 0
    report += [
        f"Spark {resources['spark_version']} used `{resources['master']}`, an {resources['driver_memory']} driver heap, "
        f"{resources['shuffle_partitions']} configured shuffle partitions and "
        f"{resources['input_partition_bytes'] // (1024 ** 2)} MiB input splits. "
        f"Kaggle exposed {resources['cpu_affinity']} logical CPUs in the process affinity mask.",
        "",
        f"The producer loop took {summary['elapsed_seconds']:,.3f} s. Reading, parsing and materializing the canonical data "
        f"took {total_transform:,.3f} s at {effective:.2f} MiB/s effective input throughput. "
        "The timing includes CSV conversion and the disk-backed canonical materialization.",
        "",
    ]
    report += table(["Layer", "Write time including lazy transformations (s)"],
                    [(name, f"{item['write_seconds']:,.3f}") for name, item in summary["layers"].items()])
    if resources.get("driver_peak_rss_bytes"):
        report += ["", f"The JVM high-water resident set was {resources['driver_peak_rss_bytes'] / 1024 ** 3:.2f} GiB. "
                   "This includes JVM memory outside the configured heap. [Per-file performance](phase2_performance.csv)"]
    if diagnostic.get("seconds") is not None:
        report += ["", f"Global duplicate diagnostics took {diagnostic['seconds']:,.3f} s."]
    if summary.get("failures"):
        report += ["", "Incomplete stages", ""] + [
            f"- {failure.get('source_day', 'global')} {failure['stage']} recorded {failure['type']}."
            for failure in summary["failures"]
        ]
    if "aggregation_demo" in summary:
        demo = summary["aggregation_demo"]
        report += [
            "", "## Spark SQL, DataFrame and RDD", "",
            f"All three methods returned the same {len(demo['groups'])} protocol groups over {demo['rows']:,} records. "
            f"The sample rule was `{demo['sample_rule']}`.", "",
        ]
        report += table(["Protocol", "Records", "Attacks"],
                        [(row["protocol"], row["records"], row["attacks"]) for row in demo["groups"]])
        for key, label in (("sql_plan", "SQL physical plan"), ("dataframe_plan", "DataFrame physical plan"), ("rdd_dag", "RDD lineage")):
            report += ["", f"<details><summary>{label}</summary>", "", "```text", demo[key].rstrip(), "```", "", "</details>"]
    if mount:
        report += [
            "", "## Saved output reuse", "",
            f"Version {probe_version} of the private verification notebook mounted the saved producer output as a notebook input. "
            f"It matched the expected evidence SHA-256 and directly verified each layer. Independent validation took "
            f"{mount['elapsed_seconds']:,.3f} s. [Verification notebook]({probe}) · [Storage guide](../docs/parquet_storage.md)",
        ]
    (report_dir / "phase2_data_engineering.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"Reconciled receipts for {len(files)} files and {counts['canonical_rows']:,} canonical rows. {verdict}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--producer", required=True)
    parser.add_argument("--producer-version", type=int, required=True)
    parser.add_argument("--producer-status", choices=("COMPLETE", "ERROR"), required=True)
    parser.add_argument("--probe")
    parser.add_argument("--probe-version", type=int)
    parser.add_argument("--output-root", type=Path, default=ROOT)
    args = parser.parse_args()
    write_report(args.evidence, args.producer, args.producer_version, args.producer_status,
                 args.probe, args.probe_version, args.output_root)
