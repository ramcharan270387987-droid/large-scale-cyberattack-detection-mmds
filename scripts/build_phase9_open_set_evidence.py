"""Bundle verified classifiers for compact rejection evidence and novelty persistence."""

import argparse
from base64 import b64encode
from hashlib import sha256
import json
from pathlib import Path

from build_phase2_notebook import ROOT, cell
from build_phase8_notebook import build
from kaggle_web_api import download_archive


SCENARIOS = ("B", "Web", "Bot", "Infiltration", "DDoS")


def notebook(scenarios):
    payloads = {}
    sources = {}
    for scenario in scenarios:
        stage = f"manifests/phase9_{scenario}.json"
        frozen = f"reports/phase9_stages/{scenario}/phase9_rejection_frozen.json"
        sources[stage], sources[frozen] = (ROOT / stage).read_text(), (ROOT / frozen).read_text()
        manifest = json.loads(sources[stage])
        spec = manifest["registry"]
        kernel = manifest["kernel_url"].split("/code/")[1]
        with download_archive(f"{kernel}/{manifest['kernel_version']}", 2 * 1024 * 1024) as archive:
            for name, expected in spec["sha256"].items():
                content = archive.read(f"mmds_phase9/{spec['artifact']}/{name}")
                if sha256(content).hexdigest() != expected:
                    raise ValueError(f"{scenario} classifier checksum differs")
                payloads[f"{scenario}/{name}"] = (expected, b64encode(content).decode("ascii"))
    for name in ("src/ml/phase9_open_set_evidence.py", "src/ml/open_set_rejection.py"):
        sources[name] = (ROOT / name).read_text()
    source = f"""from base64 import b64decode
from hashlib import sha256
archives = Path('/kaggle/temp/phase9_open_set/archive')
for name, (expected, encoded) in {payloads!r}.items():
    content = b64decode(encoded)
    if sha256(content).hexdigest() != expected:
        raise ValueError('Archived classifier checksum differs')
    target = archives / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
for name, content in {sources!r}.items():
    target = project / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
"""
    result = build("baseline", "B")
    result["cells"][0]["source"] = ["# Phase 9 frozen rejection evidence and novelty persistence"]
    result["cells"].insert(-1, cell("code", "phase9-open-set-sources", source))
    result["cells"][-1]["source"] = [
        "from src.ml.phase9_open_set_evidence import run\n",
        "run(project, Path('/kaggle/input'), archives, Path('/kaggle/working/mmds_phase9_open_set'),\n",
        f"    Path('/kaggle/temp/phase9_open_set/spark'), {tuple(scenarios)!r})\n",
    ]
    for item in result["cells"][1:]:
        compile("".join(item["source"]), item["id"], "exec")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--scenarios", nargs="+", choices=SCENARIOS, default=SCENARIOS)
    args = parser.parse_args()
    if len(set(args.scenarios)) != len(args.scenarios):
        parser.error("Scenarios must be unique")
    args.output.write_text(json.dumps(notebook(args.scenarios), indent=1) + "\n")
