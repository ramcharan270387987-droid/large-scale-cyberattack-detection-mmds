"""Validate and publish repository reports from the completed Kaggle analytics."""

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import shutil
from statistics import median


ROOT = Path(__file__).resolve().parents[1]


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def table(headers, rows):
    return ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |", *[
        "| " + " | ".join(str(value).replace("|", "\\|") for value in row) + " |" for row in rows
    ]]


def pct(part, total):
    return f"{100 * part / total:.3f}%" if total else "—"


def number(value):
    if value in (None, ""):
        return "—"
    return f"{float(value):,.4g}" if not isinstance(value, int) else f"{value:,}"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_results(source):
    validation = read_json(source / "phase3_validation.json")
    require(validation["status"] == "validated", "Only complete and validated results enter the full report")
    data = {query: read_csv(source / f"phase3_{query}.csv") for query in validation["completed_queries"]}
    daily, families = data["daily_traffic"], data["attack_families"]
    totals = {row["population"]: int(row["records"]) for row in data["traffic_totals"]}
    require(totals == {"attack": validation["attack"], "benign": validation["benign"]}, "Binary totals mismatch")
    require(sum(totals.values()) == validation["records"], "Total records mismatch")
    counts = Counter()
    for row in daily:
        counts.update(records=int(row["records"]), benign=int(row["benign"]), attack=int(row["attacks"]))
        require(int(row["records"]) == int(row["attacks"]) + int(row["benign"]), "Daily counts mismatch")
    require(dict(counts) == {"records": validation["records"], **totals}, "Day totals mismatch")
    require([row["source_day"] for row in daily] == validation["source_days"], "Day inventory mismatch")
    require(sum(int(row["records"]) for row in families) == validation["attack"], "Attack family totals mismatch")
    by_family = Counter()
    for row in data["family_by_day"]:
        by_family[row["attack_family"]] += int(row["records"])
    require(by_family == Counter({row["attack_family"]: int(row["records"]) for row in families}), "Family/day counts mismatch")
    for name in ("hourly_traffic", "time_windows"):
        require(sum(int(row["records"]) for row in data[name]) == validation["records"] - validation["temporal_ineligible"],
                f"{name} eligible counts mismatch")
    require(sum(int(row["records"]) for row in data["protocols"]) == validation["records"], "Protocol counts mismatch")
    suite = read_csv(source / "phase3_query_performance.csv")
    require(all(float(row["seconds"]) >= 0 for row in suite), "Invalid timing")
    require({row["workload"] for row in suite} == set(data) | {"day_label_equivalence"}, "Performance inventory mismatch")
    for api in ("SQL", "DataFrame"):
        bench = [row for row in suite if row["api"] == api and row["workload"] == "day_label_equivalence"]
        require(len(bench) == validation["benchmark_repeats"] and all(row["result_rows"] == "20" for row in bench),
                "Benchmark evidence mismatch")
    figures = validation["figures"]
    require(len(set(figures)) == 10 and all((source / "figures" / filename).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
                                            for filename in figures), "Invalid or missing chart")
    plans = read_json(source / "phase3_execution_plans.json")
    require(set(plans["day_label_benchmark"]) == {"SQL", "DataFrame"} and
            plans["bounded_rdd"]["rows"] == validation["rdd_sample_rows"], "Plan evidence mismatch")
    return validation, data, suite


