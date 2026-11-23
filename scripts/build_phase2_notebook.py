"""Build self-contained Phase 2 producer and compact storage-verification notebooks."""

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    "src/ingest/dataset_audit.py",
    "src/ingest/schema_contract.py",
    "src/ingest/cleaning.py",
    "src/ingest/parquet_pipeline.py",
    "src/sql/aggregation_demo.py",
    "configs/dataset.yaml",
    "configs/cleaning.yaml",
    "manifests/dataset_inventory.json",
)


def cell(kind, name, source):
    data = {"cell_type": kind, "id": name, "metadata": {}, "source": source.splitlines(keepends=True)}
    if kind == "code":
        data.update(execution_count=None, outputs=[])
    return data


def notebook(cells):
    return {
        "cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
        "nbformat": 4, "nbformat_minor": 5,
    }


def producer(days):
    setup = """import importlib.util
from importlib.metadata import PackageNotFoundError, version
import os
import platform
import subprocess
import sys
from pathlib import Path

print(f"Python {platform.python_version()}", flush=True)
try:
    installed = version("pyspark")
except PackageNotFoundError:
    installed = None
if installed != "4.3.0":
    subprocess.run([sys.executable, "-m", "pip", "install", "pyspark==4.3.0"], check=True)
if importlib.util.find_spec("pyarrow") is None:
    subprocess.run([sys.executable, "-m", "pip", "install", "pyarrow"], check=True)
subprocess.run(["java", "-version"], check=True)
os.environ["PYSPARK_PYTHON"] = sys.executable"""
    package = repr({path: (ROOT / path).read_text(encoding="utf-8") for path in SOURCES})
    bundle = """project = Path("/kaggle/temp/mmds_phase2/source")
payload = """ + package + """
for relative_name, text in payload.items():
    path = project / relative_name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
sys.path.insert(0, str(project))"""
    run = """import json
from src.ingest.parquet_pipeline import run_pipeline
from src.ingest.schema_contract import DataContract

source = json.loads((project / "configs/dataset.yaml").read_text())
phase1 = json.loads((project / "manifests/dataset_inventory.json").read_text())
contract = DataContract.load(project / "configs/cleaning.yaml")
input_dir = Path("/kaggle/input")
roots = (input_dir / "datasets" / source["owner"] / source["slug"], input_dir / source["slug"])
mount = next((candidate for candidate in roots if candidate.is_dir()), None)
if mount is None:
    raise FileNotFoundError(f"Attach {source['owner']}/{source['slug']} version {source['version']}.")
print(f"Mounted: {mount}; CPU affinity: {len(os.sched_getaffinity(0))}", flush=True)
summary = run_pipeline(contract, source, phase1, mount, Path("/kaggle/working/mmds_phase2"),
                       Path("/kaggle/temp/mmds_phase2/spark"), only_days=""" + repr(days) + """)
"""
    return notebook([
        cell("markdown", "overview", "# MMDS Phase 2 Spark data engineering\n\nPrivate CPU preprocessing against the audited dataset release."),
        cell("code", "setup", setup),
        cell("code", "source", bundle),
        cell("code", "pipeline", run),
    ])


def storage_probe(expected_sha):
    verification_code = (ROOT / "src/ingest/storage_validation.py").read_text(encoding="utf-8")
    source = verification_code + """
from hashlib import sha256
import json
from shutil import copyfile
import time

expected = """ + repr(expected_sha) + """
roots = Path("/kaggle/input")
relative = "mmds_phase2/evidence/validation_summary.json"
candidates = set(roots.rglob(relative))
for depth in (1, 2, 3, 4):
    candidates.update(roots.glob("*/" * depth + relative))
matched = {path.resolve(): path for path in sorted(candidates) if sha256(path.read_bytes()).hexdigest() == expected}
if len(matched) != 1:
    raise ValueError(f"Expected one mounted producer summary for the verified version; found {len(matched)}")
validation = next(iter(matched.values()))
summary = json.loads(validation.read_text())
producer = validation.parent.parent
output = Path("/kaggle/working/mmds_phase2_verified")
output.mkdir(exist_ok=True)
started = time.monotonic()
verification = verify_published_layers(summary, producer)
verification.update(summary_sha256=expected, producer_mount=str(producer), elapsed_seconds=round(time.monotonic() - started, 3))
for name in ("validation_summary.json", "parquet_layers.json", "phase2_count_reconciliation.csv",
             "phase2_quality_actions.csv", "phase2_performance.csv"):
    copyfile(validation.parent / name, output / name)
(output / "mount_verification.json").write_text(json.dumps(verification, indent=2) + "\\n", encoding="utf-8")
print(f"Verified producer output in an independent notebook: {verification}", flush=True)
"""
    return notebook([
        cell("markdown", "overview", "# MMDS Phase 2 Parquet reuse check"),
        cell("code", "probe", source),
    ])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "notebooks/phase2_data_engineering.ipynb")
    parser.add_argument("--day", action="append", help="Only rebuild the specified ISO capture days.")
    parser.add_argument("--storage-probe-sha", help="Build only the independent notebook-output mount verification.")
    args = parser.parse_args()
    document = storage_probe(args.storage_probe_sha) if args.storage_probe_sha else producer(args.day)
    for item in document["cells"]:
        if item["cell_type"] == "code":
            compile("".join(item["source"]), item["id"], "exec")
    args.output.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
