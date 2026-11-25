# Phase 12 adaptive learning and model refresh

## A. Starting checkpoint and environment

Phase 12 started on research-v2 at `96c1885ef97243e4de33757603fe1530994f0f8e`. Stage 12F resumed from `ccb6de944ae41b3c1210e1b2b1808db6e4e111c3` after account recovery. Historical fitting/scoring used private Kaggle CPU, Spark 4.3.0, local[4], 8 GiB driver and48 shuffle partitions. Local CPU handled controlled synthetic experiments, tests and the isolated preview. No full raw dataset was downloaded.

## B. Phase 11 acceptance

The original Phase 11 acceptance validator passed before Phase 12 began, with15 tables,24 figures and109 regression tests. Its frozen receipts and detector registry remain unchanged.

## C. Frozen protocol and amendments

Protocol commit3ff45ef precedes all new fitting. configs/phase12_adaptation.yaml defines every primary operating point and budget. docs/phase12_protocol_amendments.md documents correction of the inherited capture-only timestamp policy before replacement-primary fitting. No predictive hyperparameters or alert thresholds were selected from Phase 12 outcomes.

## D. Evaluation populations

Original late-period B retains13,191,622 training,1,151,256 validation and980,109 test flows. Archived Phase 8 independently reproduced its static scores. Primary E assigns permanent70/15/15 fitting/calibration/evaluation predictor-group roles over16,232,943 verified flows, including14 flagged observations at trusted capture-day resolution. Fitting uses a deterministic125/10000 sample of fitting predictor groups; calibration and forward evaluation use their full assigned roles. Initial fitting is February14–15, calibration February16, and forward captures February20,21,22,23,28 and March1,2. The primary matched forward evaluation has1,997,636 rows. The16,232,929-row stricter sensitivity stays separate. Synthetic data use six known mechanisms,48×512 observations,18 predictors, three seeds and 42 forward windows per run.

## E. Leakage and label availability

Exact-record, canonical-feature and predictor-group cross-role audits are zero. Imputed-vector collisions are reported diagnostically for every fitted candidate. Training-only median imputation, feature filtering and scaling remain separate from promotion and evaluation. Every prediction is issued before release/update. Delays 0, 1, 3 retain pending labels at replay end, without flushing. Eventual-label all-issued metrics support matched retrospective comparisons; released-only endpoint metrics are separate. Archived bin/family/version counts exactly reconstruct configured operating decisions; raw row predictions were materialized in private runtime scratch and are not durable outputs.

## F. Initial static performance

P0 produced 463 TP and 4,691 FP, recall 0.183%, precision 8.983%, FPR 0.269% and PR-AUC 0.1590. All primary policies/delays reuse the exact saved initial pipeline and threshold. The original late B benchmark has a different population and remains in its own table.

### Primary historical E, LR, delay0, candidate cap3

| Policy | Population | TP | FP | Recall | Precision | F1 | Benign FPR | PR-AUC | Requests | Accepted | Build cost, s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| P0 | historical E | 463 | 4,691 | 0.183% | 8.983% | 0.358% | 0.269% | 0.1590 | 0 | 0 | 0.000 |
| P1 | historical E | 463 | 8,641 | 0.183% | 5.086% | 0.353% | 0.495% | 0.1695 | 3 | 3 | 108.277 |
| P2 | historical E | 634 | 9,835 | 0.250% | 6.056% | 0.481% | 0.564% | 0.1920 | 1 | 1 | 36.507 |
| P3 | historical E | 601 | 5,631 | 0.237% | 9.644% | 0.463% | 0.323% | 0.1590 | 0 | 0 | 0.000 |
| P4 | historical E | 648 | 9,548 | 0.256% | 6.355% | 0.492% | 0.547% | 0.1561 | 3 | 2 | 56.347 |
| P5 | historical E | 548 | 18,087 | 0.216% | 2.941% | 0.403% | 1.037% | 0.2209 | 3 | 3 | 101.181 |
| P6 | historical E | 463 | 4,691 | 0.183% | 8.983% | 0.358% | 0.269% | 0.1590 | 1 | 0 | 36.507 |

