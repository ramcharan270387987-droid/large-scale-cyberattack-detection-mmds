# MMDS Phase 1 dataset audit

Kaggle version 1 reached `COMPLETE`. The audit completed 10 of 10 expected captures and counted 10. [Private CPU notebook](https://www.kaggle.com/code/ramcharan2345/mmds-phase-1-dataset-audit)

Dataset `saisathwikregula/mmds-dataset-23013`, version 1. The mounted inventory contains 10 files and 6,886,649,507 bytes. [Inventory](../manifests/dataset_inventory.json)

Inventory flags record 0 missing, 0 unreadable, 0 unexpected, 0 duplicate-basename and 0 size-mismatch entries.

## Records

| Capture | Mounted bytes | Columns | Data records | Parsed | Malformed | Blank | Headers | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2018-02-14 | 358,223,333 | 80 | 1,048,575 | 1,048,575 | 0 | 0 | 1 | complete |
| 2018-02-15 | 375,945,899 | 80 | 1,048,575 | 1,048,575 | 0 | 0 | 1 | complete |
| 2018-02-16 | 333,723,605 | 80 | 1,048,574 | 1,048,574 | 0 | 0 | 2 | complete |
| 2018-02-20 | 4,054,925,350 | 84 | 7,948,748 | 7,948,748 | 0 | 0 | 1 | complete |
| 2018-02-21 | 328,893,673 | 80 | 1,048,575 | 1,048,575 | 0 | 0 | 1 | complete |
| 2018-02-22 | 382,636,202 | 80 | 1,048,575 | 1,048,575 | 0 | 0 | 1 | complete |
| 2018-02-23 | 382,840,456 | 80 | 1,048,575 | 1,048,575 | 0 | 0 | 1 | complete |
| 2018-02-28 | 209,249,758 | 80 | 613,071 | 613,071 | 0 | 0 | 34 | complete |
| 2018-03-01 | 107,842,858 | 80 | 331,100 | 331,100 | 0 | 0 | 26 | complete |
| 2018-03-02 | 352,368,373 | 80 | 1,048,575 | 1,048,575 | 0 | 0 | 1 | complete |

Measured captures contain 16,233,012 physical lines, including 16,232,943 data records, 69 header lines (59 repeats) and 0 blank lines. Spark parsed 16,232,943 data records. Malformed records total 0, including 0 width or quoting failures and 0 Spark corrupt records. Counts use one record per physical line, with the exact original header line classified separately wherever it repeats. No source records were modified. [File statistics](dataset_file_statistics.csv)

## Labels

Measured label groups cover 16,232,943 parsed rows. The proposed mapping yields 13,484,708 benign rows (83.070014%), 2,748,235 attack rows (16.929986%), and 0 unmapped rows (0.000000%). Original spellings and all capture-specific counts are retained. The CSV stores the original label as JSON so null and empty strings stay distinct. [Label distribution](dataset_label_distribution.csv)

| Original label | Rows | Share | Capture days | Largest capture share | Proposed group |
| --- | --- | --- | --- | --- | --- |
| `"Benign"` | 13,484,708 | 83.070014% | 2018-02-14, 2018-02-15, 2018-02-16, 2018-02-20, 2018-02-21, 2018-02-22, 2018-02-23, 2018-02-28, 2018-03-01, 2018-03-02 | 54.673464% | Benign |
| `"DDOS attack-HOIC"` | 686,012 | 4.226048% | 2018-02-21 | 100.000000% | DDoS |
| `"DDoS attacks-LOIC-HTTP"` | 576,191 | 3.549517% | 2018-02-20 | 100.000000% | DDoS |
| `"DoS attacks-Hulk"` | 461,912 | 2.845522% | 2018-02-16 | 100.000000% | DoS |
| `"Bot"` | 286,191 | 1.763026% | 2018-03-02 | 100.000000% | Bot |
| `"FTP-BruteForce"` | 193,360 | 1.191158% | 2018-02-14 | 100.000000% | Credential brute force |
| `"SSH-Bruteforce"` | 187,589 | 1.155607% | 2018-02-14 | 100.000000% | Credential brute force |
| `"Infilteration"` | 161,934 | 0.997564% | 2018-02-28, 2018-03-01 | 57.469710% | Infiltration |
| `"DoS attacks-SlowHTTPTest"` | 139,890 | 0.861766% | 2018-02-16 | 100.000000% | DoS |
| `"DoS attacks-GoldenEye"` | 41,508 | 0.255702% | 2018-02-15 | 100.000000% | DoS |
| `"DoS attacks-Slowloris"` | 10,990 | 0.067702% | 2018-02-15 | 100.000000% | DoS |
| `"DDOS attack-LOIC-UDP"` | 1,730 | 0.010657% | 2018-02-21 | 100.000000% | DDoS |
| `"Brute Force -Web"` | 611 | 0.003764% | 2018-02-22, 2018-02-23 | 59.247136% | Web attack |
| `"Brute Force -XSS"` | 230 | 0.001417% | 2018-02-22, 2018-02-23 | 65.652174% | Web attack |
| `"SQL Injection"` | 87 | 0.000536% | 2018-02-22, 2018-02-23 | 60.919540% | Web attack |

Proposed attack-family totals

| Family | Rows | Share of measured labels | Share of mapped attacks |
| --- | --- | --- | --- |
| Bot | 286,191 | 1.763026% | 10.413629% |
| Credential brute force | 380,949 | 2.346765% | 13.861588% |
| DDoS | 1,263,933 | 7.786222% | 45.990718% |
| DoS | 654,300 | 4.030692% | 23.808008% |
| Infiltration | 161,934 | 0.997564% | 5.892291% |
| Web attack | 928 | 0.005717% | 0.033767% |

Observed normalized-label collisions across distinct originals: 0. Original labels with leading, trailing or repeated whitespace: 0. A family mapping is a proposal and leaves unknown names unmapped.

## Timestamps

The audit tries the configured DMY day-first and ISO patterns in order. A separate MDY parse flags alternative interpretations. All date comparisons use wall-clock timestamps without timezone (`TIMESTAMP_NTZ`). Spark's session timezone was UTC for determinism. Source timezone and clock synchronization were not established.

| Capture | Parsed / rows | Range | Missing | Invalid | Ambiguous DMY/MDY | Name disagreement |
| --- | --- | --- | --- | --- | --- | --- |
| 2018-02-14 | 1,048,575 / 1,048,575 (100.000000%) | 1970-01-05 03:01:17 to 2018-02-14 12:59:59 | 0 | 0 | 5 | 5 |
| 2018-02-15 | 1,048,575 / 1,048,575 (100.000000%) | 2018-02-15 01:00:00 to 2018-02-15 12:59:59 | 0 | 0 | 0 | 0 |
| 2018-02-16 | 1,048,574 / 1,048,574 (100.000000%) | 2018-02-16 01:00:32 to 2018-02-16 12:58:24 | 0 | 0 | 0 | 0 |
| 2018-02-20 | 7,948,748 / 7,948,748 (100.000000%) | 2018-02-20 01:00:00 to 2018-02-20 12:59:59 | 0 | 0 | 0 | 0 |
| 2018-02-21 | 1,048,575 / 1,048,575 (100.000000%) | 2018-02-21 01:55:46 to 2018-02-21 10:43:21 | 0 | 0 | 0 | 0 |
| 2018-02-22 | 1,048,575 / 1,048,575 (100.000000%) | 1970-01-10 03:04:26 to 2018-02-22 12:59:59 | 0 | 0 | 9 | 9 |
| 2018-02-23 | 1,048,575 / 1,048,575 (100.000000%) | 2018-02-23 01:00:00 to 2018-02-23 12:59:59 | 0 | 0 | 0 | 0 |
| 2018-02-28 | 613,071 / 613,071 (100.000000%) | 2018-02-28 01:00:00 to 2018-02-28 12:59:59 | 0 | 0 | 0 | 0 |
| 2018-03-01 | 331,100 / 331,100 (100.000000%) | 2018-03-01 01:00:00 to 2018-03-01 12:59:59 | 0 | 0 | 331,100 | 0 |
| 2018-03-02 | 1,048,575 / 1,048,575 (100.000000%) | 2018-03-02 01:00:00 to 2018-03-02 12:59:59 | 0 | 0 | 1,048,575 | 0 |

The parser accepted 16,232,943 of 16,232,943 timestamp cells (100.000000%). There were 14 filename-date disagreements and 1,379,689 valid alternative MDY interpretations. The MDY parse matched the filename date for 0 rows.

Observed dates outside their filename capture days were 1970-01-05 (1), 1970-01-08 (1), 1970-01-10 (1), 1970-01-11 (3), 1970-01-12 (8).

The [timestamp table](dataset_timestamp_summary.csv) retains per-date and per-format counts, plus MDY-only and MDY-match totals.

## Quality

Across 804 file-column profiles, measured nulls total 0 and empty or whitespace-only strings total 0. The Spark parser can represent empty source fields as null depending on CSV quoting.

Numeric candidates contain 59,721 NaNs, 131,799 infinities, and 0 conversion failures. Fields governed by a nonnegative rule contain 106 invalid negative cells. Initial TCP-window fields are excluded from that rule because their negative sentinel requires separate interpretation.

There are 96 constant nonempty feature profiles and 139 feature profiles with a sampled dominant-value fraction of at least 99%. The deterministic content sample uses `pmod(xxhash64(23013, raw_line), 1000) = 0`. Exact repeats enter or miss the sample together. [Quality statistics](dataset_quality_summary.csv)

Kaggle version 2 grouped all 16,232,943 parsed arrays by full string-value equality within 2 original schemas. It found 107,670 duplicate groups, 410,707 excess copies and 0 cross-day duplicate groups. The exact stage took 509.978 s. [Kaggle notebook](https://www.kaggle.com/code/ramcharan2345/mmds-phase-1-dataset-audit)

Fingerprint coverage includes 10 captures. Full parsed-line SHA-256 grouping found 107,670 duplicate groups containing 410,707 excess copies. This measures identical source-line fingerprints, including cross-file matches. Hash collisions were not independently byte-verified.

Schema-scoped fingerprints of nonidentity, nontimestamp feature values found 22,129 groups with different original labels, involving 419,528 rows. Coarse flow-metric bucketing found 778 mixed-feature buckets with 8,591 participating rows among 16,247 eligible sampled rows. The heuristic uses available flow duration, forward/backward packet counts and packet-length totals, and mean flow inter-arrival time. It groups duration and inter-arrival measurements in intervals of 1,000 source units, and packet and byte measures in intervals of 10. Bucket matches indicate similarity on those fields within the sample.

## Spark execution

Spark settings `{"driver_memory": "8g", "executor_cores": 2, "input_partition_bytes": 67108864, "master": "local[2]", "shuffle_partitions": 32, "spark_application": "mmds-phase-1-dataset-audit", "timestamp_type": "TIMESTAMP_NTZ", "timezone": "UTC", "version": "4.3.0"}`.

The measured audit loop took 2722.49 s.

Global fingerprint aggregation took 109.678 s.

The Kaggle API returned persisted execution logs for version 1 (1,253 log events) and version 2 (230 log events).

| Capture | Parse and count (s) | Label and time (s) | Quality (s) | Fingerprint staging (s) |
| --- | --- | --- | --- | --- |
| 2018-02-14 | 53.685 | 15.529 | 69.781 | 14.767 |
| 2018-02-15 | 55.933 | 15.586 | 74.083 | 16.34 |
| 2018-02-16 | 52.391 | 16.365 | 71.734 | 15.756 |
| 2018-02-20 | 479.613 | 117.845 | 598.646 | 121.639 |
| 2018-02-21 | 51.238 | 16.345 | 73.641 | 15.906 |
| 2018-02-22 | 55.807 | 15.818 | 70.577 | 15.629 |
| 2018-02-23 | 54.861 | 15.579 | 60.253 | 14.286 |
| 2018-02-28 | 40.675 | 12.622 | 52.546 | 10.837 |
| 2018-03-01 | 25.383 | 4.835 | 47.785 | 7.795 |
| 2018-03-02 | 55.485 | 5.431 | 71.732 | 19.478 |

See [the schema reference](../docs/dataset_schema.md) and [the feasibility assessment](../docs/dataset_feasibility.md).
