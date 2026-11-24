"""Verify pinned selected classifiers against their committed registries."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory

from kaggle_web_api import download_archive
from pyspark.ml import PipelineModel
from pyspark.ml.functions import vector_to_array
from pyspark.sql import SparkSession

from src.streaming.model_scoring import probe


ROOT = Path(__file__).resolve().parents[1]


def verified_archive(stage, scratch):
    kernel = stage["kernel_url"].split("/code/")[1]
    spec = stage["registry"]
    directory = scratch / stage["scenario"]
    with download_archive(f"{kernel}/{stage['kernel_version']}", 2 * 1024 * 1024) as archive:
        for name, expected in spec["sha256"].items():
            content = archive.read(f"mmds_phase9/{spec['artifact']}/{name}")
            if sha256(content).hexdigest() != expected:
                raise ValueError(f"{stage['scenario']} classifier checksum mismatch")
            target = directory / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
    return directory


def check(spark, stage, path):
    scenario = stage["scenario"]
    spec = stage["registry"]
    frozen = json.loads((ROOT / "reports/phase9_stages" / scenario / "phase9_frozen.json").read_text())
    if [frozen["classes"][k] for k in sorted(frozen["classes"])] != list(range(len(frozen["classes"]))):
        raise ValueError("Family IDs differ from the sorted training vocabulary")
    metadata = [path / name for name in spec["sha256"]
                if Path(name).parent.name == "metadata" and Path(name).name.startswith("part-")]
    if not metadata or any(json.loads(file.read_text())["sparkVersion"] != spark.version for file in metadata):
        raise ValueError(f"{scenario} archive Spark version differs")
    threshold_file = ROOT / "reports/phase9_stages" / scenario / "phase9_rejection_frozen.json"
    thresholds = None
    if threshold_file.is_file():
        if sha256(threshold_file.read_bytes()).hexdigest() != stage["tables_sha256"][threshold_file.name]:
            raise ValueError(f"{scenario} frozen thresholds differ")
        thresholds = json.loads(threshold_file.read_text())
    models = [PipelineModel.load(str(path)), PipelineModel.load(str(path))]
    scored = []
    active = frozen["preprocessing"]["active"]
    for model in models:
        if model.stages[0].getInputCols() != active or model.stages[1].getInputCols() != model.stages[0].getOutputCols():
            raise ValueError(f"{scenario} preprocessing differs from the frozen inputs")
        rows = model.transform(probe(spark, frozen["features"])).select("prediction", vector_to_array("probability")).collect()
        values = [(int(row[0]), list(row[1])) for row in rows]
        for index, vector in values:
            if (len(vector) != len(frozen["classes"]) or not 0 <= index < len(vector) or
                    vector[index] != max(vector) or any(not math.isfinite(p) or not 0 <= p <= 1 for p in vector)
                    or not math.isclose(sum(vector), 1.0, abs_tol=1e-10)):
                raise ValueError(f"{scenario} invalid class score vector")
        scored.append(values)
    if len(scored[0]) != spec["reload_probe_rows"] or scored[0] != scored[1]:
        raise ValueError(f"{scenario} repeated reload scores differ")
    return {"kernel_version": stage["kernel_version"], "artifact": spec["artifact"], "model": stage["model"],
            "training_support": stage["training_support"], "features": frozen["features"],
            "preprocessing": frozen["preprocessing"], "classes": frozen["classes"],
            "sha256": spec["sha256"], "bytes": spec["bytes"], "spark_version": spark.version,
            "rejection_thresholds": thresholds, "rejection_calibration": "known validation attacks" if thresholds else None,
            "unknown_policy": "evaluation-only class; reject strictly above frozen uncertainty bin" if thresholds else None,
            "identical_reload_probe_rows": len(scored[0])}


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    manifest = json.loads((ROOT / "manifests/phase9_experiments.json").read_text())
    stages = list(manifest["stages"].values())
    with TemporaryDirectory(prefix="phase9-classifiers-") as tmp:
        with ThreadPoolExecutor(max_workers=3) as pool:
            archives = list(pool.map(lambda stage: verified_archive(stage, Path(tmp)), stages))
        spark = SparkSession.builder.master("local[2]").appName("phase9-reload").getOrCreate()
        try:
            if spark.version != "4.3.0":
                raise ValueError("Unexpected Spark version")
            results = {stage["scenario"]: check(spark, stage, path) for stage, path in zip(stages, archives)}
        finally:
            spark.stop()
    args.output.write_text(json.dumps({"schema": "phase9-classifier-registry-v1", "models": results}, indent=2) + "\n")
    print("Verified archived classifier reloads:", ", ".join(results))


if __name__ == "__main__":
    main()
