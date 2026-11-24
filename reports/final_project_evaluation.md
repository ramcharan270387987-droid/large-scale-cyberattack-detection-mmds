# Final project evaluation

| Component | Evaluated outcome | Interpretation |
|---|---|---|
| Data engineering | 16,232,943 reconciled canonical flows with explicit quality and provenance policy | Data quality and duplicate checks support repeatable evaluation |
| Spark SQL | Verified SQL/DataFrame aggregates with timing and valid-observation counts | Counts describe the captures |
| Supervised learning | Random Forest test recall 82.82% grouped random and 0.20% chronological | Fixed-threshold transfer failed sharply on later captures |
| Clustering | k of 5, 12 and 12 on G, B and C | Stable relative to seed changes compared with the scaling ablation |
| Novelty | Held-out Web P99 recall 55.78%, precision 1.50% | A triage signal with substantial benign alert burden |
| Streaming | 15,322,987 retained flows over 49 microbatches and a verified restart | Effectively-once local aggregate accounting |
| Monitoring | 102 historical alert records with support, evidence and thresholds | Distribution and performance shifts remain distinct |
| Dashboard | Nine pages backed by the deterministic compact data package | Suitable for a local faculty demonstration |

Thresholds and provenance are recorded. Temporal anomalies, class sparsity, repeated flows, capture effects and single-node execution limit generalization. The project’s integration is reproducible through saved compact outputs. Public hosting status is reported separately. [Academic report](../docs/final_project_report.md) · [Dashboard validation](dashboard_validation.md) · [Deployment](../docs/dashboard_deployment.md)
