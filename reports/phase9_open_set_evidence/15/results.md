# Chronological B and Web rejection evidence

Kaggle version 15 completed additional evidence for B and the Web holdout.
Both archived classifiers reproduced their maximum, margin and entropy
thresholds and historical rejection counts. The new training-reference
K-Means pipelines reproduced the previous novelty and combined operating
cutoffs. Their private artifacts are stored under
`mmds_phase9_open_set/{scenario}/models/family_kmeans`.

B's maximum-score rule at the 5% calibration budget rejected 40,680 of
65,251 unknown attacks on 1 March (62.34%) and 38 of 143,274 on 2 March
(0.0265%). The B training and test attack capture days did not overlap.
Web's held-out groups rejected 15 of 362 attacks on 22 February and 17 of
566 on 23 February. Eight capture days overlapped between Web training
and evaluation attacks overall. The two held-out-family days supplied no
known training attacks.

These contrasts are descriptive. Attack family and capture conditions vary
together, which limits conclusions about family discrimination and novelty.

The worker used Spark 4.3.0, four CPUs, an 8 GiB driver and 48 partitions.
Elapsed time was 560.3 seconds and peak driver RSS was 4,702,318,592 bytes.
The retrieved aggregate artifacts totalled 320,147 bytes. The registered
B and Web novelty pipelines contain 20,293 and 20,617 bytes, respectively.

[Worker receipt](receipt.json) · [B score histogram](B/score_histograms.csv)
· [B daily decisions](B/day_rejection.csv)
· [Web score histogram](Web/score_histograms.csv)
· [Web daily decisions](Web/day_rejection.csv)
