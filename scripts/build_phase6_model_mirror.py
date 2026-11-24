"""Publish a private Notebook Output mirror of exact versioned B model files."""

import argparse
import base64
from hashlib import sha256
import json
from pathlib import Path

from build_phase2_notebook import ROOT, cell, notebook
from kaggle_web_api import download_archive


def build():
    settings = json.loads((ROOT / "configs/streaming_experiments.yaml").read_text())
    phase4 = json.loads((ROOT / "manifests/phase4_models.json").read_text())["protocols"]["B"]
    phase5 = json.loads((ROOT / "manifests/phase5_clustering_models.json").read_text())["experiments"]["B"]
    files = {"phase4": {"mmds_phase4/phase4_summary.json": None},
             "phase5": {"mmds_phase5/phase5_summary.json": None}}
    for item in phase4["models"]:
        if item["model"] in {"random_forest", "logistic_regression"} and item["training_cohort"] == "group_sample":
            base = "mmds_phase4/models/" + Path(item["path"]).name + "/"
            files["phase4"].update({base + p: digest for p, digest in item["sha256"].items()})
    files["phase5"].update({"mmds_phase5/model/" + p: digest for p, digest in phase5["model"]["sha256"].items()})
    data = {}

    for phase, paths in files.items():
        with download_archive(settings[phase], 32 * 1024 * 1024) as archive:
            for path, expected in paths.items():
                content = archive.read(path)
                digest = sha256(content).hexdigest()
                if expected and digest != expected:
                    raise ValueError(f"Incorrect versioned source file {path}")
                data[path] = (digest, base64.b64encode(content).decode("ascii"))
    code = """from base64 import b64decode
from hashlib import sha256
from pathlib import Path

"""
    code += f"files = {data!r}\n"
    code += """
root = Path("/kaggle/working")
for relative, (expected, encoded) in files.items():
    content = b64decode(encoded)
    if sha256(content).hexdigest() != expected:
        raise ValueError(f"Corrupted artifact {relative}")
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
print(f"PHASE6 mirrored {len(files)} exact artifact files from Phase 4 and Phase 5 version 2")
"""
    return notebook([cell("markdown", "overview", "# Exact chronological model mirror"),
                     cell("code", "artifacts", code)])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_text(json.dumps(build(), indent=1) + "\n")
