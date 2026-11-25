"""Consolidate compact model locations and scientific evidence without weights."""
import csv,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    models=list(csv.DictReader((ROOT/'reports/phase12_model_registry.csv').open()))
    historical=[]
    for row in models:
        receipt=json.loads(row['receipt'])
        historical.append({'model':row['model'],'family':row['family'],'backend':row['backend'],'source_commit':row['source_commit'],
            'features':json.loads(row['features']),'training_days':json.loads(row['training_days']),'rows':int(row['rows']),
            'class_support':json.loads(row['classes']),'artifact':row['archive_location'],'bytes':receipt['bytes'],
            'component_sha256':receipt['sha256'],'independent_reload':True})
    private=json.loads((ROOT/'reports/phase12_validation/synthetic_private_retrieval.json').read_text())
    synthetic=list(csv.DictReader((ROOT/'reports/phase12_synthetic/models.csv').open()))
    registry={'version':'phase12-v1','historical_models':historical,'synthetic_private_archive':private,
       'synthetic_members_sha256':{r['model']+'.pkl':r['sha256'] for r in synthetic},
       'model_lifecycle':'reports/phase12_model_lifecycle.csv','registry_table':'reports/phase12_model_registry.csv',
       'weights_in_git':False,'operating_point':'Immutable fitted artifact plus run-specific active threshold; see lifecycle and issued-window tables.'}
    (ROOT/'manifests/phase12_models.json').write_text(json.dumps(registry,indent=2)+'\n')
    policies=json.loads((ROOT/'manifests/phase12_policies.json').read_text())
    policies['config_sha256']=hashlib.sha256((ROOT/'configs/phase12_adaptation.yaml').read_bytes()).hexdigest()
    policies['phase11_detector_registry_sha256']=hashlib.sha256((ROOT/'manifests/phase11_detectors.json').read_bytes()).hexdigest()
    (ROOT/'manifests/phase12_policies.json').write_text(json.dumps(policies,indent=2)+'\n')
    manifest=json.loads((ROOT/'manifests/phase12_experiments.json').read_text())
    manifest.update(unique_historical_models=len(historical),synthetic_models=344,source_components={
       'prequential_runner':'src/adaptation/prequential_runner.py','labels_training_windows_registry':'src/adaptation/lifecycle.py',
       'thresholds_promotion_metrics':'src/adaptation/evaluation.py','historical_spark_backend':'src/adaptation/historical.py',
       'synthetic_benchmark':'src/adaptation/synthetic_benchmark.py','injected_failures':'src/adaptation/fault_validation.py'},
       scientific_unsupported=[
         {'comparison':'historical KSWIN','reason':'Seven capture arrivals cannot supply frozen100-observation warm-up.'},
         {'comparison':'historical ADWIN efficacy','reason':'Seven capture arrivals do not supply clock32 warm-up/diagnostic support; frozen synthetic sensitivity executed.'},
         {'comparison':'historical DDM','reason':'No verified intraday ordered binary error stream; no count-to-sequence reconstruction.'},
         {'comparison':'forward learning of DoS and credential brute force','reason':'No forward evaluation observations after initial capture training; zero support and undefined recall reported.'},
         {'comparison':'independent generalization and established superiority','reason':'Retrospective repeated corpus, seven captures, repeated groups and family/day confounding.'},
         {'comparison':'strict equality of realized compute budgets','reason':'Equal prespecified request caps are executed; realized opportunities/rows/cost differ. No forced alerts or outcome-selected schedule.'},
         {'comparison':'production latency and multi-node scaling','reason':'Kaggle local[4] CPU and measured materialization/model-build wall time only.'}])
    files=[]
    for folder in (ROOT/'reports',ROOT/'docs',ROOT/'configs',ROOT/'dashboard'):
        files += [p for p in folder.rglob('*') if p.is_file() and ('phase12' in p.name or any(part.startswith('phase12_') for part in p.relative_to(ROOT).parts))]
    excluded={'reports/phase12_validation/regression.json','reports/phase12_validation/acceptance.json','reports/phase12_validation/final_remote.json','reports/phase12_results.md'}
    files=[p for p in files if p.relative_to(ROOT).as_posix() not in excluded and '__pycache__' not in p.parts and not p.name.endswith('.pyc')]
    manifest['evidence_sha256']={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(files))}
    (ROOT/'manifests/phase12_experiments.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('MANIFESTS_BUILT',len(historical),'historical models;',len(files),'compact evidence files')
if __name__=='__main__':main()
