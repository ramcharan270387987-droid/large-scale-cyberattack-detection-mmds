"""Label-free Spark feature preparation for distance-based experiments."""

from pyspark.ml import Pipeline, PipelineModel
from pyspark.ml.feature import Imputer, SQLTransformer, StandardScaler, VectorAssembler
from pyspark.ml.functions import vector_to_array
from pyspark.sql import functions as F

from src.ml.feature_registry import FORBIDDEN, registry
from src.sql.traffic_analytics import identifier, require


def clustering_registry(phase4, upstream):
    return registry(phase4, upstream)


def fit_transform(training_values, names, transform="signed_log1p"):
    if set(training_values.columns) != set(names) or set(names) & FORBIDDEN:
        raise ValueError("Reference fit takes approved predictor columns only")
    if transform not in {"signed_log1p", "linear"}:
        raise ValueError("Unknown clustering transform")
    clean = []
    for name in names:
        x = identifier(name)
        value = (f"CASE WHEN {x} IS NOT NULL AND NOT isnan({x}) "
                 f"AND abs({x}) < CAST('Infinity' AS DOUBLE) THEN {x} END")
        numerical = f"signum({value}) * log1p(abs({value}))" if transform == "signed_log1p" else value
        clean.append(f"{numerical} AS {x}_valid")
    sanitizer = SQLTransformer(statement="SELECT *, " + ", ".join(clean) + " FROM __THIS__")
    finite = sanitizer.transform(training_values)
    extrema = finite.agg(*[
        expr.alias(f"{name}_{part}") for name in names
        for part, expr in (("min", F.min(f"{name}_valid")), ("max", F.max(f"{name}_valid")),
                           ("null", F.count(F.when(F.col(f"{name}_valid").isNull(), 1))))
    ]).first().asDict()
    active = [x for x in names if extrema[x + "_min"] is not None and extrema[x + "_min"] != extrema[x + "_max"]]
    if not active:
        raise ValueError("Reference population has no varying predictors")
    assembled = Pipeline(stages=[
        sanitizer, Imputer(inputCols=[x + "_valid" for x in active], outputCols=[x + "_filled" for x in active],
                           strategy="median", relativeError=0.001),
        VectorAssembler(inputCols=[x + "_filled" for x in active], outputCol="unscaled", handleInvalid="error"),
    ]).fit(training_values)
    scaler = StandardScaler(inputCol="unscaled", outputCol="features", withStd=True, withMean=True).fit(
        assembled.transform(training_values))
    stats = {name: {"invalid_or_null": extrema[name + "_null"], "available": name in active} for name in names}
    for i, name in enumerate(active):
        stats[name]["reference_std"] = float(scaler.std[i])
        stats[name]["near_constant"] = float(scaler.std[i]) < 1e-8
    return PipelineModel(stages=[*assembled.stages, scaler]), {
        "transform": transform, "fit_columns": list(names), "active": active,
        "dropped": [name for name in names if name not in active], "reference_stats": stats,
        "imputation_surrogates": assembled.stages[1].surrogateDF.first().asDict(),
        "reference_means": [float(x) for x in scaler.mean], "reference_scales": [float(x) for x in scaler.std],
    }


def verify_finite_vectors(data, size):
    values = vector_to_array("features")
    bad = (F.size(values) != size) | F.exists(values, lambda x: F.isnan(x) | (F.abs(x) == float("inf")) | x.isNull())
    require(data.where(bad).limit(1).count() == 0, "Nonfinite clustering vector")
