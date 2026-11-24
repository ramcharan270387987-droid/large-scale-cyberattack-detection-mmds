"""Build a self-contained private Spark notebook for one Phase 8 population."""

import argparse
import json
from pathlib import Path

from build_phase2_notebook import ROOT, cell, notebook, producer
from build_phase5_notebook import DEPENDENCIES


NEW = ("phase8_baselines", "run_phase8", "hybrid_detection", "threshold_calibration", "probability_calibration",
       "cost_sensitive_training", "novelty_normalization", "score_fusion", "risk_triage",
       "phase8_evaluation", "operational_metrics", "model_registry")


def build(mode, population):
    setup = "".join(producer(None)["cells"][1]["source"])
    dependencies = [*DEPENDENCIES, "src/streaming/cluster_scoring.py", "src/streaming/model_scoring.py",
                    "configs/phase8_hybrid_experiments.yaml", "manifests/phase5_clustering_models.json",
                    "reports/phase5_novelty_metrics.csv"]
    dependencies += [f"src/ml/{name}.py" for name in NEW if (ROOT / f"src/ml/{name}.py").exists()]
    bundle = "project = Path('/kaggle/temp/mmds_phase8/code')\n"
    bundle += "sources = " + repr({path: (ROOT / path).read_text(encoding="utf-8") for path in dependencies})
    bundle += """
for relative, source in sources.items():
    target = project / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8")
sys.path.insert(0, str(project))
"""
    execute = f"""from src.ml.run_phase8 import run
run(project, Path("/kaggle/input"), Path("/kaggle/working/mmds_phase8"),
    Path("/kaggle/temp/mmds_phase8/spark"), {mode!r}, {population!r})
"""
    result = notebook([cell("markdown", "overview", f"# Phase 8 · {mode} · {population}"),
                       cell("code", "setup", setup), cell("code", "source", bundle), cell("code", "run", execute)])
    for item in result["cells"]:
        if item["cell_type"] == "code":
            compile("".join(item["source"]), item["id"], "exec")
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", choices=("baseline", "hybrid"), default="hybrid")
    p.add_argument("--population", choices=("B", "C", "R1", "R2"), default="B")
    p.add_argument("--output", type=Path, default=ROOT / "notebooks/phase8_hybrid_detection.ipynb")
    args = p.parse_args()
    args.output.write_text(json.dumps(build(args.mode, args.population), indent=1, ensure_ascii=False) + "\n")
