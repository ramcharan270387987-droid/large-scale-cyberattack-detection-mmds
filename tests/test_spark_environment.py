"""Run a local Spark smoke test using only synthetic data."""

import os
import sys
import unittest
from time import perf_counter

from pyspark import __version__ as pyspark_version
from pyspark.ml import Pipeline
from pyspark.ml.feature import Binarizer, VectorAssembler
from pyspark.sql import SparkSession, functions as F


class SparkEnvironmentTest(unittest.TestCase):
    def test_spark_workloads(self):
        started = perf_counter()
        os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
        spark = (
            SparkSession.builder.master("local[2]")
            .appName("mmds-phase-0")
            .config("spark.ui.enabled", "false")
            .config("spark.sql.shuffle.partitions", "2")
            .getOrCreate()
        )
        try:
            print(f"Apache Spark {spark.version}, PySpark {pyspark_version}", flush=True)
            self.assertEqual(spark.version, pyspark_version)
            spark.sparkContext.setLogLevel("WARN")
            self.check_workloads(spark)
        finally:
            spark.stop()
            print(f"Spark stopped after {perf_counter() - started:.2f} s", flush=True)

    def check_workloads(self, spark):
        rows = spark.createDataFrame(
            [("blue", 1.0), ("blue", 3.0), ("green", 2.0), ("green", 4.0)],
            ["category", "value"],
        )
        transformed = (
            rows.filter(F.col("value") >= 2)
            .withColumn("doubled", F.col("value") * 2)
            .orderBy("doubled")
        )
        self.assertEqual([row.doubled for row in transformed.collect()], [4.0, 6.0, 8.0])

        transformed.createOrReplaceTempView("synthetic_rows")
        totals = spark.sql(
            "SELECT category, SUM(doubled) AS total "
            "FROM synthetic_rows GROUP BY category ORDER BY category"
        ).collect()
        self.assertEqual([(row.category, row.total) for row in totals], [("blue", 6.0), ("green", 12.0)])

        squared_sum = spark.sparkContext.parallelize([1, 2, 3], 2).map(lambda n: n * n).sum()
        self.assertEqual(squared_sum, 14)

        features = Pipeline(
            stages=[
                Binarizer(threshold=2.0, inputCol="value", outputCol="above_threshold"),
                VectorAssembler(inputCols=["value", "above_threshold"], outputCol="features"),
            ]
        )
        vectors = features.fit(rows).transform(rows).orderBy("value").select("features")
        self.assertEqual(
            [list(row.features) for row in vectors.collect()],
            [[1.0, 0.0], [2.0, 0.0], [3.0, 1.0], [4.0, 1.0]],
        )


if __name__ == "__main__":
    unittest.main()
