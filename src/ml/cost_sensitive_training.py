"""Fit bounded weighted Spark classifiers on a common grouped training sample."""

from time import monotonic

from pyspark.ml import PipelineModel
from pyspark.ml.classification import GBTClassifier, LogisticRegression, RandomForestClassifier
from pyspark.sql import functions as F

from src.ingest.parquet_pipeline import driver_peak_bytes
from src.ml.preprocessing import fit_preprocessing


def weights(training_support, grid):
    negative, positive = (training_support.get(i, 0) for i in (0, 1))
    if not min(negative, positive):
        raise ValueError("Weights require both classes in the training population")
    return {str(key): negative/positive if key == "inverse" else float(key) for key in grid}


def preprocess(sample, names):
    _, scaled, details = fit_preprocessing(sample, names)
    return scaled, details


def fit_candidate(sample, algorithm, weight, seed):
    common = {"labelCol": "binary_label", "weightCol": "class_weight"}
    if algorithm == "lr":
        estimator = LogisticRegression(featuresCol="scaled_features", maxIter=12, regParam=.05, standardization=False, **common)
    elif algorithm == "rf":
        estimator = RandomForestClassifier(featuresCol="features", seed=seed, numTrees=12, maxDepth=5,
                                           maxBins=24, minInstancesPerNode=30, maxMemoryInMB=192, **common)
    elif algorithm == "gbt":
        estimator = GBTClassifier(featuresCol="features", seed=seed, maxIter=6, maxDepth=3,
                                  maxBins=24, minInstancesPerNode=30, maxMemoryInMB=192, **common)
    else:
        raise ValueError(f"Unknown algorithm {algorithm}")
    if not estimator.hasParam("weightCol"):
        raise ValueError(f"Spark {algorithm} does not support weights")
    weighted = sample.withColumn("class_weight", F.when(F.col("binary_label") == 1, weight).otherwise(1.0))
    start = monotonic()
    fitted = estimator.fit(weighted)
    return fitted, {"fit_seconds": round(monotonic()-start, 3), "peak_jvm_rss_bytes": driver_peak_bytes(sample.sparkSession)}


def with_preprocessor(prep, fitted):
    return PipelineModel(stages=[*prep.stages, fitted])
