# Phase 9 evidence status

The input audit and all six family-classification runs are available in the
[experiment manifest](../manifests/phase9_experiments.json).
The grouped-random run, chronological run and four family holdouts are validated.
The chronological B test set has 208,525 retained attacks from unsupported families
and zero from training-supported families. Its closed-set accuracy, known-family
recall and known-family false rejection are undefined. The [B](../reports/phase9_hierarchy/B/results.md) and
[C](../reports/phase9_hierarchy/C/results.md) full-population hierarchies are
validated. Their archived binary confusion counts exactly match Phase 4 and
Phase 8. Only B has a strictly chronological binary policy.

## Matched closed-set references

The [reference baselines](../reports/phase9_reference_baselines/phase9_reference_baselines.csv)
use the exact archived test support. The majority baseline predicts the most
frequent training-supported family. The training-prior reference independently
draws labels according to their training proportions and uses analytical expected
confusion cells. Its reported F1 is calculated from those expected cells.
In grouped-random A, the selected RF achieved accuracy 74.05% and macro F1
0.633, versus 51.89% and 0.114 for majority and 30.92% and 0.162 for the
training-prior reference. All B closed-set comparisons have zero support.

## Existing robustness evidence

| Requirement | Evidence and status |
|---|---|
| Class weights | Validation results for unweighted, inverse-frequency and capped inverse-frequency LR and RF are available in [closed-set metrics](../reports/phase9_closed_set_metrics.csv). Matched RF test sensitivity is validated in [version 14](../reports/phase9_sensitivity/results.md). |
| Second seed | Version 14 validated the seed 23014 comparison on identical grouped-random test rows. |
| Duplicate weighting | Version 14 validated duplicate-weighted training and separately measured equal predictor-group test weights. |
| Confidence and uncertainty | Maximum score, margin, entropy, reference novelty and a combined rule were evaluated at frozen thresholds in [open-set metrics](../reports/phase9_open_set_metrics.csv). Versions 15 and 16 verified score distributions, risk–coverage and supported ROC/PR curves. |
| Rejection thresholds | The 1%, 5% and 10% known-validation budgets were evaluated with whole-bin ties retained. Realized test rejection can differ from the calibration budget. |
| Low-support families | [Per-family metrics](../reports/phase9_per_family.csv) and [support](../reports/phase9_family_support.csv) are available. Version 14 contains aggregate high-confidence errors by capture day and actual and predicted family. |
| Known rejection and unknown acceptance | Existing tables contain aggregate known rejection and unknown rejection. Unknown false acceptance is the complement of unknown rejection for supported unknown populations. Versions 15 and 16 verified daily decisions and aggregate false-rejection and false-acceptance groups. Version 14 supplies the separate high-confidence error analysis. |
| Uncertainty intervals | No row-independent intervals are reported. Flows are correlated and capture-day support is sparse. Version 14 reports a descriptive leave-one-day-out range. |

## Capture-day association

The [support heatmap](../reports/figures/phase9_capture_family_support.png)
uses only the aggregate input audit. The six attack families occur on one or
two capture days each. All 286,191 Bot flows and all 380,949 credential
brute-force flows for their respective families come from a single day each.
Of 654,300 DoS flows, 91.98% come from one day. The Web attack family contains
928 flows across two days. The grouped-random split prevents predictor-group
overlap and can still share capture days between roles. B has disjoint,
ordered capture dates. C also has disjoint roles but includes training and
validation days after its test dates, making the original archived gate
evaluation retrospective.

Predictor distributions can encode capture conditions even though capture day
is excluded from the 18 predictors. The holdout results therefore cannot
isolate family identity from capture conditions or establish generalization to
a genuinely novel attack. The study uses a retrospective corpus without
independent external confirmation.

## Frozen maximum-score operating point

These rows use the 5% calibration budget from the verified open-set table.
They measure family-stage behavior on attack rows.

| Scenario | Known support | Unknown support | Known false rejection | Unknown rejection |
|---|---:|---:|---:|---:|
| B | 0 | 208,525 | Undefined | 19.53% |
| Bot | 314,058 | 286,191 | 1.34% | 8.12% |
| DDoS | 109,434 | 1,263,933 | 7.11% | 0.0048% |
| Infiltration | 300,984 | 161,934 | 2.83% | 30.15% |
| Web | 363,966 | 928 | 2.77% | 3.45% |

The DDoS holdout rejected only 61 unknown flows with this rule. It also
exceeded the calibration budget on known test flows. The known-family
rejection budget on validation did not imply equivalent rejection on the
matched test split.

## Additional rejection evidence and persistence

The [B and Web batch](../reports/phase9_open_set_evidence/15/results.md) and
[Bot, Infiltration and DDoS batch](../reports/phase9_open_set_evidence/16/results.md)
provide matched capture-day outcomes, confidence histograms, grouped error
examples and feature quantiles. The reconstructed novelty pipelines matched
the frozen novelty and combined thresholds. All 75 historical operating points
reconciled, including accepted coverage and accuracy among accepted decisions.

The [curves](../reports/figures/phase9_risk_coverage_roc_pr.png) show supported
risk–coverage, ROC and PR evidence. B has no known attack examples, so its
rejection ROC and PR remain undefined. The [daily figure](../reports/figures/phase9_per_day_rejection.png)
shows the large day-to-day difference in chronological B and the low DDoS
rejection on both capture days.
