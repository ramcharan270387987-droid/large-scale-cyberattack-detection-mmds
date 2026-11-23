"""Validate compact Kaggle evidence and regenerate the Phase 1 repository tables."""

import argparse
from collections import Counter
import csv
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.ingest.dataset_audit import compare_schema, counts_reconcile, normalize_label, proposed_binary


# Proposed mapping of named benchmark categories. Other observed strings stay unmapped.
FAMILIES = {
    "bot": "Bot",
    "brute force -web": "Web attack",
    "brute force -xss": "Web attack",
    "ddos attack-hoic": "DDoS",
    "ddos attack-loic-udp": "DDoS",
    "ddos attacks-loic-http": "DDoS",
    "dos attacks-goldeneye": "DoS",
    "dos attacks-hulk": "DoS",
    "dos attacks-slowhttptest": "DoS",
    "dos attacks-slowloris": "DoS",
    "ftp-bruteforce": "Credential brute force",
    "infilteration": "Infiltration",
    "infiltration": "Infiltration",
    "sql injection": "Web attack",
    "ssh-bruteforce": "Credential brute force",
}
COUNT_FIELDS = [
    "physical_lines", "headers", "repeated_header_lines", "blank", "data_records",
    "malformed", "bad_width_or_quotes", "spark_corrupt", "parsed",
]
QUALITY_FIELDS = [
    "index", "original", "normalized", "type_candidate", "null", "empty_or_whitespace",
    "present", "finite_numeric", "nan", "infinite", "numeric_conversion_failures",
    "negative", "invalid_negative", "constant_nonempty", "sample_rows", "sample_present",
    "sample_dominant_count", "sample_dominant_fraction", "near_constant_sample",
]
TIME_FIELDS = [
    "index", "original", "rows", "missing", "invalid", "parsed", "parse_pct", "earliest",
    "latest", "mdy_only", "ambiguous", "date_matches", "date_mismatches", "mdy_date_matches",
    "date_formats",
]


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(headers, rows):
    def cell(value):
        return str(value if value is not None else "—").replace("|", "\\|").replace("\n", " ")

    yield "| " + " | ".join(headers) + " |"
    yield "| " + " | ".join("---" for _ in headers) + " |"
    for row in rows:
        yield "| " + " | ".join(cell(value) for value in row) + " |"


def original_label(value):
    # JSON notation makes whitespace and null distinct in Markdown and the compact CSV.
    return json.dumps(value, ensure_ascii=False)


def pct(part, whole):
    return round(100 * part / whole, 8) if whole else None


def formatted_pct(part, whole):
    return f"{100 * part / whole:.6f}%" if whole else "—"


def number(value):
    return f"{value:,}" if value is not None else "—"


def mapping(label):
    normalized = normalize_label(label)
    if proposed_binary(label) == "benign":
        return "benign", "Benign"
    family = FAMILIES.get(normalized)
    return ("attack", family) if family else ("unmapped", "Unmapped")


def validate_file(path, evidence, run_result):
    assert evidence["name"] == path["name"], path["name"]
    assert evidence["status"] == run_result["status"], path["name"]
    assert evidence["stage_seconds"] == run_result["stage_seconds"], path["name"]
    counts = evidence.get("counts")
    if counts is None:
        assert evidence["status"] != "complete", path["name"]
        return
    assert counts_reconcile(counts, evidence.get("labels")), path["name"]
    assert counts["headers"] >= 1, path["name"]
    if len(evidence.get("schema", {}).get("label_indices", [])) == 1 and evidence["status"] == "complete":
        assert "labels" in evidence, path["name"]
    for timestamp in evidence.get("timestamps", []):
        assert timestamp["rows"] == counts["parsed"], path["name"]
        assert sum(timestamp[key] for key in ("missing", "invalid", "parsed")) == counts["parsed"], path["name"]
        assert timestamp["date_matches"] + timestamp["date_mismatches"] == timestamp["parsed"], path["name"]
        if "date_formats" in timestamp:
            assert sum(day["count"] for day in timestamp["date_formats"]) == timestamp["parsed"], path["name"]
    if "quality" in evidence:
        assert len(evidence["quality"]) == len(evidence["schema"]["original"]), path["name"]
        for row in evidence["quality"]:
            assert row["present"] + row["null"] + row["empty_or_whitespace"] == counts["parsed"], path["name"]
            assert row["sample_dominant_count"] <= row["sample_present"] <= row["sample_rows"], path["name"]


