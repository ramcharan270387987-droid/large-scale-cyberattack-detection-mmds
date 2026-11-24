# Phase 9 prespecified research protocol

Version phase9-v1 extends Phase 8 commit beb558748b24309b1f752b2d744614f31b1d9351. All model and rejection decisions below precede Phase 9 fitting. The six original family mappings and 18 numerical predictors remain frozen.

## Populations and isolation

A uses the existing Phase 4 predictor-group random assignment, with 70% training, 15% validation and 15% evaluation. B uses the existing Phase 4 chronological capture boundaries. Known-class evaluation includes only families supported in training. Unknown support remains explicit. A chronological population with no known evaluation families is unsupported for closed-set accuracy.

Four separate open-set scenarios withhold all Web attack, Bot, Infiltration or DDoS rows from fitting and calibration. Known rows use the same deterministic grouped random assignment. All held-out-family predictor groups are excluded from known training and validation to prevent collisions. UNKNOWN is evaluation-only. IDs follow the sorted training-supported family vocabulary. Preserve original labels and full support tables, including absent families.

Audit exact, canonical and predictor fingerprints and imputed vectors. Fit imputation and scaling only on training. Retain earliest roles when purging temporal overlap. Record coverage, multiplicity and conflicting labels.

## Candidates and calibration

Attack-only multinomial LR and RF use the same deterministic 6.25% predictor-group training sample. Compare unweighted, inverse training frequency and inverse weights capped at ten. LR uses 12 iterations and regularization .05. RF uses 12 trees, depth five and 24 bins. Seeds are 23013 and 23014, with the second seed a bounded sensitivity comparison. Select by validation macro F1, then balanced accuracy, then lower fitting cost. Majority and training-prior baselines share evaluation rows. Standard Spark GBT is omitted because it is binary-only.

Maximum score, top-two margin, normalized entropy, training-reference K-Means distance and a fixed combined rejection rule use whole tied bins. Calibrate known-family false rejection ceilings of 1%, 5% and 10% on known validation only. Primary budget is 5%. Freeze every threshold before scoring the withheld family. Tree scores remain vote scores. Report score orientation, prevalence, accepted accuracy, coverage, known false rejection and unknown rejection. No unknown test outcomes enter selection.

## Hierarchical evaluation and interpretation

Use compatible archived Phase 4 RF and Phase 8 supervised and hybrid gates only on their exact original B/C populations. Fit family classifiers exclusively on the permitted earlier training rows. Additional binary candidates must use the same training boundary. Include all retained benign and attack rows in end-to-end accounting, including missed attacks and rejected families. Oracle attack gating is diagnostic.

Report per-family confusion, macro and weighted metrics, support, per-day acceptance, feature distributions, uncertainty sensitivity, high-confidence errors and duplicate sensitivity. Family/day association limits interpretations of novelty. The study is retrospective and has no independent external confirmation. Correlated flows do not justify row-independent significance claims.

## Resources and completion

Use Spark 4.3.0, local[4], 8 GiB driver on private Kaggle CPU. Reuse verified Phase 2 output version 1. Keep only bounded aggregates in Git. Verify saved model checksums and synthetic reload parity. Every required stage must reach terminal status and yield retrieved evidence before readiness. Failed, unsupported and incomplete stages remain explicit.
