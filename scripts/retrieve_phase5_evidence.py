"""Retrieve compact Phase 5 aggregates, figures, and the verified pipeline."""

import argparse
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re

from kaggle_web_api import download_archive


TABLES = {
    "cohorts", "model_selection", "transform_diagnostics", "cluster_profiles", "centroids", "composition",
    "window_family", "cluster_occupancy", "temporal_shift", "novelty_metrics", "score_histogram",
}


def retrieve(kernel, directory, experiment):
    with download_archive(kernel, 32 * 1024 * 1024) as archive:
        selected = {}
        for item in archive.infolist():
            parts = PurePosixPath(item.filename).parts
            if not parts or parts[0] != "mmds_phase5" or ".." in parts or item.is_dir() or item.filename.endswith(".crc"):
                continue
            if (len(parts) == 2 and re.fullmatch(r"phase5_[a-z_]+\.(csv|json)", parts[-1])
                or len(parts) == 3 and parts[1] == "figures" and re.fullmatch(r"phase5_[a-z_]+\.png", parts[-1])
                or len(parts) > 3 and parts[1] == "model"):
                path = Path(*parts[1:])
                if path in selected or item.file_size > 4 * 1024 * 1024:
                    raise ValueError("Unexpected duplicate or oversized Phase 5 artifact")
                selected[path] = item
        if sum(item.file_size for item in selected.values()) > 48 * 1024 * 1024:
            raise ValueError("Unexpected artifact archive size")
        summary = json.loads(archive.read(selected[Path("phase5_summary.json")]))
        if summary["experiment"] != experiment:
            raise ValueError("Archive belongs to a different experiment")
        if summary["status"] == "validated":
            names = TABLES | ({"duplicate_sensitivity"} if experiment == "G" else set())
            required = {Path(f"phase5_{name}.csv") for name in names}
            required |= {Path("figures") / name for name in summary["figures"]}
            if not required <= selected.keys():
                raise ValueError("Some validated evidence is missing")
        for path, item in selected.items():
            target = directory / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(item))
    if "model" in summary:
        target = directory / "model"
        hashes = {path.relative_to(target).as_posix(): sha256(path.read_bytes()).hexdigest()
                  for path in target.rglob("*") if path.is_file()}
        if summary["model"]["sha256"] != hashes:
            raise ValueError("Saved clustering pipeline checksums differ")
    print(f"Retrieved {experiment}: {len(selected)} files, status {summary['status']}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kernel")
    parser.add_argument("directory", type=Path)
    parser.add_argument("--experiment", choices=("G", "B", "C"), required=True)
    args = parser.parse_args()
    retrieve(args.kernel, args.directory, args.experiment)
