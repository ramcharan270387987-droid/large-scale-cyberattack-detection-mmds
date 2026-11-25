"""Independent fail-closed Phase13 completion acceptance; no model fitting."""
import csv,hashlib,json,subprocess,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name):return json.loads((ROOT/name).read_text())
def table(name):return list(csv.DictReader((ROOT/'reports'/('phase13_'+name+'.csv')).open()))
def verify():
    manifest=load('manifests/phase13_experiments.json');models=load('manifests/phase13_models.json')
    assert manifest['complete'] and not manifest['pending'] and manifest['verdict']=='READY FOR PHASE 14'
    report=(ROOT/'reports/phase13_research_report.md').read_text();assert all('## '+letter+'.' in report for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    for stage in ('supervised','permutation','components','diagnostics'):
        prefix='reports/phase13_'+stage+'/';r=load(prefix+'receipt.json');e=load(prefix+'execution.json');assert r['status']=='validated' and e['status']=='COMPLETE' and e['private_cpu'];assert manifest['stages'][stage]['worker_status']=='COMPLETE'
        for path,expected in e['artifacts'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected,path
        assert r['resources']['master']=='local[4]' and r['resources']['driver_memory']=='8g' and r['resources']['shuffle_partitions']==48 and r['resources']['spark_version']=='4.3.0'
        assert r['seconds']<=1800,(stage,r['seconds'])
    sup=load('reports/phase13_supervised/explanations.json');assert len(sup)==6
    for r in sup:
        assert len(r['feature_order'])==18 and r['reload_probe_rows']==3
        if 'coefficients' in r:assert r['max_logit_residual']<=1e-8 and r['max_probability_residual']<=1e-10
        else:assert len(r['native_importance'])==18 and abs(sum(r['native_importance'].values())-1)<1e-8
    perm=load('reports/phase13_permutation/permutation.json');assert len(perm)==726
    for model in {r['model'] for r in perm}:
        rows=[r for r in perm if r['model']==model];assert len(rows)==121 and len({r['condition'] for r in rows})==121
        baseline=next(r for r in rows if r['condition']=='baseline')['metrics'];assert baseline['rows']==1000
        for r in rows:
            m=r['metrics'];assert sum(m[k] for k in ('tp','tn','fp','fn'))==1000;assert m['tp']+m['fn']==baseline['tp']+baseline['fn'];assert m['tn']+m['fp']==baseline['tn']+baseline['fp']
        assert {r['seed'] for r in rows if r['seed']}=={23013,23014,23015}
    comps=load('reports/phase13_components/components.json');assert len(comps)==10 and len(models['components'])==10
    for r in comps:
        if r['kind']=='novelty':assert r['historical_sample']['rows']==1000 and r['historical_sample']['max_absolute_residual']<=1e-8
        if r['kind']=='hybrid':assert r['rows']==1000 and r['max_score_residual']<=1e-8 and sum(x['rows'] for x in r['decision_paths'])==1000
        if r['kind']=='family':
            assert sum(x['rows'] for x in r['outcomes'])==1000
            assert r['rejection_policy_supported']==(r['protocol']=='B')
        if r['kind']=='adaptive' and 'synthetic_explanations' in r:
            assert len(r['synthetic_explanations'])==3
            for x in r['synthetic_explanations']:assert abs(x['baseline']+math.fsum(x['contributions'])-x['logit'])<=1e-8
    stable=load('reports/phase13_components/linear_shap_stability.json');assert len(stable)==48
    for r in stable:assert r['prediction_parity_verified'] and r['output_space']=='log-odds' and r['max_logit_residual']<=1e-8 and r['sample_size'] in (100,500,1000) and r['background_size'] in (32,64)
    primary=[r for r in stable if r['sample_seed']==r['background_seed']==23013 and r['sample_size']==1000 and r['background_size']==64]
    assert len(primary)==2 and all(sum(s['rows'] for s in r['case_strata'])==1000 for r in primary)
    shap=load('reports/phase13_components/shap_compatibility.json');assert shap['status']=='validated' or (shap['status']=='unsupported' and shap['reason_type']=='NotImplementedError' and 'pyspark' in shap['reason'])
    errors=load('reports/phase13_diagnostics/error_cases.json');assert errors and all(0<r['rows']<=8 and r['max_logit_residual']<=1e-8 for r in errors)
    support=load('reports/phase13_diagnostics/error_support.json');assert len(support)==2
    for r in support:
        assert sum(s['count'] for s in r['strata'])==r['eligible_rows'];assert sum(s['rows'] for s in errors if s['protocol']==r['protocol'])<=1000
        assert r['eligible_rows']==next(s['eligible_test_rows'] for s in sup if s['protocol']==r['protocol'])
    shift=load('reports/phase13_diagnostics/distribution_shift.json');assert len(shift)==36
    for r in shift:assert 0<=r['js_bits']<=1 and sum(r['training_counts'].values())==r['training_rows'] and sum(r['evaluation_counts'].values())==r['evaluation_rows']
    probes=load('reports/phase13_diagnostics/adaptive_reference_probes.json');assert len(probes)==4 and all(r['rows']==32 for r in probes)
    for r in probes:assert all(0<=p<=1 for p in r['probabilities']) and r.get('max_logit_residual',0)<=1e-8
    explanations=load('manifests/phase13_explanations.json');assert len(explanations['entries'])==16
    for path,expected in explanations['evidence_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected,path
    analysis=load('reports/phase13_analysis.json')
    for name,expected in analysis['tables'].items():assert hashlib.sha256((ROOT/'reports'/name).read_bytes()).hexdigest()==expected,name
    figures=load('manifests/phase13_figures.json');assert figures['unique_figures']>=17
    for r in figures['figures']:assert hashlib.sha256((ROOT/r['file']).read_bytes()).hexdigest()==r['sha256'] and all((ROOT/p).exists() for p in r['sources'])
    browser=load('reports/phase13_validation/browser.json');assert browser['status']=='PASS' and len(browser['sections'])==17 and browser['screenshots']>=2 and not browser['page_errors'] and not browser['http_errors'] and not browser['mobile_horizontal_main_overflow']
    preview=load('reports/phase13_validation/preview.json');assert preview['status']=='PASS' and preview['empty_state'] and preview['undefined_metric']
    tests=load('reports/phase13_validation/regression.json');assert tests['status']=='PASS' and tests['original_tests']==135 and tests['phase13_tests']==12 and tests['total']==147 and tests['skipped']==0
    changed=subprocess.check_output(['git','diff','--name-only',manifest['starting_checkpoint']],cwd=ROOT,text=True).splitlines()
    assert all('phase13' in p.lower() or p.startswith('src/explainability/') for p in changed),changed
    refs=subprocess.check_output(['git','ls-remote','origin','refs/heads/work','refs/heads/main','refs/tags/v1.0-mmds-validated-baseline'],cwd=ROOT,text=True);remote={ref:sha for sha,ref in (line.split() for line in refs.splitlines())}
    expected={'refs/heads/work':'16ef2c23bbfe33c497d32863173455185fe868ed','refs/heads/main':'e6215d6834ce06ba60fe9c7e65ce4a97b611343d','refs/tags/v1.0-mmds-validated-baseline':'3295d05e5f873355ed0c5140f45f4c3b58047043'};assert remote==expected,remote
    return dict(status='PASS',archived_models=16,permutation_conditions=726,linear_shap_variants=48,tree_shap=shap['status'],error_case_rows=sum(r['rows'] for r in errors),distribution_comparisons=36,figures=figures['unique_figures'],tests=147,protected_refs=remote,phase14_started=False,public_deployment=False)
if __name__=='__main__':print(json.dumps(verify(),indent=2))
