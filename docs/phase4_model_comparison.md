# Phase 4 model comparison

The sampled model comparison uses common training groups and identical held-out rows within each protocol. The full-training Logistic Regression refit is a separate cohort. The split designs represent different evaluation populations with different mixtures, missing families and recall denominators.

The same sampled Random Forest procedure yielded test PR-AUC of 0.9166 in A, 0.6036 in B, 0.0005 in C. The corresponding test attack prevalences were 14.9702%, 21.2757%, 0.0451%. Compare recall and precision alongside PR-AUC because the evaluation class balance changes.

The full-training Logistic Regression refit reused the sample-selected settings and feature scaling. Its test PR-AUC was 0.2833 in A, 0.6496 in B, 0.0013 in C. The sampled Logistic Regression values were 0.5931 in A, 0.6232 in B, 0.0012 in C. The observed differences describe this fixed preprocessing and optimization schedule.

At the fixed 0.5 threshold, the chronological duration rule achieved F1 0.5814. The sampled Logistic Regression, Random Forest and GBT scored 0.0017, 0.0039, 0.0112. Ranking performance and operating-point performance answer different questions. A later threshold study would need separate validation support for its intended traffic.

The scenario test retained 658 positive rows. Sampled GBT found 27 at the fixed threshold with 21,976 benign false positives. The held-out dates contain the Web attack family, and the observed label mix and capture setup limit comparisons across protocols.

## Attack-family support by partition

| Protocol | Partition | Bot | Credential brute force | DDoS | DoS | Infiltration | Web attack |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | train | 205,917 | 341,040 | 885,772 | 479,941 | 116,242 | 634 |
| A | validation | 40,467 | 17,801 | 189,228 | 85,648 | 21,285 | 140 |
| A | test | 39,807 | 22,108 | 188,933 | 88,711 | 24,407 | 154 |
| B | train | 0 | 380,949 | 1,263,933 | 654,300 | 0 | 362 |
| B | validation | 0 | 0 | 0 | 0 | 56,633 | 423 |
| B | test | 143,274 | 0 | 0 | 0 | 65,251 | 0 |
| C | train | 286,191 | 380,949 | 1,263,933 | 654,300 | 93,063 | 0 |
| C | validation | 0 | 0 | 0 | 0 | 41,842 | 0 |
| C | test | 0 | 0 | 0 | 0 | 0 | 658 |

## Attack-family evaluation

| Protocol | Family | Test rows | Training-sample rows | RF attack recall | RF benign FPR | Support |
| --- | --- | --- | --- | --- | --- | --- |
| A | Benign | 2068172 | 591111 | — | 0.0108 | reported |
| A | Bot | 39807 | 13940 | 0.9945 | — | reported |
| A | Credential brute force | 22108 | 4989 | 0.6450 | — | reported |
| A | DDoS | 188933 | 56636 | 0.9617 | — | reported |
| A | DoS | 88711 | 22380 | 0.7400 | — | reported |
| A | Infiltration | 24407 | 6207 | 0.0139 | — | reported |
| A | Web attack | 154 | 44 | 0.0779 | — | reported |
| B | Benign | 771584 | 664936 | — | 0.0063 | reported |
| B | Bot | 143274 | 0 | 0.0000 | — | reported |
| B | Credential brute force | 0 | 12384 | — | — | absent |
| B | DDoS | 0 | 80477 | — | — | absent |
| B | DoS | 0 | 37445 | — | — | absent |
| B | Infiltration | 65251 | 0 | 0.0064 | — | reported |
| B | Web attack | 0 | 28 | — | — | absent |
| C | Benign | 1457560 | 659296 | — | 0.0082 | reported |
| C | Bot | 0 | 17402 | — | — | absent |
| C | Credential brute force | 0 | 12384 | — | — | absent |
| C | DDoS | 0 | 80477 | — | — | absent |
| C | DoS | 0 | 37445 | — | — | absent |
| C | Infiltration | 0 | 5516 | — | — | absent |
| C | Web attack | 658 | 0 | 0.0243 | — | reported |

The Random Forest comparison includes these test families absent from its training sample:

- Protocol B evaluated 143,274 Bot rows as unseen-family traffic. Recall was 0.0000 with support status reported.
- Protocol B evaluated 65,251 Infiltration rows as unseen-family traffic. Recall was 0.0064 with support status reported.
- Protocol C evaluated 658 Web attack rows as unseen-family traffic. Recall was 0.0243 with support status reported.

Only supported test rows contribute to recall. The 100-row display threshold is descriptive and the correlated flow and capture groups constrain generalization. The day-level differences do not establish a feature–label mechanism.

## Interpretation

| Protocol | Model | Cohort | Three highest-magnitude terms |
| --- | --- | --- | --- |
| A | Logistic Regression | group_sample | `ack_flag_cnt` (0.6055), `rst_flag_cnt` (0.418), `pkt_len_mean` (-0.3378) |
| A | Random Forest | group_sample | `fwd_iat_mean` (0.1486), `flow_pkts_s` (0.1284), `totlen_fwd_pkts` (0.1281) |
| A | GBT | group_sample | `fwd_iat_mean` (0.2944), `totlen_fwd_pkts` (0.1926), `tot_fwd_pkts` (0.09968) |
| A | Logistic Regression | full_train_refit | `ack_flag_cnt` (0.4727), `flow_pkts_s` (0.467), `pkt_len_mean` (-0.4068) |
| B | Logistic Regression | group_sample | `pkt_len_mean` (-1.781), `flow_byts_s` (-1.112), `pkt_len_std` (0.9234) |
| B | Random Forest | group_sample | `totlen_fwd_pkts` (0.1501), `ack_flag_cnt` (0.09895), `fwd_iat_mean` (0.09745) |
| B | GBT | group_sample | `tot_bwd_pkts` (0.2339), `ack_flag_cnt` (0.2119), `totlen_fwd_pkts` (0.1592) |
| B | Logistic Regression | full_train_refit | `pkt_len_mean` (-1.867), `pkt_len_std` (0.9681), `flow_duration` (-0.9397) |
| C | Logistic Regression | group_sample | `pkt_len_mean` (-1.779), `flow_byts_s` (-1.041), `flow_duration` (-0.8031) |
| C | Random Forest | group_sample | `totlen_fwd_pkts` (0.1835), `fwd_iat_mean` (0.18), `flow_iat_mean` (0.09223) |
| C | GBT | group_sample | `totlen_fwd_pkts` (0.2517), `fwd_iat_mean` (0.179), `tot_fwd_pkts` (0.1409) |
| C | Logistic Regression | full_train_refit | `pkt_len_mean` (-1.906), `flow_duration` (-0.8674), `pkt_len_std` (0.8222) |

Logistic Regression signs are conditional associations in the scaled model coordinates. Random Forest and GBT split importances can redistribute importance among correlated features and favor variables with more useful splits. Use held-out permutation or controlled ablation for follow-up and keep group isolation fixed.

[All measured metrics](../reports/phase4_metrics.csv) · [All family and original-label results](../reports/phase4_family_recall.csv)
