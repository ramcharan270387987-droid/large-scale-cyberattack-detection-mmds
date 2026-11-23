# Phase 2 Spark data engineering

**READY FOR PHASE 3.** Phase 2 validated 10 of 10 captures. The private CPU producer reached Kaggle `COMPLETE` at version 1. [Producer notebook](https://www.kaggle.com/code/ramcharan2345/mmds-phase-2-spark-data-engineering)

## Input reconciliation

| Capture day | Expected records | Canonical records | Expected header lines | Observed header lines | Repeated header lines |
| --- | --- | --- | --- | --- | --- |
| 2018-03-01 | 331,100 | 331,100 | 26 | 26 | 25 |
| 2018-02-28 | 613,071 | 613,071 | 34 | 34 | 33 |
| 2018-02-21 | 1,048,575 | 1,048,575 | 1 | 1 | 0 |
| 2018-02-16 | 1,048,574 | 1,048,574 | 2 | 2 | 1 |
| 2018-03-02 | 1,048,575 | 1,048,575 | 1 | 1 | 0 |
| 2018-02-14 | 1,048,575 | 1,048,575 | 1 | 1 | 0 |
| 2018-02-15 | 1,048,575 | 1,048,575 | 1 | 1 | 0 |
| 2018-02-22 | 1,048,575 | 1,048,575 | 1 | 1 | 0 |
| 2018-02-23 | 1,048,575 | 1,048,575 | 1 | 1 | 0 |
| 2018-02-20 | 7,948,748 | 7,948,748 | 1 | 1 | 0 |

The completed captures contain 16,233,012 physical lines and 16,232,943 data records. Spark counted 69 header lines, including 59 repeats, and 0 blank lines. The width/quoting and corrupt-record counters were 0 and 0. [Count evidence](phase2_count_reconciliation.csv)

## Cleaning and labels

The canonical label totals were 13,484,708 benign and 2,748,235 attack. There were 0 unknown labels. 14 records retained an outside-capture-day timestamp and were marked temporally ineligible.

Numeric diagnostics cover 8,257,114 distinct rows and 12,879,783 cells. Schema-only nulls cover 8,284,195 rows and 33,136,780 cells.

| Reason | Affected rows | Affected cells | Action |
| --- | --- | --- | --- |
| nan | 59,721 | 59,721 | nullify |
| positive_infinity | 95,760 | 131,799 | nullify |
| negative_infinity | 0 | 0 | nullify |
| invalid_negative | 15 | 106 | nullify |
| sentinel | 8,255,549 | 12,688,157 | nullify |
| cast_failure | 0 | 0 | typed_null |
| source_null | 0 | 0 | retain_null |

The independent mount validated 12,879,783 stored policy nullifications and re-counted the benign and attack classes directly in each primary layer.

The diagnostic policy kept all primary records. It measured 107,670 exact digest groups and 410,707 excess copies. Cleaned shared features produced 21,763 conflicting-label groups involving 710,014 rows. Phase 1's 22,129 groups refer to its own raw-feature definition. [Cell actions](phase2_quality_actions.csv)

## Parquet output

| Layer | Producer path | Day partitions | Files | Bytes | Records |
| --- | --- | --- | --- | --- | --- |
| raw_aligned | `/kaggle/working/mmds_phase2/phase2-v1/raw_aligned` | 10 | 55 | 2,712,371,594 | 16,232,943 |
| clean | `/kaggle/working/mmds_phase2/phase2-v1/clean` | 10 | 55 | 2,708,993,526 | 16,232,943 |
| feature_ready | `/kaggle/working/mmds_phase2/phase2-v1/feature_ready` | 10 | 53 | 3,003,003,600 | 16,232,943 |

The worker inspected data-file footers and verified Snappy compression and row totals. [Parquet manifest](../manifests/parquet_layers.json)

## Performance

Spark 4.3.0 used `local[4]`, an 8g driver heap, 48 configured shuffle partitions and 64 MiB input splits. Kaggle exposed 4 logical CPUs in the process affinity mask.

The producer loop took 2,629.032 s. Reading, parsing and materializing the canonical data took 1,686.290 s at 3.89 MiB/s effective input throughput. The timing includes CSV conversion and the disk-backed canonical materialization.

| Layer | Write time including lazy transformations (s) |
| --- | --- |
| raw_aligned | 240.044 |
| clean | 297.806 |
| feature_ready | 314.859 |

The JVM high-water resident set was 5.39 GiB. This includes JVM memory outside the configured heap. [Per-file performance](phase2_performance.csv)

Global duplicate diagnostics took 72.760 s.

## Spark SQL, DataFrame and RDD

All three methods returned the same 3 protocol groups over 311 records. The sample rule was `smallest capture by source bytes; pmod(xxhash64(record_fingerprint), 1024) == 0`.

| Protocol | Records | Attacks |
| --- | --- | --- |
| 0.0 | 4 | 0 |
| 6.0 | 210 | 68 |
| 17.0 | 97 | 17 |

<details><summary>SQL physical plan</summary>

```text
AdaptiveSparkPlan isFinalPlan=true
+- == Final Plan ==
   ResultQueryStage 2
   +- *(2) HashAggregate(keys=[protocol#80055], functions=[count(1), sum(binary_label#80134)], output=[protocol#80055, records#80150L, attacks#80151L])
      +- AQEShuffleRead coalesced
         +- ShuffleQueryStage 1
            +- Exchange hashpartitioning(protocol#80055, 48), ENSURE_REQUIREMENTS, [plan_id=1682]
               +- *(1) HashAggregate(keys=[knownfloatingpointnormalized(normalizenanandzero(protocol#80055)) AS protocol#80055], functions=[partial_count(1), partial_sum(binary_label#80134)], output=[protocol#80055, count#80232L, sum#80233L])
                  +- TableCacheQueryStage 0
                     +- InMemoryTableScan [protocol#80055, binary_label#80134]
                           +- InMemoryRelation [protocol#80055, binary_label#80134], StorageLevel(disk, memory, deserialized, 1 replicas)
                                 +- *(1) Project [protocol#80055, binary_label#80134]
                                    +- *(1) Filter (pmod(xxhash64(record_fingerprint#80136, 42), 1024) = 0)
                                       +- *(1) ColumnarToRow
                                          +- FileScan parquet [protocol#80055,binary_label#80134,record_fingerprint#80136] Batched: true, DataFilters: [(pmod(xxhash64(record_fingerprint#80136, 42), 1024) = 0)], Format: Parquet, Location: InMemoryFileIndex(1 paths)[file:/kaggle/working/mmds_phase2/phase2-v1/feature_ready/source_day=20..., PartitionFilters: [], PushedFilters: [], ReadSchema: struct<protocol:double,binary_label:tinyint,record_fingerprint:binary>
+- == Initial Plan ==
   HashAggregate(keys=[protocol#80055], functions=[count(1), sum(binary_label#80134)], output=[protocol#80055, records#80150L, attacks#80151L])
   +- Exchange hashpartitioning(protocol#80055, 48), ENSURE_REQUIREMENTS, [plan_id=1652]
      +- HashAggregate(keys=[knownfloatingpointnormalized(normalizenanandzero(protocol#80055)) AS protocol#80055], functions=[partial_count(1), partial_sum(binary_label#80134)], output=[protocol#80055, count#80232L, sum#80233L])
         +- InMemoryTableScan [protocol#80055, binary_label#80134]
               +- InMemoryRelation [protocol#80055, binary_label#80134], StorageLevel(disk, memory, deserialized, 1 replicas)
                     +- *(1) Project [protocol#80055, binary_label#80134]
                        +- *(1) Filter (pmod(xxhash64(record_fingerprint#80136, 42), 1024) = 0)
                           +- *(1) ColumnarToRow
                              +- FileScan parquet [protocol#80055,binary_label#80134,record_fingerprint#80136] Batched: true, DataFilters: [(pmod(xxhash64(record_fingerprint#80136, 42), 1024) = 0)], Format: Parquet, Location: InMemoryFileIndex(1 paths)[file:/kaggle/working/mmds_phase2/phase2-v1/feature_ready/source_day=20..., PartitionFilters: [], PushedFilters: [], ReadSchema: struct<protocol:double,binary_label:tinyint,record_fingerprint:binary>
```

</details>

<details><summary>DataFrame physical plan</summary>

```text
AdaptiveSparkPlan isFinalPlan=true
+- == Final Plan ==
   ResultQueryStage 2
   +- *(2) HashAggregate(keys=[protocol#80055], functions=[count(1), sum(binary_label#80134)], output=[protocol#80055, records#80154L, attacks#80155L])
      +- AQEShuffleRead coalesced
         +- ShuffleQueryStage 1
            +- Exchange hashpartitioning(protocol#80055, 48), ENSURE_REQUIREMENTS, [plan_id=1739]
               +- *(1) HashAggregate(keys=[knownfloatingpointnormalized(normalizenanandzero(protocol#80055)) AS protocol#80055], functions=[partial_count(1), partial_sum(binary_label#80134)], output=[protocol#80055, count#80289L, sum#80290L])
                  +- TableCacheQueryStage 0
                     +- InMemoryTableScan [protocol#80055, binary_label#80134]
                           +- InMemoryRelation [protocol#80055, binary_label#80134], StorageLevel(disk, memory, deserialized, 1 replicas)
                                 +- *(1) Project [protocol#80055, binary_label#80134]
                                    +- *(1) Filter (pmod(xxhash64(record_fingerprint#80136, 42), 1024) = 0)
                                       +- *(1) ColumnarToRow
                                          +- FileScan parquet [protocol#80055,binary_label#80134,record_fingerprint#80136] Batched: true, DataFilters: [(pmod(xxhash64(record_fingerprint#80136, 42), 1024) = 0)], Format: Parquet, Location: InMemoryFileIndex(1 paths)[file:/kaggle/working/mmds_phase2/phase2-v1/feature_ready/source_day=20..., PartitionFilters: [], PushedFilters: [], ReadSchema: struct<protocol:double,binary_label:tinyint,record_fingerprint:binary>
+- == Initial Plan ==
   HashAggregate(keys=[protocol#80055], functions=[count(1), sum(binary_label#80134)], output=[protocol#80055, records#80154L, attacks#80155L])
   +- Exchange hashpartitioning(protocol#80055, 48), ENSURE_REQUIREMENTS, [plan_id=1709]
      +- HashAggregate(keys=[knownfloatingpointnormalized(normalizenanandzero(protocol#80055)) AS protocol#80055], functions=[partial_count(1), partial_sum(binary_label#80134)], output=[protocol#80055, count#80289L, sum#80290L])
         +- InMemoryTableScan [protocol#80055, binary_label#80134]
               +- InMemoryRelation [protocol#80055, binary_label#80134], StorageLevel(disk, memory, deserialized, 1 replicas)
                     +- *(1) Project [protocol#80055, binary_label#80134]
                        +- *(1) Filter (pmod(xxhash64(record_fingerprint#80136, 42), 1024) = 0)
                           +- *(1) ColumnarToRow
                              +- FileScan parquet [protocol#80055,binary_label#80134,record_fingerprint#80136] Batched: true, DataFilters: [(pmod(xxhash64(record_fingerprint#80136, 42), 1024) = 0)], Format: Parquet, Location: InMemoryFileIndex(1 paths)[file:/kaggle/working/mmds_phase2/phase2-v1/feature_ready/source_day=20..., PartitionFilters: [], PushedFilters: [], ReadSchema: struct<protocol:double,binary_label:tinyint,record_fingerprint:binary>
```

</details>

<details><summary>RDD lineage</summary>

```text
(4) PythonRDD[403] at collect at /kaggle/temp/mmds_phase2/source/src/sql/aggregation_demo.py:19 []
 |  MapPartitionsRDD[386] at mapPartitions at PythonRDD.scala:197 []
 |  ShuffledRDD[385] at partitionBy at DirectMethodHandleAccessor.java:103 []
 +-(4) PairwiseRDD[384] at reduceByKey at /kaggle/temp/mmds_phase2/source/src/sql/aggregation_demo.py:17 []
    |  PythonRDD[383] at reduceByKey at /kaggle/temp/mmds_phase2/source/src/sql/aggregation_demo.py:17 []
    |  MapPartitionsRDD[382] at javaToPython at DirectMethodHandleAccessor.java:103 []
    |  MapPartitionsRDD[381] at javaToPython at DirectMethodHandleAccessor.java:103 []
    |  SQLExecutionRDD[380] at javaToPython at DirectMethodHandleAccessor.java:103 []
    |  MapPartitionsRDD[379] at javaToPython at DirectMethodHandleAccessor.java:103 []
    |  MapPartitionsRDD[378] at javaToPython at DirectMethodHandleAccessor.java:103 []
    |  MapPartitionsRDD[377] at javaToPython at DirectMethodHandleAccessor.java:103 []
    |  *(1) Project [protocol#80055, binary_label#80134]
+- *(1) Filter (pmod(xxhash64(record_fingerprint#80136, 42), 1024) = 0)
   +- *(1) ColumnarToRow
      +- FileScan parquet [protocol#80055,binary_label#80134,record_fingerprint#80136] Batched: true, DataFilters: [(pmod(xxhash64(record_fingerprint#80136, 42), 1024) = 0)], Format: Parquet, Location: InMemoryFileIndex(1 paths)[file:/kaggle/working/mmds_phase2/phase2-v1/feature_ready/source_day=20..., PartitionFilters: [], PushedFilters: [], ReadSchema: struct<protocol:double,binary_label:tinyint,record_fingerprint:binary>
 MapPartitionsRDD[376] at javaToPython at DirectMethodHandleAccessor.java:103 []
    |      CachedPartitions: 4; MemorySize: 2.9 KiB; DiskSize: 0.0 B
    |  MapPartitionsRDD[375] at javaToPython at DirectMethodHandleAccessor.java:103 []
    |  MapPartitionsRDD[374] at javaToPython at DirectMethodHandleAccessor.java:103 []
    |  MapPartitionsRDD[373] at javaToPython at DirectMethodHandleAccessor.java:103 []
    |  FileScanRDD[372] at javaToPython at DirectMethodHandleAccessor.java:103 []
```

</details>

## Saved output reuse

Version 1 of the private verification notebook mounted the saved producer output as a notebook input. It matched the expected evidence SHA-256 and directly verified each layer. Independent validation took 101.019 s. [Verification notebook](https://www.kaggle.com/code/ramcharan2345/mmds-phase-2-parquet-reuse-check) · [Storage guide](../docs/parquet_storage.md)
