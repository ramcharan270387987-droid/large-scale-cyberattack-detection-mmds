# Phase 6 historical Structured Streaming replay

**READY FOR PHASE 7.** The replay covered the complete chronological B population. The frozen supervised confusion counts, binned PR-AUCs, K-Means novelty counts and window occupancy distances reconcile to Phases 4 and 5. [Private Kaggle notebook](https://www.kaggle.com/code/ramcharan2345/mmds-phase-6-historical-streaming-drift-monitoring) · [Run evidence](../manifests/phase6_replay_runs.json)

## Input, replay and recovery

The Phase 2 receipt covers 16,232,943 original flows and 14 timestamp anomalies. The overlap purge removed 909,956 rows. Spark processed 15,322,987 retained flows in 49 replay microbatches. 14 retained anomaly rows contribute only to their capture day. The saved Phase 4 and Phase 5 B pipelines and their original preprocessing passed hash and synthetic scoring checks. The direct version-qualified preflight could not locate Phase 4 B. The completed notebook mounted a byte-verified private mirror of the exact version 2 files. [Private model mirror](https://www.kaggle.com/code/ramcharan2345/mmds-phase-6-pinned-chronological-models)

The query used available-now and a one-file trigger. A planned failure at batch 1 left its atomic aggregate intact and its Spark checkpoint uncommitted. Restart reused the query ID with a new run ID, replayed batch 1 without rewriting its aggregate, ignored a partial sink file, and matched the complete batch and checkpoint ranges. [Spark progress](../manifests/phase6_stream_progress.json) · [Recovery evidence](phase6_recovery_tests.csv)

## Frozen later-capture performance

| Model | TP | TN | FP | FN | Precision | Recall | F1 | PR-AUC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| random_forest | 417 | 766,721 | 4,863 | 208,108 | 7.8977% | 0.2000% | 0.00390 | 0.603592 |
| logistic_regression | 177 | 771,533 | 51 | 208,348 | 77.6316% | 0.0849% | 0.00170 | 0.623175 |
| duration_rule | 172,571 | 559,001 | 212,583 | 35,954 | 44.8057% | 82.7579% | 0.58136 | 0.407487 |

At the saved P99 distance of 16.679406, K-Means flagged 21,042 test flows, including 4,437 attack-labeled and 16,605 benign-labeled flows. Attack recall was 2.1278% and benign false-positive rate was 2.1521%. The unlabelled flag rate was 2.1469%, compared with 1.0023% in training. [Window metrics](phase6_window_metrics.csv)

## Alert and performance evidence

| Alert category | Warning | High |
| --- | --- | --- |
| INPUT_SHIFT | 15 | 0 |
| SCORE_SHIFT | 4 | 44 |
| CLUSTER_SHIFT | 10 | 0 |
| NOVELTY_RATE | 11 | 2 |
| PERFORMANCE_WARNING | 0 | 16 |

[Alert records](phase6_alerts.csv) · [Shift measures](phase6_shift_metrics.csv) · [Interpretation](../docs/phase6_drift_interpretation.md)

| Configuration | Files per trigger | Batches | Rows | Elapsed (s) | Rows/s | Checkpoint bytes |
| --- | --- | --- | --- | --- | --- | --- |
| historical | 1 | 49 | 15,322,987 | 862.32 | 17,770 | 78,005 |
| comparison-1 | 1 | 4 | 944,675 | 63.02 | 14,991 | 5,529 |
| comparison-2 | 2 | 2 | 944,675 | 47.84 | 19,746 | 3,037 |

Staging used 1,715,782,027 bytes and took 397.69 seconds. The Spark JVM peaked at 9.38 GiB RSS. The historical query recorded 3.107 seconds in Spark's offset and commit timing counters. Each comparison used the same four chunks on the same local CPU session with a separate checkpoint. [Batch timings](phase6_replay_batches.csv) · [Performance metrics](phase6_performance.csv)

## Figures

- [Timeline](figures/phase6_timeline.png)
- [Batch rows](figures/phase6_batch_rows.png)
- [Batch latency](figures/phase6_batch_latency.png)
- [Predicted attack](figures/phase6_predicted_attack.png)
- [Novelty](figures/phase6_novelty.png)
- [Occupancy](figures/phase6_occupancy.png)
- [Cluster shift](figures/phase6_cluster_shift.png)
- [Input shift](figures/phase6_input_shift.png)
- [Score shift](figures/phase6_score_shift.png)
- [Alerts](figures/phase6_alerts.png)
- [Performance](figures/phase6_performance.png)
