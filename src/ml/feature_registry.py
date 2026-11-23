"""Phase 4 predictor contract and the predictor-equivalence key."""

from pyspark.sql import functions as F


META = ("source_day", "binary_label", "attack_family", "original_label", "temporal_eligibility")
FORBIDDEN = {
    *META, "normalized_label", "dst_port", "src_port", "src_ip", "dst_ip", "flow_id",
    "source_file", "parsed_event_time", "original_timestamp", "record_fingerprint",
    "split_feature_key", "predictor_key", "schema_variant", "quality_issues", "protocol",
    "init_fwd_win_byts", "init_bwd_win_byts",
}


def registry(config, upstream):
    names = config["numerical_features"]
    if len(names) != len(set(names)) or not names or set(names) & FORBIDDEN or not set(names) <= set(upstream):
        raise ValueError("Invalid Phase 4 predictor registry")
    return list(names)


def finite(column):
    value = F.col(column).cast("double")
    return F.when(value.isNotNull() & ~F.isnan(value) & (F.abs(value) < float("inf")),
                  F.when(value == 0.0, F.lit(0.0)).otherwise(value))


def predictor_input(frame, names, version):
    """Hash the actual primary scalar vector before training-only transformations."""
    data = frame.select(*META, "record_fingerprint", "split_feature_key", *map(lambda name: finite(name).alias(name), names))
    return data.withColumn("predictor_key", F.unhex(F.sha2(
        F.concat(F.lit(version + "\u0000"), F.to_json(F.array(*names))), 256,
    )))