### Archived late-period B, fixed original operating points

These reused benchmarks incur zero new Phase 12 fitting cost. Original fitting times remain in reports/phase4_metrics.csv.

| Policy | Population | TP | FP | Recall | Precision | F1 | Benign FPR | PR-AUC | Requests | Accepted | Build cost, s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| archived majority | archived B test | 0 | 0 | 0.000% | undefined | 0.000% | 0.000% | 0.2128 | 0 | 0 | 0.000 |
| archived duration_rule | archived B test | 172,571 | 212,583 | 82.758% | 44.806% | 58.136% | 27.552% | 0.4075 | 0 | 0 | 0.000 |
| archived logistic_regression | archived B test | 177 | 51 | 0.085% | 77.632% | 0.170% | 0.007% | 0.6232 | 0 | 0 | 0.000 |
| archived random_forest | archived B test | 417 | 4,863 | 0.200% | 7.898% | 0.390% | 0.630% | 0.6036 | 0 | 0 | 0.000 |
| archived gradient_boosted_trees | archived B test | 1,218 | 7,021 | 0.584% | 14.783% | 1.124% | 0.910% | 0.2188 | 0 | 0 | 0.000 |
| archived logistic_regression | archived B test | 787 | 91 | 0.377% | 89.636% | 0.752% | 0.012% | 0.6496 | 0 | 0 | 0.000 |

## G. Periodic retraining

P1 accepted 3 candidates after 3 requests. It yielded 463 TP and 8641 FP. Compare its integer-count tradeoff with P0; accepting a valid refresh does not establish useful adaptation.

## H. Drift-triggered refresh

P2 executed the frozen .1 JS input-distribution policy with 1 alerts and 1 fitting requests. End-of-replay, support and cooldown suppressions are explicit. An alert without a future activation opportunity cannot improve issued predictions. The trigger is independent of evolving model scores.

## I. Adaptive threshold

P3 changed the operating threshold 6 times using released, separate calibration labels and frozen coefficients. Its resulting recall is 0.237% and FPR 0.323%. The 1% ceiling applies to eligible validation benign observations, not an assured future FPR. The no-positive threshold remains permissible.

## J. Sliding and expanding windows

P4 used the latest 2 released fitting captures, with 648 TP,9548 FP and 2 accepted candidates. P1 expands every 2 captures; P5 requests expanding refresh every capture subject to the same cooldown/cap. P5 yielded 548 TP and 18087 FP. Sliding3 and other bounded sensitivities are in phase12_robustness.csv.

## K. Guarded promotion

P6 made 1 requests and accepted 0 candidates in the primary historical run. The historical opportunity count limits any guard efficacy conclusion. Synthetic guard comparisons and focused tests exercise actual acceptance/rejection. Guard rules compare candidate and incumbent on the same released calibration rows, plus separate fixed retention diagnostics.

## L. Compute budgets

The primary comparison shares a maximum 3 requests, model family, deterministic fitting sample, validation requirements and evaluation cohort. Cap 6 natural-policy P1/P2 sensitivity is separately reported. Equal caps do not imply equal realized rows, requests or cost. Identical saved candidates are reused when histories match, with original build duration charged counterfactually. Physical work is counted once. Ratios with zero/nonpositive detection benefit remain undefined.

## M. Label-delay sensitivity

All seven LR policies were executed at delays 0, 1, 3 on the same forward cohort. Pending last-delay windows remain unavailable for adaptation. phase12_label_delay.csv and phase12_released_only_metrics.csv distinguish eventual-label evaluation from labels released by termination. Delayed-label and calendar-gap clocks are simulation assumptions, not observed analyst turnaround times.

## N. Controlled synthetic recovery

The 288 controlled runs cover stationary, feature-only distribution shift, prior shift, abrupt/gradual conditional reversal and recurring concepts over seeds23013/14/15. Local sklearn LR uses C=20, max_iter=200; it is a separate implementation from historical Spark LR. JS cannot generally detect a conditional change that leaves inputs stationary. Periodic adaptation can recover recall while worsening false alarms; guard retention can reject useful new-concept fitting. Recovery is the first postchange three-window block with pooled recall reaching prechange recall minus.05. Full seed/delay outcomes and undefined recovery are retained.

