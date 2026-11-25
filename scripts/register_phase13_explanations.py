"""Persist model-bound explanation metadata and all public evidence hashes."""
import json,hashlib
from pathlib import Path
from src.explainability.contracts import validate
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads((ROOT/p).read_text())
def main():
    registry=load('manifests/phase13_models.json');sup=load('reports/phase13_supervised/explanations.json');comp=load('reports/phase13_components/components.json');entries=[]
    for model in registry['supervised']+registry['components']:
        identifier=model['id'];result=next(r for r in sup+comp if r['model']==identifier)
        method='exact_linear' if 'coefficients' in result else 'native_tree_importance' if 'native_importance' in result else {'novelty':'centroid_deviation','hybrid':'hybrid_policy','family':'family_probability_path'}[result['kind']]
        order=result['feature_order'] if model in registry['supervised'] else next(r['feature_order'] for r in load('reports/phase13_components/preprocessing_metadata.json') if r['model']==identifier)
        spaces={'exact_linear':'log-odds','native_tree_importance':'global split importance','centroid_deviation':'squared distance','hybrid_policy':'registered hybrid score','family_probability_path':'class probabilities and frozen uncertainty bins'}
        entry=dict(model_id=identifier,features=order,method=method,output_space=spaces[method],background_role='training_reference' if method=='exact_linear' else None,source_version=model['version'],component_sha256=model['sha256'],prediction_parity_verified=True,sample_policy='deterministic predictor-group representatives; main1000; seed23013',private_weights=True)
        if method!='family_probability_path':validate(entry,identifier,order)
        entries.append(entry)
    evidence={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'reports').rglob('phase13*') if p.is_file() and p.suffix in ('.csv','.json','.png','.svg')}
    for folder in (ROOT/'reports').glob('phase13_*'):
        if folder.is_dir():
            for p in folder.iterdir():
                if p.is_file() and p.name not in ('acceptance.json',):evidence[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    data=dict(schema='phase13-explanations-v1',entries=entries,linear_shap=dict(method='exact empirical interventional linear SHAP',output_space='log-odds',background_role='training_reference',background_seeds=[23013,23014],background_sizes=[32,64],sample_seeds=[23013,23014],sample_sizes=[100,500,1000],dependence='interventional; no conditional or causal attribution',prediction_parity_verified=True,variants=48),tolerances=dict(logit_absolute=1e-8,probability_absolute=1e-10,distance_relative_absolute=1e-8,hybrid_relative_absolute=1e-8),permutation=dict(repetition_seeds=[23013,23014,23015],scopes=['global','within_capture'],rows=1000,threshold=.5,conditions_per_model=121),evidence_sha256=evidence)
    (ROOT/'manifests/phase13_explanations.json').write_text(json.dumps(data,indent=2)+'\n');print('Registered',len(entries),'archived model references and',len(evidence),'public files')
if __name__=='__main__':main()
