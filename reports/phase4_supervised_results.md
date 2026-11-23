# Phase 4 supervised attack detection

**READY FOR PHASE 5.** All three prespecified Kaggle protocols completed and were reconciled against their run logs. All 12 saved pipelines passed archive checksum verification and a second reload in Codex Cloud with synthetic probes. [Private Kaggle notebook](https://www.kaggle.com/code/ramcharan2345/mmds-phase-4-supervised-attack-detection) · [Model and run manifest](../manifests/phase4_models.json)

## Input and cohort integrity

Each run verified 16,232,943 input records across ten capture days, with 13,484,708 benign and 2,748,235 attack. The pinned Phase 2 receipt and cleaning version matched, and the 14 timestamp-flagged records remain eligible for capture-day assignment. The primary version registers 18 shared numerical predictors and fits preprocessing only on training-group samples. All evaluation predictions use the retained population. [Protocol specification](../docs/phase4_experimental_protocol.md)

| Protocol | Train | Validation | Test | Purged | Train sample | Sample share of train |
| --- | --- | --- | --- | --- | --- | --- |
| A | 11,455,925 | 2,344,726 | 2,432,292 | 0 | 695,307 | 6.069% |
| B | 13,191,622 | 1,151,256 | 980,109 | 909,956 | 795,270 | 6.029% |
| C | 13,522,722 | 392,902 | 1,458,218 | 859,101 | 812,520 | 6.009% |

Attack prevalence in retained cohorts

| Protocol | Train | Validation | Test | Train sample |
| --- | --- | --- | --- | --- |
| A | 17.7161% | 15.1220% | 14.9702% | 14.9856% |
| B | 17.4319% | 4.9560% | 21.2757% | 16.3886% |
| C | 19.8069% | 10.6495% | 0.0451% | 18.8579% |

The retained cohorts had zero crossing primary, exact-record or Phase 2 cleaned-feature groups. Imputed vectors were audited separately. [Day, binary and original-label support](phase4_split_diagnostics.csv)

| Protocol | Crossing predictor groups before purge | Crossing imputed vectors | Rows in those imputed groups |
| --- | --- | --- | --- |
| A | 0 | 0 | 0 |
| B | 136,985 | 0 | 0 |
| C | 142,016 | 0 | 0 |

## Test metrics

PR-AUC is binned average precision. Blank denominators appear as dashes. Baseline setup is included in overall runtime and its reported fit time excludes cutoff calibration. [Validation and test metrics with confusion matrices](phase4_metrics.csv)

| Protocol | Model | PR-AUC | ROC-AUC | Precision | Recall | F1 | Balanced accuracy |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | Majority | 0.1497 | 0.5000 | — | 0.0000 | 0.0000 | 0.5000 |
| A | Duration rule | 0.1659 | 0.5541 | 0.1758 | 0.6196 | 0.2739 | 0.5541 |
| A | Logistic Regression | 0.5931 | 0.8064 | 0.9848 | 0.0009 | 0.0018 | 0.5004 |
| A | Random Forest | 0.9166 | 0.9656 | 0.9313 | 0.8282 | 0.8767 | 0.9087 |
| A | GBT | 0.8892 | 0.9577 | 0.9282 | 0.8496 | 0.8872 | 0.9190 |
| A | Logistic Regression (full refit) | 0.2833 | 0.7521 | 0.0161 | 0.0038 | 0.0062 | 0.4814 |
| B | Majority | 0.2128 | 0.5000 | — | 0.0000 | 0.0000 | 0.5000 |
| B | Duration rule | 0.4075 | 0.7760 | 0.4481 | 0.8276 | 0.5814 | 0.7760 |
| B | Logistic Regression | 0.6232 | 0.8225 | 0.7763 | 0.0008 | 0.0017 | 0.5004 |
| B | Random Forest | 0.6036 | 0.7986 | 0.0790 | 0.0020 | 0.0039 | 0.4978 |
| B | GBT | 0.2188 | 0.4297 | 0.1478 | 0.0058 | 0.0112 | 0.4984 |
| B | Logistic Regression (full refit) | 0.6496 | 0.8276 | 0.8964 | 0.0038 | 0.0075 | 0.5018 |
| C | Majority | 0.0005 | 0.5000 | — | 0.0000 | 0.0000 | 0.5000 |
| C | Duration rule | 0.0004 | 0.4422 | 0.0002 | 0.1079 | 0.0004 | 0.4422 |
| C | Logistic Regression | 0.0012 | 0.3606 | 0.0004 | 0.0015 | 0.0007 | 0.5000 |
| C | Random Forest | 0.0005 | 0.5063 | 0.0013 | 0.0243 | 0.0025 | 0.5081 |
| C | GBT | 0.0007 | 0.4777 | 0.0012 | 0.0410 | 0.0024 | 0.5130 |
| C | Logistic Regression (full refit) | 0.0013 | 0.3645 | 0.0000 | 0.0000 | 0.0000 | 0.4998 |

## Execution

| Protocol | Kaggle version | Runtime (s) | Spark | CPU workers | Driver heap | JVM peak GiB | Log events |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | 1 | 517.592 | 4.3.0 | 4 | 8g | 6.96 | 952 |
| B | 2 | 745.004 | 4.3.0 | 4 | 8g | 6.27 | 1091 |
| C | 3 | 491.052 | 4.3.0 | 4 | 8g | 6.93 | 836 |

[Fit and validation-scoring timings](phase4_training_performance.csv) · [Family and original-label recall](phase4_family_recall.csv) · [Model comparison](../docs/phase4_model_comparison.md)
