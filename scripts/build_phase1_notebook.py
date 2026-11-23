"""Embed the tested Phase 1 audit and configuration in a self-contained notebook."""

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def cell(kind, cell_id, source):
    value = {"cell_type": kind, "id": cell_id, "metadata": {}, "source": source.splitlines(keepends=True)}
    if kind == "code":
        value.update(execution_count=None, outputs=[])
    return value


def notebook(exact_duplicates=False):
    implementation = (ROOT / "src/ingest/dataset_audit.py").read_text().split('\nif __name__ == "__main__":', 1)[0]
    config = json.loads((ROOT / "configs/dataset.yaml").read_text())
    if exact_duplicates:
        config["spark"].update(master="local[4]", shuffle_partitions=48)
    setup = """import os
from importlib.metadata import PackageNotFoundError, version
import platform
import subprocess
import sys

print(f"Python {platform.python_version()}", flush=True)
try:
    installed = version("pyspark")
except PackageNotFoundError:
    installed = None
if installed != "4.3.0":
    subprocess.run([sys.executable, "-m", "pip", "install", "pyspark==4.3.0"], check=True)
subprocess.run(["java", "-version"], check=True)
os.environ["PYSPARK_PYTHON"] = sys.executable"""
    run = """from shutil import disk_usage

# To resume after a partial run, set this to the list of unfinished ISO days.
ONLY_DAYS = None
EXACT_DUPLICATES = """ + repr(exact_duplicates) + """
input_dir = Path("/kaggle/input")
roots = (
    input_dir / "datasets" / CONFIG["owner"] / CONFIG["slug"],
    input_dir / CONFIG["slug"],
)
mounted = next((root for root in roots if root.is_dir()), None)
if mounted is None:
    raise FileNotFoundError(f"Attach the pinned source {CONFIG['owner']}/{CONFIG['slug']} version {CONFIG['version']}.")
output = Path("/kaggle/working/mmds_phase1")
scratch = Path("/kaggle/temp/mmds_phase1")
scratch.mkdir(parents=True, exist_ok=True)
print(f"Kaggle CPU affinity: {len(os.sched_getaffinity(0))}; scratch free: {disk_usage(scratch).free} bytes", flush=True)
print(f"Mounted: {mounted}", flush=True)
if EXACT_DUPLICATES:
    audit_exact_duplicates(CONFIG, mounted, output, scratch)
else:
    summary = audit_dataset(CONFIG, mounted, output, scratch, ONLY_DAYS)
    print(f"Completed audit loop in {summary['elapsed_seconds']} s", flush=True)
    print({name: data["status"] for name, data in summary["files"].items()}, flush=True)"""
    return {
        "cells": [
            cell("markdown", "overview", "# MMDS Phase 1 dataset audit\n\nPrivate Kaggle CPU audit of version 1. Repository sources are embedded by `scripts/build_phase1_notebook.py`."),
            cell("code", "runtime", setup),
            cell("code", "audit-source", implementation),
            cell("code", "configuration", "CONFIG = " + repr(config)),
            cell("code", "run", run),
        ],
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "notebooks/phase1_dataset_audit.ipynb")
    parser.add_argument("--exact-duplicates", action="store_true")
    args = parser.parse_args()
    args.output.write_text(json.dumps(notebook(args.exact_duplicates), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
