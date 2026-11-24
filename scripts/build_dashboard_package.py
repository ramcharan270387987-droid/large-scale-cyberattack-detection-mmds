"""Derive the compact Streamlit package from the committed research evidence."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dashboard.validation import digest, parse_table, reconcile, require


def build(root=ROOT):
    data = root / "dashboard/data"
    contract = (root / "configs/dashboard.yaml").read_bytes()
    config = json.loads(contract)
    payloads, inputs, tables, metadata = {}, {}, {}, {}

    def read(path, phase):
        body = (root / path).read_bytes()
        inputs[path] = {"phase": phase, "version": config["phase_versions"][str(phase)],
                        "sha256": digest(body), "bytes": len(body)}
        return body

    for name, spec in config["tables"].items():
        content = read(spec["source"], spec["phase"])
        payloads[f"{name}.csv"] = content
        tables[name] = parse_table(content, spec["columns"], name)
        metadata[name] = {"source": spec["source"], "sha256": digest(content), "rows": len(tables[name])}
    source_phases = {"parquet": 2, "sql": 3, "models": 4, "clusters": 5, "replay": 6, "splits": 4}
    parquet, sql, models, clusters, replay, splits = (
        json.loads(read(config["sources"][name], phase)) for name, phase in source_phases.items())
    require(all(x["status"] == "validated" for x in (parquet, sql, models, replay)) and
            all(x["status"] == "COMPLETE" for x in clusters["experiments"].values()), "An input lacks a validation receipt")
    require(sql["phase2_receipt_sha256"] == replay["input"]["receipt_sha256"] ==
            parquet["independent_mount"]["summary_sha256"], "Upstream Phase 2 lineage differs")
    historical = next(x for x in replay["configurations"] if x["configuration"] == "historical")
    summary = {
        "dataset": {"identity": parquet["dataset"], "totals": parquet["totals"], "days": sql["source_days"],
                    "policy": parquet["policy_version"], "producer": parquet["producer"]},
        "sql": {"resources": sql["resources"], "benchmark_repeats": sql["benchmark_repeats"],
                "quantile_accuracy": sql["quantile_accuracy"]},
        "protocols": splits["protocols"],
        "model_support": {k: v["split_support"] for k, v in models["protocols"].items()},
        "models": {"threshold": splits["threshold"], "url": models["kernel_url"], "version": models["config_version"]},
        "clusters": {k: {"selected_k": v["selected_k"], "retained_rows": v["retained_rows"], "version": v["version"],
                         "cutoffs": v["calibration"]["cutoffs"], "seed_ari": v["robustness"]["seed_ari"],
                         "scale_ari": v["robustness"]["scale_ari"]} for k, v in clusters["experiments"].items()},
        "replay": historical | {"version": replay["kaggle"]["version"], "url": replay["kaggle"]["url"],
                                "ineligible": replay["staging"]["ineligible_retained"], "alerts": replay["alerts"],
                                "purged": replay["staging"]["purged_rows"], "spark": replay["spark"],
                                "cutoff": replay["clustering"]["p99"]},
    }
    reconcile(summary, tables)
    encode = lambda obj: (json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode()
    payloads["summary.json"] = encode(summary)
    manifest = {"schema_version": config["schema_version"], "source_revision": config["source_revision"],
                "config_sha256": digest(contract), "inputs": inputs, "tables": metadata,
                "summary_sha256": digest(payloads["summary.json"]),
                "package_bytes": sum(map(len, payloads.values()))}
    data.mkdir(parents=True, exist_ok=True)
    for name, content in payloads.items():
        (data / name).write_bytes(content)
    (root / "manifests/dashboard_package.json").write_bytes(encode(manifest))
    print(f"Built {len(tables)} aggregate tables, {manifest['package_bytes']:,} bytes.")


if __name__ == "__main__":
    build()
