"""Generate bounded window evidence, throughput tables and charts from callback commits."""

from collections import defaultdict
import csv
import json

from src.ingest.dataset_audit import atomic_json
from src.sql.traffic_analytics import require, write_rows
from src.streaming.alert_engine import signals
from src.streaming.model_scoring import SUPERVISED
from src.streaming.replay_source import CAPTURE_ONLY
from src.streaming.shift_metrics import combine, model_metrics, novelty, tail_upper


def context(day, rank, hour, batch_ids, duration):
    valid = hour is not None and hour != CAPTURE_ONLY
    return {"scope": "daily" if hour is None else "intraday" if valid else "capture_only",
            "source_day": day, "split_rank": rank, "batch_ids": batch_ids, "window_hour": hour,
            "wall_start": f"{hour:02}:00" if valid else None, "wall_end": f"{hour + duration:02}:00" if valid else None}


def window_evidence(item, reference, ctx, config):
    scores = {name: model_metrics(item["scores"][name], config["score_bins"]) for name in SUPERVISED}
    hist = item["scores"]["random_forest"]
    bins = config["score_bins"] // 32
    rounded_hist = [0] * 32
    for score, support in hist.items():
        rounded_hist[int(score) // bins] += sum(support)
    row = ctx | {"rows": item["rows"], "eligible": item["eligible"], "attacks": item["attacks"], "benign": item["benign"],
                 "mean_distance": item["distance_sum"] / item["rows"], "distance_p95_upper": tail_upper(item, config["distance_bounds"]),
                 "cluster_counts": item["histograms"]["cluster"], "rf_score_counts_32": rounded_hist,
                 "classifier_metrics": scores, "novelty_metrics": novelty(item)}
    shifts, alerts = signals(item, reference, ctx, config)
    return row, shifts, alerts


def scope_summary(item, config):
    return {"rows": item["rows"], "eligible": item["eligible"], "attacks": item["attacks"], "benign": item["benign"],
            "models": {name: model_metrics(item["scores"][name], config["score_bins"]) for name in SUPERVISED},
            "novelty": novelty(item), "cluster_counts": item["histograms"]["cluster"]}


def performance(label, files, documents, result):
    rows = sum(chunk["rows"] for doc in documents for chunk in doc["source"])
    return {"configuration": label, "files_per_trigger": files, "batches": len(documents),
            "rows": rows, "staging_bytes_replayed": sum(chunk["bytes"] for doc in documents for chunk in doc["source"]),
            "elapsed_seconds": result["elapsed_seconds"], "rows_per_second": rows / result["elapsed_seconds"],
            "scoring_seconds": sum(doc["scoring_seconds"] for doc in documents),
            "callback_seconds": sum(doc["processing_seconds"] for doc in documents),
            "checkpoint_bytes": result["checkpoint_bytes"]}


def publish_results(output, full, run, comparisons, summary, reference, config):
    windows, shifts, alerts, batches = [], [], [], []
    days, ranks = defaultdict(list), defaultdict(list)
    for doc in full:
        batch_id = doc["batch_id"]
        for source, chunk in zip(doc["source"], doc["chunks"]):
            day, split, hour = chunk["source_day"], chunk["split_rank"], chunk["window_hour"]
            days[day, split].append((batch_id, chunk))
            ranks[split].append(chunk)
            batches.append(source | {"batch_id": batch_id, "temporally_eligible": chunk["eligible"],
                                     "entered_utc": doc["entered_utc"], "finished_utc": doc["finished_utc"],
                                     "scoring_seconds": doc["scoring_seconds"], "processing_seconds": doc["processing_seconds"],
                                     "rows_per_second": chunk["rows"] / doc["processing_seconds"]})
            row, comparison, alarm = window_evidence(chunk, reference, context(day, split, hour, [batch_id], config["window_hours"]), config)
            windows.append(row)
            shifts.extend(comparison)
            alerts.extend(alarm)
    for (day, split), entries in sorted(days.items()):
        row, comparison, alarm = window_evidence(combine([chunk for _, chunk in entries]), reference,
                                               context(day, split, None, [i for i, _ in entries], config["window_hours"]), config)
        windows.append(row)
        shifts.extend(comparison)
        alerts.extend(alarm)

    summary["scopes"] = {name: scope_summary(combine(ranks[i]), config) for i, name in enumerate(("train", "validation", "test"))}
    require(sum(v["rows"] for v in summary["scopes"].values()) == summary["staging"]["rows"], "Report lost replay rows")
    require(sum(v["eligible"] for v in summary["scopes"].values()) ==
            summary["staging"]["rows"] - summary["staging"]["ineligible_retained"],
            "Report lost capture-day-only records")
    require(all(r["rows"] == r["eligible"] if r["scope"] == "intraday" else
                r["eligible"] == 0 if r["scope"] == "capture_only" else True for r in windows), "Ineligible intraday contribution")
    summary["recovery"] = run["recovery"]
    summary["configurations"] = [performance("historical", config["files_per_trigger"], full, run)]
    for label, files, docs, evidence in comparisons:
        require([x for doc in docs for x in doc["source"]] ==
                [x for doc in full for x in doc["source"] if x["replay_seq"] in {
                    i["replay_seq"] for d in docs for i in d["source"]}], "Comparison population differs")
        expected_sequences = {item["replay_seq"] for document in docs for item in document["chunks"]}
        expected = combine([x for d in full for x in d["chunks"] if x["replay_seq"] in expected_sequences])
        observed = combine([x for d in docs for x in d["chunks"]])
        require(all(value == observed[key] for key, value in expected.items() if key != "distance_sum") and
                abs(expected["distance_sum"] - observed["distance_sum"]) <= 1e-5 * expected["rows"],
                "Configuration changed scoring counts")
        summary["configurations"].append(performance(label, files, docs, evidence))
    summary["alerts"] = {"count": len(alerts), "high": sum(r["severity"] == "high" for r in alerts)}
    for name, rows in (("replay_batches", batches), ("window_metrics", windows), ("shift_metrics", shifts),
                       ("recovery_tests", run["recovery"]), ("performance", summary["configurations"])):
        write_rows(output / f"phase6_{name}.csv", rows)
    if alerts:
        write_rows(output / "phase6_alerts.csv", alerts)
    else:
        with (output / "phase6_alerts.csv").open("w", encoding="utf-8") as handle:
            csv.writer(handle).writerow([*shifts[0], "severity", "evidence"])
    atomic_json(output / "phase6_stream_progress.json", {"historical": run,
                **{label: evidence for label, _, _, evidence in comparisons}})
    # Retain only compact aggregate counts and digests in the published evidence.
    atomic_json(output / "phase6_reference.json", reference)
    from src.streaming.replay_charts import draw

    summary["figures"] = draw(output)
