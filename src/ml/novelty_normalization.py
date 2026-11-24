"""Reference-only quantile normalization of squared centroid distance."""

from bisect import bisect_left


def percentile(grid, distance):
    if not grid or distance is None:
        return None
    return bisect_left(grid, distance) / len(grid)


def reference_grid(frame):
    grid = frame.approxQuantile("distance", [i / 256 for i in range(257)], 0.001)
    if len(grid) != 257:
        raise ValueError("No defined reference distance sample")
    return grid


def step_expression(value, bounds, outputs, tail):
    """Construct a balanced binary decision tree on numeric Spark columns."""
    from pyspark.sql import functions as F

    if not bounds:
        return F.lit(float(tail))
    i = len(bounds) // 2
    return F.when(value <= bounds[i], step_expression(value, bounds[:i], outputs[:i], outputs[i])).otherwise(
        step_expression(value, bounds[i+1:], outputs[i+1:], tail))


def percentile_column(column, grid):
    from pyspark.sql import functions as F

    unique = sorted(set(grid))
    return F.when(column.isNotNull(),
                  step_expression(column, unique, [percentile(grid, x) for x in unique], 1.0))


def calibrated_column(column, spec, bins):
    from pyspark.sql import functions as F

    bucket = F.least(F.floor(column * bins), F.lit(bins - 1))
    if spec["method"] == "platt":
        raw = F.lit(spec["intercept"]) + F.lit(spec["slope"]) * (bucket + .5) / bins
        return 1 / (1 + F.exp(-F.greatest(F.lit(-35.0), F.least(F.lit(35.0), raw))))
    return step_expression(bucket, spec["upper_bins"], spec["probabilities"], spec["probabilities"][-1])
