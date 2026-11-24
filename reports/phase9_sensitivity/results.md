# Grouped-random sensitivity

Kaggle version 14 scored the same 364,120 known-family evaluation flows for
every comparison. Each predictor group contributes one total unit under
group-weighted evaluation (191,704 groups). Class weights and seed variants
were fixed before fitting, and their test outcomes did not change the
original selected classifier.

| Variant | Flow accuracy | Flow macro F1 | Group-weighted accuracy | Group-weighted macro F1 |
|---|---:|---:|---:|---:|
| Original capped inverse, seed 23013 | 74.05% | 0.633 | 94.62% | 0.781 |
| Unweighted | 78.76% | 0.610 | 95.12% | 0.779 |
| Inverse frequency | 71.28% | 0.602 | 93.12% | 0.778 |
| Duplicate-group training weights | 65.51% | 0.565 | 94.97% | 0.787 |
| Capped inverse, seed 23014 | 65.86% | 0.563 | 91.15% | 0.726 |

The second seed reduced macro F1 under both weighting schemes. Duplicate weighting reduced flow macro F1 and slightly increased group-weighted macro F1. Unweighted fitting improved flow accuracy while
reducing flow macro F1. Group weights change the target from a random flow
to a random predictor group, which explains why the two evaluation columns
can give different impressions.

The frozen RF made 4,837 incorrect predictions with maximum vote score at
least 0.90. Its descriptive leave-one-capture-day-out flow accuracy ranged
from 66.87% to 83.79%. This is a sensitivity range, with no independent
flow-level or capture-level replication claim.

Spark 4.3.0 with four CPUs and an 8 GiB driver ran for 131.3 seconds. Peak
driver RSS was 3,261,235,200 bytes. The retrieved receipt and aggregate CSVs
totalled 19,348 bytes. [Receipt](phase9_sensitivity_receipt.json)
· [Metrics](phase9_sensitivity_metrics.csv) · [Confusion](phase9_sensitivity_confusion.csv)
· [Capture days](phase9_sensitivity_day.csv)
· [High-confidence errors](phase9_sensitivity_high_confidence_errors.csv)
