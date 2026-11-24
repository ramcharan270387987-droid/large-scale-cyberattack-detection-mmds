"""Reference-fitted finite numerical bins for flow transactions."""
from pyspark.sql import functions as F


def fit(frame, names, bins):
    quantiles = frame.approxQuantile(names, [i / bins for i in range(1, bins)], 0.001)
    return {name: sorted(set(values)) for name, values in zip(names, quantiles)}


def transform(frame, boundaries):
    items = []
    for name, cuts in boundaries.items():
        value = F.col(name)
        index = sum((F.when(value > cut, 1).otherwise(0) for cut in cuts), F.lit(0))
        items.append(F.when(value.isNull(), F.lit(name + '=MISSING')).otherwise(
            F.concat(F.lit(name + '=BIN_'), index.cast('string'))))
    return frame.withColumn('items', F.array(*items))
