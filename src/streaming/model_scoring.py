"""Verify and score the original Phase 4 chronological supervised pipelines."""

from hashlib import sha256
import json
import math
from pathlib import Path

from pyspark.ml import PipelineModel
from pyspark.ml.functions import vector_to_array
from pyspark.sql import functions as F


SUPERVISED = ("random_forest", "logistic_regression", "duration_rule")


def mounted_summary(root, name, identity, key):
    found = [path for path in root.rglob(name) if json.loads(path.read_text()).get(key) == identity]
    if len(found) != 1:
        raise ValueError(f"Expected one mounted chronological {name}, found {len(found)}")
    return found[0].parent, json.loads(found[0].read_text())


def verified_model(spark, path, hashes, names, imputer_suffix="", output_suffix="_imputed"):
    files = {p.relative_to(path).as_posix(): sha256(p.read_bytes()).hexdigest()
             for p in path.rglob("*") if p.is_file() and not p.name.endswith(".crc")}
    if not files or files != hashes:
        raise ValueError(f"Model checksum mismatch for {path.name}")
    metadata = [path / name for name in files
                if Path(name).parent.name == "metadata" and Path(name).name.startswith("part-")]
    if not metadata or any(json.loads(item.read_text())["sparkVersion"] != spark.version for item in metadata):
        raise ValueError(f"Spark version mismatch for {path.name}")
    model = PipelineModel.load(str(path))
    imputer, assembler = next(s for s in model.stages if type(s).__name__ == "ImputerModel"), next(
        s for s in model.stages if type(s).__name__ == "VectorAssembler")
    if (imputer.getInputCols() != [n + imputer_suffix for n in names] or
            assembler.getInputCols() != imputer.getOutputCols() or
            assembler.getInputCols() != [n + output_suffix for n in names]):
        raise ValueError(f"Model predictor order mismatch for {path.name}")
    return model


def probe(spark, names):
    return spark.createDataFrame([
        tuple(None for _ in names), tuple(0.0 for _ in names), tuple(float(i + 1) for i in range(len(names))),
    ], ", ".join(name + " DOUBLE" for name in names))


def supervised(spark, root, names, registered):
    directory, receipt = mounted_summary(root, "phase4_summary.json", "B", "protocol")
    if (receipt["registered_predictors"] != names or receipt["baselines"] != registered["baselines"] or
            receipt["status"] != "validated" or receipt["input"]["receipt_sha256"] != registered["input"]["receipt_sha256"]):
        raise ValueError("Supervised artifact receipt is inconsistent")
    models, evidence = {}, {}
    for algorithm in SUPERVISED[:2]:
        entry = next(m for m in registered["models"] if m["model"] == algorithm and m["training_cohort"] == "group_sample")
        mounted = next(m for m in receipt["models"] if m["model"] == algorithm and m["training_cohort"] == "group_sample")
        if mounted["sha256"] != entry["sha256"]:
            raise ValueError(f"Mounted {algorithm} is not the pinned Phase 4 pipeline")
        name = Path(entry["path"]).name
        model = verified_model(spark, directory / "models" / name, entry["sha256"], names)
        predictions = model.transform(probe(spark, names)).select(vector_to_array("probability")[1]).collect()
        if len(predictions) != 3 or any(not math.isfinite(r[0]) or not 0 <= r[0] <= 1 for r in predictions):
            raise ValueError(f"Invalid {algorithm} synthetic probe")
        models[algorithm] = model
        evidence[algorithm] = {"directory": name, "files": len(entry["sha256"]), "probe_rows": len(predictions),
                               "sha256": entry["sha256"]}
    cutoff = registered["baselines"]["duration_rule"]["benign_training_median_us"]
    return models, cutoff, evidence


def supervised_scores(frame, models, duration_cutoff):
    for name, model in models.items():
        frame = model.transform(frame).select(*frame.columns, vector_to_array("probability")[1].alias(name))
    return frame.withColumn("duration_rule", F.when(F.col("flow_duration") <= duration_cutoff, 1.0).otherwise(0.0))