### Synthetic stationary, seed23013, delay0

| Policy | Population | TP | FP | Recall | Precision | F1 | Benign FPR | PR-AUC | Requests | Accepted | Build cost, s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| P0 | synthetic stationary | 99 | 3 | 5.861% | 97.059% | 11.055% | 0.179% | 0.8582 | 0 | 0 | 0.000 |
| P1 | synthetic stationary | 234 | 6 | 13.854% | 97.500% | 24.261% | 0.357% | 0.8633 | 5 | 5 | 0.021 |
| P2 | synthetic stationary | 99 | 3 | 5.861% | 97.059% | 11.055% | 0.179% | 0.8582 | 0 | 0 | 0.000 |
| P3 | synthetic stationary | 195 | 10 | 11.545% | 95.122% | 20.591% | 0.595% | 0.8582 | 0 | 0 | 0.000 |
| P6 | synthetic stationary | 99 | 3 | 5.861% | 97.059% | 11.055% | 0.179% | 0.8582 | 0 | 0 | 0.000 |

### Synthetic feature-shift, seed23013, delay0

| Policy | Population | TP | FP | Recall | Precision | F1 | Benign FPR | PR-AUC | Requests | Accepted | Build cost, s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| P0 | synthetic feature-shift | 1,102 | 10 | 45.164% | 99.101% | 62.050% | 1.255% | 0.9707 | 0 | 0 | 0.000 |
| P1 | synthetic feature-shift | 911 | 10 | 37.336% | 98.914% | 54.210% | 1.255% | 0.9704 | 5 | 3 | 0.020 |
| P2 | synthetic feature-shift | 762 | 5 | 31.230% | 99.348% | 47.521% | 0.627% | 0.9702 | 6 | 5 | 0.023 |
| P3 | synthetic feature-shift | 1,037 | 14 | 42.500% | 98.668% | 59.410% | 1.757% | 0.9707 | 0 | 0 | 0.000 |
| P6 | synthetic feature-shift | 1,102 | 10 | 45.164% | 99.101% | 62.050% | 1.255% | 0.9707 | 6 | 0 | 0.023 |

### Synthetic prior-shift, seed23013, delay0

| Policy | Population | TP | FP | Recall | Precision | F1 | Benign FPR | PR-AUC | Requests | Accepted | Build cost, s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| P0 | synthetic prior-shift | 290 | 6 | 17.618% | 97.973% | 29.866% | 0.373% | 0.9205 | 0 | 0 | 0.000 |
| P1 | synthetic prior-shift | 683 | 24 | 41.495% | 96.605% | 58.054% | 1.493% | 0.9274 | 5 | 5 | 0.021 |
| P2 | synthetic prior-shift | 384 | 7 | 23.329% | 98.210% | 37.703% | 0.435% | 0.9360 | 6 | 6 | 0.026 |
| P3 | synthetic prior-shift | 580 | 18 | 35.237% | 96.990% | 51.693% | 1.119% | 0.9205 | 0 | 0 | 0.000 |
| P6 | synthetic prior-shift | 372 | 8 | 22.600% | 97.895% | 36.723% | 0.498% | 0.9251 | 6 | 1 | 0.026 |

### Synthetic abrupt-conditional, seed23013, delay0

| Policy | Population | TP | FP | Recall | Precision | F1 | Benign FPR | PR-AUC | Requests | Accepted | Build cost, s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| P0 | synthetic abrupt-conditional | 35 | 67 | 2.073% | 34.314% | 3.911% | 3.986% | 0.4407 | 0 | 0 | 0.000 |
| P1 | synthetic abrupt-conditional | 235 | 90 | 13.922% | 72.308% | 23.348% | 5.354% | 0.7058 | 5 | 5 | 0.020 |
| P2 | synthetic abrupt-conditional | 35 | 67 | 2.073% | 34.314% | 3.911% | 3.986% | 0.4407 | 0 | 0 | 0.000 |
| P3 | synthetic abrupt-conditional | 73 | 11 | 4.325% | 86.905% | 8.239% | 0.654% | 0.4407 | 0 | 0 | 0.000 |
| P6 | synthetic abrupt-conditional | 35 | 67 | 2.073% | 34.314% | 3.911% | 3.986% | 0.4407 | 0 | 0 | 0.000 |

