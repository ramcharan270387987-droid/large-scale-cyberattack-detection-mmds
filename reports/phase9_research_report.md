# Phase 9 multiclass and open-set evaluation

## Repository and protocol

Phase 9 resumed from `f315c872f37c8ae24fa60c9e6c4ca84314f12697`
on `research-v2`, building on Phase 8 commit
`beb558748b24309b1f752b2d744614f31b1d9351`. The input audit verified
16,232,943 flows, including 2,748,235 attacks, from the checksum-pinned
Phase 2 version 1 producer. The study uses 18 frozen numerical predictors
and training-derived family IDs.

Original Phase 9 Kaggle versions 1, 2, 7, 8, 9, 10 and 11 were reused.
All 33 committed per-stage aggregate hashes matched their receipts. The
[protocol](../docs/phase9_research_protocol.md),
[methodology](../docs/phase9_multiclass_methodology.md) and
[C amendment](../docs/phase9_c_methodological_amendment.md) describe
eligibility, preprocessing, sampling and frozen thresholds.

## Grouped-random, chronological and family holdout results

| Scenario | Version | Selected model | Known evaluation attacks | Accuracy | Macro F1 |
|---|---:|---|---:|---:|---:|
| Grouped-random A | 2 | RF, capped inverse | 364,120 | 74.05% | 0.633 |
| Chronological B | 7 | LR, inverse | 0 | Undefined | Undefined |
| Web holdout | 8 | RF, capped inverse | 363,966 | 73.73% | 0.753 |
| Bot holdout | 9 | RF, capped inverse | 314,058 | 68.20% | 0.611 |
| Infiltration holdout | 10 | RF, capped inverse | 300,984 | 74.42% | 0.767 |
| DDoS holdout | 11 | LR, capped inverse | 109,434 | 76.08% | 0.697 |

The grouped-random RF improved on the majority baseline's 51.89% accuracy
and 0.114 macro F1. The analytical training-prior reference had 30.92%
accuracy and 0.162 macro F1 computed from expected confusion cells. The
frozen RF predicted zero Web attack flows among 154 true Web attacks in A.
Web precision is undefined, recall is zero and F1 is zero.

Chronological B has 208,525 attacks, all from families absent during family
training. Its closed-set accuracy, known-family recall, known-family false
rejection and known-versus-unknown ROC and PR are undefined. Rejection recall
over the unknowns remains measurable. C's earlier-only family stage also has
zero known test attacks.

[Reference baselines](phase9_reference_baselines/phase9_reference_baselines.csv)
· [Closed-set results](phase9_closed_set_metrics.csv)
· [Confusion matrices](phase9_family_confusion.csv)
· [Per-family precision and recall](phase9_per_family.csv)

## Known acceptance and unknown rejection

At the frozen maximum-score 5% known-validation budget, unknown rejection
recall was 19.53% in B, 3.45% for Web, 8.12% for Bot, 30.15% for
Infiltration and 0.0048% for DDoS. The corresponding observed known false
rejection rates in the four family holdouts were 2.77%, 1.34%, 2.83% and
7.11%. Only 61 of 1,263,933 held-out DDoS flows were rejected by maximum
uncertainty. Unknown false acceptance is the complement of unknown
rejection among the supported unknown evaluation groups.

Five scores and three known-validation budgets were evaluated with cutoff
ties retained. The validation constraint transferred unevenly to held-out
traffic. Results reported at the frozen operating points remain the
primary results. The reproduced histograms reconciled all 75 historical
operating points, including rejection, acceptance coverage and accepted
correct-family rates.

[Operating points](phase9_open_set_metrics.csv)
· [Tradeoff figure](figures/phase9_open_set_tradeoffs.png)
· [Risk–coverage, ROC and PR](figures/phase9_risk_coverage_roc_pr.png)
· [Known and unknown distributions](figures/phase9_known_unknown_score_distributions.png)
· [Per-day rates](figures/phase9_per_day_rejection.png)

## End-to-end and oracle comparisons

The chronological B hierarchy reconciled all 980,109 retained rows.
Both Phase 8 gates missed all 208,525 attacks. The Phase 4 RF passed 417
attacks to the family stage and correctly rejected 342 as UNKNOWN.
Conditional rejection was 82.01%, and full-population attack rejection was
0.164%. The oracle bypassed all binary misses, yielding 40,718 correct
UNKNOWN results (19.53%). It is a diagnostic using ground truth.

The retrospective C hierarchy reconciled all 1,458,218 retained rows.
None of the three archived gates rejected a Web attack as UNKNOWN. The
Phase 8 supervised gate missed all 658 attacks. Its hybrid passed 108
attacks and the family stage falsely accepted all 108 as known. The oracle
rejected 9 of 658 (1.37%). The predominantly benign C population makes
overall accuracy a weak measure of unknown-family performance.

The results include all benign flows, false alarms, missed attacks, correct
and incorrect complete decisions, and review burden. No end-to-end
known-family recall is reportable for B or C because neither test set
contains known attacks at the family stage.

