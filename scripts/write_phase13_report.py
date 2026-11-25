"""Write A–Z scientific report from verified Phase13 aggregate evidence."""
import csv,json,statistics,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads((ROOT/p).read_text())
def table(n):return list(csv.DictReader((ROOT/'reports'/('phase13_'+n+'.csv')).open()))
def main():
    acceptance=load('reports/phase13_validation/acceptance.json');assert acceptance['status']=='PASS'
    s=load('reports/phase13_supervised/explanations.json');c=load('reports/phase13_components/components.json');perm=load('reports/phase13_permutation/permutation.json');support=load('reports/phase13_diagnostics/error_support.json');shifts=load('reports/phase13_diagnostics/distribution_shift.json');errors=load('reports/phase13_diagnostics/error_cases.json');figures=load('manifests/phase13_figures.json');ranks=table('rank_agreement');stable=table('stability');probes=table('adaptive_probes');hist=table('adaptive_history');threshold=table('threshold_history')
    baseline='\n'.join('| '+r['model']+' | '+str(r['metrics']['tp'])+' | '+str(r['metrics']['fp'])+' | '+str(r['metrics']['fn'])+' | '+f"{r['metrics']['pr_auc']:.4f}"+' | '+f"{r['metrics']['roc_auc']:.4f}"+' |' for r in perm if r['condition']=='baseline')
    tops=[]
    for r in s:
        values=dict(zip(r['feature_order'],map(abs,r['coefficients']))) if 'coefficients' in r else r['native_importance'];top=sorted(values,key=values.get,reverse=True)[:5];tops.append(r['model']+': '+', '.join(top)+'.')
    worst=sorted(shifts,key=lambda r:r['js_bits'],reverse=True)[:6];shift_text='; '.join(f"{r['protocol']} {r['feature']}={r['js_bits']:.3f} bits" for r in worst)
    support_text='; '.join(f"{r['protocol']}: {r['eligible_rows']:,} eligible test rows, {len(r['strata'])} observed day/family/outcome strata" for r in support)
    case_text='; '.join(f"{p}: "+', '.join(f"{o}={sum(r['rows'] for r in errors if r['protocol']==p and r['outcome']==o)}" for o in ('TP','FP','FN','TN')) for p in ('A','B'))
    rank_defined=[float(r['spearman']) for r in ranks if r['spearman']];stable_defined=[float(r['spearman']) for r in stable if r['spearman']]
    adaptive_text='; '.join(r['policies']+f": mean paired score change {float(r['mean_paired_score_change']):.5f}, max absolute change {float(r['max_absolute_score_change']):.5f}, changed fixed0.5 decisions {r['changed_fixed_half_decisions']}/32" for r in probes)
    novelty='; '.join(r['model']+f": max distance residual {r['historical_sample']['max_absolute_residual']:.3g}" for r in c if r['kind']=='novelty')
    family='; '.join(r['model']+f": rejected {sum(s['rows'] for s in r['outcomes'] if s['rejected'])}/{r['rows']}, policy supported={r['rejection_policy_supported']}" for r in c if r['kind']=='family')
    costs='; '.join(stage+f"={load('reports/phase13_'+stage+'/receipt.json')['seconds']:.2f}s" for stage in ('supervised','permutation','components','diagnostics'))
    fp=sum(r['rows'] for r in errors if r['outcome']=='FP');unsupported_fp='No LR false-positive strata were observed, so an LR false-positive contribution figure is unsupported.' if not fp else f'{fp} enriched LR false-positive cases have valid signed decompositions.'
    text=f'''# Phase 13 — Explainable AI research report

## A. Outcome and scope

Phase13 completed four private Kaggle CPU stages, exact archived-model reconstruction, matched permutation, chronological/failure analysis, adaptive comparisons, figures and the isolated laboratory. The independent acceptance receipt is PASS. No Phase14 work or public deployment was performed. All interpretation is model behavior and association rather than causation.

## B. Starting checkpoint and protected state

The phase started at `be53a63b7f8f330c3561efcdf73f2501d66ccac7` on research-v2. Main, work and the validated-baseline tag retain their original hashes, independently checked by the completion validator. The original135 tests remain intact.

## C. Prespecification and execution

Protocol commit `98e18753783665fd9b3a0805a623047d3af01ede` preceded historical explanation scoring. Notebook `ramcharan2345/mmds-phase-13-explainable-ai` versions1–4 all completed and have version-pinned output hashes and terminal-log receipts. Stage1 conditional metadata strata are superseded by the deterministic representative correction, documented before their acceptance. Stage1 numerical/global results remain valid.

## D. Model selection and leakage control

Six Phase4 A/B group-sample LR/RF/GBT pipelines and ten novelty/hybrid/family/adaptive pipeline references were loaded from original versioned archives and hash checked. The selected adaptive P1/P2 first activated LR is shared, P4 has its separate first activation and P6 retains the initial incumbent. Selection used archived policies, without explanation-driven refitting or threshold changes. Explanation backgrounds use training/reference observations only.

## E. Bounded benchmark context

Every row below uses the same corrected1,000 predictor-group evaluation observations within its protocol and a fixed0.5 threshold. These descriptive sample metrics are distinct from original full-population benchmark metrics. PR and ROC are computed from2,048 whole-score bins. High PR ranking can coexist with no score crossing0.5.

| Archived model | TP | FP | FN | PR area | ROC area |
|---|---:|---:|---:|---:|---:|
{baseline}

The sharp A-to-B tree recall deterioration persists. At0.5 both LR models have zero sampled positives. Explanation evidence separates score ranking from the frozen operational decision rather than treating a contribution plot as evidence of detection quality.

## F. Exact LR local explanations

A/B maximum original logit residuals are {s[0]['max_logit_residual']:.3g} and {s[3]['max_logit_residual']:.3g}; maximum probability residuals are {s[0]['max_probability_residual']:.3g} and {s[3]['max_probability_residual']:.3g}. Uncentered beta-times-model-input contributions plus intercept reconstruct log-odds. Centered training-background contributions use their adjusted baseline. Synthetic probe1 supplies the public local contribution figure; private record explanations remain in versioned Kaggle outputs.

## G. RF/GBT and coefficient rankings

{chr(10).join(tops)}

Absolute scaled coefficients, raw-unit coefficients, mean absolute contributions and native split importance have different units and meanings. Native importance is global split usage; it is not local SHAP. Correlated predictors and cardinality can change how importance is distributed.

## H. SHAP compatibility and results

All48 exact interventional linear SHAP variants passed archived-logit parity; the maximum residual is {max(r['max_logit_residual'] for r in load('reports/phase13_components/linear_shap_stability.json')):.3g}. The independent coalition-enumeration test verifies the closed-form game. Values are additive in log-odds with empirical training backgrounds, sizes32/64. Direct tree SHAP is unsupported: the installed library raised `NotImplementedError: Predict with pyspark isn't implemented. Don't run 'interventional' as feature_perturbation.` No tree SHAP values or tree SHAP figure are reported.

## I. Matched permutation importance

Six models each have121 conditions: original plus20 individual/grouped specifications ×3seeds ×2 donor scopes. All726 evaluations preserve1,000 rows and class counts. The summary retains every repetition's mean, minimum, maximum and spread for PR/ROC/recall/precision/F1/FPR. Negative changes and undefined precision remain visible. Global versus capture-preserving donors and related-feature groups reveal dependence/correlation sensitivity, with no claim that arbitrary perturbed combinations are realizable network traffic.

## J. Samples and denominators

{support_text}. Primary estimates weight each selected predictor group once; flow weighting applies represented multiplicity as a separate sensitivity analysis. Source-group representatives are selected deterministically across conflicting metadata. Enriched error explanations contain at most8 cases per capture/family/outcome and1,000 per protocol, chosen after support enumeration. Their support is {case_text}. They do not estimate traffic prevalence. No row-independent confidence intervals are reported.

## K. Chronological distributions

Training-only quantile cuts define36 A/B feature comparisons; missing values have a separate bin. Full eligible reference/evaluation counts and out-of-training-range rates accompany quantiles. Largest observed JS comparisons: {shift_text}. These support distribution mismatch as a descriptive explanation context. Capture and family composition, predictor support and preprocessing can co-vary, so the analysis cannot identify a causal mechanism or prove concept drift.

## L. False negatives and false positives

Corrected primary LR samples contain122 A and225 B false negatives, with23 and41 respectively having scores≤0.1. Case tables include fixed-threshold margin, score, capture, family and mean absolute centered contributions. Enriched signed decompositions and full eligible support provide a separate rare-stratum view. {unsupported_fp} The false-negative contribution figure and full support remain available. Tree models' false positives are retained in matched benchmark metrics; a native tree global map is not presented as a local tree decomposition.

## M. Attack-family explanations

Family/capture-conditioned contribution tables preserve sample support and outcome labels. Attribution differences across families combine model dependence and changing input composition. The family heatmap summarizes observed supported strata without claiming unsupported strata have zero influence. No closed-set family recall is invented for unknown-family-only evaluation.

## N. K-Means novelty

{novelty}. Each observed squared distance equals the sum of feature deviations to its actual assigned centroid. Frozen training-calibrated novelty thresholds remain unchanged. Per-feature squared model-space units explain unusualness relative to centers; they do not constitute an attack probability.

## O. Hybrid paths

B's archived OR policy and C's archived0.5 blend reconstruct exactly on matched1,000-group samples, with maximum score residual0. Tables preserve separate supervised and novelty gates, frozen operating bins and final decisions by day/family/label. Logical gates and calibrated blend scores are identified separately.

## P. Open-set rejection

{family}. B uses the archived maximum-score5% rejection cutoff and class-ID map. A has no committed rejection cutoff and is explicitly unsupported as a rejection policy. Top-two margin and maximum score are aggregated for each conditional family path. Original Phase9 B closed-set test rows=0, so its closed-set metrics remain undefined. The original hierarchical binary-gate misses remain misses; these conditional explanations do not replace full Phase9 hierarchical performance.

## Q. Adaptive evolution

The same32 permitted reference-derived probes are scored by all four prespecified adaptive artifacts. {adaptive_text}. Three fixed synthetic probes additionally retain exact LR contribution and probability decompositions. Raw-unit coefficients divide stored coefficients by each model's own training standard deviation; imputation, intercept and training-day metadata are persisted. P1/P2 share an artifact, P4 differs, and P6 has no activated replacement. The issued-history table reuses original Phase12 predict-before-release outputs on changing captures. Threshold-only P3 has {len(threshold)} archived calibration events; coefficients remain fixed while its operating bin changes. Later models are never reassigned to earlier issued decisions.

## R. Stability and robustness

All48 sample/background combinations are retained: seeds23013/14, nested sample100/500/1,000 and training background32/64. Predictor-group versus represented-flow weighting and leave-one-capture-out descriptive ranks are separate rows. Defined Spearman sensitivity spans {min(stable_defined):.4f} to {max(stable_defined):.4f}. Top5 Jaccard, signed-attribution agreement, magnitude change and exact residuals accompany rank comparisons. These ranges describe sensitivity, not independent-flow uncertainty or a guarantee of robust future behavior.

## S. Cross-method agreement

Defined compatible-feature Spearman comparisons span {min(rank_defined):.4f} to {max(rank_defined):.4f}. Each pair retains its semantics and canonical top5 tie handling. Coefficient size, empirical contribution magnitude, split usage and performance decrease need not agree. Sign and negative permutation effects are preserved rather than selecting favorable methods.

## T. Computational performance

Measured whole-stage monotonic times: {costs}. Per-pipeline reload and bounded component/explanation times are separate. Peak driver RSS and CPU/memory/partition configuration are in each receipt. Whole-stage times include verified input and Spark work; they are not online latency estimates. The optional unsupported tree method has no fabricated timing or throughput. All stage work completed within the prespecified1,800-second per-stage bound.

## U. Persistence and reproducibility

`manifests/phase13_models.json` maps every model to original source versions and exact component hashes. The explanation registry records method/output space, sample/background configuration, feature order, tolerances, source outputs and aggregate SHA256s. Actual model weights and private row explanations remain private Kaggle artifacts. Retrieval checks every archive receipt hash, including private outputs before retaining only permitted public aggregates. Terminal logs and exact submitted notebook hashes remain independently recorded.

## V. Tables and figures

There are {figures['unique_figures']} supported research figures, each in PNG and SVG with provenance and hashes in `manifests/phase13_figures.json`. Figure families include coefficients, contributions, native tree maps, ranking agreement, valid linear SHAP, synthetic local decomposition, permutation, distributions, supported error/family comparisons, novelty, hybrid, rejection, adaptive evolution, stability and cost. Unsupported methods and unsupported error strata receive explicit textual findings instead of invented data.

## W. Isolated preview

`dashboard/phase13_preview.py` provides17 aggregate evidence sections, protocol/model/capture/family selectors, fixed synthetic local explanations, filtered downloads, limitations and figures. AppTest verifies every section plus empty and undefined states. Chromium verifies filters and downloaded row counts across all sections, actual figure download and desktop/mobile layout, with no page/HTTP errors. The preview is local and retrospective; the protected public dashboard is unchanged.

## X. Regression and acceptance

All147 tests passed with zero skips:135 preserved plus12 Phase13 tests. Completion independently checks artifact identities, exact residuals, matched class support, all726 permutation conditions, all48 linear SHAP variants, component paths, full-support diagnostic counts, figures, browser evidence, restricted changed paths and protected references. The receipt is `reports/phase13_validation/acceptance.json`.

## Y. Checkpoints, contribution and limitations

Each completed Kaggle stage was validated and checkpointed on research-v2 before continuing. Final remote verification is recorded separately after the final push to avoid a self-referential commit hash. The scientific contribution is a traceable explanation of archived scoring behavior and its sensitivity under chronological mismatch and adaptive refresh. Negative detection/rejection findings, correlated-feature ambiguity, bounded sampling, finite capture support, unsupported tree SHAP and the absence of causal identification remain explicit. See `docs/phase13_research_contribution.md`, `docs/phase13_limitations.md` and the explanation contract.

## Z. Readiness

**READY FOR PHASE 14**

This verdict records Phase13 completion only. Phase14 has not begun.
'''
    (ROOT/'reports/phase13_research_report.md').write_text(text)
    print('Wrote A–Z report')
if __name__=='__main__':main()
