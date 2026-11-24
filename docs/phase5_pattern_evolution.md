# Phase 5 pattern evolution

## Retrospective behavior and capture composition

The global clusters combine behavioral summaries and post-fit capture context. Reported feature means use the available clean values in each assigned cluster.

| Cluster | Rows | Attack share | Mean duration (µs) | Mean forward packets | Mean backward packets | Largest day contribution |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 3,313,334 | 35.9252% | 1,095.6 | 1.77 | 0.37 | 2018-02-20 · 35.6039% |
| 1 | 4,931,789 | 6.8878% | 29,438.2 | 1.61 | 1.72 | 2018-02-20 · 53.1707% |
| 2 | 2,115,505 | 33.4574% | 31,471,329.9 | 3.83 | 0.35 | 2018-02-20 · 46.3859% |
| 3 | 602,891 | 1.4498% | 3,055,178.3 | 2.72 | 0.41 | 2018-02-20 · 63.2766% |
| 4 | 5,269,424 | 9.5207% | 24,537,855.7 | 68.02 | 17.42 | 2018-02-20 · 52.8334% |

Counting one representative per exact source digest yields 15,822,236 records. Global cluster occupancy changes by 0.000475 Jensen–Shannon bits under that count.

| Rare original label | Records | Observed cluster distribution |
| --- | --- | --- |
| Brute Force -Web | 611 | 0 (189), 1 (2), 2 (154), 3 (1), 4 (265) |
| Brute Force -XSS | 230 | 0 (112), 1 (1), 2 (5), 4 (112) |
| SQL Injection | 87 | 0 (34), 2 (5), 4 (48) |

Those rare-label counts describe recorded support. Repeated or related flows can reduce effective sample size.

## Capture-day occupancy

Jensen–Shannon values compare the full retained reference occupancy with each observed day or three-hour wall-clock bin. The source timezone is unverified. The model is frozen within each experiment. Labels provide post-fit composition only.

| Experiment | Largest described daily shift | Rows | Jensen–Shannon bits | Occupied clusters |
| --- | --- | --- | --- | --- |
| G | 2018-02-16 | 1,048,574 | 0.16632 | 5 |
| B | 2018-03-02 | 748,636 | 0.09671 | 12 |
| C | 2018-02-23 | 729,537 | 0.18816 | 12 |

### Held-out dates

| Experiment | Capture day | Rows | Jensen–Shannon bits | Largest cluster and share | P99 flag rate |
| --- | --- | --- | --- | --- | --- |
| B | 2018-03-01 | 231,473 | 0.04560 | 0 · 23.4196% | 3.7395% |
| B | 2018-03-02 | 748,636 | 0.09671 | 8 · 19.1263% | 1.6545% |
| C | 2018-02-22 | 728,681 | 0.18470 | 7 · 27.1506% | 1.6500% |
| C | 2018-02-23 | 729,537 | 0.18816 | 7 · 27.3286% | 1.7005% |

The day and window summaries also retain mean flow attributes, distance tails, flag counts and an explicit cohort denominator. Day-specific behavior and attack composition can change together. The observed contrasts describe the capture collection and do not identify a feature-to-label mechanism. [Occupancy](../reports/phase5_cluster_occupancy.csv) · [Shifts](../reports/phase5_temporal_shift.csv) · [Window family support](../reports/phase5_window_family.csv)

## Phase 4 generalization cases

| Cohort | Family | Matched test rows | P99 flags | P99 flag recall | Phase 4 RF recall |
| --- | --- | --- | --- | --- | --- |
| B | Bot | 143,274 | 987 | 0.6889% | 0.0014% |
| B | Infiltration | 65,251 | 3,450 | 5.2873% | 0.6360% |
| C | Web attack | 658 | 367 | 55.7751% | 2.4316% |

The historical P99 flagged 2.1278% of attacks and 2.1521% of benign flows. In the Web capture holdout, 55.7751% of attacks exceeded P99. Only 1.5023% of flagged flows carried an attack label in that low-prevalence cohort.

The comparison recreates Phase 4's retained cohorts and checks support. It uses aggregate metrics because Phase 4 preserved no row-level predictions. Random Forest operates at a 0.5 classification threshold, and the centroid rule uses a reference P99 cutoff. Compare benign false positives and precision before considering either signal for a detection decision. Distance can complement model review by identifying unusual traffic for inspection. These experiments neither establish that flagged rows represent new attacks nor demonstrate an improvement at matched operating points.

## Stability and feature influence

| Experiment | Paired probe rows | Alternative-seed ARI | Linear-scaling ARI | Largest between-centroid contribution |
| --- | --- | --- | --- | --- |
| G | 18,099 | 0.8955 | 0.2900 | pkt_len_mean (7.4552%) |
| B | 14,426 | 0.8504 | 0.2183 | fin_flag_cnt (6.4919%) |
| C | 15,229 | 0.7974 | 0.4202 | fin_flag_cnt (6.5127%) |

| Experiment | Empty clusters across grid | Smallest selected cluster share | Predictors dropped | Near-constant predictors | Strongest weighted centroid correlation |
| --- | --- | --- | --- | --- | --- |
| G | 0 | 4.3376% | 0 | 0 | totlen_fwd_pkts / pkt_len_std (+0.998) |
| B | 0 | 0.3841% | 0 | 0 | flow_duration / flow_pkts_s (-0.990) |
| C | 0 | 0.4006% | 0 | 0 | flow_duration / flow_pkts_s (-0.992) |

ARI is invariant to cluster ID permutations. The contribution statistic is the fitted-cluster-size-weighted between-centroid variance share in the scaled space. Correlations use the selected cluster centers, weighted by training counts. They indicate where features describe similar centroid profiles. Per-flow redundancy would require within-cluster covariance. [Full results and figures](../reports/phase5_clustering_results.md)
