"""Retrieve only Phase 6 aggregate evidence and figures from a pinned run."""

import argparse
from pathlib import Path, PurePosixPath
import re

from kaggle_web_api import download_archive


TABLES = ("replay_batches", "window_metrics", "shift_metrics", "alerts", "recovery_tests", "performance")


def retrieve(version, destination):
    files = {f"phase6_{name}.csv" for name in TABLES} | {
        "phase6_summary.json", "phase6_stream_progress.json", "phase6_reference.json",
    }
    destination.mkdir(parents=True, exist_ok=True)
    seen = set()
    with download_archive(version, 16 * 1024 * 1024) as archive:
        for item in archive.infolist():
            path = PurePosixPath(item.filename)
            if not path.parts or path.parts[0] != "mmds_phase6":
                continue
            relative = PurePosixPath(*path.parts[1:])
            if relative.as_posix() not in files and not re.fullmatch(r"figures/phase6_[a-z_]+\.png", relative.as_posix()):
                continue
            if relative in seen or item.file_size > 3 * 1024 * 1024:
                raise ValueError(f"Unexpected archive member {relative}")
            seen.add(relative)
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(item))
    if not files <= {x.as_posix() for x in seen}:
        raise ValueError("Some compact Phase 6 evidence is missing")
    print(f"Retrieved {len(seen)} compact Phase 6 artifacts.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version")
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    retrieve(args.version, args.destination)