def generate(source, kernel_url, version, execution_status, output_root, exact_source=None, exact_version=None):
    inventory = read_json(source / "inventory.json")
    run_summary = source / "run_summary.json"
    run = read_json(run_summary) if run_summary.exists() else {"files": {}, "spark": {}}
    config = read_json(ROOT / "configs/dataset.yaml")
    assert inventory["dataset"] == {key: config[key] for key in ("owner", "slug", "version")}
    assert inventory["expected_bytes"] == sum(config["files"].values())
    assert inventory["actual_total_bytes"] == sum(item["bytes"] or 0 for item in inventory["files"])
    exact = None
    if exact_source is not None:
        assert read_json(exact_source / "inventory.json") == inventory
        exact = read_json(exact_source / "exact_duplicates.json")
    expected = [item for item in inventory["files"] if not item["unexpected"]]
    assert len(expected) == len(config["files"])
    assert {record["name"]: record["expected_bytes"] for record in expected} == config["files"]
    file_rows, labels, quality, timestamps = [], [], [], []
    schemas = {}
    stage_rows = []
    label_days = {}
    for file in sorted(expected, key=lambda row: row["capture_day"]):
        name, day = file["name"], file["capture_day"]
        item_path = source / (name + ".json")
        item = read_json(item_path) if item_path.exists() else {}
        if item:
            validate_file(file, item, run["files"].get(name, item))
        counts = item.get("counts", {})
        file["audit_status"] = item.get("status", "not_measured")
        file["counts"] = counts
        dataset_keys = {"file": name, "capture_day": day}
        stage = item.get("stage_seconds", {})
        file_rows.append(dataset_keys | {
            "path": file["path"], "bytes": file["bytes"], "expected_bytes": file["expected_bytes"],
            "access": file["access"], "status": file["audit_status"],
            "columns": len(item["schema"]["original"]) if "schema" in item else None,
            "error": item.get("error", "").split(":", 1)[0] or None,
        } | counts)
        stage_rows.append((day, *(stage.get(key) for key in ("parse_and_count", "labels_and_time", "quality", "fingerprints"))))
        if "schema" in item:
            schemas[name] = item["schema"]
        for row in item.get("labels", []):
            label, count = row["label"], row["count"]
            binary, family = mapping(label)
            labels.append(dataset_keys | {
                "original_label": original_label(label), "normalized_label": normalize_label(label),
                "proposed_binary": binary, "proposed_family": family, "count": count,
                "percent_of_file": pct(count, counts["parsed"]),
            })
            label_days.setdefault(label, Counter())[day] += count
        quality.extend(dataset_keys | row for row in item.get("quality", []))
        for row in item.get("timestamps", []):
            timestamps.append(dataset_keys | row | {
                "parse_pct": pct(row["parsed"], row["rows"]),
                "date_formats": json.dumps(row["date_formats"], separators=(",", ":")) if "date_formats" in row else None,
            })

    complete = sum(row["status"] == "complete" for row in file_rows)
    measured = [row for row in file_rows if row.get("data_records") is not None]
    totals = {key: sum(row[key] for row in measured) for key in COUNT_FIELDS}
    assert counts_reconcile(totals)
    if exact is not None:
        assert exact["files"] == len(measured) == len(expected)
        assert exact["parsed_rows"] == totals["parsed"]
        assert exact["parsed_rows"] == exact["distinct_rows"] + exact["excess_copies"]
        assert exact["cross_day_groups"] <= exact["duplicate_groups"] <= exact["excess_copies"]
    label_total = sum(row["count"] for row in labels)
    raw_totals = Counter()
    binary_totals = Counter()
    family_totals = Counter()
    for row in labels:
        raw_totals[row["original_label"]] += row["count"]
        binary_totals[row["proposed_binary"]] += row["count"]
        family_totals[row["proposed_family"]] += row["count"]
        row["percent_of_measured_labeled_rows"] = pct(row["count"], label_total)

    reports = output_root / "reports"
    docs = output_root / "docs"
    manifests = output_root / "manifests"
    for path in (reports, docs, manifests):
        path.mkdir(parents=True, exist_ok=True)
    manifest = inventory | {"audit": {
        "kernel_url": kernel_url, "kernel_version": version, "execution_status": execution_status,
        "complete_files": complete, "counted_files": len(measured), "counts": totals,
        "spark": run["spark"], "processing_seconds": run.get("elapsed_seconds"),
    }}
    if exact is not None:
        manifest["audit"]["exact_duplicates"] = exact | {"kernel_version": exact_version}
    (manifests / "dataset_inventory.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    write_csv(reports / "dataset_file_statistics.csv",
              ["file", "capture_day", "path", "bytes", "expected_bytes", "access", "status", "columns", *COUNT_FIELDS, "error"],
              file_rows)
    write_csv(reports / "dataset_label_distribution.csv",
              ["file", "capture_day", "original_label", "normalized_label", "proposed_binary",
               "proposed_family", "count", "percent_of_file", "percent_of_measured_labeled_rows"], labels)
    write_csv(reports / "dataset_quality_summary.csv", ["file", "capture_day", *QUALITY_FIELDS], quality)
    write_csv(reports / "dataset_timestamp_summary.csv", ["file", "capture_day", *TIME_FIELDS], timestamps)

    schema_doc = [
        "# MMDS dataset schema", "",
        f"Kaggle version {version} returned readable headers for {len(schemas)} of {len(expected)} expected captures. "
        "Column indices are zero-based. Header strings are shown in JSON notation to preserve whitespace.", "",
    ]
    if schemas:
        baseline = Counter(tuple(schema["original"]) for schema in schemas.values()).most_common(1)[0][0]
        reference_name = next(name for name, schema in schemas.items() if tuple(schema["original"]) == baseline)
        reference = schemas[reference_name]
        schema_doc += [f"The most common original header, from `{reference_name}`, is the reference for comparisons.", ""]
        schema_doc += list(markdown_table(
            ["File", "Columns", "Feature candidates", "Label index", "Timestamp index", "Same normalized order", "Exact original header",
             "Normalized schema compatible", "Extra", "Missing", "Duplicate names", "Whitespace / encoding"],
            [
                (
                    name, len(schema["original"]), len(schema["original"]) - len(set(
                        schema["label_indices"] + schema["timestamp_indices"] + schema["unsupported_indices"]
                    )), ", ".join(map(str, schema["label_indices"])) or None,
                    ", ".join(map(str, schema["timestamp_indices"])) or None, cmp["same_order"],
                    cmp["same_original_header"], cmp["compatible"], ", ".join(cmp["extra"]) or None,
                    ", ".join(cmp["missing"]) or None, ", ".join(schema["normalized_duplicates"]) or None,
                    f"{len(schema['whitespace_columns'])} whitespace, {len(schema['encoding_columns'])} non-ASCII"
                    + (", UTF-8 BOM" if schema["utf8_bom"] else ""),
                )
                for name, schema in schemas.items()
                for cmp in [compare_schema(reference, schema)]
            ],
        ))
        grouped = {}
        for name, schema in schemas.items():
            grouped.setdefault(tuple(schema["original"]), []).append(name)
        quality_lookup = {
            (entry["file"], entry["index"]): entry["type_candidate"] for entry in quality
        }
        for index, (header, names) in enumerate(grouped.items(), 1):
            schema = schemas[names[0]]
            schema_doc += ["", f"## Original header {index}", "", ", ".join(f"`{name}`" for name in names), ""]
            schema_doc += list(markdown_table(
                ["Index", "Original", "Normalized", "Profile candidates"],
                [(i, f"`{original_label(raw)}`", f"`{schema['normalized'][i]}`",
                  ", ".join(sorted({quality_lookup.get((name, i), "unmeasured") for name in names})))
                 for i, raw in enumerate(header)],
            ))
        schema_doc += [
            "",
            "The parser preserves field order and assigns internal names by position. Normalized names are for comparison. "
            "Repeated or empty normalized names are flagged as unsupported for feature matching. "
            "Numeric candidates have at least 95% numeric lexical values among present cells, counting NaN and infinity as numeric tokens. "
            "IP and flow identifiers, protocol, labels and timestamps use their explicit roles. "
            "See the quality table for candidates that vary by capture. [Column profiles](../reports/dataset_quality_summary.csv)",
        ]
    (docs / "dataset_schema.md").write_text("\n".join(schema_doc) + "\n", encoding="utf-8")

    inventory_flags = Counter(
        flag for item in inventory["files"] for flag, condition in {
            "missing": item["access"] == "missing",
            "unreadable": item["access"] == "unreadable",
            "unexpected": item["unexpected"],
            "duplicate_basename": item["duplicate_basename"],
            "size_mismatch": item["size_matches"] is False,
        }.items() if condition
    )
    lines = [
        "# MMDS Phase 1 dataset audit", "",
        f"Kaggle version {version} reached `{execution_status}`. "
        f"The audit completed {complete} of {len(expected)} expected captures and counted {len(measured)}. "
        f"[Private CPU notebook]({kernel_url})", "",
        f"Dataset `{config['owner']}/{config['slug']}`, version {config['version']}. "
        f"The mounted inventory contains {sum(item['bytes'] is not None for item in inventory['files'])} files "
        f"and {inventory['actual_total_bytes']:,} bytes. [Inventory](../manifests/dataset_inventory.json)", "",
        f"Inventory flags record {inventory_flags['missing']} missing, {inventory_flags['unreadable']} unreadable, "
        f"{inventory_flags['unexpected']} unexpected, {inventory_flags['duplicate_basename']} duplicate-basename "
        f"and {inventory_flags['size_mismatch']} size-mismatch entries.", "",
        "## Records", "",
    ]
    lines += list(markdown_table(
        ["Capture", "Mounted bytes", "Columns", "Data records", "Parsed", "Malformed", "Blank", "Headers", "Status"],
        [(row["capture_day"], number(row["bytes"]), row["columns"], number(row.get("data_records")),
          number(row.get("parsed")), number(row.get("malformed")), number(row.get("blank")),
          number(row.get("headers")), row["status"]) for row in file_rows],
    ))
    lines += [
        "",
        f"Measured captures contain {totals['physical_lines']:,} physical lines, including {totals['data_records']:,} data records, "
        f"{totals['headers']:,} header lines ({totals['repeated_header_lines']:,} repeats) and {totals['blank']:,} blank lines. "
        f"Spark parsed {totals['parsed']:,} data records. Malformed records total {totals['malformed']:,}, "
        f"including {totals['bad_width_or_quotes']:,} width or quoting failures and {totals['spark_corrupt']:,} Spark corrupt records. "
        "Counts use one record per physical line, with the exact original header line classified separately wherever it repeats. "
        "No source records were modified. [File statistics](dataset_file_statistics.csv)", "",
        "## Labels", "",
        f"Measured label groups cover {label_total:,} parsed rows. "
        f"The proposed mapping yields {binary_totals['benign']:,} benign rows ({formatted_pct(binary_totals['benign'], label_total)}), "
        f"{binary_totals['attack']:,} attack rows ({formatted_pct(binary_totals['attack'], label_total)}), "
        f"and {binary_totals['unmapped']:,} unmapped rows ({formatted_pct(binary_totals['unmapped'], label_total)}). "
        "Original spellings and all capture-specific counts are retained. The CSV stores the original label as JSON "
        "so null and empty strings stay distinct. [Label distribution](dataset_label_distribution.csv)", "",
    ]
    lines += list(markdown_table(
        ["Original label", "Rows", "Share", "Capture days", "Largest capture share", "Proposed group"],
        [(f"`{label}`", number(count), formatted_pct(count, label_total), ", ".join(sorted(label_days[json.loads(label)])),
          formatted_pct(max(label_days[json.loads(label)].values()), count), mapping(json.loads(label))[1])
         for label, count in sorted(raw_totals.items(), key=lambda pair: (-pair[1], pair[0]))],
    ))
    lines += ["", "Proposed attack-family totals", ""]
    lines += list(markdown_table(
        ["Family", "Rows", "Share of measured labels", "Share of mapped attacks"],
        [(name, number(count), formatted_pct(count, label_total),
          None if name == "Unmapped" else formatted_pct(count, binary_totals["attack"]))
         for name, count in sorted(family_totals.items()) if name != "Benign"],
    ))
    variants = {}
    for raw in raw_totals:
        value = json.loads(raw)
        variants.setdefault(normalize_label(value), []).append(value)
    differences = [values for values in variants.values() if len(values) > 1]
    whitespace = [value for values in variants.values() for value in values
                  if value is not None and value != " ".join(value.split())]
    lines += [
        "",
        f"Observed normalized-label collisions across distinct originals: {len(differences)}. "
        f"Original labels with leading, trailing or repeated whitespace: {len(whitespace)}. "
        "A family mapping is a proposal and leaves unknown names unmapped.", "",
        "## Timestamps", "",
        "The audit tries the configured DMY day-first and ISO patterns in order. A separate MDY parse flags alternative interpretations. "
        "All date comparisons use wall-clock timestamps without timezone (`TIMESTAMP_NTZ`). "
        "Spark's session timezone was UTC for determinism. Source timezone and clock synchronization were not established.", "",
    ]
    lines += list(markdown_table(
        ["Capture", "Parsed / rows", "Range", "Missing", "Invalid", "Ambiguous DMY/MDY", "Name disagreement"],
        [(row["capture_day"], f"{number(row['parsed'])} / {number(row['rows'])} ({formatted_pct(row['parsed'], row['rows'])})",
          f"{row['earliest']} to {row['latest']}", number(row["missing"]), number(row["invalid"]),
          number(row["ambiguous"]), number(row["date_mismatches"])) for row in timestamps],
    ))
    if timestamps:
        parsed = sum(row["parsed"] for row in timestamps)
        timestamp_rows = sum(row["rows"] for row in timestamps)
        disagreements = sum(row["date_mismatches"] for row in timestamps)
        ambiguous = sum(row["ambiguous"] for row in timestamps)
        lines += [
            "",
            f"The parser accepted {parsed:,} of {timestamp_rows:,} timestamp cells ({formatted_pct(parsed, timestamp_rows)}). "
            f"There were {disagreements:,} filename-date disagreements and {ambiguous:,} valid alternative MDY interpretations. "
            f"The MDY parse matched the filename date for {sum(row['mdy_date_matches'] for row in timestamps):,} rows.",
        ]
        outlier_dates = Counter()
        for row in timestamps:
            if row["date_formats"]:
                for date in json.loads(row["date_formats"]):
                    if date["date"] != row["capture_day"]:
                        outlier_dates[date["date"]] += date["count"]
        if outlier_dates:
            dates = ", ".join(f"{date} ({count:,})" for date, count in sorted(outlier_dates.items()))
            lines += ["", f"Observed dates outside their filename capture days were {dates}."]
    lines += ["", "The [timestamp table](dataset_timestamp_summary.csv) retains per-date and per-format counts, plus MDY-only and MDY-match totals.",
              "", "## Quality", ""]
    numeric = [row for row in quality if row["type_candidate"] == "numeric"]
    features = [row for row in quality if row["type_candidate"] in {"numeric", "categorical"}]
    quality_total = lambda key, rows: sum(row[key] or 0 for row in rows)
    lines += [
        f"Across {len(quality):,} file-column profiles, measured nulls total {quality_total('null', quality):,} "
        f"and empty or whitespace-only strings total {quality_total('empty_or_whitespace', quality):,}. "
        "The Spark parser can represent empty source fields as null depending on CSV quoting.",
        "",
        f"Numeric candidates contain {quality_total('nan', numeric):,} NaNs, {quality_total('infinite', numeric):,} infinities, "
        f"and {quality_total('numeric_conversion_failures', numeric):,} conversion failures. "
        f"Fields governed by a nonnegative rule contain {quality_total('invalid_negative', numeric):,} invalid negative cells. "
        "Initial TCP-window fields are excluded from that rule because their negative sentinel requires separate interpretation.",
        "",
        f"There are {quality_total('constant_nonempty', features):,} constant nonempty feature profiles and "
        f"{quality_total('near_constant_sample', features):,} feature profiles with a sampled dominant-value fraction of at least 99%. "
        "The deterministic content sample uses `pmod(xxhash64(23013, raw_line), 1000) = 0`. "
        "Exact repeats enter or miss the sample together. [Quality statistics](dataset_quality_summary.csv)", "",
    ]
    fingerprint = run.get("fingerprint_summary")
    if exact is not None:
        lines += [
            f"Kaggle version {exact_version} grouped all {exact['parsed_rows']:,} parsed arrays by full string-value equality "
            f"within {exact['original_schemas']} original schemas. It found {exact['duplicate_groups']:,} duplicate groups, "
            f"{exact['excess_copies']:,} excess copies and {exact['cross_day_groups']:,} cross-day duplicate groups. "
            f"The exact stage took {exact['elapsed_seconds']} s. [Kaggle notebook]({kernel_url})",
            "",
        ]
    if fingerprint:
        duplicates = fingerprint["raw_line_duplicates_sha256"]
        conflicts = fingerprint["label_conflicting_features_sha256"]
        near = fingerprint["near_sample_buckets"]
        lines += [
            f"Fingerprint coverage includes {run['fingerprint_files']} captures. Full parsed-line SHA-256 grouping found "
            f"{duplicates['groups']:,} duplicate groups containing {duplicates['excess']:,} excess copies. "
            "This measures identical source-line fingerprints, including cross-file matches. Hash collisions were not independently byte-verified.",
            "",
            f"Schema-scoped fingerprints of nonidentity, nontimestamp feature values found {conflicts['groups']:,} groups "
            f"with different original labels, involving {conflicts['rows']:,} rows. "
            f"Coarse flow-metric bucketing found {near['groups']:,} mixed-feature buckets with {near['rows']:,} participating rows "
            f"among {near['eligible_sample_rows']:,} eligible sampled rows. "
            "The heuristic uses available flow duration, forward/backward packet counts and packet-length totals, and mean flow inter-arrival time. "
            "It groups duration and inter-arrival measurements in intervals of 1,000 source units, and packet and byte measures in intervals of 10. "
            "Bucket matches indicate similarity on those fields within the sample.", "",
        ]
    else:
        error_type = run.get("fingerprint_error", "").split(":", 1)[0]
        lines += ["Global fingerprint results are unmeasured." + (f" The private log recorded {error_type}." if error_type else ""), ""]
    lines += ["## Spark execution", ""]
    if run["spark"]:
        lines += [f"Spark settings `{json.dumps(run['spark'], sort_keys=True)}`.", ""]
    if run.get("elapsed_seconds") is not None:
        lines += [f"The measured audit loop took {run['elapsed_seconds']} s.", ""]
    if run.get("fingerprint_seconds") is not None:
        lines += [f"Global fingerprint aggregation took {run['fingerprint_seconds']} s.", ""]
    logs = []
    for folder, notebook_version in [(source, version), (exact_source, exact_version)]:
        if folder is not None and (folder / "kaggle.log").exists():
            try:
                events = read_json(folder / "kaggle.log")
            except json.JSONDecodeError:
                continue
            if isinstance(events, list) and events:
                logs.append(f"version {notebook_version} ({len(events):,} log events)")
    if logs:
        lines += ["The Kaggle API returned persisted execution logs for " + " and ".join(logs) + ".", ""]
    lines += list(markdown_table(
        ["Capture", "Parse and count (s)", "Label and time (s)", "Quality (s)", "Fingerprint staging (s)"], stage_rows,
    ))
    lines += ["", "See [the schema reference](../docs/dataset_schema.md) and [the feasibility assessment](../docs/dataset_feasibility.md)."]
    (reports / "dataset_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Validated {len(measured)} file counts, {label_total:,} labeled rows, {len(quality)} column profiles.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--kernel-url", required=True)
    parser.add_argument("--version", type=int, required=True)
    parser.add_argument("--status", choices=("COMPLETE", "ERROR"), required=True)
    parser.add_argument("--output-root", type=Path, default=ROOT)
    parser.add_argument("--exact-source", type=Path)
    parser.add_argument("--exact-version", type=int)
    args = parser.parse_args()
    if (args.exact_source is None) != (args.exact_version is None):
        parser.error("--exact-source and --exact-version must be supplied together")
    generate(args.source, args.kernel_url, args.version, args.status, args.output_root, args.exact_source, args.exact_version)
