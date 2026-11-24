"""Independently verify the private Phase 9 novelty pipelines and probes."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory

from kaggle_web_api import download_archive
from pyspark.ml import PipelineModel
from pyspark.sql import SparkSession
from src.ml.novelty_scoring import squared_distance
from src.streaming.model_scoring import probe


ROOT = Path(__file__).resolve().parents[1]
KERNEL = "ramcharan2345/mmds-phase-9-multiclass-open-set-classification"


def evidence(root, manifest, location):
    raw = (root / location).read_bytes()
    if sha256(raw).hexdigest() != manifest["artifacts"][location]:
        raise ValueError(f"Receipt checksum differs for {location}")
    return json.loads(raw)


def stages(root):
    manifest = json.loads((root / "manifests/phase9_experiments.json").read_text())
    c_stage = manifest["hierarchy"]["C"]
    c_model = evidence(root, c_stage, "reports/phase9_hierarchy/C/family/phase9_novelty_registry.json")
    result = {"C": (c_stage["kernel_version"], "mmds_phase9_hierarchy/family",
                    c_model["registry"], c_model["features"], c_model["reference_grid"])}
    for version, stage in manifest.get("open_set_evidence", {}).items():
        for scenario in stage["scenarios"]:
            location = f"reports/phase9_open_set_evidence/{version}/{scenario}/receipt.json"
            spec = evidence(root, stage, location)
            result[scenario] = (stage["kernel_version"], f"mmds_phase9_open_set/{scenario}",
                                spec["model"], spec["features"], spec["reference_grid"])
    return result


def fetch(version, models, destination):
    with download_archive(f"{KERNEL}/{version}", 12 * 1024 * 1024) as archive:
        for scenario, prefix, spec in models:
            for name, expected in spec["sha256"].items():
                content = archive.read(f"{prefix}/{spec['artifact']}/{name}")
                if sha256(content).hexdigest() != expected:
                    raise ValueError(f"Archived novelty pipeline differs for {scenario}")
                target = destination / scenario / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)


def verify(spark, model_dir, names, grid, spec):
    if len(grid) != 257 or any(not math.isfinite(item) for item in grid) or sorted(grid) != grid:
        raise ValueError("Invalid training-reference grid")
    metadata = [model_dir / name for name in spec["sha256"]
                if Path(name).parent.name == "metadata" and Path(name).name.startswith("part-")]
    if not metadata or any(json.loads(path.read_text())["sparkVersion"] != spark.version for path in metadata):
        raise ValueError("Archive runtime compatibility differs")
    results = []
    probes = probe(spark, names)
    for _ in range(2):
        pipeline = PipelineModel.load(str(model_dir))
        preprocessor, kmeans = PipelineModel(stages=pipeline.stages[:-1]), pipeline.stages[-1]
        active = preprocessor.stages[0].getInputCols()
        if active != [name for name in names if name in active] or len(kmeans.clusterCenters()) != 12:
            raise ValueError("Novelty preprocessing or cluster count differs")
        values = squared_distance(kmeans, preprocessor.transform(probes)).select("cluster", "score").collect()
        if any(not 0 <= row.cluster < 12 or not math.isfinite(row.score) or row.score < 0 for row in values):
            raise ValueError("Invalid synthetic novelty score")
        results.append([list(row) for row in values])
    if len(results[0]) != spec["reload_probe_rows"] or results[0] != results[1]:
        raise ValueError("Two independent novelty reloads differ")
    return results[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    models = stages(ROOT)
    by_version = {}
    for scenario, (version, prefix, spec, _, _) in models.items():
        by_version.setdefault(version, []).append((scenario, prefix, spec))
    results = {}
    with TemporaryDirectory(prefix="phase9-novelty-") as tmp:
        directory = Path(tmp)
        with ThreadPoolExecutor(max_workers=3) as pool:
            pending = [pool.submit(fetch, version, items, directory) for version, items in by_version.items()]
            for future in pending:
                future.result()
        spark = SparkSession.builder.master("local[2]").appName("phase9-novelty-reload").getOrCreate()
        try:
            if spark.version != "4.3.0":
                raise ValueError("Unexpected Spark runtime")
            for scenario, (version, prefix, spec, names, grid) in models.items():
                values = verify(spark, directory / scenario, names, grid, spec)
                results[scenario] = {"kernel_version": version, "artifact": f"{prefix}/{spec['artifact']}",
                                     "spark_version": spark.version, "synthetic_cluster_distance": values,
                                     "reloaded_probe_rows": len(values)}
        finally:
            spark.stop()
    args.output.write_text(json.dumps({"schema": "phase9-novelty-reload-v1", "models": results}, indent=2) + "\n")
    print("Verified private novelty model reloads:", ", ".join(results))


if __name__ == "__main__":
    main()
