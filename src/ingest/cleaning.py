"""Phase 2 value-level diagnostics and policy transformations."""

from pyspark.sql import Window, functions as F

from src.ingest.dataset_audit import NONNEGATIVE, SENTINELS, timestamp_columns
from src.ingest.schema_contract import EXTRA_FIELDS, FEATURE_CONTEXT, TARGETS, TEXT_METADATA, record_key


def issue_rule(item):
    text, value = item["text"], item["value"]
    missing = text.isNull() | (F.trim(text) == "")
    inf = F.lower(F.trim(text)).isin(*sorted(SENTINELS)) | F.coalesce(F.abs(value) == float("inf"), F.lit(False))
    return (
        F.when(missing, "source_null")
        .when(F.isnan(value), "nan")
        .when(inf & (F.trim(text).startswith("-") | (value < 0)), "negative_infinity")
        .when(inf, "positive_infinity")
        .when(value.isNull(), "cast_failure")
        .when(F.array_contains(item["sentinels"], value), "sentinel")
        .when(item["nonnegative"] & (value < 0), "invalid_negative")
    )


def canonical_frame(frame, contract, variant, source_name, source_day, timestamp_formats):
    numeric_names = tuple(name for name in (*contract.common_values, "src_port") if name in frame.columns)
    raw_values = F.array(*[F.col(name) for name in numeric_names])
    config = contract.policy
    policies = config["numeric_actions"]
    policy_pairs = [F.lit(v) for pair in policies.items() for v in pair]
    actions = F.create_map(*policy_pairs)
    descriptors = F.array(*[
        F.struct(F.lit(name).alias("field"), F.lit(bool(NONNEGATIVE.search(name) and not name.startswith("init_"))).alias("nonnegative"),
                 F.array(*[F.lit(value).cast("double") for value in config["sentinel_values"].get(name, [])])
                 .cast("array<double>").alias("sentinels"))
        for name in numeric_names
    ])
    parsed, _, _ = timestamp_columns(F.col("timestamp"), timestamp_formats)
    base = (
        frame.where(F.col("kind") == "parsed")
        .withColumn("_text", raw_values)
        .withColumn("_numbers", F.transform("_text", lambda value: F.trim(value).try_cast("double")))
        .withColumn("_rules", descriptors)
        .withColumn("_tokens", F.zip_with(F.arrays_zip("_text", "_numbers"), "_rules",
                                         lambda x, r: F.struct(r["field"].alias("field"), x["_text"].alias("text"),
                                                              x["_numbers"].alias("value"), r["nonnegative"],
                                                              r["sentinels"])))
        .withColumn("_issues", F.transform("_tokens", lambda token: F.struct(
            token["field"], token["text"].alias("source_text"), issue_rule(token).alias("reason"),
        )))
        .withColumn("quality_issues", F.transform(F.filter("_issues", lambda item: item["reason"].isNotNull()),
                                                 lambda item: F.struct(item["field"], item["source_text"], item["reason"],
                                                                       actions[item["reason"]].alias("action"))))
        .withColumn("record_fingerprint", record_key(F.col("raw"), variant))
        .withColumn("_label", contract.label_lookup()[F.col("label")])
        .withColumn("parsed_event_time", parsed)
    )
    match = F.to_date("parsed_event_time") == F.lit(source_day).cast("date")
    status = (F.when(F.col("timestamp").isNull() | (F.trim("timestamp") == ""), "missing")
              .when(F.col("parsed_event_time").isNull(), "unparseable")
              .when(match, "matched")
              .otherwise("outside_capture_day"))
    fields = {name: F.col("_numbers")[i].alias(name) for i, name in enumerate(numeric_names)}
    for name in EXTRA_FIELDS:
        if name in TEXT_METADATA:
            fields[name] = (F.col(name) if name in frame.columns else F.lit(None).cast("string")).alias(name)
        elif name not in fields:
            fields[name] = F.lit(None).cast("double").alias(name)
    missing_fields = [name for name in EXTRA_FIELDS if name not in frame.columns]
    return base.select(
        *fields.values(),
        F.col("label").alias("original_label"), F.col("_label.normalized").alias("normalized_label"),
        F.col("_label.binary").alias("binary_label"), F.col("_label.family").alias("attack_family"),
        F.col("timestamp").alias("original_timestamp"), "parsed_event_time",
        F.lit(source_name).alias("source_file"), F.lit(source_day).alias("source_day"),
        "record_fingerprint", F.lit(variant).alias("schema_variant"),
        F.lit(config["version"]).alias("cleaning_policy_version"),
        F.lit(config["dataset_version"]).cast("int").alias("dataset_version"),
        status.alias("timestamp_parse_status"), match.alias("timestamp_capture_day_match"),
        F.coalesce(match, F.lit(False)).alias("temporal_eligibility"),
        F.array(*[F.lit(name) for name in missing_fields]).cast("array<string>").alias("structural_missing_fields"),
        "quality_issues",
    )


def clean_frame(canonical, contract):
    null_fields = F.transform(F.filter("quality_issues", lambda issue: issue["action"] == "nullify"),
                              lambda issue: issue["field"])
    base = canonical.withColumn("_null_fields", null_fields)
    numeric = {*contract.common_values, "src_port"}
    return base.select(*[
        F.when(F.array_contains("_null_fields", name), F.lit(None).cast("double"))
        .otherwise(F.col(name)).alias(name) if name in numeric else F.col(name)
        for name in canonical.columns
    ])


def feature_frame(clean, contract):
    # Hash the shared cleaned feature vector in fixed contract order, with a policy version prefix.
    values = F.array(*[F.col(name) for name in contract.feature_names])
    split_key = F.unhex(F.sha2(F.concat(F.lit(contract.policy["version"] + "\u0000"), F.to_json(values)), 256))
    with_key = clean.withColumn("split_feature_key", split_key)
    return with_key.select(*contract.feature_names, *TARGETS, *FEATURE_CONTEXT)


def exact_groups(frame):
    return (frame.groupBy("record_fingerprint")
            .agg(F.count("*").alias("multiplicity"), F.min("source_file").alias("representative_source"))
            .where(F.col("multiplicity") > 1))


def conflict_groups(frame):
    return (frame.groupBy("split_feature_key")
            .agg(F.count("*").alias("rows"), F.count_distinct("original_label").alias("label_count"))
            .where(F.col("label_count") > 1))


def apply_duplicate_policy(frame, mode):
    if mode in {"preserve_all", "diagnostic"}:
        return frame
    if mode != "exact_representative":
        raise ValueError(f"Unsupported duplicate policy: {mode}")
    # Rows tied on source_file and digest are identical visible occurrences in that source.
    window = Window.partitionBy("record_fingerprint").orderBy("source_file")
    return frame.withColumn("_representative", F.row_number().over(window)).where("_representative = 1").drop("_representative")
