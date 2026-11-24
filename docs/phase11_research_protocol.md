# Phase 11 prespecified research protocol

Version phase11-v1 begins from 901a9f33954653cf6b327aa366700d7b91d997da. Phase 12 is gated on validated Phase 11 completion and a verified GitHub push.

## Populations and signals

Reuse the checksum-pinned Phase 2 receipt and Phase 6 retained chronological replay. Historical results are retrospective. Aggregate windows preserve replay sequence and capture gaps. Historical feature JS distances, RF score histograms, occupancy and performance come from saved Phase 6 Spark aggregates. Window detectors report delay in windows. No claim of raw-observation coverage is made for aggregate monitoring. No authoritative historical drift-event labels exist.

Synthetic streams contain 4096 observations, with changes beginning at index 2048 and at 3072 for a recurring return. Three seeds are 23013, 23014 and 23015. Separate independent calibration streams use seeds 13013, 13014 and 13015. Generate stationary, abrupt, gradual, incremental, recurring, variance, correlation, prior, missingness and predictive-error scenarios. Explicit conditional-relation reversal is a separate synthetic concept scenario. Mean signals, covariance products, missingness indicators, priors and released binary errors preserve their distinct semantics. Synthetic shifts never imply real attack discovery.

## Detectors and calibration

Use River 0.22.0 ADWIN, Page-Hinkley and KSWIN after API verification. DDM consumes only binary errors released after delays of zero, one or three 64-observation windows. Frozen-reference JS in bits and PSI use ten reference bins, 64-observation evaluation windows and declared additive smoothing of 1e-6. Warm-up uses 256 observations. ADWIN delta candidates .001 and .01, Page-Hinkley threshold 10 and 30 with tolerance .005, and KSWIN alpha .001 and .01 with window size 100 and reference sample 30 are fixed before evaluation. DDM uses warning two and drift three standard deviations after at least 30 binary errors.

Primary selection minimizes missed changes only among configurations meeting stationary calibration false alarms at most one per 1000 eligible observations. Where tied, prefer lower stationary false alarms and lower update time. If no configuration is feasible retain the most conservative candidate and disclose the failed budget. Synthetic evaluation seeds and historic evaluation labels do not enter calibration. JS and PSI thresholds are calibration-only empirical 99th percentiles, with a fixed JS .1 control. Ensemble requires two detector families to alert within a 64-observation interval.

## Event metrics and safeguards

Match each alert to at most one as-yet unmatched true episode starting within the preceding 512 observations. One episode contributes at most one true detection. Other alerts count separately as repeated in-episode alerts or stationary false alarms. No detection has undefined delay. Report observation and 64-observation-window delays separately. Historical alert agreement is descriptive. Label-dependent updates occur only after simulated release, including end-of-stream pending labels.

Compare window sizes 32, 64 and 128, two shift magnitudes and all three seeds where supported. Include no-detector and fixed-JS controls, individual detectors and the prespecified ensemble. State checkpoints must preserve config, update sequence, duplicate-batch suppression and detector state. Validate uninterrupted versus restored replay and report serialized state bytes and CPU timing.

## Resources and acceptance

Use bounded synthetic data locally and private Kaggle CPU with Spark 4.3.0 and four workers. Reuse saved Spark aggregates rather than reprocessing millions of flows unnecessarily. Record runtime versions, source and output hashes and actual logs. Each validated major stage is committed, pushed and independently checked. Phase 11 remains incomplete until synthetic, historical, label timing, state, figures, full regressions and actual Kaggle execution are verified. Phase 12 may begin only after that gate is satisfied.
