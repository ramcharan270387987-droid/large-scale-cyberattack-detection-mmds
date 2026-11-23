"""Bundle one independently reproducible Phase 4 protocol per Kaggle version."""

import argparse
import json
from pathlib import Path

from build_phase2_notebook import ROOT, cell, notebook, producer


DEPENDENCIES = (
    "src/ingest/dataset_audit.py", "src/ingest/schema_contract.py", "src/ingest/cleaning.py",
    "src/ingest/parquet_pipeline.py", "src/sql/aggregation_demo.py", "src/sql/traffic_analytics.py",
    "src/ml/feature_registry.py", "src/ml/split_protocols.py", "src/ml/preprocessing.py",
    "src/ml/baselines.py", "src/ml/evaluate_supervised.py", "src/ml/model_explanations.py",
    "src/ml/train_supervised.py", "configs/cleaning.yaml", "configs/ml_experiments.yaml", "manifests/parquet_layers.json",
)


def build(protocol):
    setup = "".join(producer(None)["cells"][1]["source"])
    bundle = "project = Path('/kaggle/temp/mmds_phase4/code')\n"
    bundle += "sources = " + repr({path: (ROOT / path).read_text(encoding="utf-8") for path in DEPENDENCIES})
    bundle += """
for relative, source in sources.items():
    target = project / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8")
sys.path.insert(0, str(project))
"""
    run = f"""from src.ml.train_supervised import run
run(project, Path("/kaggle/input"), Path("/kaggle/working/mmds_phase4"),
    Path("/kaggle/temp/mmds_phase4/spark"), protocol={protocol!r})
"""
    contents = notebook([
        cell("markdown", "overview", f"# MMDS Phase 4 supervised evaluation\n\nProtocol {protocol}, fitted on the verified Phase 2 output."),
        cell("code", "setup", setup), cell("code", "source", bundle), cell("code", "protocol", run),
    ])
    for item in contents["cells"]:
        if item["cell_type"] == "code":
            compile("".join(item["source"]), item["id"], "exec")
    return contents


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", choices=("A", "B", "C"), default="A")
    parser.add_argument("--output", type=Path, default=ROOT / "notebooks/phase4_supervised_detection.ipynb")
    args = parser.parse_args()
    args.output.write_text(json.dumps(build(args.protocol), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
