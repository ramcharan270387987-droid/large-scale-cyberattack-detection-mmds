"""Score with the original Phase 5 B preprocessing and frozen K-Means stages."""

import math

from pyspark.ml import PipelineModel
from pyspark.sql import functions as F

from src.ml.novelty_scoring import squared_distance
from src.streaming.model_scoring import mounted_summary, probe, verified_model


def clustering(spark, root, names, registered):
    directory, receipt = mounted_summary(root, "phase5_summary.json", "B", "experiment")
    if (receipt["features"] != names or receipt["status"] != "validated" or
            receipt["model"]["sha256"] != registered["model"]["sha256"] or
            receipt["calibration"] != registered["calibration"] or
            receipt["reference_occupancy"] != registered["reference_occupancy"]):
        raise ValueError("Mounted clustering receipt differs from Phase 5 B")
    pipeline = verified_model(spark, directory / "model", registered["model"]["sha256"], names, "_valid", "_filled")
    preparation, model = PipelineModel(stages=pipeline.stages[:-1]), pipeline.stages[-1]
    cutoff = registered["calibration"]["cutoffs"]["0.99"]
    results = cluster_scores(probe(spark, names), preparation, model, cutoff).select("cluster", "distance").collect()
    k = registered["selected_k"]
    if (len(model.clusterCenters()) != k or len(results) != 3 or
            any(not 0 <= r.cluster < k or not math.isfinite(r.distance) or r.distance < 0 for r in results)):
        raise ValueError("Invalid clustering synthetic probe")
    return (preparation, model, cutoff), {"probe_rows": len(results), "k": k, "p99": cutoff,
                                         "sha256": registered["model"]["sha256"]}


def cluster_scores(frame, preparation, model, cutoff):
    return (squared_distance(model, preparation.transform(frame))
            .select(*frame.columns, "cluster", F.col("score").alias("distance"))
            .withColumn("novel", F.col("distance") > cutoff))
