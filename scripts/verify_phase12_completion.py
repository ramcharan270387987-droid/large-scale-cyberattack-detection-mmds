"""Fail-closed Phase12 research acceptance; no fitting or deployment actions."""
import csv,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(path):return list(csv.DictReader((ROOT/path).open()))
def load(path):return json.loads((ROOT/path).read_text())

def verify():
    manifest=load('manifests/phase12_experiments.json')
    policies=read('reports/phase12_policy_comparison.csv');events=read('reports/phase12_training_events.csv')
    primary=[r for r in policies if r['backend']=='E-LR-seed23013-sample125-weight1' and r['budget']=='3' and r['sliding']=='2' and r['cooldown']=='2' and r['minimum']=='200']
    assert {(r['policy'],int(r['delay'])) for r in primary}=={('P'+str(p),d) for p in range(7) for d in (0,1,3)}
    assert len({r['initial_model'] for r in primary})==1
    assert len({r['initial_threshold_bin'] for r in primary})==1
    summaries={r['run']:r for r in policies}
    forward=['2018-02-20','2018-02-21','2018-02-22','2018-02-23','2018-02-28','2018-03-01','2018-03-02']
    for event in events:
        row=summaries[event['run']]
        allowed=forward[:max(0,int(event['window'])-int(row['delay'])+1)]
        if event.get('training_days'):
            assert set(json.loads(event['training_days']))<=set(['2018-02-14','2018-02-15',*allowed])
        if event.get('calibration_days'):
            assert set(json.loads(event['calibration_days']))<=set(['2018-02-16',*allowed])
        if event.get('activation_index'):
            assert int(event['activation_index'])>int(event['window'])
            if event.get('training_complete'):assert float(event['activation_time'])>=float(event['training_complete'])
        if event.get('candidate_metrics'):
            assert json.loads(event['candidate_metrics'])['fpr']<=.01+1e-12
    for row in policies:
        assert int(row['retrainings'])<=int(row['budget'])
        assert int(row['pending_label_windows'])==int(row['delay'])
        assert sum(int(row[k]) for k in ('tp','fp','tn','fn'))==int(row['rows'])
    for stage in ('12C','12D','12E'):
        prefix='reports/phase12_'+stage+'/'
        receipt=load(prefix+'receipt.json');retrieved=load(prefix+'retrieval.json');execution=load(prefix+'execution.json')
        assert receipt['status']=='validated' and retrieved['status']==execution['status']=='COMPLETE'
        assert execution['private_cpu'] and receipt['retained_rows']==16232943 and receipt['capture_only_rows']==14
        assert not any(receipt['cross_role_groups'].values())
        assert receipt['spark_version']=='4.3.0'
        if stage!='12C':assert receipt['frozen_reference_reload']['calibration_histogram_identical']
    synthetic=read('reports/phase12_synthetic_metrics.csv');assert len(synthetic)==288
    assert {r['backend'].split('-seed')[1] for r in synthetic}=={'23013','23014','23015'}
    archive=load('reports/phase12_validation/synthetic_private_retrieval.json');assert archive['status']=='PASS' and archive['models']==344
    reload=load('reports/phase12_validation/12C_reload_independent.json')
    assert reload['status']=='PASS' and reload['controlled_spark_rollback']['status']=='PASS'
    for stage in ('12D','12E'):
        assert load('reports/phase12_validation/'+stage+'_reload_independent.json')['status']=='PASS'
    faults=read('reports/phase12_faults.csv');assert len(faults)==12 and all(r['pass']=='True' for r in faults)
    browser=load('reports/phase12_validation/browser.json');assert browser['status']=='PASS' and browser['screenshots']>=2
    assert not browser['page_errors'] and not browser['http_errors'] and not browser['mobile_horizontal_main_overflow']
    assert load('reports/phase12_validation/preview.json')['status']=='PASS'
    tests=load('reports/phase12_validation/regression.json');assert tests['status']=='PASS' and tests['original_tests']==109 and tests['skipped']==0
    figures=list((ROOT/'reports/figures').glob('phase12_*.png'));assert len(figures)>=13
    for path,expected in manifest['evidence_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected,path
    changed=subprocess.check_output(['git','diff','--name-only','96c1885ef97243e4de33757603fe1530994f0f8e'],cwd=ROOT,text=True).splitlines()
    assert all(not path.startswith('dashboard/') or path=='dashboard/phase12_preview.py' for path in changed)
    import re
    assert not any(re.match(r'reports/phase(?:[1-9]|10|11)(?:_|/|\.)',path) for path in changed)
    output=subprocess.check_output(['git','ls-remote','origin','refs/heads/work','refs/heads/main','refs/tags/v1.0-mmds-validated-baseline'],cwd=ROOT,text=True)
    remote={ref:sha for sha,ref in (line.split() for line in output.splitlines())}
    expected={'refs/heads/work':'16ef2c23bbfe33c497d32863173455185fe868ed','refs/heads/main':'e6215d6834ce06ba60fe9c7e65ce4a97b611343d','refs/tags/v1.0-mmds-validated-baseline':'3295d05e5f873355ed0c5140f45f4c3b58047043'}
    assert remote==expected,remote
    return {'status':'PASS','historical_comparisons':len(policies),'primary_policy_delays':len(primary),'synthetic_runs':288,
            'unique_historical_models':len(read('reports/phase12_model_registry.csv')),'figures':len(figures),
            'total_regression_tests':tests['total'],'protected_refs':remote,'public_dashboard_unchanged':True,'phase13_started':False}
if __name__=='__main__':print(json.dumps(verify(),indent=2))
