# Phase 13 — Explainable AI research report

## A. Outcome and scope

Phase 13 completed four private Kaggle CPU stages, exact archived-model reconstruction, matched permutation, chronological/failure analysis, adaptive comparisons, figures and the isolated laboratory. The independent acceptance receipt is PASS. No Phase 14 work or public deployment was performed. All interpretation is model behavior and association rather than causation.

## B. Starting checkpoint and protected state

The phase started at `be53a63b7f8f330c3561efcdf73f2501d66ccac7` on research-v2. Main, work and the validated-baseline tag retain their original hashes, independently checked by the completion validator. The original 135 tests remain intact.

## C. Prespecification and execution

Protocol commit `98e18753783665fd9b3a0805a623047d3af01ede` preceded historical explanation scoring. Notebook `ramcharan2345/mmds-phase-13-explainable-ai` versions1–4 all completed and have version-pinned output hashes and terminal-log receipts. Stage1 conditional metadata strata are superseded by the deterministic representative correction, documented before their acceptance. Stage1 numerical/global results remain valid.

## D. Model selection and leakage control

Six Phase 4 A/B group-sample LR/RF/GBT pipelines and ten novelty/hybrid/family/adaptive pipeline references were loaded from original versioned archives and hash checked. The selected adaptive P1/P2 first activated LR is shared, P4 has its separate first activation and P6 retains the initial incumbent. Selection used archived policies, without explanation-driven refitting or threshold changes. Explanation backgrounds use training/reference observations only.

## E. Bounded benchmark context

Every row below uses the same corrected 1,000 predictor-group evaluation observations within its protocol and a fixed 0.5 threshold. These descriptive sample metrics are distinct from original full-population benchmark metrics. PR and ROC are computed from 2,048 whole-score bins. High PR ranking can coexist with no score crossing 0.5.

| Archived model | TP | FP | FN | PR area | ROC area |
|---|---:|---:|---:|---:|---:|
| A-logistic_regression | 0 | 0 | 122 | 0.3878 | 0.7702 |
| A-random_forest | 103 | 10 | 19 | 0.9271 | 0.9704 |
| A-gradient_boosted_trees | 105 | 6 | 17 | 0.8965 | 0.9622 |
| B-logistic_regression | 0 | 0 | 225 | 0.6655 | 0.8276 |
| B-random_forest | 0 | 5 | 225 | 0.6206 | 0.7794 |
| B-gradient_boosted_trees | 1 | 9 | 224 | 0.2271 | 0.3880 |

The sharp A-to-B tree recall deterioration persists. At 0.5 both LR models have zero sampled positives. Explanation evidence separates score ranking from the frozen operational decision rather than treating a contribution plot as evidence of detection quality.

## F. Exact LR local explanations

A/B maximum original logit residuals are 1.78e-15 and 3.55e-15; maximum probability residuals are 1.67e-16 and 2.08e-16. Uncentered beta-times-model-input contributions plus intercept reconstruct log-odds. Centered training-background contributions use their adjusted baseline. Synthetic probe 1 supplies the public local contribution figure; private record explanations remain in versioned Kaggle outputs.

## G. RF/GBT and coefficient rankings

- A-logistic_regression: ack_flag_cnt, rst_flag_cnt, pkt_len_mean, syn_flag_cnt, flow_duration.
- A-random_forest: fwd_iat_mean, flow_pkts_s, totlen_fwd_pkts, flow_iat_mean, flow_duration.
- A-gradient_boosted_trees: fwd_iat_mean, totlen_fwd_pkts, tot_fwd_pkts, flow_iat_mean, flow_iat_std.
- B-logistic_regression: pkt_len_mean, flow_byts_s, pkt_len_std, flow_duration, ack_flag_cnt.
- B-random_forest: totlen_fwd_pkts, ack_flag_cnt, fwd_iat_mean, flow_pkts_s, tot_bwd_pkts.
- B-gradient_boosted_trees: tot_bwd_pkts, ack_flag_cnt, totlen_fwd_pkts, fwd_iat_mean, flow_duration.

Absolute scaled coefficients, raw-unit coefficients, mean absolute contributions and native split importance have different units and meanings. Native importance is global split usage; it is not local SHAP. Correlated predictors and cardinality can change how importance is distributed.

## H. SHAP compatibility and results

