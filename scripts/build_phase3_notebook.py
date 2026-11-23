"""Build the self-contained private Phase 3 Spark analytics notebook."""

import json
from pathlib import Path

from build_phase2_notebook import ROOT, cell, notebook, producer


DEPENDENCIES = (
    "src/ingest/dataset_audit.py", "src/ingest/schema_contract.py", "src/ingest/cleaning.py",
    "src/ingest/parquet_pipeline.py", "src/sql/aggregation_demo.py",
    "src/sql/traffic_analytics.py", "src/sql/temporal_analytics.py", "src/sql/attack_patterns.py",
    "src/sql/query_benchmarks.py", "src/sql/phase3_pipeline.py", "src/visualization/eda_charts.py",
    "configs/analytics.yaml", "configs/cleaning.yaml", "manifests/parquet_layers.json",
)


def build():
    setup = "".join(producer(None)["cells"][1]["source"])
    setup += "\nif importlib.util.find_spec('matplotlib') is None:\n    subprocess.run([sys.executable, '-m', 'pip', 'install', 'matplotlib'], check=True)\n"
    setup += "os.environ['MPLCONFIGDIR'] = '/kaggle/temp/mmds_phase3/matplotlib'\n"
    bundle = "project = Path('/kaggle/temp/mmds_phase3/code')\n"
    bundle += "sources = " + repr({path: (ROOT / path).read_text(encoding="utf-8") for path in DEPENDENCIES})
    bundle += """
for relative, source in sources.items():
    target = project / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8")
sys.path.insert(0, str(project))
"""
    run = """from src.sql.phase3_pipeline import run
run(project, Path("/kaggle/input"), Path("/kaggle/working/mmds_phase3"),
    Path("/kaggle/temp/mmds_phase3/spark"))
"""
    contents = notebook([
        cell("markdown", "overview", "# MMDS Phase 3 Spark SQL analytics\n\nRead the verified Phase 2 saved output and emit compact aggregate evidence."),
        cell("code", "setup", setup), cell("code", "source", bundle), cell("code", "analytics", run),
    ])
    for item in contents["cells"]:
        if item["cell_type"] == "code":
            compile("".join(item["source"]), item["id"], "exec")
    return contents


if __name__ == "__main__":
    destination = Path(ROOT / "notebooks/phase3_spark_sql_analytics.ipynb")
    destination.write_text(json.dumps(build(), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
