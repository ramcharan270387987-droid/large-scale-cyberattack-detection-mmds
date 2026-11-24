"""Reload saved Kaggle clustering pipelines with synthetic values in Codex Cloud."""

import argparse
import json
import math
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pyspark.ml import PipelineModel

from src.ingest.dataset_audit import spark_session
from src.ml.clustering_features import verify_finite_vectors
from src.ml.novelty_scoring import squared_distance


def verify(root):
    config = {"spark": {"master": "local[2]", "driver_memory": "2g", "shuffle_partitions": 4,
                        "input_partition_bytes": 67108864}}
    results = {}
    with TemporaryDirectory() as temp:
        spark = spark_session(config, temp)
        spark.sparkContext.setLogLevel("ERROR")
        try:
            for experiment in "GBC":
                folder = root / experiment / "results"
                evidence = json.loads((folder / "phase5_summary.json").read_text())
                names = evidence["features"]
                inspected = PipelineModel.load(str(folder / "model"))
                probes = spark.createDataFrame([
                    tuple(None for _ in names), tuple(float("inf") for _ in names),
                    tuple(float(i + 1) for i in range(len(names))),
                ], ", ".join(name + " DOUBLE" for name in names))
                result = inspected.transform(probes)
                verify_finite_vectors(result, len(evidence["preprocessing"]["active"]))
                distances = squared_distance(inspected.stages[-1], result.drop("cluster")).select("cluster", "score").collect()
                if len(distances) != 3 or any(not 0 <= row.cluster < evidence["selected_k"]
                                              or not math.isfinite(row.score) or row.score < 0 for row in distances):
                    raise ValueError(f"Reloaded {experiment} model has invalid predictions")
                results[experiment] = {"probes": len(distances), "pipeline_stages": len(inspected.stages), "verified": True}
        finally:
            spark.stop()
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_text(json.dumps(verify(args.runs), indent=2) + "\n", encoding="utf-8")
    print("Reloaded all three pipelines and reproduced finite synthetic assignments.")
