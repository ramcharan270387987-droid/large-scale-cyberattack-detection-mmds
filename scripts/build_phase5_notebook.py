"""Bundle one independently staged Phase 5 experiment per Kaggle version."""

import argparse
import json
from pathlib import Path

from build_phase4_notebook import DEPENDENCIES as PHASE4
from build_phase2_notebook import ROOT, cell, notebook, producer


DEPENDENCIES = (*PHASE4, "src/ml/train_clustering.py", "src/ml/clustering_features.py",
                "src/ml/novelty_scoring.py", "src/ml/cluster_diagnostics.py", "src/ml/cluster_evolution.py",
                "src/visualization/clustering_charts.py", "configs/clustering_experiments.yaml",
                "manifests/phase4_models.json", "reports/phase4_metrics.csv")


def build(experiment):
    setup = "".join(producer(None)["cells"][1]["source"])
    setup += "\nif importlib.util.find_spec('matplotlib') is None:\n    subprocess.run([sys.executable, '-m', 'pip', 'install', 'matplotlib'], check=True)\n"
    setup += "os.environ['MPLCONFIGDIR'] = '/kaggle/temp/mmds_phase5/matplotlib'\n"
    bundle = "project = Path('/kaggle/temp/mmds_phase5/code')\n"
    bundle += "sources = " + repr({path: (ROOT / path).read_text(encoding="utf-8") for path in DEPENDENCIES})
    bundle += """
for relative, source in sources.items():
    target = project / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8")
sys.path.insert(0, str(project))
"""
    run = f"""from src.ml.train_clustering import run
run(project, Path("/kaggle/input"), Path("/kaggle/working/mmds_phase5"),
    Path("/kaggle/temp/mmds_phase5/spark"), experiment={experiment!r})
"""
    contents = notebook([
        cell("markdown", "overview", f"# MMDS Phase 5 clustering\n\nExperiment {experiment} against the verified Phase 2 output."),
        cell("code", "setup", setup), cell("code", "source", bundle), cell("code", "experiment", run),
    ])
    for item in contents["cells"]:
        if item["cell_type"] == "code":
            compile("".join(item["source"]), item["id"], "exec")
    return contents


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", choices=("G", "B", "C"), default="G")
    parser.add_argument("--output", type=Path, default=ROOT / "notebooks/phase5_clustering_evolution.ipynb")
    args = parser.parse_args()
    args.output.write_text(json.dumps(build(args.experiment), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
