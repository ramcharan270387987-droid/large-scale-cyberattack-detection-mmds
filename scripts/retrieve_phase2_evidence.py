"""Recover the producer receipt and fetch only the compact probe notebook archive."""

import argparse
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath


PROBE_FILES = {
    "mount_verification.json", "validation_summary.json", "parquet_layers.json",
    "phase2_count_reconciliation.csv", "phase2_quality_actions.csv", "phase2_performance.csv",
}


def log_summary(path):
    events = json.loads(path.read_text(encoding="utf-8"))
    decoder = json.JSONDecoder()
    prefix = "PHASE2_EVIDENCE "
    candidates = [record["data"] for record in events if isinstance(record.get("data"), str)]
    for i in range(len(candidates) - 1, -1, -1):
        data = candidates[i]
        if prefix not in data:
            continue
        payload = data.split(prefix, 1)[1]
        for tail in range(i + 1, min(i + 10, len(candidates) + 1)):
            try:
                summary, _ = decoder.raw_decode(payload)
                return summary
            except json.JSONDecodeError:
                if tail < len(candidates):
                    payload += candidates[tail]
    raise ValueError("No complete Phase 2 receipt in the producer log")


def receive_probe(kernel, destination):
    # The probe archive contains compact receipts only.
    from kaggle_web_api import download_archive

    with download_archive(kernel, 8 * 1024 * 1024) as archive:
        files = {}
        for member in archive.infolist():
            path = PurePosixPath(member.filename)
            if path.parts[:1] != ("mmds_phase2_verified",) or len(path.parts) != 2 or path.name not in PROBE_FILES:
                continue
            if path.name in files or member.file_size > 1024 * 1024:
                raise ValueError("Unexpected duplicate or oversized compact artifact")
            files[path.name] = archive.read(member)
        if files.keys() != PROBE_FILES:
            raise ValueError(f"Missing probe artifacts: {sorted(PROBE_FILES - files.keys())}")
        destination.mkdir(parents=True, exist_ok=True)
        for name, data in files.items():
            (destination / name).write_bytes(data)
    observed = json.loads(files["mount_verification.json"])
    if observed["summary_sha256"] != sha256(files["validation_summary.json"]).hexdigest():
        raise ValueError("Downloaded producer evidence does not match the verified mount")
    print(f"Retrieved and verified {len(files)} compact artifacts.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    log = commands.add_parser("producer")
    log.add_argument("log", type=Path)
    log.add_argument("output", type=Path)
    mount = commands.add_parser("probe")
    mount.add_argument("kernel")
    mount.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.command == "producer":
        data = (json.dumps(log_summary(args.log), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        args.output.write_bytes(data)
        print(sha256(data).hexdigest())
    else:
        receive_probe(args.kernel, args.output)
