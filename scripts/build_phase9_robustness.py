"""Bundle the grouped-random Phase 9 sensitivity run."""

import argparse
from base64 import b64encode
from hashlib import sha256
import json
from pathlib import Path

from build_phase2_notebook import ROOT, cell
from build_phase8_notebook import build
from kaggle_web_api import download_archive


def notebook():
    stage = json.loads((ROOT / "manifests/phase9_A.json").read_text())
    spec = stage["registry"]
    kernel = stage["kernel_url"].split("/code/")[1]
    payloads = {}
    with download_archive(f"{kernel}/{stage['kernel_version']}", 2 * 1024 * 1024) as archive:
        for name, expected in spec["sha256"].items():
            data = archive.read(f"mmds_phase9/{spec['artifact']}/{name}")
            if sha256(data).hexdigest() != expected:
                raise ValueError("Frozen classifier checksum differs")
            payloads[name] = (expected, b64encode(data).decode("ascii"))
    paths = ("src/ml/phase9_robustness.py", "src/ml/phase9_evaluation.py",
             "configs/phase9_multiclass_experiments.yaml", "manifests/phase9_A.json")
    sources = {name: (ROOT / name).read_text() for name in paths}
    source = f"""from base64 import b64decode
from hashlib import sha256
archive_model = Path('/kaggle/temp/phase9_sensitivity/archive')
for name, (expected, encoded) in {payloads!r}.items():
    data = b64decode(encoded)
    if sha256(data).hexdigest() != expected:
        raise ValueError('Frozen classifier checksum differs')
    target = archive_model / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
for name, content in {sources!r}.items():
    target = project / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
"""
    result = build("baseline", "B")
    result["cells"][0]["source"] = ["# Phase 9 grouped-random sensitivity"]
    result["cells"].insert(-1, cell("code", "phase9-sensitivity-source", source))
    result["cells"][-1]["source"] = [
        "from src.ml.phase9_robustness import run\n",
        "run(project, Path('/kaggle/input'), archive_model, Path('/kaggle/working/mmds_phase9_sensitivity'),\n",
        "    Path('/kaggle/temp/phase9_sensitivity/spark'))\n",
    ]
    for item in result["cells"][1:]:
        compile("".join(item["source"]), item["id"], "exec")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_text(json.dumps(notebook(), indent=1) + "\n")