### Synthetic gradual-conditional, seed23013, delay0

| Policy | Population | TP | FP | Recall | Precision | F1 | Benign FPR | PR-AUC | Requests | Accepted | Build cost, s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| P0 | synthetic gradual-conditional | 50 | 52 | 3.010% | 49.020% | 5.672% | 3.044% | 0.5194 | 0 | 0 | 0.000 |
| P1 | synthetic gradual-conditional | 240 | 29 | 14.449% | 89.219% | 24.870% | 1.698% | 0.7450 | 5 | 5 | 0.024 |
| P2 | synthetic gradual-conditional | 50 | 52 | 3.010% | 49.020% | 5.672% | 3.044% | 0.5194 | 0 | 0 | 0.000 |
| P3 | synthetic gradual-conditional | 87 | 4 | 5.238% | 95.604% | 9.932% | 0.234% | 0.5194 | 0 | 0 | 0.000 |
| P6 | synthetic gradual-conditional | 50 | 52 | 3.010% | 49.020% | 5.672% | 3.044% | 0.5194 | 0 | 0 | 0.000 |

### Synthetic recurring, seed23013, delay0

| Policy | Population | TP | FP | Recall | Precision | F1 | Benign FPR | PR-AUC | Requests | Accepted | Build cost, s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| P0 | synthetic recurring | 62 | 40 | 3.671% | 60.784% | 6.924% | 2.381% | 0.5908 | 0 | 0 | 0.000 |
| P1 | synthetic recurring | 109 | 109 | 6.454% | 50.000% | 11.432% | 6.488% | 0.5734 | 5 | 5 | 0.022 |
| P2 | synthetic recurring | 62 | 40 | 3.671% | 60.784% | 6.924% | 2.381% | 0.5908 | 0 | 0 | 0.000 |
| P3 | synthetic recurring | 116 | 12 | 6.868% | 90.625% | 12.768% | 0.714% | 0.5908 | 0 | 0 | 0.000 |
| P6 | synthetic recurring | 62 | 40 | 3.671% | 60.784% | 6.924% | 2.381% | 0.5908 | 0 | 0 | 0.000 |

## O. Families and forgetting

Family/window/version counts cover DDoS,DoS,credential brute force,Bot,Infiltration and Web attacks. Initial/newly released fitting support, first exposure, active versions and forward misses are explicit. Fixed retention rows are separate from forward evaluation. Capture day and attack family are strongly confounded. A family with no later post-exposure evaluation cannot support a forward-learning claim. No row-independent confidence intervals or established-superiority claim is made.

## P. Candidate outcomes

Across accepted historical execution scopes, 52 logical fitting requests and 48 acceptance decisions are reported. A trained model can still fail validation support or guard criteria. Fitting success, action failure, rejection and actual future activation are separate fields. Rejected candidates never replace the incumbent.

## Q. Registry and versioning

The compact registry indexes 33 unique saved historical pipelines, with source commits, feature order, training days/classes/families, hyperparameters, preprocessing, hashes, private archive locations and reload receipts. Run-specific lifecycle tables contain parent, operating thresholds, calibration populations, decisions and served windows. The final controller atomically persists model and operating threshold together; interrupted updates preserve the previous pointer. Completed replay receipts are idempotent.

## R. Rollback and failure recovery

Controlled tests exercise twelve failure/recovery cases, including corrupt files, failed reload, schema mismatch, missing classes/labels, failed fitting/write, nonfinite scores, duplicate requests, interrupted promotion and actual saved-model restoration. Fresh-process Spark verification additionally restores a retrieved pipeline and checks its probes. Injected events are labeled separately. Natural historical rollback totals remain their observed values in the policy table, including zero.

