"""Retrieve bounded Phase 8 notebook outputs and validate saved model hashes."""

import argparse
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
from tempfile import TemporaryDirectory

from kaggle_web_api import download_archive


def extract(version, destination):
    seen = set()
    prefix = "mmds_phase8"
    with download_archive(version, 32 * 1024 * 1024) as archive:
        for item in archive.infolist():
            path = PurePosixPath(item.filename)
            if item.is_dir() or not path.parts or path.parts[0] != prefix or ".." in path.parts:
                continue
            relative = PurePosixPath(*path.parts[1:])
            if not re.fullmatch(r"phase8_[a-z_]+\.(csv|json)", relative.as_posix()) and relative.parts[0] != "models":
                continue
            if item.filename.endswith(".crc"):
                continue
            if relative in seen or item.file_size > 8 * 1024 * 1024:
                raise ValueError(f"Unexpected archive member {relative}")
            seen.add(relative)
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(item))
    summary = json.loads((destination / "phase8_summary.json").read_text())
    if summary["status"] not in ("validated", "unsupported"):
        raise ValueError("Incomplete stage receipt")
    for entry in summary.get("registry", {}).values():
        root = destination / entry["artifact"]
        hashes = {p.relative_to(root).as_posix(): sha256(p.read_bytes()).hexdigest()
                  for p in root.rglob("*") if p.is_file()}
        if hashes != entry["sha256"]:
            raise ValueError(f"Retrieved model hash mismatch in {entry['artifact']}")
    return len(seen), summary


def retrieve(version, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="phase8-download-", dir=destination.parent) as temporary:
        staging = Path(temporary) / "verified"
        staging.mkdir()
        count, summary = extract(version, staging)
        staging.rename(destination)
    print(f"Retrieved {count} files for {summary['stage']} {summary['population']} ({summary['status']})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version")
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    retrieve(args.version, args.destination)
