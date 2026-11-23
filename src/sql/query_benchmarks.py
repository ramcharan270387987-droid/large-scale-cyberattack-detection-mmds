"""Controlled equivalent SQL and DataFrame workloads."""

import time

from pyspark.sql import functions as F

from src.sql.traffic_analytics import compact, require


def compare_workload(frame, repeats):
    view = "phase3_benchmark"
    frame.createOrReplaceTempView(view)
    spark = frame.sparkSession
    makers = {
        "SQL": lambda: spark.sql(
            f"SELECT source_day, binary_label, count(*) AS records FROM {view} "
            "GROUP BY source_day, binary_label ORDER BY source_day, binary_label"),
        "DataFrame": lambda: frame.groupBy("source_day", "binary_label").agg(F.count("*").alias("records"))
        .orderBy("source_day", "binary_label"),
    }
    rows, timings, plans = {}, [], {}
    try:
        for api, make in makers.items():
            rows[api] = compact(make(), 40)
        require(rows["SQL"] == rows["DataFrame"], "Warm-up benchmark mismatch")
        for i in range(repeats):
            order = tuple(makers) if i % 2 == 0 else tuple(reversed(makers))
            for api in order:
                started = time.monotonic()
                query = makers[api]()
                actual = compact(query, 40)
                elapsed = round(time.monotonic() - started, 6)
                require(actual == rows["SQL"], f"Benchmark result mismatch: {api}")
                timings.append({"workload": "day_label_equivalence", "api": api, "iteration": i + 1,
                                "seconds": elapsed, "result_rows": len(actual)})
                if api not in plans:
                    plans[api] = query._jdf.queryExecution().executedPlan().toString()
    finally:
        spark.catalog.dropTempView(view)
    return timings, plans, rows["SQL"]