## S. Computational overhead

Accepted historical artifacts required 33 unique physical model builds, totaling 1117.972 measured build seconds, including 108.598 optimizer seconds. Build timing includes training-only preprocessing, validation safeguards, persistence/reload and imputed-overlap audits. Per-policy charged work is counterfactual and must not be summed as actual physical compute. Physical scoring tables include Parquet materialization and histogram IO; cache-hit call latency is not production inference throughput. Distribution construction, scalar JS/detector work, registry updates, peak driver RSS, model bytes, rejected runs and total notebook runtime have separately scoped receipts. CPU consumption and multi-node scalability were not measured.

## T. Saved models and independent reload

All historical model components are SHA256-verified after Kaggle output retrieval. Fresh local Spark processes reopen retrieved saved pipelines and compare deterministic probes, including controlled Spark rollback. Later Kaggle runtimes reload the exact frozen initial pipeline and reproduce its archived calibration histogram. A separate fresh process reloaded all 344 synthetic models and matched their registered probes. Fitted weights remain outside Git.

## U. Kaggle execution receipts

Accepted primary stages are:

- 12C: `ramcharan2345/mmds-phase-12-adaptive-learning-model-refresh/3` · COMPLETE · 4 runs · 9 verified model artifacts
- 12D: `ramcharan2345/mmds-phase12-12d-adaptive-research/1` · COMPLETE · 5 runs · 4 verified model artifacts
- 12E: `ramcharan2345/mmds-phase-12-robustness-completion/1` · COMPLETE · 26 runs · 29 verified model artifacts

Primary notebook versions1 and2 remain documented as rejected-engineering and separate stricter sensitivity, respectively. Submitted/running states are never called completed. The first Stage12E worker stopped with an RF vector-validation error after fourteen completed LR scopes. The final robustness worker restores those verified scopes and executes the twelve remaining profiles; source-specific ERROR and COMPLETE receipts are retained.

## V. Figures and isolated dashboard

13 reproducible multi-panel figures cover architecture/clocks, policy metrics, active versions, thresholds, delays, families, retention, budgets, synthetic mechanisms, ablations, injected recovery and overhead. Preview status is PASS. The browser receipt enumerates actual sections, filters, CSV downloads, charts, console/network results and desktop/mobile screenshots. The public dashboard was not modified or deployed.

## W. Regression results

Complete regression receipt: `{"command": "python -m unittest discover -s tests -v", "errors": 0, "evidence_frozen_during_run": true, "failures": 0, "log_sha256": "967993a0c4bf089ca4547dd53f074737cf7b7fe370d0583c629cc6d7f49dcdc6", "original_tests": 109, "passed": 135, "python": "3.12.14", "seconds": 146.388, "skipped": 0, "spark": "4.3.0", "starting_tests": 135, "status": "PASS", "total": 135}`. All original 109 tests remain intact. New tests enforce information boundaries, source coverage, role typing, atomic model/threshold recovery, serialization, real rollback, idempotency, synthetic definitions and artifact reconciliation.

## X. GitHub verification

Every successful stage is committed and pushed to origin/research-v2, followed by independent ls-remote verification. Final remote SHA is reported in the final task response and final validation receipt. Protected work/main and the baseline tag must match their starting values. No force push or merge is performed.

## Y. Conclusions and limitations

Adaptation is not assumed beneficial. Small seven-capture historical support, family/day confounding, correlated/repeated predictor groups, retrospective reuse, simulated labels and cross-version score comparability limit interpretation. Input drift does not establish concept drift or forecast model failure. Synthetic improvements establish controlled behavior only. Guarded retention can impede new-concept adaptation. Scientific unsupported comparisons are listed explicitly; engineering defects are corrected and their execution receipts retained.

## Z. Acceptance verdict

READY FOR PHASE 13. Supported experimental scopes, independent histogram metrics, model reloads, figures, preview/browser checks, full regression and protected-reference checks passed. The final response identifies the independently verified remote checkpoint. Phase 13 awaits separate authorization.
