"""Deterministic disjoint predictor cohorts and ordered capture-day policies."""

from pyspark.sql import functions as F


SPLITS = ("train", "validation", "test")


def check_days(protocol, design, days):
    selected = [day for name in SPLITS for day in design[name]]
    if len(set(selected)) != len(selected) or set(selected) != set(days) or any(not design[name] for name in SPLITS):
        raise ValueError("Capture days must map exactly once to a nonempty partition")
    if protocol == "B" and not (max(design["train"]) < min(design["validation"])
                                and max(design["validation"]) < min(design["test"])):
        raise ValueError("Chronological holdout must be strictly ordered")


def assign_population(frame, protocol, config, days):
    if protocol == "A":
        ratios = config["random_permyriad"]
        if sum(ratios.values()) != 10000 or any(ratios[name] <= 0 for name in SPLITS):
            raise ValueError("Invalid random split proportions")
        index = F.pmod(F.xxhash64(F.lit(config["seed"]), "predictor_key"), F.lit(10000))
        return frame.withColumn("split_rank", F.when(index < ratios["train"], 0)
                                .when(index < ratios["train"] + ratios["validation"], 1).otherwise(2))
    if protocol not in ("B", "C"):
        raise ValueError(f"Unknown protocol {protocol}")
    design = config["protocols"][protocol]
    check_days(protocol, design, days)
    pairs = [value for rank, name in enumerate(SPLITS) for day in design[name] for value in (F.lit(day), F.lit(rank))]
    return frame.withColumn("split_rank", F.create_map(*pairs)[F.col("source_day")])


def crossing_groups(frame, key):
    return (frame.groupBy(key).agg(F.min("split_rank").alias("first_rank"), F.max("split_rank").alias("last_rank"),
                                   F.count("*").alias("occurrences"))
            .where("first_rank <> last_rank"))


def mark_retention(assigned, crossing, count):
    groups = crossing.select("predictor_key", "first_rank")
    # Bound executor replication and use Spark's normal join above the cap.
    groups = F.broadcast(groups) if count <= 400000 else groups
    return (assigned.join(groups, "predictor_key", "left")
            .withColumn("retained", F.col("first_rank").isNull() | (F.col("first_rank") == F.col("split_rank")))
            .drop("first_rank"))


def group_sample(frame, config):
    fraction = config["group_sample_permyriad"]
    if not 0 < fraction <= 10000:
        raise ValueError("Invalid grouped sampling fraction")
    return frame.withColumn("sampled", F.pmod(F.xxhash64(F.lit(config["seed"]), F.lit("training-sample"), "predictor_key"),
                                             F.lit(10000)) < fraction)


def group_summary(groups):
    row = groups.agg(F.count("*").alias("groups"), F.coalesce(F.sum("occurrences"), F.lit(0)).alias("rows")).first()
    return row.asDict()


def label_conflicts(frame):
    return (frame.groupBy("predictor_key")
            .agg(F.min("binary_label").alias("low"), F.max("binary_label").alias("high"),
                 F.count("*").alias("occurrences"))
            .where("low <> high"))
