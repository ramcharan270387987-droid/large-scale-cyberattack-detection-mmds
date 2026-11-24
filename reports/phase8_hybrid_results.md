# Phase 8 hybrid detection results

The B and C experiments are retrospective benchmarks. The R folds use strictly earlier fit and calibration dates within the same previously examined corpus. All results below use the same retained rows within each population.

[Private Kaggle CPU notebook](https://www.kaggle.com/code/ramcharan2345/mmds-phase-8-robust-hybrid-cyberattack-detection) · [Run receipts](../manifests/phase8_experiments.json)

## Execution and eligibility

| Stage | Version | Result | Seconds | JVM peak GiB |
| --- | --- | --- | --- | --- |
| baseline-B | 1 | validated | 320.5 | 3.63 |
| baseline-C | 2 | validated | 211.7 | 3.84 |
| hybrid-B | 6 | validated | 974.7 | 4.35 |
| hybrid-C | 3 | validated | 562.5 | 4.51 |
| hybrid-R1 | 4 | validated | 1055.7 | 5.16 |
| hybrid-R2 | 5 | validated | 713.9 | 5.01 |

Both retrospective stages verified their Phase 2 receipt and reproduced the 12 Phase 4/5 validation and test comparisons per population.
[Baseline reconciliation](phase8_baseline_reconciliation.csv)

## B held-out evaluation

The operating split selected **lr_w10** as its supervised base and **or** as its fusion. Training used 795,270 grouped sample rows. Evaluation retained 71.039% of originally assigned test rows.

| Method | Precision | Recall | F1 | Binned PR-AUC | Benign FPR | Rows | Scoring time |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Random Forest at 0.5 | 7.898% | 0.200% | 0.00390 | 0.60359 | 0.630% | 980,109 | 6.07s baseline pass |
| Budget-selected Random Forest | 11.000% | 0.295% | 0.00575 | 0.60359 | 0.646% | 980,109 | 6.07s baseline pass |
| Best LR (lr_w10) | 11.738% | 0.332% | 0.00646 | 0.61800 | 0.675% | 980,109 | 5.70s held out (raw base) |
| Best weighted (lr_w10) | 11.738% | 0.332% | 0.00646 | 0.61800 | 0.675% | 980,109 | 5.70s held out (raw base) |
| Calibrated supervised | NA | 0.000% | 0.00000 | 0.21276 | 0.000% | 980,109 | Shared Spark pass |
| Novelty only | 0.000% | 0.000% | 0.00000 | 0.25262 | 0.001% | 980,109 | Shared Spark pass |
| Selected fusion (or) | 0.000% | 0.000% | 0.00000 | 0.21276 | 0.001% | 980,109 | 27.28s held out |

Against calibrated supervised scoring, selected fusion changed recall by +0.000 percentage points and realized benign FPR by +0.001 points. At its frozen operating point it produced 5 false alarms per million benign flows. Triage referred 0 rows per 100,000 flows for review and automatically covered 100.000%. The frozen cutoff was 0.50000 and the validation FPR was 0.001%.

The measured base and selected-fusion scoring passes took 5.70s and 27.28s over the same 980,109 rows. These timings cover the selected methods and include Spark execution overhead.

| Probability method | Rows | Brier | Log loss | ECE |
| --- | --- | --- | --- | --- |
| raw | 980,109 | 0.22641 | 0.64261 | 0.33183 |
| platt | 980,109 | 0.19412 | 0.67926 | 0.16320 |
| isotonic | 980,109 | 0.18502 | 0.60431 | 0.15909 |

The probability-split Platt fit used a slope of +0.00472 and intercept of -2.95363 on raw-score bin midpoints. A negative slope reverses the fitted score ordering before binning.

| Attack family | Support | Seen in training | Calibrated recall | Weighted recall | Novelty recall | Fusion recall | Fusion referred or abstained |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Infiltration | 65,251 | False | 0.000% | 0.449% | 0.000% | 0.000% | 0 |
| Bot | 143,274 | False | 0.000% | 0.279% | 0.000% | 0.000% | 0 |

## C held-out evaluation

The operating split selected **rf_w5** as its supervised base and **blend_0_5** as its fusion. Training used 812,520 grouped sample rows. Evaluation retained 69.533% of originally assigned test rows.

| Method | Precision | Recall | F1 | Binned PR-AUC | Benign FPR | Rows | Scoring time |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Random Forest at 0.5 | 0.134% | 2.432% | 0.00253 | 0.00055 | 0.821% | 1,458,218 | 5.22s baseline pass |
| Budget-selected Random Forest | 0.228% | 2.432% | 0.00416 | 0.00055 | 0.481% | 1,458,218 | 5.22s baseline pass |
| Best LR (logistic_regression) | 0.044% | 0.152% | 0.00068 | 0.00121 | 0.157% | 1,458,218 | 4.82s baseline pass |
| Best weighted (rf_w5) | 0.031% | 3.040% | 0.00062 | 0.00088 | 4.370% | 1,458,218 | 4.43s held out (raw base) |
| Calibrated supervised | 0.000% | 0.000% | 0.00000 | 0.00038 | 0.001% | 1,458,218 | Shared Spark pass |
| Novelty only | 0.000% | 0.000% | 0.00000 | 0.00896 | 0.000% | 1,458,218 | Shared Spark pass |
| Selected fusion (blend_0_5) | 1.398% | 16.413% | 0.02577 | 0.01042 | 0.522% | 1,458,218 | 19.67s held out |

Against calibrated supervised scoring, selected fusion changed recall by +16.413 percentage points and realized benign FPR by +0.521 points. At its frozen operating point it produced 5,224 false alarms per million benign flows. Triage referred 1,868 rows per 100,000 flows for review and automatically covered 98.132%. The frozen cutoff was 0.55273 and the validation FPR was 0.977%.

The measured base and selected-fusion scoring passes took 4.43s and 19.67s over the same 1,458,218 rows. These timings cover the selected methods and include Spark execution overhead.

| Probability method | Rows | Brier | Log loss | ECE |
| --- | --- | --- | --- | --- |
| raw | 1,458,218 | 0.08241 | 0.27698 | 0.17659 |
| platt | 1,458,218 | 0.01151 | 0.11123 | 0.10378 |
| isotonic | 1,458,218 | 0.01190 | 0.11453 | 0.10689 |

The probability-split Platt fit used a slope of -0.93661 and intercept of -2.00116 on raw-score bin midpoints. A negative slope reverses the fitted score ordering before binning.

| Attack family | Support | Seen in training | Calibrated recall | Weighted recall | Novelty recall | Fusion recall | Fusion referred or abstained |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Web attack | 658 | False | 0.000% | 3.040% | 0.000% | 16.413% | 260 |

## R1 held-out evaluation

The operating split selected **rf_w10** as its supervised base and **blend_0_5** as its fusion. Training used 123,543 grouped sample rows. Evaluation retained 50.393% of originally assigned test rows.

| Method | Precision | Recall | F1 | Binned PR-AUC | Benign FPR | Rows | Scoring time |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Random Forest at 0.5 | 85.686% | 1.032% | 0.02039 | 0.97857 | 0.080% | 528,411 | 10.84s operating |
| Budget-selected Random Forest | 85.096% | 1.032% | 0.02039 | 0.97857 | 0.084% | 528,411 | 10.84s operating |
| Best LR (lr_w10) | 100.000% | 1.032% | 0.02043 | 0.21880 | 0.000% | 528,411 | 8.45s operating |
| Best weighted (rf_w10) | 0.000% | 0.000% | 0.00000 | 0.58979 | 0.081% | 528,411 | 3.93s held out (raw base) |
| Calibrated supervised | NA | 0.000% | 0.00000 | 0.68234 | 0.000% | 528,411 | Shared Spark pass |
| Novelty only | NA | 0.000% | 0.00000 | 0.31149 | 0.000% | 528,411 | Shared Spark pass |
| Selected fusion (blend_0_5) | NA | 0.000% | 0.00000 | 0.55277 | 0.000% | 528,411 | 13.08s held out |

Against calibrated supervised scoring, selected fusion changed recall by +0.000 percentage points and realized benign FPR by +0.000 points. At its frozen operating point it produced 0 false alarms per million benign flows. Triage referred 0 rows per 100,000 flows for review and automatically covered 100.000%. The frozen cutoff was 0.97412 and the validation FPR was 0.000%.

The measured base and selected-fusion scoring passes took 3.93s and 13.08s over the same 528,411 rows. These timings cover the selected methods and include Spark execution overhead.

| Probability method | Rows | Brier | Log loss | ECE |
| --- | --- | --- | --- | --- |
| raw | 528,411 | 0.22400 | 0.65052 | 0.12440 |
| platt | 528,411 | 0.42372 | 1.08551 | 0.54114 |
| isotonic | 528,411 | 0.25245 | 0.69804 | 0.18928 |

The probability-split Platt fit used a slope of -10.54404 and intercept of +3.14270 on raw-score bin midpoints. A negative slope reverses the fitted score ordering before binning.

| Attack family | Support | Seen in training | Calibrated recall | Weighted recall | Novelty recall | Fusion recall | Fusion referred or abstained |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DDoS | 167,666 | False | 0.000% | 0.000% | 0.000% | 0.000% | 0 |

## R2 held-out evaluation

The operating split selected **lr_w1** as its supervised base and **or** as its fusion. Training used 728,118 grouped sample rows. Evaluation retained 71.384% of originally assigned test rows.

Learned fusion was skipped. The disjoint meta-training role retained 257,649 benign flows and 97 attack flows. The minimum was 100 per class.

| Method | Precision | Recall | F1 | Binned PR-AUC | Benign FPR | Rows | Scoring time |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Random Forest at 0.5 | 15.549% | 1.565% | 0.02843 | 0.11397 | 1.263% | 437,632 | 1.72s operating |
| Budget-selected Random Forest | 4.822% | 0.074% | 0.00146 | 0.11397 | 0.218% | 437,632 | 1.72s operating |
| Best LR (lr_w1) | 20.573% | 2.433% | 0.04352 | 0.13373 | 1.396% | 437,632 | 4.08s held out (raw base) |
| Best weighted (lr_w5) | 21.324% | 3.088% | 0.05395 | 0.13291 | 1.694% | 437,632 | 1.23s operating |
| Calibrated supervised | NA | 0.000% | 0.00000 | 0.12940 | 0.000% | 437,632 | Shared Spark pass |
| Novelty only | 0.000% | 0.000% | 0.00000 | 0.11949 | 0.002% | 437,632 | Shared Spark pass |
| Selected fusion (or) | 0.000% | 0.000% | 0.00000 | 0.12940 | 0.002% | 437,632 | 16.52s held out |

Against calibrated supervised scoring, selected fusion changed recall by +0.000 percentage points and realized benign FPR by +0.002 points. At its frozen operating point it produced 18 false alarms per million benign flows. Triage referred 0 rows per 100,000 flows for review and automatically covered 100.000%. The frozen cutoff was 0.50000 and the validation FPR was 0.000%.

The measured base and selected-fusion scoring passes took 4.08s and 16.52s over the same 437,632 rows. These timings cover the selected methods and include Spark execution overhead.

| Probability method | Rows | Brier | Log loss | ECE |
| --- | --- | --- | --- | --- |
| raw | 437,632 | 0.11847 | 0.40858 | 0.03677 |
| platt | 437,632 | 0.12934 | 1.07656 | 0.12916 |
| isotonic | 437,632 | 0.12921 | 1.06425 | 0.12888 |

The probability-split Platt fit used a slope of -2.07818 and intercept of -7.85814 on raw-score bin midpoints. A negative slope reverses the fitted score ordering before binning.

| Attack family | Support | Seen in training | Calibrated recall | Weighted recall | Novelty recall | Fusion recall | Fusion referred or abstained |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Infiltration | 56,631 | False | 0.000% | 3.088% | 0.000% | 0.000% | 0 |

## Scientific interpretation

Selected fusion did not demonstrate a recall gain without added false positives in the supported populations.
This comparison uses validation-selected thresholds. A validation FPR ceiling can differ materially from achieved held-out FPR.
The score calibration experiments use midpoint-binned probability estimates. Binned ranking metrics and capture-day comparisons do not provide row-independent uncertainty intervals. The paired disagreement table preserves same-row categorical counts.

[Probability calibration](phase8_calibration_metrics.csv) · [Family coverage](phase8_family_recall.csv) · [Operating budgets](phase8_false_positive_budgets.csv) · [Ablations](phase8_ablation_results.csv) · [Timing](phase8_performance.csv) · [Paired disagreements](phase8_paired_disagreement.csv) · [High-confidence errors](phase8_error_audit.csv) · [Inference registry](../manifests/phase8_models.json)

## Figures

- [precision recall](figures/phase8_precision_recall.png)
- [roc](figures/phase8_roc.png)
- [threshold recall](figures/phase8_threshold_recall.png)
- [threshold fpr](figures/phase8_threshold_fpr.png)
- [reliability](figures/phase8_reliability.png)
- [brier](figures/phase8_brier.png)
- [class weights](figures/phase8_class_weights.png)
- [fusion weights](figures/phase8_fusion_weights.png)
- [validation budgets](figures/phase8_validation_budgets.png)
- [family recall](figures/phase8_family_recall.png)
- [false alarms](figures/phase8_false_alarms.png)
- [risk coverage](figures/phase8_risk_coverage.png)
- [review workload](figures/phase8_review_workload.png)
- [ablation](figures/phase8_ablation.png)
- [overhead](figures/phase8_overhead.png)
- [rolling folds](figures/phase8_rolling_folds.png)
