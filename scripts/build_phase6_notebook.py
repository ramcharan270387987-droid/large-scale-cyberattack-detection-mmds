"""Build the pinned Phase 6 replay and model-validation notebooks."""

import argparse
import json
from pathlib import Path

from build_phase5_notebook import DEPENDENCIES as PHASE5
from build_phase2_notebook import ROOT, cell, notebook, producer


def build(mode):
    setup = "".join(producer(None)["cells"][1]["source"])
    setup += "\nif importlib.util.find_spec('matplotlib') is None:\n    subprocess.run([sys.executable, '-m', 'pip', 'install', 'matplotlib'], check=True)\n"
    dependencies = [*PHASE5, "configs/streaming_experiments.yaml", "manifests/phase5_clustering_models.json"]
    dependencies.extend(str(p.relative_to(ROOT)) for p in sorted((ROOT / "src/streaming").glob("*.py")))
    bundle = "project = Path('/kaggle/temp/mmds_phase6/code')\n"
    bundle += "sources = " + repr({p: (ROOT / p).read_text(encoding="utf-8") for p in dependencies})
    bundle += """
for relative, source in sources.items():
    target = project / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8")
sys.path.insert(0, str(project))
"""
    run = f"""from src.streaming.run_replay import run
run(project, Path("/kaggle/input"), Path("/kaggle/working/mmds_phase6"),
    Path("/kaggle/temp/mmds_phase6/replay"), mode={mode!r})
"""
    result = notebook([cell("markdown", "overview", f"# MMDS Phase 6 historical replay\n\nMode: {mode}."),
                       cell("code", "setup", setup), cell("code", "source", bundle), cell("code", "run", run)])
    for item in result["cells"]:
        if item["cell_type"] == "code":
            compile("".join(item["source"]), item["id"], "exec")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("preflight", "full"), default="full")
    parser.add_argument("--output", type=Path, default=ROOT / "notebooks/phase6_streaming_drift_monitoring.ipynb")
    args = parser.parse_args()
    args.output.write_text(json.dumps(build(args.mode), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