[B hierarchy and receipt](phase9_hierarchy/B/results.md)
· [C hierarchy and receipt](phase9_hierarchy/C/results.md)
· [Attack outcome figure](figures/phase9_hierarchical_attack_outcomes.png)

## Robustness and capture-day interpretation

All five grouped-random configurations used the same 364,120 evaluation
flows. Seed 23014 reduced flow macro F1 from 0.633 to 0.563. Duplicate
training weights reduced flow macro F1 to 0.565 and increased group-weighted
macro F1 from 0.781 to 0.787. Unweighted RF improved flow accuracy while
reducing flow macro F1. The frozen grouped-random RF made 4,837
high-confidence errors at a maximum vote score of at least 0.90.
Leave-one-capture-day-out accuracy ranged from 66.87% to 83.79%.

Each attack family occurs on one or two capture days. All Bot and
credential brute-force examples each occur on a single day. Dropping
capture-day metadata from predictors does not remove capture conditions
from flow features. Rejected traffic comes from existing labeled families
in a retrospective corpus. The study provides no independent external
confirmation and correlates many flows within each capture. Descriptive
day and predictor-group comparisons replace row-independent intervals.

Under B's frozen maximum-score rule, the first test day rejected 40,680
of 65,251 unknown attacks and the second rejected 38 of 143,274. Median
registered flow duration was 39,838 µs on the first day and 10,917 µs on
the second. Median forward packet counts were two and three,
respectively. These feature and outcome contrasts coincide with a change
in evaluated family composition. B's training and test attack dates have
zero overlap. In the Web holdout, eight capture days overlap between
training and evaluation attacks overall, with the held-out family's two
days absent from known training attacks.

[Sensitivity results](phase9_sensitivity/results.md)
· [Capture-day support](figures/phase9_capture_family_support.png)
· [Evidence checklist](../docs/phase9_evidence_status.md)
· [B and Web daily evidence](phase9_open_set_evidence/15/results.md)
· [Bot, Infiltration and DDoS daily evidence](phase9_open_set_evidence/16/results.md)

## Models, execution and integration

The [classifier registry](../manifests/phase9_classifier_registry.json)
records the six original selected classifier identifiers, class mappings,
feature order, frozen rejection policies, model component hashes and
independent Spark 4.3.0 reload results. Phase 4 and Phase 8 binary and
clustering assets were checksum-verified against their original registries.
The C classifier and novelty pipeline are versioned private outputs, with
their registries linked from the C report. Versions 15 and 16 reconstructed
and persisted the five training-reference novelty pipelines used by the
original open-set scenarios. Grouped-random A is the closed-set reference.
The [novelty reload receipt](../manifests/phase9_novelty_reload.json) records
independently repeated centroid assignments and distances on synthetic
probes.

| Version | Validated stage | Worker status | Measured execution seconds | Peak driver RSS bytes |
|---|---|---|---:|---:|
| 12 | Chronological B hierarchy | COMPLETE | 299.2 | 3,753,791,488 |
| 13 | Retrospective C hierarchy and model persistence | COMPLETE | 468.7 | 4,532,752,384 |
| 14 | Grouped-random sensitivity | COMPLETE | 131.3 | 3,261,235,200 |
| 15 | B and Web open-set evidence and persistence | COMPLETE | 560.3 | 4,702,318,592 |
| 16 | Bot, Infiltration and DDoS open-set evidence and persistence | COMPLETE | 300.5 | 3,943,927,808 |

The new workers used Spark 4.3.0, four CPUs, an 8 GiB driver heap and
48 shuffle partitions. Additional resources, input counts and artifact
checksums are recorded in the [experiment manifest](../manifests/phase9_experiments.json)
and linked receipts. [Measured worker runtime and driver memory](figures/phase9_worker_resources.png)

The [inference contract](../docs/phase9_inference_contract.md) version
`phase9-hierarchy-v1` preserves Phase 8 score and abstention semantics
and defines the class probability-vector ordering and family rejection
fields. Three local synthetic B hierarchy probes reproduced the calibrated
and hybrid scores and Phase 8 abstention behavior. The isolated
[Streamlit preview](../dashboard/phase9_preview.py) reads verified aggregate
evidence. Run it locally with `streamlit run dashboard/phase9_preview.py`.

The local Spark 4.3.0 regression suite passed 76 tests, including earlier-
only C splitting, exact hierarchical reconciliation and unsupported
open-set discrimination metrics. The preview was smoke-tested with
Streamlit AppTest across all six family evaluation scenarios and both
hierarchical populations.

## Scientific conclusion and readiness

The grouped-random result shows measurable family discrimination relative to
the prespecified references, alongside marked second-seed, duplicate-weighting
and capture-day sensitivity. The archived deployment-like gates failed to
support useful unknown-family rejection in the chronological B population.
The retrospective C hierarchy yielded zero correct unknown decisions across
the three archived gates. These negative findings, the unsupported closed-set
metrics and the capture-family association are part of the validated record.

All required Phase 9 experimental stages and their compact evidence are
verified. **READY FOR PHASE 10.**
