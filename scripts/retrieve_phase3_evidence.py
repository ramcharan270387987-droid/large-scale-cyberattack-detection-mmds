"""Retrieve and verify the compact Phase 3 archive via the proven Kaggle route."""

import argparse
import json
from pathlib import Path, PurePosixPath
import re

from kaggle_web_api import download_archive


def retrieve(kernel, destination):
    with download_archive(kernel, 8 * 1024 * 1024) as archive:
        files = {}
        for item in archive.infolist():
            path = PurePosixPath(item.filename)
            if not path.parts or path.parts[0] != "mmds_phase3":
                continue
            if len(path.parts) == 2 and re.fullmatch(r"phase3_[a-z_]+\.(csv|json)", path.name):
                target = Path(path.name)
            elif len(path.parts) == 3 and path.parts[1] == "figures" and re.fullmatch(r"phase3_[a-z_]+\.png", path.name):
                target = Path("figures") / path.name
            else:
                continue
            if target in files or item.file_size > 1024 * 1024:
                raise ValueError("Unexpected duplicate or oversized Phase 3 output")
            files[target] = archive.read(item)
    summary = json.loads(files[Path("phase3_validation.json")])
    if summary["status"] == "validated":
        expected = {Path(f"phase3_{name}.csv") for name in summary["completed_queries"]}
        expected |= {Path("figures") / name for name in summary["figures"]}
        expected.update(map(Path, ("phase3_validation.json", "phase3_execution_plans.json", "phase3_query_performance.csv")))
        if files.keys() != expected:
            raise ValueError("Archive does not match the validated result inventory")
    for name, data in files.items():
        output = destination / name
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(data)
    print(f"Retrieved {len(files)} compact files with status {summary['status']}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kernel")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    retrieve(args.kernel, args.output)
