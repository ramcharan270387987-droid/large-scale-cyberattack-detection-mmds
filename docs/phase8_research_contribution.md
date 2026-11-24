# Phase 8 research contribution

Earlier supervised models ranked traffic above chance while producing very low chronological recall at 0.5. The study adds a common validation FPR ceiling, disjoint probability and fusion calibration, reference-normalized novelty, matched ablations and selective triage after freezing the operating policies. The contribution is experimental methodology and engineering integration using established algorithms.

The deltas below use the same held-out rows. Positive recall and negative FPR deltas favor the first method. H1 compares the same RF at the validation-selected threshold and at 0.5. H2 compares the validation-selected weighted candidate with its unweighted algorithm. H3 compares the selected fusion with each single-signal policy. H4 compares automatic errors before and after referrals and reports coverage.

| Population | H1 recall Δ | H1 FPR Δ | H2 recall Δ | H2 FPR Δ | H3 recall Δ vs supervised | H3 FPR Δ vs supervised | H3 recall Δ vs novelty | H3 FPR Δ vs novelty | Binary error | H4 automatic error | Automatic coverage | Review rate | Fusion/base time |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B | +0.095 pp | +0.016 pp | +0.304 pp | +0.448 pp | +0.000 pp | +0.001 pp | +0.000 pp | +0.000 pp | 21.276% | 21.276% | 100.000% | 0.000% | 4.79× |
| C | +0.000 pp | -0.340 pp | +0.608 pp | +3.889 pp | +16.413 pp | +0.521 pp | +16.413 pp | +0.522 pp | 0.560% | 0.552% | 98.132% | 1.868% | 4.44× |
| R1 | +0.000 pp | +0.004 pp | -1.032 pp | -0.003 pp | +0.000 pp | +0.000 pp | +0.000 pp | +0.000 pp | 31.730% | 31.730% | 100.000% | 0.000% | 3.33× |
| R2 | -1.490 pp | -1.045 pp | +0.655 pp | +0.297 pp | +0.000 pp | +0.002 pp | +0.000 pp | +0.000 pp | 12.942% | 12.942% | 100.000% | 0.000% | 4.05× |

Selected fusion did not demonstrate a recall gain without added false positives in the supported populations.
Triage conditions error on the automated subset. Review work and missed attacks remain visible in the full population. Compute ratios come from matched single-node scoring and can vary with Spark caching and query plans.

Ten correlated capture days, family/day association, one training seed and retrospective access constrain inference. An independently reserved compatible capture and a prospective comparison of frozen policies at a feasible alert workload are needed before deployment. The literature review should investigate calibration under temporal shift, fixed-FPR transfer, classifier–novelty complementarity and selective prediction under constrained review.

[Measured results](../reports/phase8_hybrid_results.md) · [Evaluation limitations](phase8_evaluation_limitations.md)
