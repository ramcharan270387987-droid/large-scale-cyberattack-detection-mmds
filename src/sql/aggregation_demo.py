"""Compare equivalent SQL, DataFrame and RDD aggregations on a bounded sample."""

from pyspark.sql import functions as F


def run_aggregation_demo(features):
    sample = (features.select("protocol", "binary_label", "record_fingerprint")
              .where(F.pmod(F.xxhash64("record_fingerprint"), F.lit(1024)) == 0)
              .select("protocol", "binary_label").cache())
    sample.createOrReplaceTempView("phase2_demo_sample")
    try:
        sql = features.sparkSession.sql(
            "SELECT protocol, count(*) AS records, sum(binary_label) AS attacks "
            "FROM phase2_demo_sample GROUP BY protocol")
        dataframe = sample.groupBy("protocol").agg(F.count("*").alias("records"), F.sum("binary_label").alias("attacks"))
        rdd = (sample.rdd.map(lambda row: (row.protocol, (1, row.binary_label)))
               .reduceByKey(lambda a, b: (a[0] + b[0], a[1] + b[1])))
        result = {row.protocol: (row.records, row.attacks) for row in sql.collect()}
        if result != {row.protocol: (row.records, row.attacks) for row in dataframe.collect()} or result != dict(rdd.collect()):
            raise ValueError("SQL, DataFrame and RDD aggregation disagree")
        if not result:
            raise ValueError("The demonstration sample is empty")
        return {
            "sample_rule": "smallest capture by source bytes; pmod(xxhash64(record_fingerprint), 1024) == 0",
            "rows": sum(count for count, _ in result.values()),
            "groups": [{"protocol": key, "records": value[0], "attacks": value[1]}
                       for key, value in sorted(result.items())],
            "sql_plan": sql._jdf.queryExecution().executedPlan().toString(),
            "dataframe_plan": dataframe._jdf.queryExecution().executedPlan().toString(),
            "rdd_dag": rdd.toDebugString().decode("utf-8"),
        }
    finally:
        features.sparkSession.catalog.dropTempView("phase2_demo_sample")
        sample.unpersist()
