# Phase 3 research readiness

Start future comparisons with duration, directional packets and bytes, packet length, mean inter-arrival time and TCP flags. Use correlations to prioritize redundant pairs for a controlled ablation. Treat IP protocol as categorical context and evaluate it separately. Exclude target values, time, capture day, source identity, port and fingerprints from the feature vector. Use provenance and fingerprints to group records and check split overlap.

## Missingness and transformation design

The rows below identify every canonical candidate with observed missingness. Choose an imputation and missingness-indicator policy inside each training partition. Consider log transforms and robust training-only scaling for nonnegative heavy-tailed measures in clustering or other scale-sensitive experiments. [All 77 candidates](phase3_feature_missingness.csv)

| Feature | Missing rows | Missing share | At least 5% |
| --- | --- | --- | --- |
| init_bwd_win_byts | 8,255,549 | 50.857% | Yes |
| init_fwd_win_byts | 4,432,608 | 27.306% | Yes |
| flow_pkts_s | 95,774 | 0.590% | No |
| flow_byts_s | 95,760 | 0.590% | No |
| flow_iat_min | 15 | 0.000% | No |
| fwd_iat_min | 15 | 0.000% | No |
| flow_duration | 14 | 0.000% | No |
| flow_iat_mean | 14 | 0.000% | No |
| fwd_iat_mean | 14 | 0.000% | No |
| fwd_iat_tot | 14 | 0.000% | No |
| flow_iat_max | 3 | 0.000% | No |
| fwd_iat_max | 3 | 0.000% | No |

## Time windows and class support

The rarest original labels were SQL Injection (87), Brute Force -XSS (230), Brute Force -Web (611). 50 family-day combinations had zero observed attacks. For held-out capture comparisons, publish support and distinguish absent classes from errors.

Track duration, packet count, and byte volume with three-hour wall-clock windows, partitioned by capture day and binary label. Use hourly counts separately to monitor prevalence. Compare the same class across days with a prespecified support floor and report coverage. Changes can reflect capture protocols or the mix of activity within each class. Evidence of concept drift would require controlled later evaluation of the relationship between features and labeled outcomes.

Among benign windows with at least 500 rows, approximate median durations ranged from 1,164 µs on 2018-02-28 at hour 0 (118,029 rows) to 1.11e+08 µs on 2018-02-21 at hour 9 (1,995 rows). This is a descriptive within-label contrast.

| Capture day | Families with zero observed attacks |
| --- | --- |
| 2018-02-14 | Bot, DDoS, DoS, Infiltration, Web attack |
| 2018-02-15 | Bot, Credential brute force, DDoS, Infiltration, Web attack |
| 2018-02-16 | Bot, Credential brute force, DDoS, Infiltration, Web attack |
| 2018-02-20 | Bot, Credential brute force, DoS, Infiltration, Web attack |
| 2018-02-21 | Bot, Credential brute force, DoS, Infiltration, Web attack |
| 2018-02-22 | Bot, Credential brute force, DDoS, DoS, Infiltration |
| 2018-02-23 | Bot, Credential brute force, DDoS, DoS, Infiltration |
| 2018-02-28 | Bot, Credential brute force, DDoS, DoS, Web attack |
| 2018-03-01 | Bot, Credential brute force, DDoS, DoS, Web attack |
| 2018-03-02 | Credential brute force, DDoS, DoS, Infiltration, Web attack |

[Family-day counts](phase3_family_by_day.csv) · [Window statistics](phase3_time_windows.csv)
