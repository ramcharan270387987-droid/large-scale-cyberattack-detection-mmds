# Phase 3 Spark SQL traffic analytics

**READY FOR PHASE 4.** Kaggle notebook version 1 reached `COMPLETE` and produced 19 compact query results over 16,232,943 validated records. [Private Kaggle notebook](https://www.kaggle.com/code/ramcharan2345/mmds-phase-3-spark-sql-attack-analytics)

## Input validation

Phase 2 output version 1 matched saved receipt `1fa00cd2b9c853ee33eaacee8ca7632dbb41f739573326280d6ffbfb2ccff25a` and policy `phase2-v1`. Spark reconciled labels, original-label family mappings and temporal eligibility across the clean and feature-ready layers. The feature-ready schema contained 77 canonical model candidates. [Validation evidence](phase3_validation.json)

| Layer | Mounted path | Partitions | Records |
| --- | --- | --- | --- |
| feature_ready | `/kaggle/input/notebooks/ramcharan2345/mmds-phase-2-spark-data-engineering/mmds_phase2/phase2-v1/feature_ready` | 10 | 16,232,943 |
| clean | `/kaggle/input/notebooks/ramcharan2345/mmds-phase-2-spark-data-engineering/mmds_phase2/phase2-v1/clean` | 10 | 16,232,943 |
| raw_aligned | `/kaggle/input/notebooks/ramcharan2345/mmds-phase-2-spark-data-engineering/mmds_phase2/phase2-v1/raw_aligned` | 10 | 16,232,943 |

## Traffic and temporal counts

13,484,708 records were benign and 2,748,235 (16.930%) were labeled attack. The largest attack count was 687,742 on 2018-02-21. Attack prevalence ranged from 0.0345% on 2018-02-22 to 65.5883% on 2018-02-21. [Daily traffic](phase3_daily_traffic.csv)

| Population | Packet count | Byte count |
| --- | --- | --- |
| attack | 306,194,295 | 10,852,060,785 |
| benign | 178,292,446 | 81,740,137,674 |

Eligible event-time queries retained 16,232,929 records and excluded 14 timestamp outliers. The 93 observed hourly groups included a peak of 686,012 attack records on 2018-02-21 at 02:00 local wall time. Source timezone is unverified. Capture-day groups include all rows. Empty or unobserved hours are left out of the hourly table. [Hourly traffic](phase3_hourly_traffic.csv) · [Three-hour windows](phase3_time_windows.csv)

## Families and flow statistics

| Family | Attack records | Share of attacks | Capture days | Rows with nonsentinel issues |
| --- | --- | --- | --- | --- |
| DDoS | 1,263,933 | 45.991% | 2 | 0 |
| DoS | 654,300 | 23.808% | 2 | 0 |
| Credential brute force | 380,949 | 13.862% | 1 | 6 |
| Bot | 286,191 | 10.414% | 1 | 0 |
| Infiltration | 161,934 | 5.892% | 2 | 1,295 |
| Web attack | 928 | 0.034% | 2 | 0 |

Approximate flow quantiles use Spark percentile accuracy 4,096. The feature tables also contain finite-value counts, means, sample standard deviations and extrema. [By binary label](phase3_feature_statistics.csv) · [By family](phase3_family_feature_statistics.csv) · [Original labels](phase3_original_labels.csv)

| Measure | Benign P50 | Attack P50 | Benign P99 | Attack P99 |
| --- | --- | --- | --- | --- |
| flow_duration | 3.421e+04 | 1.076e+04 | 1.183e+08 | 8.342e+07 |
| total_packets | 3 | 2 | 70 | 44 |
| total_bytes | 174 | 0 | 3.142e+04 | 4,625 |
| flow_iat_mean | 1.426e+04 | 4,588 | 8.625e+07 | 3.98e+07 |
| flow_pkts_s | 104.3 | 383.7 | 2e+06 | 2e+06 |

Aggregate IP protocol counts were code 6.0 (11,800,335), code 17.0 (4,194,295), code 0.0 (238,313). [Protocol by family](phase3_protocols.csv) · [Top destination ports](phase3_destination_ports.csv)

## Data-quality sensitivity

Exact duplicate groups contained 518,377 occurrences. A representative-per-exact-content count would be 15,822,236, removing 410,707 excess copies from that count. The Phase 2 cleaned-feature conflict groups contained 710,014 rows (4.374%) across 21,763 groups. Default Phase 3 statistics preserve full multiplicity. [Duplicate and anomaly summary](phase3_duplicate_quality.csv)

| Feature | Raw NaN | Raw infinity | Raw minus one | Clean nulls |
| --- | --- | --- | --- | --- |
| flow_byts_s | 59,721 | 36,039 | 0 | 95,760 |
| flow_pkts_s | 0 | 95,760 | 0 | 95,774 |
| init_fwd_win_byts | 0 | 0 | 4,432,608 | 4,432,608 |
| init_bwd_win_byts | 0 | 0 | 8,255,549 | 8,255,549 |
| flow_duration | 0 | 0 | 0 | 14 |

Finite means and class-specific counts are retained in the sensitivity tables. [Raw-aligned](phase3_raw_sensitivity.csv) · [Clean](phase3_clean_sensitivity.csv)

## Performance

Spark 4.3.0 used `local[4]`, 8g configured driver heap, 48 configured shuffle partitions and 64 MiB input splits. The notebook took 620.821s from input validation to chart generation. Input validation took 67.009s. JVM high-water RSS was 4.59 GiB.

| API | Measured runs (s) | Median (s) |
| --- | --- | --- |
| SQL | 2.958, 2.991, 2.983 | 2.983 |
| DataFrame | 3.038, 2.984, 2.983 | 2.984 |

The bounded SQL, DataFrame and RDD comparison agreed on 311 records. The full-data benchmark warmed each API and alternated execution order over the same cached inputs. [Measured query timings](phase3_query_performance.csv) · [Physical plans and RDD lineage](phase3_execution_plans.json)

## Figures

- [Binary distribution](figures/phase3_binary_distribution.png)
- [Attack family frequencies](figures/phase3_attack_family_frequencies.png)
- [Daily traffic volume](figures/phase3_daily_traffic_volume.png)
- [Daily attack prevalence](figures/phase3_daily_attack_prevalence.png)
- [Family by capture day](figures/phase3_family_by_capture_day.png)
- [Flow duration comparison](figures/phase3_flow_duration_comparison.png)
- [Packet byte distributions](figures/phase3_packet_byte_distributions.png)
- [Protocol distribution](figures/phase3_protocol_distribution.png)
- [Destination ports](figures/phase3_destination_ports.png)
- [Temporal feature changes](figures/phase3_temporal_feature_changes.png)

[Candidate pattern findings](../docs/attack_pattern_findings.md) · [Research readiness](phase3_research_readiness.md)