All 48 exact interventional linear SHAP variants passed archived-logit parity; the maximum residual is 7.11e-15. The independent coalition-enumeration test verifies the closed-form game. Values are additive in log-odds with empirical training backgrounds, sizes 32/64. Direct tree SHAP is unsupported: the installed library raised `NotImplementedError: Predict with pyspark isn't implemented. Don't run 'interventional' as feature_perturbation.` No tree SHAP values or tree SHAP figure are reported.

## I. Matched permutation importance

Six models each have121 conditions: original plus 20 individual/grouped specifications ×3seeds ×2 donor scopes. All 726 evaluations preserve1,000 rows and class counts. The summary retains every repetition's mean, minimum, maximum and spread for PR/ROC/recall/precision/F1/FPR. Negative changes and undefined precision remain visible. Global versus capture-preserving donors and related-feature groups reveal dependence/correlation sensitivity, with no claim that arbitrary perturbed combinations are realizable network traffic.

## J. Samples and denominators

A: 2,432,292 eligible test rows, 25 observed day/family/outcome strata; B: 980,109 eligible test rows, 7 observed day/family/outcome strata. Primary estimates weight each selected predictor group once; flow weighting applies represented multiplicity as a separate sensitivity analysis. Source-group representatives are selected deterministically across conflicting metadata. Enriched error explanations contain at most 8 cases per capture/family/outcome and 1,000 per protocol, chosen after support enumeration. Their support is A: TP=16, FP=5, FN=80, TN=80; B: TP=8, FP=16, FN=16, TN=16. They do not estimate traffic prevalence. No row-independent confidence intervals are reported.

## K. Chronological distributions

Training-only quantile cuts define 36 A/B feature comparisons; missing values have a separate bin. Full eligible reference/evaluation counts and out-of-training-range rates accompany quantiles. Largest observed JS comparisons: B flow_duration=0.049 bits; B flow_byts_s=0.047 bits; B ack_flag_cnt=0.044 bits; B flow_pkts_s=0.042 bits; B totlen_fwd_pkts=0.041 bits; B flow_iat_std=0.040 bits. These support distribution mismatch as a descriptive explanation context. Capture and family composition, predictor support and preprocessing can co-vary, so the analysis cannot identify a causal mechanism or prove concept drift.

## L. False negatives and false positives

Corrected primary LR samples contain 122 A and 225 B false negatives, with 23 and 41 respectively having scores≤0.1. Case tables include fixed-threshold margin, score, capture, family and mean absolute centered contributions. Enriched signed decompositions and full eligible support provide a separate rare-stratum view. 21 enriched LR false-positive cases have valid signed decompositions. The false-negative contribution figure and full support remain available. Tree models' false positives are retained in matched benchmark metrics; a native tree global map is not presented as a local tree decomposition.

## M. Attack-family explanations

Family/capture-conditioned contribution tables preserve sample support and outcome labels. Attribution differences across families combine model dependence and changing input composition. The family heatmap summarizes observed supported strata without claiming unsupported strata have zero influence. No closed-set family recall is invented for unknown-family-only evaluation.

## N. K-Means novelty

novelty-B: max distance residual 2.84e-14; novelty-C: max distance residual 7.11e-15. Each observed squared distance equals the sum of feature deviations to its actual assigned centroid. Frozen training-calibrated novelty thresholds remain unchanged. Per-feature squared model-space units explain unusualness relative to centers; they do not constitute an attack probability.

## O. Hybrid paths

B's archived OR policy and C's archived0.5 blend reconstruct exactly on matched1,000-group samples, with maximum score residual 0. Tables preserve separate supervised and novelty gates, frozen operating bins and final decisions by day/family/label. Logical gates and calibrated blend scores are identified separately.

## P. Open-set rejection

family-A: rejected 0/1000, policy supported=False; family-B: rejected 378/1000, policy supported=True. B uses the archived maximum-score 5% rejection cutoff and class-ID map. A has no committed rejection cutoff and is explicitly unsupported as a rejection policy. Top-two margin and maximum score are aggregated for each conditional family path. Original Phase 9 B closed-set test rows=0, so its closed-set metrics remain undefined. The original hierarchical binary-gate misses remain misses; these conditional explanations do not replace full Phase 9 hierarchical performance.

## Q. Adaptive evolution

