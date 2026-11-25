"""Fail-closed final Phase14 scientific, artifact, benchmark and UI acceptance."""
import json,hashlib,subprocess,csv
from pathlib import Path
from verify_phase14_evaluation import validate as external
from src.scalability.acceptance import volume,optimization,same
ROOT=Path(__file__).resolve().parents[1]
def load(name):return json.loads((ROOT/name).read_text())
def verify():
    manifest=load('manifests/phase14_experiments.json');assert all(manifest['stages'][stage]['status']=='validated' for stage in ('14A','14B','14C','14V','14D','14E'))
    audit=load('reports/phase14_14B/external_audit.json');assert audit['physical_data_rows']==audit['eligible_rows']==2830743 and audit['excluded_rows']==0 and len(audit['files'])==8
    metrics=external();d=volume(ROOT/'reports/phase14_14D');e=optimization(ROOT/'reports/phase14_14E')
    assert load('reports/phase14_14E/receipt.json')['input_population']==load('reports/phase14_14D/benchmark_populations.json')[0]
    original=next(r['result'] for r in load('reports/phase14_14D/scalability_runs.json') if r['requested_rows']==1000000 and r['workload']=='ingest_checksum')
    assert all(same(r['result'],original) for r in load('reports/phase14_14E/optimization_runs.json') if r['matrix']=='storage_full_read')
    model=load('manifests/phase14_models.json');assert model['common_feature_order']==['flow_duration','tot_fwd_pkts','tot_bwd_pkts'] and model['exact_archived18_external_transfer'].startswith('UNSUPPORTED')
    reload=load('reports/phase14_validation/local_reload_independent.json');assert reload['status']=='PASS' and len(reload['models'])==12 and reload['compared_to_prior_process']
    independent=load('reports/phase14_14V/independent_reload.json');assert len(independent)==12 and all(r['calibration_histogram_identical'] and r['threshold_bin_unchanged'] for r in independent)
    assert all(r['fraction']>=.95 and r['eligible_rows']>=1000 for r in load('reports/phase14_14V/unit_consistency.json'))
    for stage in ('14D','14E'):
        retrieved=load('reports/phase14_'+stage+'/retrieval.json');assert retrieved['status']=='COMPLETE'
        log=(ROOT/'reports'/('phase14_'+stage)/'execution-logs.json').read_bytes();assert hashlib.sha256(log).hexdigest()==retrieved['log_sha256']
    analysis=load('reports/phase14_analysis.json');assert analysis['external_records']==64 and analysis['scalability_runs']==64 and analysis['optimization_runs']==130
    for name,expected in analysis['tables'].items():assert hashlib.sha256((ROOT/'reports'/name).read_bytes()).hexdigest()==expected,name
    figs=load('manifests/phase14_figures.json');assert set(figs['topic_coverage'])==set(range(1,25)) and figs['unique_figures']==len(figs['figures'])//2 and figs['unique_figures']>=17
    for r in figs['figures']:assert hashlib.sha256((ROOT/r['file']).read_bytes()).hexdigest()==r['sha256'] and all((ROOT/p).exists() for p in r['sources'])
    preview=load('reports/phase14_validation/preview.json');browser=load('reports/phase14_validation/browser.json');assert preview['status']==browser['status']=='PASS' and preview['empty_state'] and preview['undefined_metric']
    assert len(browser['sections'])==20 and not browser['page_errors'] and not browser['http_errors'] and not browser['mobile_horizontal_main_overflow'] and browser['screenshots']>=2 and browser['download_hashes_verified']
    tests=load('reports/phase14_validation/regression.json');assert tests['status']=='PASS' and tests['original_tests']==161 and tests['total']==164 and tests['skipped']==0
    rows=list(csv.DictReader((ROOT/'reports/phase14_failure_analysis.csv').open()))
    for r in rows:
        if int(r['rows'])<5:assert r['mean_score']=='' and r['mean_signed_contributions']==''
    for name,expected in manifest['evidence_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected,name
    assert (ROOT/'reports/phase14_research_report.md').exists()
    refs=subprocess.check_output(['git','ls-remote','origin','refs/heads/main','refs/heads/work','refs/tags/v1.0-mmds-validated-baseline','refs/tags/v1.0-mmds-validated-baseline^{}'],text=True,cwd=ROOT);protected={ref:sha for sha,ref in (line.split() for line in refs.splitlines())}
    assert protected=={'refs/heads/main':'e6215d6834ce06ba60fe9c7e65ce4a97b611343d','refs/heads/work':'16ef2c23bbfe33c497d32863173455185fe868ed','refs/tags/v1.0-mmds-validated-baseline':'3295d05e5f873355ed0c5140f45f4c3b58047043','refs/tags/v1.0-mmds-validated-baseline^{}':'16ef2c23bbfe33c497d32863173455185fe868ed'}
    changed=subprocess.check_output(['git','diff','--name-only','74e909ac3771dcaf5730437d3567f24c4fa4913b'],text=True,cwd=ROOT).splitlines();assert all('phase14' in p.lower() or p.startswith('src/scalability/') for p in changed),changed
    return dict(status='PASS',external=metrics,volume=d,optimization=e,figures=figs['unique_figures'],tests=164,protected=protected,phase15_started=False)
if __name__=='__main__':print(json.dumps(verify(),indent=2))
