"""Orchestrate verified input, model reload, replay and bounded reporting."""

import json

from src.ingest.dataset_audit import atomic_json, spark_session
from src.ml.feature_registry import registry
from src.ml.train_supervised import verified_input
from src.sql.traffic_analytics import locate_producer, require
from src.streaming.cluster_scoring import clustering
from src.streaming.model_scoring import supervised


def run(project, input_root, output, scratch, mode):
    def read(name):
        return json.loads((project / name).read_text())

    config = read("configs/streaming_experiments.yaml")
    phase2 = read("manifests/parquet_layers.json")
    phase4 = read("manifests/phase4_models.json")["protocols"]["B"]
    phase5 = read("manifests/phase5_clustering_models.json")["experiments"]["B"]
    design = read("configs/ml_experiments.yaml")
    names = registry(design, phase2["feature_columns"])
    scratch.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    spark = spark_session(config, scratch / "spark")
    spark.conf.set("spark.sql.sources.partitionColumnTypeInference.enabled", "false")
    spark.sparkContext.setLogLevel("WARN")
    try:
        require(spark.version == "4.3.0", "Unexpected Spark runtime")
        receipt = locate_producer(input_root, phase2["independent_mount"]["summary_sha256"])
        _, input_evidence = verified_input(spark, receipt, phase2, read("configs/cleaning.yaml"))
        models, duration, supervised_evidence = supervised(spark, input_root, names, phase4)
        cluster, cluster_evidence = clustering(spark, input_root, names, phase5)
        summary = {"mode": mode, "status": "inputs_validated", "spark": spark.version, "config": config,
                   "features": names, "input": input_evidence, "supervised": supervised_evidence,
                   "clustering": cluster_evidence, "duration_cutoff": duration}
        atomic_json(output / "phase6_summary.json", summary)
        print("PHASE6 pinned inputs and three frozen pipelines validated", flush=True)
        if mode == "full":
            from src.streaming.structured_replay import full_replay

            full_replay(spark, receipt, phase2, design, phase4, phase5, names, models, duration,
                        cluster, config, output, scratch, summary)
    finally:
        spark.stop()
