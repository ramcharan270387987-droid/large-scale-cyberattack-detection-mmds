"""Verify the packaged and authoritative source artifacts."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashboard.validation import verify_package

if __name__ == "__main__":
    manifest, _ = verify_package(sources=True)
    print(f"Validated {manifest['schema_version']}, {len(manifest['tables'])} tables.")
