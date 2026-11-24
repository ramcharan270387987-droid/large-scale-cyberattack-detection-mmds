"""Run a bounded phase 8 stage against the verified Phase 2 snapshot."""

from time import monotonic

from src.ingest.dataset_audit import atomic_json, spark_session
from src.ingest.parquet_pipeline import driver_peak_bytes, resource_limits
from src.ml.feature_registry import predictor_input, registry
from src.ml.phase8_baselines import benchmark_population, json_file, load_models, reconcile
from src.ml.train_supervised import verified_input
from src.sql.traffic_analytics import locate_producer, require


def run(project, input_root, output, scratch, mode, population):
    start = monotonic()
    output.mkdir(parents=True, exist_ok=True)
    scratch.mkdir(parents=True, exist_ok=True)
    config = json_file(project, "configs/phase8_hybrid_experiments.yaml")
    design = json_file(project, "configs/ml_experiments.yaml")
    parquet = json_file(project, "manifests/parquet_layers.json")
    phase4 = json_file(project, "manifests/phase4_models.json")
    phase5 = json_file(project, "manifests/phase5_clustering_models.json")
    policy = json_file(project, "configs/cleaning.yaml")
    summary = {"status": "running", "stage": mode, "population": population, "protocol": config["version"]}
    receipt_path = output / "phase8_summary.json"
    atomic_json(receipt_path, summary)
    spark = spark_session(config, scratch)
    spark.conf.set("spark.sql.sources.partitionColumnTypeInference.enabled", "false")
    spark.sparkContext.setLogLevel("WARN")
    try:
        require(spark.version == "4.3.0", "Unexpected Spark version")
        receipt = locate_producer(input_root, parquet["independent_mount"]["summary_sha256"])
        frame, summary["input"] = verified_input(spark, receipt, parquet, policy)
        names = registry(design, parquet["feature_columns"])
        summary["predictors"] = names
        summary["resources"] = resource_limits(spark, config, output)
        prepared = predictor_input(frame, names, design["version"])
        if population in ("B", "C"):
            active, summary["split"] = benchmark_population(prepared, population, design, summary["input"]["days"], phase4, output)
            saved, km, summary["baseline_models"] = load_models(
                spark, input_root, population, names, phase4["protocols"][population], phase5["experiments"][population])
            atomic_json(receipt_path, summary)
            if mode == "baseline":
                result = reconcile(project, population, active, saved, km, phase4["protocols"][population], design, output)
                summary["baseline_checks"] = len(result)
            else:
                from src.ml.hybrid_detection import benchmark
                benchmark(project, output, spark, active, saved, km, population, names, config, summary)
        else:
            from src.ml.hybrid_detection import rolling
            rolling(project, output, spark, prepared, population, names, config, summary)
        summary.update(status=summary.get("outcome", "validated"), elapsed_seconds=round(monotonic() - start, 3),
                       driver_peak_rss_bytes=driver_peak_bytes(spark))
        atomic_json(receipt_path, summary)
        print(f"PHASE8 complete {mode} {population} status {summary['status']}", flush=True)
    finally:
        spark.stop()
