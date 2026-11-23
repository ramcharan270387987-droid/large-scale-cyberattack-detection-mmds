"""Reload downloaded Kaggle models and validate bounded inference locally."""

import argparse
import json
import math
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pyspark.ml import PipelineModel
from pyspark.ml.functions import vector_to_array

from src.ingest.dataset_audit import spark_session


def verify(root):
    config = {"spark": {"master": "local[2]", "driver_memory": "2g", "shuffle_partitions": 4,
                        "input_partition_bytes": 67108864}}
    with TemporaryDirectory() as temp:
        spark = spark_session(config, temp)
        spark.sparkContext.setLogLevel("ERROR")
        result = {}
        try:
            for protocol in "ABC":
                folder = root / protocol / "results"
                summary = json.loads((folder / "phase4_summary.json").read_text())
                names = summary["registered_predictors"]
                source = spark.createDataFrame([
                    tuple(None for _ in names), tuple(0.0 for _ in names), tuple(float(n + 1) for n in range(len(names))),
                ], ", ".join(name + " DOUBLE" for name in names))
                results = []
                for item in summary["models"]:
                    relative = Path(item["path"]).name
                    model = PipelineModel.load(str(folder / "models" / relative))
                    predictions = model.transform(source).select(vector_to_array("probability")[1]).collect()
                    if len(predictions) != 3 or any(not math.isfinite(row[0]) or not 0 <= row[0] <= 1 for row in predictions):
                        raise ValueError(f"Invalid local reload predictions for {protocol} {relative}")
                    results.append({"artifact_directory": relative, "finite_probe_predictions": len(predictions)})
                result[protocol] = results
        finally:
            spark.stop()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    verified = verify(args.evidence_root)
    args.output.write_text(json.dumps(verified, indent=2) + "\n", encoding="utf-8")
    print(f"Reloaded and scored {sum(map(len, verified.values()))} downloaded Kaggle models.")
