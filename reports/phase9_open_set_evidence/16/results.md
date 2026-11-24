# Bot, Infiltration and DDoS rejection evidence

Kaggle version 16 completed and reconciled the three remaining holdouts.
The archived confidence thresholds and measured rejection counts matched.
Each reconstructed novelty pipeline reproduced the original novelty and
combined cutoff bins. The private models appear under
`mmds_phase9_open_set/{scenario}/models/family_kmeans`.

| Holdout | Known support | Unknown support | Unknown rejected by day at the 5% maximum-score budget | Training/test capture-day overlap |
|---|---:|---:|---|---:|
| Bot | 314,058 | 286,191 | 23,242 of 286,191 on 2 March | 9 |
| Infiltration | 300,984 | 161,934 | 23,854 of 68,871 on 28 February and 24,963 of 93,063 on 1 March | 8 |
| DDoS | 109,434 | 1,263,933 | 0 of 576,191 on 20 February and 61 of 687,742 on 21 February | 8 |

The support and error tables are aggregate. Known and unknown amounts vary
by capture day and family, limiting generalization beyond the recorded captures.

The worker used Spark 4.3.0, four CPUs, an 8 GiB driver and 48 shuffle
partitions. Its elapsed time was 300.5 seconds and measured peak driver RSS
was 3,943,927,808 bytes. The compact retrieved artifacts totalled 547,945
bytes. Registered novelty pipeline sizes were 20,586 bytes for Bot, 20,348
bytes for Infiltration and 20,562 bytes for DDoS.

[Worker receipt](receipt.json) · [Bot daily decisions](Bot/day_rejection.csv)
· [Infiltration daily decisions](Infiltration/day_rejection.csv)
· [DDoS daily decisions](DDoS/day_rejection.csv)
