# Faculty demonstration guide

## 60-second introduction

This project investigates why a cyberattack detector can score well in a benchmark and still fail when it encounters a later capture. We audited over 16 million historical network flows using Spark, compared grouped-random, chronological and held-out scenarios, and measured how supervised predictions and K-Means distance flags changed. Random Forest recall dropped from about 83% in grouped-random testing to 0.20% on later captures at the frozen threshold. We also replayed over 15 million flows through Structured Streaming, forced a checkpoint restart, and reconciled 49 batches. The dashboard makes the verified evidence explorable and shows where the data supports conclusions about generalization, novelty and alert behavior.

## Five-minute browser walkthrough

| Time | What to open | What to explain |
|---|---|---|
| 0:00–0:45 | Overview | Data scale, corpus caveats and the recall gap |
| 0:45–1:25 | Dataset explorer, then Spark SQL analytics | Cleaning, capture counts, descriptive distributions and workload timings |
| 1:25–2:25 | Machine learning, A then B then C | Grouping, overlap purge, evaluation prevalence and Random Forest confusion |
| 2:25–3:10 | Clustering B, then Novelty C at P99 | Frozen centroids, label-free assignment and the Web precision tradeoff |
| 3:10–4:15 | Historical replay, March 2 | Three-hour windows, captured score divergence, checkpoint tests |
| 4:15–5:00 | Alerts explorer, high severity, then export | Evidence categories and support. Close at Architecture |

## Checklist and troubleshooting

- Use the dashboard from a verified public deployment if available, or launch the exact `work` checkout using the [quick start](dashboard_quickstart.md).
- Open Overview, all nine navigation routes, and check that filters have populated examples. The default demo uses saved results.
- Inspect protocol C test prevalence with any PR-AUC comparison. Show unsupported family rows without treating an undefined metric as zero.
- If alert results are empty, reset filters or lower minimum support. A CSV export is enabled when matching records exist.
- If a checksum error appears, restore or regenerate the aggregate package. If Streamlit is missing, activate the environment and reinstall the pinned dashboard requirements.
- If hosted startup fails, verify branch, entry point, dependency file and Python version. [Deployment](dashboard_deployment.md)
