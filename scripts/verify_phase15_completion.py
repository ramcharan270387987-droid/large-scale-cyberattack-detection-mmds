"""Independent Phase15 inference,evidence,UI and protected-reference acceptance."""
import json,hashlib,csv,subprocess,math
from pathlib import Path
from src.interactive import evidence,portable,inputs
ROOT=Path(__file__).resolve().parents[1]
def read(name):return json.loads((ROOT/name).read_text())
def verify():
    manifest=read('manifests/phase15_experiments.json');registry=evidence.models();parity=read('reports/phase15_validation/parity.json');assert len(registry)==3 and parity['status']=='PASS' and parity['spark']=='4.3.0' and not parity['fitting_performed']
    originals=read('manifests/phase13_models.json')['supervised'];km=read('manifests/phase5_clustering_models.json')['experiments']['B']
    for entry in registry:
        model=portable.verify(ROOT/entry['artifact'],entry['sha256']);proof=next(r for r in parity['models'] if r['id']==entry['id']);assert proof['portable_sha256']==entry['sha256'] and proof['probes']==proof['decisions_equal']
        if model['kind']=='KMeans':assert model['source_sha256']==km['model']['sha256'] and model['threshold']==km['calibration']['cutoffs']['0.99'] and model['input_transform']=='signed_log1p' and proof['max_absolute_residual']<=1e-8
        else:assert model['source_sha256']==next(r['sha256'] for r in originals if r['id']==entry['id']) and model['threshold']==.5 and proof['max_absolute_residual']<=1e-10
        rows=inputs.parse_csv((ROOT/'dashboard/data/phase15_demo.csv').read_bytes(),model['features']);predictions=inputs.batch(model,rows);assert len(predictions)==3 and all(r['status']=='valid' for r in predictions)
        result=portable.predict(model,dict.fromkeys(model['features'],None))
        if 'contributions' in result:assert math.isclose(result.get('baseline',0)+math.fsum(result['contributions']),result.get('logit',result.get('squared_distance')),rel_tol=1e-8,abs_tol=1e-8)
    catalog=evidence.catalog();assert len(catalog['groups'])==9
    for entries in catalog['groups'].values():
        assert entries
        for entry in entries:assert isinstance(evidence.load(entry),__import__('pandas').DataFrame)
    for fig in catalog['figures']:assert hashlib.sha256((ROOT/fig['path']).read_bytes()).hexdigest()==fig['sha256']
    browser=read('reports/phase15_validation/browser.json');preview=read('reports/phase15_validation/preview.json');assert browser['status']==preview['status']=='PASS' and len(browser['research_areas'])==9 and len(browser['manual_models'])==3 and len(preview['modules'])==13
    assert browser['invalid_csv'] and browser['manual_invalid'] and browser['prediction_downloads_verified'] and browser['uploaded_row_explanation'] and browser['model_unavailable'] and browser['replay'] and browser['provenance'] and not browser['mobile_horizontal_main_overflow'] and not browser['page_errors'] and not browser['http_errors'];assert len(browser['screenshots'])>=4 and all((ROOT/'reports/phase15_validation'/p).exists() for p in browser['screenshots']);assert preview['empty_state'] and preview['undefined_metric'] and preview['model_unavailable']
    for table in browser['research_areas']:
        index=browser['research_areas'].index(table);file=ROOT/'reports/phase15_validation'/('download-area-'+str(index)+'.csv');assert hashlib.sha256(file.read_bytes()).hexdigest()==table['download_sha256']
    tests=read('reports/phase15_validation/regression.json');assert tests['status']=='PASS' and tests['baseline_tests']==164 and tests['new_tests']==16 and tests['total']==180 and tests['skipped']==0
    required=['integration_protocol','architecture','inference_contract','deployment_guide','demo_guide','limitations']
    assert all((ROOT/'docs'/('phase15_'+name+'.md')).exists() for name in required);assert (ROOT/'reports/phase15_results.md').exists()
    for path,expected in manifest['evidence_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected,path
    # Preserve the complete historical research tree and public entry point.
    changed=subprocess.check_output(['git','diff','--name-only',manifest['starting_checkpoint']],cwd=ROOT,text=True).splitlines();assert all(p=='README.md' or 'phase15' in p.lower() or p.startswith('src/interactive/') or p=='dashboard/advanced_app.py' for p in changed),changed
    assert not subprocess.check_output(['git','diff',manifest['starting_checkpoint'],'--','dashboard/app.py','dashboard/requirements.txt','configs','src/ml','src/streaming'],cwd=ROOT,text=True)
    refs=subprocess.check_output(['git','ls-remote','origin','refs/heads/main','refs/heads/work','refs/tags/v1.0-mmds-validated-baseline','refs/tags/v1.0-mmds-validated-baseline^{}'],cwd=ROOT,text=True);actual={ref:sha for sha,ref in (line.split() for line in refs.splitlines())};expected={'refs/heads/main':'e6215d6834ce06ba60fe9c7e65ce4a97b611343d','refs/heads/work':'16ef2c23bbfe33c497d32863173455185fe868ed','refs/tags/v1.0-mmds-validated-baseline':'3295d05e5f873355ed0c5140f45f4c3b58047043','refs/tags/v1.0-mmds-validated-baseline^{}':'16ef2c23bbfe33c497d32863173455185fe868ed'};assert actual==expected
    return dict(status='PASS',executable_models=3,parity_probes=sum(r['probes'] for r in parity['models']),research_areas=9,evidence_tables=sum(map(len,catalog['groups'].values())),application_modules=13,tests=180,public_baseline_unchanged=True,protected=actual,public_deployment=False,phase16_started=False)
if __name__=='__main__':print(json.dumps(verify(),indent=2))
