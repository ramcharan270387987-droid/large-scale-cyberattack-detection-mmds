"""Re-score pinned family classifiers and persist the missing novelty pipelines."""

from hashlib import sha256
from time import monotonic

from pyspark import StorageLevel
from pyspark.ml import PipelineModel
from pyspark.ml.clustering import KMeans
from pyspark.ml.functions import vector_to_array
from pyspark.sql import functions as F

from src.ingest.dataset_audit import atomic_json, spark_session
from src.ingest.parquet_pipeline import driver_peak_bytes, resource_limits
from src.ml.feature_registry import predictor_input, registry
from src.ml.model_registry import capture
from src.ml.novelty_normalization import percentile_column, reference_grid
from src.ml.novelty_scoring import squared_distance
from src.ml.open_set_rejection import cutoff
from src.ml.phase8_baselines import json_file, retain
from src.ml.split_protocols import assign_population, group_sample
from src.ml.train_supervised import verified_input
from src.sql.traffic_analytics import locate_producer, require, write_rows
from src.streaming.model_scoring import probe


METHODS = ("maximum", "margin", "entropy", "novelty", "combined")
HOLDOUTS = {"Web": "Web attack", "Bot": "Bot", "Infiltration": "Infiltration", "DDoS": "DDoS"}
BINS = 2048


def population(frame, scenario, design, days):
    withheld = HOLDOUTS.get(scenario)
    assigned = assign_population(frame, "A" if withheld else scenario, design, days)
    if withheld:
        excluded = assigned.where(F.col("attack_family") == withheld).select("predictor_key").distinct()
        known = assigned.where(F.col("attack_family") != withheld).join(excluded, "predictor_key", "left_anti")
        unknown = assigned.where(F.col("attack_family") == withheld).withColumn("split_rank", F.lit(2))
        assigned = known.unionByName(unknown)
    return retain(assigned)


