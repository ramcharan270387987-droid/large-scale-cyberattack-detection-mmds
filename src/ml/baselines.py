"""Two prespecified binary baselines using training data only."""

from pyspark.sql import functions as F


def fit_baselines(train, benign, attacks):
    if train.where("split_rank <> 0 OR split_rank IS NULL").limit(1).count():
        raise ValueError("Baseline calibration requires train rows only")
    threshold = train.where("binary_label = 0").agg(F.percentile_approx("flow_duration", 0.5, 4096)).first()[0]
    if threshold is None:
        raise ValueError("Benign reference is unavailable for duration baseline")
    return {"majority": {"attack_prediction": int(attacks > benign)}, "duration_rule": {"benign_training_median_us": threshold}}


def baseline_score(frame, name, parameters):
    if name == "majority":
        score = F.lit(float(parameters["attack_prediction"]))
    elif name == "duration_rule":
        score = F.when(F.col("flow_duration") <= parameters["benign_training_median_us"], 1.0).otherwise(0.0)
    else:
        raise ValueError(f"Unknown baseline {name}")
    return frame.withColumn("score", score)
