"""Transparent supervised and novelty fusion over bounded scalar scores."""

from src.ml.probability_calibration import sigmoid


def weighted(supervised, novelty, alpha):
    if not 0 <= alpha <= 1:
        raise ValueError("Fusion weight is outside [0,1]")
    return alpha * supervised + (1 - alpha) * novelty


def learned(frame):
    from pyspark.ml.classification import LogisticRegression
    from pyspark.ml.feature import VectorAssembler
    from pyspark.sql import functions as F

    if frame.where(F.col("role").isNull() | (F.col("role") != "meta")).limit(1).count():
        raise ValueError("Learned fusion requires a disjoint meta-training role")
    vector = VectorAssembler(inputCols=["supervised", "novelty"], outputCol="meta_features").transform(frame)
    model = LogisticRegression(featuresCol="meta_features", labelCol="binary_label", maxIter=16, regParam=.05).fit(vector)
    return {"intercept": model.intercept, "coefficients": [float(x) for x in model.coefficients],
            "features": ["supervised", "novelty"], "reg_param": .05}


def learned_score(spec, supervised, novelty):
    return sigmoid(spec["intercept"] + spec["coefficients"][0] * supervised + spec["coefficients"][1] * novelty)
