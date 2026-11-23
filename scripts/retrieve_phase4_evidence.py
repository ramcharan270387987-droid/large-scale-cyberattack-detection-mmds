"""Fetch versioned Phase 4 receipts and temporary trained-model archives."""

import argparse
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath

from kaggle_web_api import download_archive


EVIDENCE = {
    "phase4_summary.json", "phase4_config.json", "phase4_metrics.csv", "phase4_split_diagnostics.csv",
    "phase4_family_recall.csv", "phase4_training_performance.csv",
}


def check_models(directory, summary):
    for model in summary["models"]:
        name = PurePosixPath(model["path"]).name
        target = directory / "models" / name
        actual = {path.relative_to(target).as_posix(): sha256(path.read_bytes()).hexdigest()
                  for path in target.rglob("*") if path.is_file()}
        if actual != model["sha256"]:
            raise ValueError(f"Saved model checksums differ for {name}")
        if sum(path.stat().st_size for path in target.rglob("*") if path.is_file()) != model["model_bytes"]:
            raise ValueError(f"Saved model bytes differ for {name}")
    return len(summary["models"])


def retrieve(kernel, directory, protocol):
    with download_archive(kernel, 64 * 1024 * 1024) as archive:
        selected = {}
        for item in archive.infolist():
            parts = PurePosixPath(item.filename).parts
            if not parts or parts[0] != "mmds_phase4" or ".." in parts or item.is_dir():
                continue
            if item.filename.endswith(".crc"):
                continue
            if len(parts) == 2 and parts[-1] in EVIDENCE or len(parts) > 3 and parts[1] == "models":
                relative = Path(*parts[1:])
                if relative in selected or item.file_size > 16 * 1024 * 1024:
                    raise ValueError("Unexpected duplicate or oversized artifact")
                selected[relative] = item
        if sum(item.file_size for item in selected.values()) > 72 * 1024 * 1024:
            raise ValueError("Unexpected artifact archive size")
        receipt = Path("phase4_summary.json")
        summary = json.loads(archive.read(selected[receipt]))
        if summary["protocol"] != protocol:
            raise ValueError("Archive belongs to a different protocol")
        if summary["status"] == "validated" and not EVIDENCE <= {str(path) for path in selected}:
            raise ValueError("Missing completed protocol evidence")
        for path, item in selected.items():
            target = directory / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(item))
    print(f"Retrieved protocol {protocol}: {summary['status']}; {check_models(directory, summary)} model hashes verified.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kernel")
    parser.add_argument("directory", type=Path)
    parser.add_argument("--protocol", choices=("A", "B", "C"), required=True)
    args = parser.parse_args()
    retrieve(args.kernel, args.directory, args.protocol)