def write_report(source, kernel_url, version, output):
    validation, data, timings = load_results(source)
    reports = output / "reports"
    docs = output / "docs"
    (reports / "figures").mkdir(parents=True, exist_ok=True)
    docs.mkdir(parents=True, exist_ok=True)
    for path in sorted(source.glob("phase3_*")):
        if path.is_file():
            shutil.copyfile(path, reports / path.name)
    for name in validation["figures"]:
        shutil.copyfile(source / "figures" / name, reports / "figures" / name)

    resources = validation["resources"]
    quality = {key: int(value) for key, value in data["duplicate_quality"][0].items()}
    daily, families = data["daily_traffic"], data["attack_families"]
    most_attacks = max(daily, key=lambda row: int(row["attacks"]))
    top_share = max(daily, key=lambda row: float(row["attack_share"]))
    min_share = min(daily, key=lambda row: float(row["attack_share"]))
    peak_hour = max(data["hourly_traffic"], key=lambda row: int(row["attacks"]))
    protocols = Counter()
    for row in data["protocols"]:
        protocols[row["protocol"]] += int(row["records"])
    stats = {(r["population"], r["feature"]): r for r in data["feature_statistics"]}
    correlations = {(r["population"], r["x"], r["y"]): r for r in data["correlations"]}
    pattern_groups = {}
    for row in data["candidate_patterns"]:
        total = pattern_groups.setdefault((row["population"], row["pattern"]), Counter())
        total.update(matches=int(row["matches"]), eligible=int(row["eligible"]))
    total_rows, attack = validation["records"], validation["attack"]

    report = [
        "# Phase 3 Spark SQL traffic analytics", "",
        f"**READY FOR PHASE 4.** Kaggle notebook version {version} reached `COMPLETE` and produced "
        f"{len(data)} compact query results over {total_rows:,} validated records. [Private Kaggle notebook]({kernel_url})",
        "", "## Input validation", "",
        f"Phase 2 output version {validation['producer']['kernel_version']} matched saved receipt "
        f"`{validation['phase2_receipt_sha256']}` and policy `{validation['policy_version']}`. "
        f"Spark reconciled labels, original-label family mappings and temporal eligibility across the clean and feature-ready layers. "
        f"The feature-ready schema contained {len(validation['features'])} canonical model candidates. [Validation evidence](phase3_validation.json)", "",
    ]
    report += table(["Layer", "Mounted path", "Partitions", "Records"], [
        (key, f"`{layer['path']}`", layer["partitions"], f"{layer['records']:,}")
        for key, layer in validation["layers"].items()
    ])
    report += [
        "", "## Traffic and temporal counts", "",
        f"{validation['benign']:,} records were benign and {attack:,} ({pct(attack, total_rows)}) were labeled attack. "
        f"The largest attack count was {int(most_attacks['attacks']):,} on {most_attacks['source_day']}. "
        f"Attack prevalence ranged from {100 * float(min_share['attack_share']):.4f}% on {min_share['source_day']} "
        f"to {100 * float(top_share['attack_share']):.4f}% on {top_share['source_day']}. [Daily traffic](phase3_daily_traffic.csv)",
        "",
    ]
    report += table(["Population", "Packet count", "Byte count"], [
        (row["population"], f"{float(row['packet_count']):,.0f}", f"{float(row['byte_count']):,.0f}")
        for row in data["traffic_totals"]
    ])
    report += [
        "",
        f"Eligible event-time queries retained {total_rows - validation['temporal_ineligible']:,} records and excluded "
        f"{validation['temporal_ineligible']} timestamp outliers. The {len(data['hourly_traffic'])} observed hourly groups included a peak of "
        f"{int(peak_hour['attacks']):,} attack records "
        f"on {peak_hour['source_day']} at {int(peak_hour['local_hour']):02d}:00 local wall time. Source timezone is unverified. "
        "Capture-day groups include all rows. Empty or unobserved hours are left out of the hourly table. "
        "[Hourly traffic](phase3_hourly_traffic.csv) · [Three-hour windows](phase3_time_windows.csv)",
        "", "## Families and flow statistics", "",
    ]
    report += table(["Family", "Attack records", "Share of attacks", "Capture days", "Rows with nonsentinel issues"], [
        (row["attack_family"], f"{int(row['records']):,}", pct(int(row["records"]), attack), row["capture_days"],
         f"{int(row['invalid_affected_rows']):,}") for row in families
    ])
    report += ["", "Approximate flow quantiles use Spark percentile accuracy 4,096. The feature tables also contain finite-value counts, "
               "means, sample standard deviations and extrema. [By binary label](phase3_feature_statistics.csv) · "
               "[By family](phase3_family_feature_statistics.csv) · [Original labels](phase3_original_labels.csv)", ""]
    report += table(["Measure", "Benign P50", "Attack P50", "Benign P99", "Attack P99"], [
        (feature, *(number(json.loads(stats[population, feature]["quantiles"])[index])
                    for index in (1, 3) for population in ("benign", "attack")))
        for feature in ("flow_duration", "total_packets", "total_bytes", "flow_iat_mean", "flow_pkts_s")
    ])
    report += [
        "",
        "Aggregate IP protocol counts were " + ", ".join(f"code {key} ({value:,})" for key, value in protocols.most_common()) + ". "
        "[Protocol by family](phase3_protocols.csv) · [Top destination ports](phase3_destination_ports.csv)",
        "", "## Data-quality sensitivity", "",
        f"Exact duplicate groups contained {quality['rows_in_exact_groups']:,} occurrences. A representative-per-exact-content count "
        f"would be {validation['duplicate_aware_records']:,}, removing {quality['excess_copies']:,} excess copies from that count. "
        f"The Phase 2 cleaned-feature conflict groups contained {quality['rows_in_feature_label_conflicts']:,} rows "
        f"({pct(quality['rows_in_feature_label_conflicts'], total_rows)}) across {quality['feature_label_conflict_groups']:,} groups. "
        "Default Phase 3 statistics preserve full multiplicity. [Duplicate and anomaly summary](phase3_duplicate_quality.csv)",
    ]
    raw = {(r["binary_label"], r["feature"]): r for r in data["raw_sensitivity"]}
    clean = {(r["binary_label"], r["feature"]): r for r in data["clean_sensitivity"]}
    report += [""] + table(["Feature", "Raw NaN", "Raw infinity", "Raw minus one", "Clean nulls"], [
        (name, *(f"{sum(int(raw[key, name][field]) for key in ('0', '1')):,}" for field in ("nan", "infinities", "minus_one")),
         f"{sum(int(clean[key, name]['nulls']) for key in ('0', '1')):,}")
        for name in ("flow_byts_s", "flow_pkts_s", "init_fwd_win_byts", "init_bwd_win_byts", "flow_duration")
    ])
    report += ["", "Finite means and class-specific counts are retained in the sensitivity tables. "
               "[Raw-aligned](phase3_raw_sensitivity.csv) · [Clean](phase3_clean_sensitivity.csv)",
               "", "## Performance", "",
               f"Spark {resources['spark_version']} used `{resources['master']}`, {resources['driver_memory']} configured driver heap, "
               f"{resources['shuffle_partitions']} configured shuffle partitions and {resources['input_partition_bytes'] // 1048576} MiB input splits. "
               f"The notebook took {validation['elapsed_seconds']:.3f}s from input validation to chart generation. "
               f"Input validation took {validation['validation_seconds']:.3f}s. JVM high-water RSS was "
               f"{resources['driver_peak_rss_bytes'] / 1024 ** 3:.2f} GiB.", ""]
    report += table(["API", "Measured runs (s)", "Median (s)"], [
        (api, ", ".join(f"{x:.3f}" for x in values), f"{median(values):.3f}")
        for api in ("SQL", "DataFrame")
        for values in [[float(row["seconds"]) for row in timings
                        if row["workload"] == "day_label_equivalence" and row["api"] == api]]
    ])
    report += [
        "", f"The bounded SQL, DataFrame and RDD comparison agreed on {validation['rdd_sample_rows']} records. "
        "The full-data benchmark warmed each API and alternated execution order over the same cached inputs. "
        "[Measured query timings](phase3_query_performance.csv) · [Physical plans and RDD lineage](phase3_execution_plans.json)",
        "", "## Figures", "",
    ]
    report += [f"- [{file.removeprefix('phase3_').removesuffix('.png').replace('_', ' ').capitalize()}](figures/{file})"
               for file in validation["figures"]]
    report += ["", "[Candidate pattern findings](../docs/attack_pattern_findings.md) · [Research readiness](phase3_research_readiness.md)"]
    (reports / "phase3_analytics.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    thresholds = data["reference_thresholds"][0]
    patterns = [
        "# Observed attack-pattern candidates", "",
        "These retrospective comparisons use the saved labels and full eligible feature support for each statistic. "
        "The rule cutoffs are descriptive approximate quantiles of benign traffic in the same capture collection. "
        "Use them as hypotheses for held-out evaluation. [Threshold values](../reports/phase3_reference_thresholds.csv)", "",
    ]
    patterns += table(["Pattern", "Benign matches / eligible", "Attack matches / eligible", "Benign share", "Attack share"], [
        (pattern, f"{a['matches']:,} / {a['eligible']:,}", f"{b['matches']:,} / {b['eligible']:,}",
         pct(a["matches"], a["eligible"]), pct(b["matches"], b["eligible"]))
        for pattern in sorted({key[1] for key in pattern_groups})
        for a, b in [(pattern_groups["benign", pattern], pattern_groups["attack", pattern])]
    ])
    rule_names = {key[1] for key in pattern_groups}
    compared = [(pattern_groups["benign", key], pattern_groups["attack", key]) for key in rule_names]
    if all(a["eligible"] and b["eligible"] and a["matches"] * b["eligible"] >= b["matches"] * a["eligible"]
           for a, b in compared):
        patterns += [
            "", "Every rule matched benign records at least as often as attack records among its eligible rows. "
            "The short-duration, high-byte rule produced particularly few matches. "
            "These results favor investigating family-specific context and comparing feature distributions before choosing candidate indicators.",
        ]
    patterns += [
        "",
        f"High packet rate and large packet count used strict values above benign P99 "
        f"({number(thresholds['packet_rate_p99'])} packets/s and {number(thresholds['packet_count_p99'])} packets). "
        f"Short high-byte flows used duration at or below benign P10 ({number(thresholds['duration_p10'])} µs) "
        f"and bytes above benign P99 ({number(thresholds['byte_count_p99'])} bytes). "
        f"High mean inter-arrival time used benign P99 ({number(thresholds['iat_p99'])} µs). "
        "[Patterns by family](../reports/phase3_candidate_patterns.csv)",
        "", "## Selected correlations", "",
    ]
    patterns += table(["Pair", "Benign Pearson r", "Attack Pearson r", "Benign pairs", "Attack pairs"], [
        (f"`{x}` · `{y}`", number(correlations["benign", x, y]["pearson"]),
         number(correlations["attack", x, y]["pearson"]), f"{int(correlations['benign', x, y]['pairs']):,}",
         f"{int(correlations['attack', x, y]['pairs']):,}")
        for x, y in sorted({(key[1], key[2]) for key in correlations})
    ])
    patterns += [
        "", "Counts and bytes share a mechanical volume relationship, and flow duration and inter-arrival summaries share timing information. "
        "Correlations describe the observed rows. Family composition, repeated traffic and heavy tails can affect their magnitude.",
        "", "## TCP flags and transport context", "",
    ]
    common_flags = [
        max((r for r in data["tcp_flags"] if r["population"] == group), key=lambda r: int(r["records"]))
        for group in ("benign", "attack")
    ]
    patterns += table(["Class", "Leading family-specific TCP flag tuple", "Records"], [
        (row["population"], row["attack_family"] + " · " + ", ".join(name.upper() for name in ("syn", "ack", "fin", "rst")
                                                                   if row[name].lower() == "true"),
         f"{int(row['records']):,}") for row in common_flags
    ])
    ports = [row for row in data["destination_ports"] if row["scope"] == "population" and row["rank"] == "1"]
    patterns += [
        "", "The most common observed destination ports were "
        + ", ".join(f"{row['dst_port']} for {row['population']} ({int(row['records']):,} records)" for row in ports) + ". "
        "Ports and flag tuples can reflect the laboratory scenario and protocol composition. "
        "[TCP flags](../reports/phase3_tcp_flags.csv) · [Ports by family](../reports/phase3_destination_ports.csv)",
    ]
    (docs / "attack_pattern_findings.md").write_text("\n".join(patterns) + "\n", encoding="utf-8")

    absent = [row for row in data["family_by_day"] if int(row["records"]) == 0]
    rare = sorted((row for row in data["original_labels"] if row["attack_family"] != "Benign"),
                  key=lambda row: int(row["records"]))[:3]
    missing = sorted(
        (r for r in data["feature_missingness"] if int(r["missing"]) > 0),
        key=lambda row: -int(row["missing"]),
    )
    benign_windows = [r for r in data["time_windows"] if r["population"] == "benign" and r["median_duration_us"] and int(r["records"]) >= 500]
    readiness = [
        "# Phase 3 research readiness", "",
        "Start future comparisons with duration, directional packets and bytes, packet length, mean inter-arrival time and TCP flags. "
        "Use correlations to prioritize redundant pairs for a controlled ablation. Treat IP protocol as categorical context and evaluate it separately. "
        "Exclude target values, time, capture day, source identity, port and fingerprints from the feature vector. "
        "Use provenance and fingerprints to group records and check split overlap.", "",
        "## Missingness and transformation design", "",
        "The rows below identify every canonical candidate with observed missingness. Choose an imputation and missingness-indicator policy inside "
        "each training partition. Consider log transforms and robust training-only scaling for nonnegative heavy-tailed measures in clustering "
        "or other scale-sensitive experiments. [All 77 candidates](phase3_feature_missingness.csv)", "",
    ]
    readiness += table(["Feature", "Missing rows", "Missing share", "At least 5%"], [
        (row["feature"], f"{int(row['missing']):,}", pct(int(row["missing"]), int(row["records"])),
         "Yes" if int(row["missing"]) / int(row["records"]) >= 0.05 else "No") for row in missing
    ])
    readiness += [
        "", "## Time windows and class support", "",
        f"The rarest original labels were {', '.join(row['original_label'] + ' (' + str(row['records']) + ')' for row in rare)}. "
        f"{len(absent)} family-day combinations had zero observed attacks. "
        "For held-out capture comparisons, publish support and distinguish absent classes from errors.",
        "",
        "Track duration, packet count, and byte volume with three-hour wall-clock windows, partitioned by capture day and binary label. "
        "Use hourly counts separately to monitor prevalence. Compare the same class across days with a prespecified support floor and report coverage. "
        "Changes can reflect capture protocols or the mix of activity within each class. Evidence of concept drift would require controlled later "
        "evaluation of the relationship between features and labeled outcomes.", "",
    ]
    if benign_windows:
        low = min(benign_windows, key=lambda row: float(row["median_duration_us"]))
        high = max(benign_windows, key=lambda row: float(row["median_duration_us"]))
        readiness += [
            f"Among benign windows with at least 500 rows, approximate median durations ranged from {number(low['median_duration_us'])} µs "
            f"on {low['source_day']} at hour {low['window_start_hour']} ({int(low['records']):,} rows) to "
            f"{number(high['median_duration_us'])} µs on {high['source_day']} at hour {high['window_start_hour']} "
            f"({int(high['records']):,} rows). This is a descriptive within-label contrast.", "",
        ]
    readiness += table(["Capture day", "Families with zero observed attacks"], [
        (day, ", ".join(row["attack_family"] for row in absent if row["source_day"] == day) or "—")
        for day in validation["source_days"]
    ])
    readiness += ["", "[Family-day counts](phase3_family_by_day.csv) · [Window statistics](phase3_time_windows.csv)"]
    (reports / "phase3_research_readiness.md").write_text("\n".join(readiness) + "\n", encoding="utf-8")
    print(f"Published {len(data)} reconciled query tables, {len(validation['figures'])} charts, and the measured reports.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--kernel-url", required=True)
    parser.add_argument("--version", type=int, required=True)
    parser.add_argument("--output-root", type=Path, default=ROOT)
    args = parser.parse_args()
    write_report(args.evidence, args.kernel_url, args.version, args.output_root)
