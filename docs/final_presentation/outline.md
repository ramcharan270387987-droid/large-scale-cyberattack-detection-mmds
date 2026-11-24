# Final presentation outline

| Slide | Visual | Speaker notes |
|---|---|---|
| Problem | Overview generalization chart | Ask whether good shuffled-cohort results predict later performance. Introduce the academic retrospective scope. |
| Data and architecture | Pipeline diagram | Walk from raw captures through versioned Parquet. Explain provenance, timestamp eligibility and quality rules. |
| SQL analytics | Daily prevalence and family heatmap | Show how capture mix changes. Point out counts, units and descriptive scope. |
| Supervised experiments | Protocol A/B/C results | Explain predictor grouping, overlap purge and different test prevalence. Compare ranking and frozen-threshold recall. |
| Unsupervised pattern mining | Cluster profiles and Web novelty | Explain fit-specific cluster IDs, calibration and false positives. Present 55.78% recall alongside 1.50% precision. |
| Historical streaming | Batch timeline and recovery evidence | Describe monotone chunk release, inference, checkpoint interruption and aggregate idempotency. |
| Monitoring | Alerts Explorer | Show observed/reference/threshold/support for an alert. Distinguish score shift and reported performance degradation. |
| Evaluation | Measured performance and limitations | Report 17,770 flows/s in one CPU environment. State what generalization and concept drift remain unverified. |
| Demonstration | Streamlit | Follow the faculty walkthrough. Use the saved compact evidence. |
| Questions | Findings and contributions | Emphasize methodology and usable evidence over algorithm invention. |

[Full speaker walkthrough](../faculty_demo_guide.md) · [Viva preparation](../viva_questions.md)