The same 32 permitted reference-derived probes are scored by all four prespecified adaptive artifacts. P0;P6: mean paired score change 0.00000, max absolute change 0.00000, changed fixed 0.5 decisions 0/32; P1-LR;P2-LR: mean paired score change 0.02053, max absolute change 0.24843, changed fixed 0.5 decisions 0/32; P4-LR: mean paired score change 0.01504, max absolute change 0.27345, changed fixed 0.5 decisions 0/32; P1-RF: mean paired score change -0.02510, max absolute change 0.60015, changed fixed 0.5 decisions 1/32. Three fixed synthetic probes additionally retain exact LR contribution and probability decompositions. Raw-unit coefficients divide stored coefficients by each model's own training standard deviation; imputation, intercept and training-day metadata are persisted. P1/P2 share an artifact, P4 differs, and P6 has no activated replacement. The issued-history table reuses original Phase 12 predict-before-release outputs on changing captures. Threshold-only P3 has 6 archived calibration events; coefficients remain fixed while its operating bin changes. Later models are never reassigned to earlier issued decisions.

## R. Stability and robustness

All 48 sample/background combinations are retained: seeds23013/14, nested sample100/500/1,000 and training background32/64. Predictor-group versus represented-flow weighting and leave-one-capture-out descriptive ranks are separate rows. Defined Spearman sensitivity spans 0.9360 to 1.0000. Top5 Jaccard, signed-attribution agreement, magnitude change and exact residuals accompany rank comparisons. These ranges describe sensitivity, not independent-flow uncertainty or a guarantee of robust future behavior.

## S. Cross-method agreement

Defined compatible-feature Spearman comparisons span -0.2690 to 0.8060. Each pair retains its semantics and canonical top5 tie handling. Coefficient size, empirical contribution magnitude, split usage and performance decrease need not agree. Sign and negative permutation effects are preserved rather than selecting favorable methods.

## T. Computational performance

Measured whole-stage monotonic times: supervised=476.42s; permutation=575.95s; components=826.61s; diagnostics=549.75s. Per-pipeline reload and bounded component/explanation times are separate. Peak driver RSS and CPU/memory/partition configuration are in each receipt. Whole-stage times include verified input and Spark work; they are not online latency estimates. The optional unsupported tree method has no fabricated timing or throughput. All stage work completed within the prespecified 1,800-second per-stage bound.

## U. Persistence and reproducibility

`manifests/phase13_models.json` maps every model to original source versions and exact component hashes. The explanation registry records method/output space, sample/background configuration, feature order, tolerances, source outputs and aggregate SHA256s. Actual model weights and private row explanations remain private Kaggle artifacts. Retrieval checks every archive receipt hash, including private outputs before retaining only permitted public aggregates. Terminal logs and exact submitted notebook hashes remain independently recorded.

## V. Tables and figures

There are 18 supported research figures, each in PNG and SVG with provenance and hashes in `manifests/phase13_figures.json`. Figure families include coefficients, contributions, native tree maps, ranking agreement, valid linear SHAP, synthetic local decomposition, permutation, distributions, supported error/family comparisons, novelty, hybrid, rejection, adaptive evolution, stability and cost. Unsupported methods and unsupported error strata receive explicit textual findings instead of invented data.

## W. Isolated preview

`dashboard/phase13_preview.py` provides 17 aggregate evidence sections, protocol/model/capture/family selectors, fixed synthetic local explanations, filtered downloads, limitations and figures. AppTest verifies every section plus empty and undefined states. Chromium verifies filters and downloaded row counts across all sections, actual figure download and desktop/mobile layout, with no page/HTTP errors. The preview is local and retrospective; the protected public dashboard is unchanged.

## X. Regression and acceptance

All 147 tests passed with zero skips:135 preserved plus 12 Phase 13 tests. Completion independently checks artifact identities, exact residuals, matched class support, all 726 permutation conditions, all 48 linear SHAP variants, component paths, full-support diagnostic counts, figures, browser evidence, restricted changed paths and protected references. The receipt is `reports/phase13_validation/acceptance.json`.

## Y. Checkpoints, contribution and limitations

Each completed Kaggle stage was validated and checkpointed on research-v2 before continuing. Final remote verification is recorded separately after the final push to avoid a self-referential commit hash. The scientific contribution is a traceable explanation of archived scoring behavior and its sensitivity under chronological mismatch and adaptive refresh. Negative detection/rejection findings, correlated-feature ambiguity, bounded sampling, finite capture support, unsupported tree SHAP and the absence of causal identification remain explicit. See `docs/phase13_research_contribution.md`, `docs/phase13_limitations.md` and the explanation contract.

## Z. Readiness

**READY FOR PHASE 14**

This verdict records Phase 13 completion only. Phase 14 has not begun.
