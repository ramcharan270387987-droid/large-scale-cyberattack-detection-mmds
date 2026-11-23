"""Spark MLlib preprocessing with an explicit training-only fit boundary."""

from pyspark.ml import Pipeline, PipelineModel
from pyspark.ml.feature import Imputer, StandardScaler, VectorAssembler
from pyspark.sql import functions as F


def fit_preprocessing(train, names):
    if train.where("split_rank <> 0 OR split_rank IS NULL").limit(1).count():
        raise ValueError("Preprocessing requires train rows only")
    metrics = train.agg(*[
        expr.alias(f"{name}_{key}")
        for name in names for key, expr in (("min", F.min(name)), ("max", F.max(name)))
    ]).first().asDict()
    active = [name for name in names if metrics[f"{name}_min"] is not None and metrics[f"{name}_min"] != metrics[f"{name}_max"]]
    if not active:
        raise ValueError("Training population has no varying finite predictors")
    imputed = [name + "_imputed" for name in active]
    model = Pipeline(stages=[
        Imputer(strategy="median", relativeError=0.001, inputCols=active, outputCols=imputed),
        VectorAssembler(inputCols=imputed, outputCol="features", handleInvalid="error"),
    ]).fit(train)
    scaler = StandardScaler(inputCol="features", outputCol="scaled_features", withStd=True,
                            withMean=False).fit(model.transform(train))
    scaled = PipelineModel(stages=[*model.stages, scaler])
    medians = model.stages[0].surrogateDF.first().asDict()
    return model, scaled, {"active": active, "dropped_train_constant_or_empty": [name for name in names if name not in active],
                           "training_medians": medians}


def verify_vectors(assembled, active_count):
    from pyspark.ml.functions import vector_to_array

    for name in ("features", "scaled_features"):
        values = vector_to_array(name)
        invalid = (F.size(values) != active_count) | F.exists(
            values, lambda item: item.isNull() | F.isnan(item) | (F.abs(item) == float("inf")))
        if assembled.where(invalid).limit(1).count():
            raise ValueError(f"Nonfinite or invalid {name} supplied to estimators")
