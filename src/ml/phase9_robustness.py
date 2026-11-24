"""Matched grouped-random sensitivity checks for the frozen Phase 9 protocol."""

from hashlib import sha256
from time import monotonic

from pyspark import StorageLevel
from pyspark.ml import PipelineModel
from pyspark.ml.classification import RandomForestClassifier
from pyspark.ml.functions import vector_to_array
from pyspark.sql import Window, functions as F

from src.ingest.dataset_audit import atomic_json, spark_session
from src.ingest.parquet_pipeline import driver_peak_bytes, resource_limits
from src.ml.feature_registry import predictor_input, registry
from src.ml.phase8_baselines import json_file
from src.ml.phase9_evaluation import multiclass
from src.ml.preprocessing import fit_preprocessing
from src.ml.split_protocols import assign_population, group_sample
from src.ml.train_supervised import verified_input
from src.sql.traffic_analytics import locate_producer, require, write_rows


def run(project, input_root, archive, output, scratch):
    start = monotonic()
    scratch.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    design = json_file(project, "configs/ml_experiments.yaml")
    protocol = json_file(project, "configs/phase9_multiclass_experiments.yaml")
    upstream = json_file(project, "manifests/parquet_layers.json")
    phase9 = json_file(project, "manifests/phase9_A.json")
    names = registry(design, upstream["feature_columns"])
    classes = phase9["classes"]
    spark = spark_session(design, scratch)
    spark.conf.set("spark.sql.sources.partitionColumnTypeInference.enabled", "false")
    spark.sparkContext.setLogLevel("WARN")
    try:
        require(spark.version == "4.3.0", "Unexpected Spark version")
        source = locate_producer(input_root, upstream["independent_mount"]["summary_sha256"])
        frame, receipt = verified_input(spark, source, upstream, json_file(project, "configs/cleaning.yaml"))
        assigned = assign_population(predictor_input(frame, names, design["version"]), "A", design, receipt["days"])
        labels = F.create_map(*[value for family, index in classes.items() for value in (F.lit(family), F.lit(index))])
        attacks = assigned.where("binary_label = 1").withColumn("label", labels[F.col("attack_family")].cast("double"))
        columns = [*names, "source_day", "predictor_key", "attack_family", "label", "split_rank"]
        attacks = attacks.select(*columns).persist(StorageLevel.DISK_ONLY)
        train = attacks.where("split_rank = 0")
        support = {row.attack_family: row["count"] for row in train.groupBy("attack_family").count().collect()}
        require(support == phase9["training_support"], "Grouped-random training support differs")
        hashes = {p.relative_to(archive).as_posix(): sha256(p.read_bytes()).hexdigest()
                  for p in archive.rglob("*") if p.is_file()}
        require(hashes == phase9["registry"]["sha256"], "Frozen classifier hash mismatch")
        baseline = PipelineModel.load(str(archive))
        test = attacks.where("split_rank = 2").withColumn(
            "evaluation_weight", 1 / F.count("*").over(Window.partitionBy("predictor_key"))).persist(StorageLevel.DISK_ONLY)
        rows = test.count()
        require(rows == phase9["test"]["rows"], "Grouped-random test rows differ")
        weights = {family: sum(support.values()) / (len(classes) * count) for family, count in support.items()}
        seed1, seed2 = protocol["seeds"]
        models = {"frozen_seed_23013": baseline}
        training = {}
        for seed, variants in ((seed1, ("unweighted", "inverse", "duplicate_group_weight")),
                               (seed2, ("second_seed",))):
            sampled = group_sample(train, design | {"seed": seed}).where("sampled").persist(StorageLevel.DISK_ONLY)
            fit_support = {row.attack_family: row["count"] for row in sampled.groupBy("attack_family").count().collect()}
            require(set(fit_support) == set(classes), "Sensitivity sample lacks a trained family")
            if seed == seed1:
                require(fit_support == phase9["sample_support"], "Original fitting sample differs")
            _, prep, details = fit_preprocessing(sampled, names)
            prepared = prep.transform(sampled).withColumn(
                "multiplicity", F.count("*").over(Window.partitionBy("predictor_key"))).persist(StorageLevel.DISK_ONLY)
            for variant in variants:
                adjusted = {family: (1.0 if variant == "unweighted" else value if variant == "inverse" else min(10.0, value))
                            for family, value in weights.items()}
                mapping = F.create_map(*[value for family, weight in adjusted.items() for value in (F.lit(family), F.lit(weight))])
                weight = mapping[F.col("attack_family")]
                if variant == "duplicate_group_weight":
                    weight = weight / F.col("multiplicity")
                estimator = RandomForestClassifier(featuresCol="features", numTrees=12, maxDepth=5, maxBins=24,
                                                   minInstancesPerNode=30, maxMemoryInMB=192, seed=seed, weightCol="class_weight")
                begin = monotonic()
                models[variant] = PipelineModel(stages=[*prep.stages, estimator.fit(prepared.withColumn("class_weight", weight))])
                training[variant] = {"seed": seed, "sample_support": fit_support, "fit_seconds": monotonic() - begin,
                                     "active_features": details["active"]}
            prepared.unpersist()
            sampled.unpersist()

        comparison, per_day, high_errors, all_confusion = [], [], [], []
        for variant, model in models.items():
            scored = model.transform(test).select("source_day", "label", "prediction", "evaluation_weight",
                                                   F.array_max(vector_to_array("probability")).alias("confidence"))
            grouped = scored.groupBy("source_day", "label", "prediction").agg(
                F.count("*").alias("rows"), F.sum("evaluation_weight").alias("group_weight"),
                F.count(F.when(F.col("confidence") >= 0.90, 1)).alias("high_confidence")).collect()
            for measure, value in (("flow", "rows"), ("predictor_group_equal", "group_weight")):
                counts = {}
                for row in grouped:
                    pair = (int(row.label), int(row.prediction))
                    counts[pair] = counts.get(pair, 0) + row[value]
                metrics, _ = multiclass(counts, range(len(classes)))
                comparison.append({"variant": variant, "weighting": measure, **metrics})
                all_confusion.extend({"variant": variant, "weighting": measure, "actual": actual, "predicted": pred, "count": n}
                                     for (actual, pred), n in sorted(counts.items()))
                if variant == "frozen_seed_23013" and measure == "flow":
                    require(metrics["rows"] == phase9["test"]["rows"] and
                            abs(metrics["macro_f1"] - phase9["test"]["macro_f1"]) < 1e-12 and
                            abs(metrics["accuracy"] - phase9["test"]["accuracy"]) < 1e-12,
                            "Frozen grouped-random test metrics differ")
            for day in sorted({row.source_day for row in grouped}):
                n = sum(row.rows for row in grouped if row.source_day == day)
                correct = sum(row.rows for row in grouped if row.source_day == day and row.label == row.prediction)
                per_day.append({"variant": variant, "capture_day": day, "rows": n, "correct": correct})
            high_errors.extend({"variant": variant, "capture_day": row.source_day, "class_id": int(row.label),
                                "predicted_class_id": int(row.prediction), "rows": row.high_confidence}
                               for row in grouped if row.label != row.prediction and row.high_confidence)
        write_rows(output / "phase9_sensitivity_metrics.csv", comparison)
        write_rows(output / "phase9_sensitivity_confusion.csv", all_confusion)
        write_rows(output / "phase9_sensitivity_day.csv", per_day)
        if high_errors:
            write_rows(output / "phase9_sensitivity_high_confidence_errors.csv", high_errors)
        atomic_json(output / "phase9_sensitivity_receipt.json",
                    {"status": "validated", "scenario": "A", "input": receipt, "features": names, "classes": classes,
                     "training_support": support, "matched_test_rows": rows, "training": training,
                     "high_confidence_threshold": 0.90, "resources": resource_limits(spark, design, output),
                     "driver_peak_rss_bytes": driver_peak_bytes(spark), "elapsed_seconds": monotonic() - start})
        print("PHASE9 grouped-random sensitivity complete", flush=True)
    finally:
        spark.stop()
