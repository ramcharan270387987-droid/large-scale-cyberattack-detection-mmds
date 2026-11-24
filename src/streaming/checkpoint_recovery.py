"""Atomic aggregate accounting for retried Structured Streaming batch IDs."""

import json
import os


class ReplayInterruption(RuntimeError):
    pass


def commit_file(folder, batch_id):
    return folder / f"{batch_id:06}.json"


def load_commits(folder):
    return [json.loads(path.read_text()) for path in sorted(folder.glob("*.json"))]


def commit_aggregate(folder, batch_id, payload):
    folder.mkdir(parents=True, exist_ok=True)
    path = commit_file(folder, batch_id)
    if path.exists():
        stored = json.loads(path.read_text())
        if any(stored[key] != payload[key] for key in ("batch_id", "source")):
            raise ValueError("Batch ID was presented with a different source signature")
        return False
    temporary = path.with_suffix(".partial")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=1, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    descriptor = os.open(folder, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return True


def committed_ids(checkpoint):
    return sorted(int(p.name) for p in (checkpoint / "commits").iterdir() if p.name.isdecimal())
