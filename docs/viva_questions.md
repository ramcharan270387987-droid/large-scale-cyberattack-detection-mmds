# Viva questions and answers

1. **What is the original contribution?** The audited evidence chain connects leakage-aware comparisons, label-free pattern mining, checkpoint-tested historical replay and an explorable report. The underlying algorithms are established methods.
2. **Why use Spark?** The project repeatedly projects, joins, groups and evaluates over 16 million flows. Spark supports these operations, pipeline persistence and Structured Streaming with a shared execution model.
3. **Why use Parquet?** Column pruning and capture partitions make repeated analyses feasible. The explicit schema and provenance fields allow independent validation.
4. **What does the overlap purge protect?** Predictor-side duplicates can let a benchmark reuse training patterns. Phase 4 B/Phase 6 preserve an earlier split occurrence and remove later overlaps, changing the retained evaluation support.
5. **Why can PR-AUC and recall disagree?** PR-AUC measures ranking across thresholds. Recall in the presentation uses 0.5. PR-AUC also depends on the positive class prevalence.
6. **Why is the duration rule competitive later?** It matches many later positive examples at its fixed cutoff but produces many benign false positives. It illustrates the effect of the operating point and the composition of the evaluation cohort.
7. **What makes K-Means label-free here?** Labels are applied after assignment to describe cluster composition. Reference preprocessing and centroids use predictor data only.
8. **Why should Web novelty flags be interpreted cautiously?** Many Web attack records exceed P99, but only 1.50% of flags are attacks. The class is sparse, and the flag is distance-based.
9. **What is the difference between shift and concept drift?** Marginal predictors, scores, or cluster occupancy can change even when the conditional relation between predictors and labels is stable. The project does not identify that conditional change.
10. **Where is the streaming evidence?** Executed Spark progress includes query IDs, run IDs and 49 distinct data batch IDs. The restart reconciles checkpoint commits and sink outputs.
11. **Why exclude 14 records from intraday windows?** Their timestamps are ineligible. Trusted capture provenance still supports daily accounting, preserving multiplicity.
12. **Was refresh evaluated?** The project kept March captures frozen for final evaluation. No verified availability schedule supports an operational refresh comparison.
13. **What scalability did you establish?** Measured throughput and trigger differences on one CPU node. Distributed scaling and failure across machines remain future work.
14. **How can faculty reproduce the demo?** Run the pinned Streamlit app and checksum validator against the supplied compact package. Spark and training data are needed only to reproduce research runs.