def scenario_evidence(spark, project, data, scenario, design, names, source, archive, output):
    start = monotonic()
    output.mkdir(parents=True, exist_ok=True)
    receipt = json_file(project, f"manifests/phase9_{scenario}.json")
    stage = project / "reports/phase9_stages" / scenario
    frozen = json_file(stage, "phase9_rejection_frozen.json")
    classes = receipt["classes"]
    active, overlap = population(data, scenario, design, source["days"])
    labels = F.create_map(*[value for family, index in classes.items() for value in (F.lit(family), F.lit(index))])
    attacks = active.where("binary_label = 1").withColumn("label", labels[F.col("attack_family")].cast("double"))
    training = attacks.where("split_rank = 0")
    sample = group_sample(training, design).where("sampled").persist(StorageLevel.DISK_ONLY)
    validation = attacks.where("split_rank = 1 AND label IS NOT NULL")
    test = attacks.where("split_rank = 2")
    try:
        support = {r.attack_family: r["count"] for r in training.groupBy("attack_family").count().collect()}
        sample_support = {r.attack_family: r["count"] for r in sample.groupBy("attack_family").count().collect()}
        require((support, sample_support, overlap) ==
                (receipt["training_support"], receipt["sample_support"], receipt["overlap"]), "Phase 9 cohort differs")
        hashes = {p.relative_to(archive).as_posix(): sha256(p.read_bytes()).hexdigest()
                  for p in archive.rglob("*") if p.is_file()}
        require(hashes == receipt["registry"]["sha256"], "Archived classifier differs")
        family = PipelineModel.load(str(archive))
        prep = PipelineModel(stages=family.stages[:-1])
        prepared = prep.transform(sample).select("features").persist(StorageLevel.DISK_ONLY)
        try:
            cluster = KMeans(k=12, seed=23013, maxIter=12, featuresCol="features", predictionCol="cluster").fit(prepared)
            grid = reference_grid(squared_distance(cluster, prepared).select(F.col("score").alias("distance")))
        finally:
            prepared.unpersist()

        def scored(frame):
            predictions = family.transform(frame).withColumn("scores", vector_to_array("probability"))
            ordered = F.reverse(F.array_sort("scores"))
            entropy = -F.aggregate(F.col("scores"), F.lit(0.0), lambda acc, x:
                                   acc + F.when(x > 0, x * F.log(x)).otherwise(0.0)) / F.log(F.lit(float(len(classes))))
            predictions = squared_distance(cluster, predictions).withColumn("novelty", percentile_column(F.col("score"), grid))
            scores = {"maximum": 1 - ordered[0], "margin": 1 - (ordered[0] - ordered[1]), "entropy": entropy,
                      "novelty": F.col("novelty"), "combined": F.greatest(F.col("novelty"), 1 - ordered[0])}
            return predictions.select("source_day", "attack_family", "label", "prediction",
                                      (F.col("label").isNotNull()).alias("known"),
                                      F.coalesce(F.col("label") == F.col("prediction"), F.lit(False)).alias("correct"),
                                      *[F.floor(scores[method] * BINS).alias(method) for method in METHODS])

        def unpivot(frame, keys):
            values = [F.struct(F.lit(name).alias("method"), F.col(name).alias("bin")) for name in METHODS]
            return frame.select(*keys, F.explode(F.array(*values)).alias("score")).select(*keys, "score.*")

        hist = {method: {} for method in METHODS}
        for row in unpivot(scored(validation), []).groupBy("method", "bin").count().collect():
            hist[row.method][row.bin] = row["count"]
        budgets = (0.01, 0.05, 0.1)
        new = {name: {str(budget): cutoff(hist[name], budget) for budget in budgets} for name in METHODS}
        require(all(new[name] == frozen[name] for name in ("maximum", "margin", "entropy")),
                "Archived classifier did not reproduce frozen confidence thresholds")
        atomic_json(output / "thresholds.json", {"original": frozen, "reproduction": new})
        scored_test = scored(test).persist(StorageLevel.DISK_ONLY)
        try:
            counts = unpivot(scored_test, ["known", "correct"]).groupBy("method", "bin", "known", "correct").count()
            write_rows(output / "score_histograms.csv", [r.asDict() for r in counts.collect()])
            point = [(method, int(new[method]["0.05"])) for method in METHODS]
            threshold_map = F.create_map(*[value for method, value in point
                                         for value in (F.lit(method), F.lit(value))])
            decided = unpivot(scored_test, ["source_day", "attack_family", "known", "correct", "prediction"]).withColumn(
                "rejected", F.col("bin") > threshold_map[F.col("method")])
            by_day = decided.groupBy("source_day", "method", "known", "correct", "rejected").count().collect()
            write_rows(output / "day_rejection.csv", [r.asDict() for r in by_day])
            examples = (decided.where("method = 'maximum' AND ((NOT known AND NOT rejected) OR (known AND rejected))")
                        .groupBy("source_day", "attack_family", "known", "rejected", "prediction").count().collect())
            if examples:
                write_rows(output / "rejection_error_groups.csv", [r.asDict() for r in examples])
            support_rows = scored_test.groupBy("known").count().collect()
        finally:
            scored_test.unpersist()

        # Descriptive comparisons on raw finite registered predictors.
        features = ("flow_duration", "pkt_len_mean", "flow_iat_mean", "tot_fwd_pkts")
        comparisons = attacks.withColumn("known", F.col("label").isNotNull()).groupBy(
            "split_rank", "source_day", "known").agg(F.count("*").alias("rows"),
            *[F.percentile_approx(F.col(name), [0.1, 0.5, 0.9], 1024).alias(name) for name in features]).collect()
        write_rows(output / "capture_feature_quantiles.csv", [r.asDict() for r in comparisons])
        model = capture(PipelineModel(stages=[*prep.stages, cluster]), "family_kmeans", output, probe(spark, names), kmeans=True)
        atomic_json(output / "receipt.json",
                    {"status": "validated", "scenario": scenario, "classifier_version": receipt["kernel_version"],
                     "classes": classes, "features": names, "training_support": support, "sample_support": sample_support,
                     "support": {str(r.known).lower(): r["count"] for r in support_rows}, "reference_grid": grid,
                     "original_novelty_thresholds_reproduced": {name: new[name] == frozen[name] for name in ("novelty", "combined")},
                     "model": model, "spark_version": spark.version, "elapsed_seconds": monotonic() - start})
        print(f"PHASE9 open-set evidence {scenario} complete", flush=True)
    finally:
        sample.unpersist()
        active.unpersist()


def run(project, input_root, archives, output, scratch, scenarios):
    start = monotonic()
    scratch.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    design = json_file(project, "configs/ml_experiments.yaml")
    upstream = json_file(project, "manifests/parquet_layers.json")
    names = registry(design, upstream["feature_columns"])
    spark = spark_session(design, scratch)
    spark.conf.set("spark.sql.sources.partitionColumnTypeInference.enabled", "false")
    spark.sparkContext.setLogLevel("WARN")
    try:
        require(spark.version == "4.3.0", "Unexpected Spark version")
        producer = locate_producer(input_root, upstream["independent_mount"]["summary_sha256"])
        raw, source = verified_input(spark, producer, upstream, json_file(project, "configs/cleaning.yaml"))
        # Retention must also consider predictor groups containing benign flows.
        data = predictor_input(raw, names, design["version"]).persist(StorageLevel.DISK_ONLY)
        data.count()
        for scenario in scenarios:
            scenario_evidence(spark, project, data, scenario, design, names, source, archives / scenario, output / scenario)
        atomic_json(output / "receipt.json", {"status": "validated", "scenarios": scenarios, "input": source,
                                             "resources": resource_limits(spark, design, output),
                                             "driver_peak_rss_bytes": driver_peak_bytes(spark),
                                             "elapsed_seconds": monotonic() - start})
        print("PHASE9 open-set evidence complete", flush=True)
    finally:
        spark.stop()
