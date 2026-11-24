"""Rescore the exact Phase 9 B population with frozen archived binary gates."""

from hashlib import sha256
from pathlib import Path
from time import monotonic

from pyspark import StorageLevel
from pyspark.ml import PipelineModel
from pyspark.ml.functions import vector_to_array
from pyspark.sql import functions as F

from src.ingest.dataset_audit import atomic_json, spark_session
from src.ingest.parquet_pipeline import driver_peak_bytes, resource_limits
from src.ml.feature_registry import predictor_input, registry
from src.ml.hybrid_detection import encode_columns, fusion_columns, model_score
from src.ml.phase8_baselines import benchmark_population, json_file
from src.ml.phase8_evaluation import bucket
from src.ml.phase9_label_registry import vocabulary
from src.ml.train_supervised import verified_input
from src.sql.traffic_analytics import locate_producer, require, write_rows
from src.streaming.model_scoring import verified_model


def run(project, input_root, archives, output, scratch):
    """Score the retained B test traffic, including benign rows and missed attacks."""
    start = monotonic()
    output.mkdir(parents=True, exist_ok=True)
    scratch.mkdir(parents=True, exist_ok=True)
    design = json_file(project, "configs/ml_experiments.yaml")
    config = json_file(project, "configs/phase8_hybrid_experiments.yaml")
    parquet = json_file(project, "manifests/parquet_layers.json")
    phase4 = json_file(project, "manifests/phase4_models.json")
    phase5 = json_file(project, "manifests/phase5_clustering_models.json")["experiments"]["B"]
    phase8 = json_file(project, "manifests/phase8_models.json")["populations"]["B"]
    phase9 = json_file(project, "manifests/phase9_B.json")
    names = registry(design, parquet["feature_columns"])
    spark = spark_session(config, scratch)
    spark.conf.set("spark.sql.sources.partitionColumnTypeInference.enabled", "false")
    spark.sparkContext.setLogLevel("WARN")
    try:
        require(spark.version == "4.3.0", "Unexpected Spark version")
        producer = locate_producer(input_root, parquet["independent_mount"]["summary_sha256"])
        data, source = verified_input(spark, producer, parquet, json_file(project, "configs/cleaning.yaml"))
        active, split = benchmark_population(predictor_input(data, names, design["version"]), "B",
                                            design, source["days"], phase4, output)
        support = {r.attack_family: r["count"] for r in active.where("split_rank = 0 AND binary_label = 1")
                   .groupBy("attack_family").count().collect()}
        classes = vocabulary(support)
        require(support == phase9["training_support"] and classes == phase9["classes"], "Family training support differs")
        require(names == phase8["feature_order"], "Binary gate feature order differs")
        base = phase8["base"]
        winner = phase8["selected_hybrid"]
        bins = phase8["bins"]
        rf_meta = next(m for m in phase4["protocols"]["B"]["models"]
                       if m["model"] == "random_forest" and m["training_cohort"] == "group_sample")
        rf = verified_model(spark, archives / "rf", rf_meta["sha256"], names)
        supervised = verified_model(spark, archives / "supervised", phase8["saved_pipelines"][base]["sha256"], names)
        cluster = verified_model(spark, archives / "cluster", phase5["model"]["sha256"], names, "_valid", "_filled")
        km = (PipelineModel(stages=cluster.stages[:-1]), cluster.stages[-1], phase5["calibration"]["cutoffs"]["0.99"])
        family = PipelineModel.load(str(archives / "family"))
        frozen = json_file(project, "reports/phase9_stages/B/phase9_frozen.json")
        thresholds = json_file(project, "reports/phase9_stages/B/phase9_rejection_frozen.json")
        require(frozen["features"] == names and frozen["classes"] == classes and
                frozen["model"] == phase9["model"] and family.stages[-1].numClasses == len(classes),
                "Family model feature or class contract differs")
        require(family.stages[0].getInputCols() == names, "Family imputation order differs")
        actual_hashes = {p.relative_to(archives / "family").as_posix(): sha256(p.read_bytes()).hexdigest()
                         for p in (archives / "family").rglob("*") if p.is_file()}
        require(actual_hashes == phase9["registry"]["sha256"], "Family model checksum differs")

        test = active.where("split_rank = 2")
        scored = model_score(test, rf, "phase4_rf")
        scored = fusion_columns(encode_columns(scored, {base: supervised}, km, phase8["reference_grid"], base,
                                               phase8["calibration"], bins), config, phase8["gates"], phase8["learned"])
        scored = family.transform(scored).select("source_day", "binary_label", "attack_family", "prediction",
                                                vector_to_array("probability").alias("family_scores"),
                                                "phase4_rf", "supervised", winner)
        ordered = F.reverse(F.array_sort("family_scores"))
        known = F.col("attack_family").isin(list(classes))
        labels = F.array(*[F.lit(name) for name in classes])
        predicted = F.element_at(labels, F.col("prediction").cast("int") + 1)
        uncertainty = 1 - ordered[0]
        rejected = F.floor(uncertainty * 2048) > thresholds["maximum"]["0.05"]
        attack = F.col("binary_label") == 1
        gated = scored.select("source_day", "binary_label", "attack_family", known.alias("known"),
                              predicted.alias("family_prediction"), rejected.alias("rejected"),
                              (F.col("phase4_rf") >= design["threshold"]).alias("phase4_rf"),
                              (bucket(F.col("supervised"), bins) >= phase8["operating_bins"]["supervised"]).alias("phase8_supervised"),
                              (bucket(F.col(winner), bins) >= phase8["operating_bins"][winner]).alias("phase8_hybrid"),
                              attack.alias("oracle")).persist(StorageLevel.DISK_ONLY)
        counts = []
        for name in ("phase4_rf", "phase8_supervised", "phase8_hybrid", "oracle"):
            gate = F.col(name)
            outcome = (F.when(~attack & ~gate, "correct_benign").when(~attack, "benign_false_alarm")
                       .when(~gate, "missed_attack").when(F.col("known") & F.col("rejected"), "known_rejected")
                       .when(F.col("known") & (F.col("attack_family") == F.col("family_prediction")), "known_correct")
                       .when(F.col("known"), "known_incorrect").when(F.col("rejected"), "unknown_rejected")
                       .otherwise("unknown_false_accept"))
            decision = F.when(~gate, "Benign").when(F.col("rejected"), "UNKNOWN").otherwise(F.col("family_prediction"))
            rows = gated.select("source_day", "binary_label", "attack_family", outcome.alias("outcome"),
                                decision.alias("decision")).groupBy("source_day", "binary_label", "attack_family",
                                                                    "outcome", "decision").count().collect()
            counts.extend({"gate": name, **row.asDict()} for row in rows)
        write_rows(output / "phase9_hierarchical_counts.csv", counts)
        expected = test.count()
        totals = {name: sum(r["count"] for r in counts if r["gate"] == name)
                  for name in ("phase4_rf", "phase8_supervised", "phase8_hybrid", "oracle")}
        require(set(totals.values()) == {expected}, "Hierarchical rows do not reconcile")
        require(not any(r["binary_label"] and r["attack_family"] in classes for r in counts),
                "Chronological B unexpectedly contains known attacks")
        atomic_json(output / "phase9_hierarchical_receipt.json",
                    {"status": "validated", "population": "B", "input": source, "split": split,
                     "classes": classes, "features": names, "gate_rows": totals,
                     "rejection_method": "maximum", "rejection_budget": 0.05,
                     "rejection_bin": thresholds["maximum"]["0.05"],
                     "resources": resource_limits(spark, config, output),
                     "driver_peak_rss_bytes": driver_peak_bytes(spark), "elapsed_seconds": monotonic() - start})
        print("PHASE9 hierarchical B complete", flush=True)
    finally:
        spark.stop()
