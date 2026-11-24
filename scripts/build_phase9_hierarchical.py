"""Bundle the exact archived models for the B or C hierarchy."""
import argparse
from base64 import b64encode
from hashlib import sha256
import json
from pathlib import Path

from build_phase2_notebook import ROOT, cell
from build_phase8_notebook import build
from kaggle_web_api import download_archive


def read_json(name):
    return json.loads((ROOT / name).read_text())


def notebook(population):
    phase4 = read_json("manifests/phase4_models.json")
    phase5 = read_json("manifests/phase5_clustering_models.json")
    phase8 = read_json("manifests/phase8_models.json")
    phase9 = read_json("manifests/phase9_B.json")
    config = read_json("configs/phase8_hybrid_experiments.yaml")
    rf = next(m for m in phase4["protocols"][population]["models"]
              if m["model"] == "random_forest" and m["training_cohort"] == "group_sample")
    hybrid = phase8["populations"][population]
    supervised = hybrid["saved_pipelines"][hybrid["base"]]
    version = config["versions"][population]
    inputs = [
        ("rf", f"{config['phase4']}/{version}", f"mmds_phase4/models/{Path(rf['path']).name}", rf["sha256"]),
        ("cluster", f"{config['phase5']}/{version}", "mmds_phase5/model", phase5["experiments"][population]["model"]["sha256"]),
        ("supervised", f"{phase8['kernel_url'].split('/code/')[1]}/{hybrid['kernel_version']}",
         f"mmds_phase8/{supervised['artifact']}", supervised["sha256"]),
    ]
    if population == "B":
        inputs.append(("family", f"{phase9['kernel_url'].split('/code/')[1]}/{phase9['kernel_version']}",
                       f"mmds_phase9/{phase9['registry']['artifact']}", phase9["registry"]["sha256"]))
    payloads = {}
    for name, reference, directory, hashes in inputs:
        with download_archive(reference, 32 * 1024 * 1024) as archive:
            for file, expected in hashes.items():
                data = archive.read(f"{directory}/{file}")
                if sha256(data).hexdigest() != expected:
                    raise ValueError(f"Archived {name} model checksum differs")
                payloads[f"{name}/{file}"] = (expected, b64encode(data).decode("ascii"))
    result = build("baseline", population)
    result["cells"][0]["source"] = [f"# Phase 9 hierarchy · population {population}"]
    paths = ("src/ml/phase9_hierarchical.py", "src/ml/phase9_label_registry.py", "manifests/phase8_models.json",
             "manifests/phase9_B.json", "reports/phase9_stages/B/phase9_frozen.json",
             "reports/phase9_stages/B/phase9_rejection_frozen.json")
    if population == "C":
        paths += ("src/ml/train_multiclass.py", "src/ml/phase9_evaluation.py", "src/ml/open_set_rejection.py")
    sources = {name: (ROOT / name).read_text() for name in paths}
    source = f"""from base64 import b64decode
from hashlib import sha256
archives = Path('/kaggle/temp/phase9_hierarchy/archives')
for path, (expected, encoded) in {payloads!r}.items():
    content = b64decode(encoded)
    if sha256(content).hexdigest() != expected:
        raise ValueError('Archived model checksum differs')
    target = archives / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
for path, value in {sources!r}.items():
    target = project / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(value)
"""
    result["cells"].insert(-1, cell("code", "phase9-archives", source))
    result["cells"][-1]["source"] = [
        "from src.ml.phase9_hierarchical import run\n",
        "run(project, Path('/kaggle/input'), archives, Path('/kaggle/working/mmds_phase9_hierarchy'),\n",
        "    Path('/kaggle/temp/phase9_hierarchy/spark'))\n",
    ]
    if population == "C":
        result["cells"][-1]["source"] = [
            "from src.ml.phase9_hierarchical import run_c\n",
            "run_c(project, Path('/kaggle/input'), archives, Path('/kaggle/working/mmds_phase9_hierarchy'))\n",
        ]
    for item in result["cells"][1:]:
        compile("".join(item["source"]), item["id"], "exec")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--population", choices=("B", "C"), default="B")
    args = parser.parse_args()
    args.output.write_text(json.dumps(notebook(args.population), indent=1) + "\n")
