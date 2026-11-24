# Phase 10 frequent and emerging pattern mining results

## Protocol and provenance

The phase10-v1 protocol preceded fitting. All 16,232,943 feature-ready flows were verified against the pinned Phase 2 version 1 receipt. The corpus contains 13,484,708 benign and 2,748,235 attack flows across ten captures. The 18-predictor audit creates one unique item per predictor. Primary FP-Growth uses six numerical predictors with frozen three-bin discretization.

## Mining and associations

Spark 4.3.0 executed FP-Growth over the full eligible population. Subsequent class, family and temporal enumeration sums complete signature counts. These operations use exact sufficient counts.

| Minimum support | Itemsets | Rules at confidence 0.70 | Fit and itemset summary seconds |
|---|---:|---:|---:|
| 10% | 203 | 468 | 71.97 |
| 5% | 298 | 629 | 72.26 |
| 2% | 539 | 1009 | 71.25 |
| 1% | 759 | 1428 | 70.12 |

The primary registry contains all 298 itemsets. The archived rule export contains 500 of 629 rules. Joint, antecedent and consequent counts reconstruct support, confidence, lift, leverage and conviction. Twenty canonical rules were independently verified from signature predicates. Confidence one has infinite conviction when consequent support is below one. Undefined ratios remain explicit.

## Contrast, families and temporal evolution

Class-conditioned supports and enrichment use the appropriate benign and attack denominators. All six attack families have separate support and pattern tables. Family and capture-day associations constrain causal interpretation.
- Bot has 286,191 flows and 126 eligible family patterns.
- Credential brute force has 380,949 flows and 126 eligible family patterns.
- DDoS has 1,263,933 flows and 202 eligible family patterns.
- DoS has 654,300 flows and 97 eligible family patterns.
- Infiltration has 161,934 flows and 206 eligible family patterns.
- Web attack has 928 flows and 171 eligible family patterns.

The fixed-reference analysis tracks 5,610 pattern/capture observations across 561 patterns. Categories are {'stable': 3296, 'declining': 1724, 'emerging': 278, 'disappearing': 144, 'strongly_emerging': 168}. Of these patterns, 174 exceed 5% support on at least eight captures. Categories compare each capture with the frozen reference. Zero-count disappearance and support-threshold crossings have separate definitions.

Support-weighted Jaccard complements ordinary set overlap. Capture deletion ranges describe sensitivity to the ten observed captures. Calendar gaps and fixed binary-mixture supports are recorded. Neither statistic supplies independent-flow significance.

## Chronological detection

Twenty patterns were selected using only retained training counts. Validation chose whole-score thresholds under a 1% benign FPR ceiling. The primary configuration was preserved after observing test outcomes.

| Configuration | TP | FP | FN | TN | Recall | Benign FPR | Precision |
|---|---:|---:|---:|---:|---:|---:|---:|
| Primary three bins | 0 | 0 | 208525 | 771584 | 0.0000% | 0.0000% | NA |
| Five-bin sensitivity | 461 | 4137 | 208064 | 767447 | 0.2211% | 0.5362% | 0.10026098303610265 |

Both evaluations use 980,109 retained test flows, comprising 771,584 benign and 208,525 attacks. The primary policy produced no alerts. The five-bin sensitivity produced 461 true positives and 4,137 false positives. This is a negative operational result. Its larger detection count does not establish a better acceptable detection tradeoff.

## Robustness and computational scope

Three-bin, five-bin and domain definitions and flow versus predictor-group weights have separate tables. Full-corpus group-weighted mass is approximately 10,368,838 predictor groups. Domain group weights were not exported. No claim is made for that unsupported comparison. The original full-corpus mining run took 349.41 seconds across four supports and peaked at 8.32 GiB JVM RSS. Timing scopes differ between mining, transaction preparation, rule evaluation and offline signature scoring. Per-flow deployed latency and multi-node scaling were not measured.

| Target sample | Actual flows | FP-Growth seconds | Transaction seconds | Rule seconds |
|---:|---:|---:|---:|---:|
| 1,000,000 | 996,584 | 10.75 | 135.02 | 1.84 |
| 4,000,000 | 4,071,873 | 20.76 | 105.67 | 1.42 |
| 8,000,000 | 7,979,942 | 34.45 | 110.80 | 1.20 |

## Persistence, dashboard and validation

The archived version 2 FP-Growth model was downloaded and every component matched its receipt hash. Independent reload reproduced all 298 itemsets and 629 rules. Three deterministic probes matched predictions reconstructed directly from association rules. Discretization, item vocabulary and frozen detector policies have hashed registries.

The isolated Emerging Attack Pattern Explorer provides filters, charts and downloads from compact evidence. It passed 32 support/section combinations and an empty-rule filter state. The protected public dashboard retains its original revision.

## Scientific contribution and limits

The contribution is a reproducible experiment using standard FP-Growth and exact aggregate support accounting. Frequent associations and prevalence changes cannot establish causation, concept drift or discovery of a new attack. Capture conditions, family/day confounding, discretization and duplicates materially limit interpretation. PrefixSpan is unsupported because the verified contract lacks defensible session identifiers and ordering semantics. Independent external validation remains future work.
