# Phase 4 experimental protocol

The positive class is attack. All runs attach the Phase 2 Notebook Output and verify its pinned receipt, Parquet footers, shared schema, ten capture days, original-label mapping and totals before preparing model data. The 14 out-of-day timestamps remain in the benchmarks because partition assignment uses capture-day provenance exclusively. [Experiment configuration](../configs/ml_experiments.yaml) · [Phase 2 data contract](data_contract.md)

## Predictor registry

Version `phase4-v1` prespecifies 18 numerical measurements covering duration, directional packet and byte volume, packet length, inter-arrival time, flow rates, direction ratio and TCP flags. This compact shared subset bounds training and inference cost. The other shared measurements remain candidates for later work. Initial TCP windows are excluded because their sentinel-related missingness is substantial and could encode capture conditions. Protocol is a categorical context variable reserved for an optional ablation. Destination port, IP and flow identifiers, source file and day, schema metadata, timestamps, original labels, derived labels, family and fingerprints are excluded from modeled vectors. Identifiers and timestamps can reveal endpoint and capture identity, and target fields directly reveal the outcome. Fingerprints and source days are evaluation grouping keys.

Phase 3 observed strong packet-byte dependence and related timing measures. This benchmark retains directional packet and byte measurements with regularization to keep a fixed comparison set. Zero-variance or entirely unavailable columns are removed using the training sample only. Future feature ablations should use the same cohorts and repeat the overlap audit. The present experiment uses no protocol or exact-representative ablation. [Phase 3 research readiness](../reports/phase3_research_readiness.md)

## Prespecified partitions

| Protocol | Assignment | Evaluation treatment |
| --- | --- | --- |
| A | Hash the ordered finite-or-null primary predictor tuple using a versioned SHA-256 digest, then bucket the digest with xxHash64 and seed 23013. Target proportions are 70% train, 15% validation and 15% test. | Every occurrence of a predictor digest shares the same partition. Actual label and day proportions are measured. |
| B | Train on February 14–22 observed captures, validate on February 23 and 28, test on March 1 and 2. | Preserve the earliest assigned partition for each repeated predictor digest and remove later occurrences from evaluation. |
| C | Hold out February 22–23, which contain all Web attack records. Validate on February 28. Train on the remaining seven captures. | Apply the same overlap purge with training, validation and test priority. This is a capture holdout with one attack family absent from training. Its day, traffic and capture conditions also differ. |

Digest keys exclude outcome and all provenance. Missing and nonfinite numeric inputs become null before hashing, and signed zero is canonicalized. The pipeline reports crossing group sizes before purging and verifies isolation afterward for the new predictor key, the Phase 2 cleaned-feature key and the exact original-record key. Conflicting labels are kept where their group remains eligible. Imputed-vector overlap is measured separately because training-only replacement can create additional equivalence. Purging affects the measured day-holdout population and can alter prevalence or family support.

## Fitting and selection

The majority label and the duration rule are calibrated on the full retained training partition. The duration baseline predicts attack at or below the approximate benign-training median flow duration and benign for missing durations. The MLlib comparisons use a common deterministic sample of training-only groups, targeting 625 of 10,000 buckets. A distinct hash salt separates sampling from split assignment. The actual retained rows, binary support and per-family support are recorded. All retained validation and test rows are scored.

The common Spark pipeline fits median imputation and constant-feature selection on that training sample. Trees use unscaled assembled values. Logistic Regression additionally fits a standard-deviation scaler on the sample. Normalization and finite checks use per-row arithmetic without a population fit. The full-training Logistic Regression refit uses the same sample-fitted transform and fixed sample-selected settings. It is a distinct training-cohort comparison. Saved models contain the fitted preprocessing stages and expect the verified Phase 2 numerical schema.

Two preregistered settings per model are fit to the common sample. Selection maximizes validation PR-AUC, with lower trial number breaking ties. Settings are frozen before scoring any test set. Tree searches are intentionally small with bounded depth, bin counts, iteration budgets and worker memory. Predictions are evaluated at a fixed score threshold of 0.5. Scores do not persist as row-level artifacts.

## Metrics and interpretation

Accuracy, precision, recall, specificity, F1 and balanced accuracy are computed from exact counts. Undefined denominators are left blank. ROC-AUC is the trapezoidal area over descending score bins. PR-AUC is the step-integrated precision–recall curve, or binned average precision. The histogram uses 2,048 equal-width bins, treats ties within each bin together and produces no AUC for a single-class population. Prediction duration includes scoring and collecting bounded aggregate counts. Per-family and original-label recall include zero-support rows, whether the fitting cohort included the class, and a descriptive low-support flag below 100 observations. Benign false-positive rate is separate.

Launch `scripts/build_phase4_notebook.py --protocol A|B|C --output PATH` and attach the Phase 2 producer as the only Kaggle dataset source through `kernel_sources`. Each run is a version of the same private notebook, with its own logs, configuration, cohort counts, metric files and fitted artifacts. The archive retriever validates the per-file model hashes. The model verifier reloads downloaded pipeline artifacts from temporary storage. The report generator reconciles metrics, split manifests, selections and terminal log markers before publishing compact evidence.
