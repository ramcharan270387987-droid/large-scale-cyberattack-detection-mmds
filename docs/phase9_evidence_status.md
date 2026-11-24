# Phase 9 evidence status

The input audit and all six family-classification runs are available in the
[experiment manifest](../manifests/phase9_experiments.json).
The grouped-random run, chronological run and four family holdouts are validated.
The chronological B test set has 208,525 retained attacks from unsupported families
and zero from training-supported families. Its closed-set accuracy, known-family
recall and known-family false rejection are undefined.

## Existing robustness evidence

| Requirement | Evidence and status |
|---|---|
| Class weights | Validation results for unweighted, inverse-frequency and capped inverse-frequency LR and RF are available in [closed-set metrics](../reports/phase9_closed_set_metrics.csv). Final-test class-weight sensitivity on matched rows is pending. |
| Second seed | Seed 23014 is prespecified. A matched bounded comparison is pending. |
| Duplicate weighting | Cross-partition predictor-group retention is documented. Matched duplicate-weighting sensitivity is pending. |
| Confidence and uncertainty | Maximum score, margin, entropy, reference novelty and a combined rule were evaluated at frozen thresholds in [open-set metrics](../reports/phase9_open_set_metrics.csv). Full score distributions and risk–coverage curves are pending. |
| Rejection thresholds | The 1%, 5% and 10% known-validation budgets were evaluated with whole-bin ties retained. Realized test rejection can differ from the calibration budget. |
| Low-support families | [Per-family metrics](../reports/phase9_per_family.csv) and [support](../reports/phase9_family_support.csv) are available. Stratified error examples and uncertainty assessments are pending. |
| Known rejection and unknown acceptance | Existing tables contain aggregate known rejection and unknown rejection. Unknown false acceptance is the complement of unknown rejection for supported unknown populations. Per-day and high-confidence error breakdowns are pending. |
| Uncertainty intervals | No row-independent intervals are reported. Capture-day support is sparse and the flows are correlated. |

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
