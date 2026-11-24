"""Mirror exact Phase 4/5 B and C versions through a private CPU notebook."""

import argparse
import base64
from hashlib import sha256
import json
from pathlib import Path

from build_phase2_notebook import ROOT, cell, notebook
from kaggle_web_api import download_archive


def build():
    config = json.loads((ROOT / "configs/phase8_hybrid_experiments.yaml").read_text())
    phase4 = json.loads((ROOT / "manifests/phase4_models.json").read_text())["protocols"]
    phase5 = json.loads((ROOT / "manifests/phase5_clustering_models.json").read_text())["experiments"]
    data = {}
    for protocol, version in config["versions"].items():
        paths = {"phase4": {"mmds_phase4/phase4_summary.json": None},
                 "phase5": {"mmds_phase5/phase5_summary.json": None}}
        for model in phase4[protocol]["models"]:
            if model["training_cohort"] == "group_sample":
                directory = f"mmds_phase4/models/{Path(model['path']).name}/"
                paths["phase4"].update({directory + p: h for p, h in model["sha256"].items()})
        paths["phase5"].update({"mmds_phase5/model/" + p: h for p, h in phase5[protocol]["model"]["sha256"].items()})
        for phase, entries in paths.items():
            with download_archive(f"{config[phase]}/{version}", 32 * 1024 * 1024) as archive:
                for path, expected in entries.items():
                    payload = archive.read(path)
                    digest = sha256(payload).hexdigest()
                    if expected and digest != expected:
                        raise ValueError(f"Hash mismatch in {protocol}/{path}")
                    data[f"{protocol}/{path}"] = (digest, base64.b64encode(payload).decode())
    code = """from base64 import b64decode
from hashlib import sha256
from pathlib import Path
"""
    code += f"\nfiles = {data!r}\n"
    code += """
root = Path("/kaggle/working")
for relative, (expected, encoded) in files.items():
    content = b64decode(encoded)
    if sha256(content).hexdigest() != expected:
        raise ValueError(f"Corrupted artifact {relative}")
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
print(f"PHASE8 mirrored {len(files)} verified model files and receipts")
"""
    return notebook([cell("markdown", "overview", "# Exact B and C model mirror"), cell("code", "payload", code)])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_text(json.dumps(build(), indent=1) + "\n")
