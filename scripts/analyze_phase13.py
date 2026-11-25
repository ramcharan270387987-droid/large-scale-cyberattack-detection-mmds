"""Derive aggregate tables from hash-verified Phase13 outputs; never fit models."""
import csv,json,hashlib,itertools,statistics
from pathlib import Path
from collections import defaultdict
from src.explainability.rankings import agreement
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads((ROOT/p).read_text())
def write(name,rows):
    rows=list(rows);assert rows,name
    keys=list(dict.fromkeys(k for r in rows for k in r));path=ROOT/'reports'/('phase13_'+name+'.csv')
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,keys);writer.writeheader();writer.writerows({k:json.dumps(v) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in rows)
    return path

def main():
    supervised=load('reports/phase13_supervised/explanations.json');permutation=load('reports/phase13_permutation/permutation.json');stability=load('reports/phase13_components/linear_shap_stability.json');components=load('reports/phase13_components/components.json')
    primary=[r for r in stability if r['sample_seed']==23013 and r['sample_size']==1000 and r['background_seed']==23013 and r['background_size']==64]
    maps=defaultdict(dict);global_rows=[]
    def add(model,protocol,method,values,unit):
        maps[model][method]=values
        global_rows.extend(dict(model=model,protocol=protocol,method=method,feature=k,value=v,units=unit) for k,v in values.items())
    for r in supervised:
        if 'coefficients' in r:
            add(r['model'],r['protocol'],'absolute_scaled_coefficient',dict(zip(r['feature_order'],map(abs,r['coefficients']))),'log-odds per scaled unit')
        if 'native_importance' in r:add(r['model'],r['protocol'],'native_split_importance',r['native_importance'],'normalized split importance')
    for r in primary:
        model=r['protocol']+'-logistic_regression';add(model,r['protocol'],'linear_SHAP_mean_absolute',dict(zip(r['feature_order'],r['mean_absolute_contributions'])),'absolute log-odds')
        add(model,r['protocol'],'absolute_raw_unit_coefficient',dict(zip(r['feature_order'],[abs(v) if v is not None else 0. for v in r['raw_unit_coefficients']])),'log-odds per raw unit')
    grouped=defaultdict(list)
    for r in permutation:
        if r['condition']=='baseline':continue
        for metric,value in r['original_minus_permuted'].items():grouped[(r['model'],r['protocol'],r['scope'],'+'.join(r['features']),metric)].append(value)
    perm=[]
    for key,values in grouped.items():
        valid=[v for v in values if v is not None];perm.append(dict(model=key[0],protocol=key[1],scope=key[2],feature=key[3],metric=key[4],repetitions=len(values),defined_repetitions=len(valid),mean=statistics.mean(valid) if valid else None,minimum=min(valid) if valid else None,maximum=max(valid) if valid else None,spread=max(valid)-min(valid) if valid else None))
    write('permutation_summary',perm)
    for model in sorted({r['model'] for r in permutation}):
        values={r['feature']:r['mean'] for r in perm if r['model']==model and r['metric']=='pr_auc' and r['scope']=='global' and '+' not in r['feature'] and r['mean'] is not None}
        add(model,model[0],'permutation_PR_decrease',values,'baseline minus permuted PR area')
    write('global_importance',global_rows)
    ranks=[]
    for model,methods in maps.items():
        for (a,x),(b,y) in itertools.combinations(methods.items(),2):ranks.append(dict(model=model,comparison='within model',first=a,second=b,**agreement(x,y)))
    for protocol in ('A','B'):
        models=[m for m in maps if m.startswith(protocol+'-')]
        for a,b in itertools.combinations(models,2):
            x=next(v for k,v in maps[a].items() if k!='permutation_PR_decrease');y=next(v for k,v in maps[b].items() if k!='permutation_PR_decrease');ranks.append(dict(model=protocol,comparison='cross model; distinct semantics',first=a,second=b,**agreement(x,y)))
    write('rank_agreement',ranks)
    robust=[];cases=[]
    for r in stability:
        reference=next(p for p in primary if p['protocol']==r['protocol']);a=dict(zip(r['feature_order'],reference['mean_absolute_contributions']));b=dict(zip(r['feature_order'],r['mean_absolute_contributions']))
        sign=sum((x>=0)==(y>=0) for x,y in zip(reference['mean_signed_contributions'],r['mean_signed_contributions']))/len(a)
        robust.append(dict(protocol=r['protocol'],comparison='sample/background variation',sample_seed=r['sample_seed'],sample_size=r['sample_size'],background_seed=r['background_seed'],background_size=r['background_size'],sign_agreement=sign,mean_absolute_change=statistics.mean(abs(a[k]-b[k]) for k in a),max_residual=r['max_logit_residual'],**agreement(a,b)))
    for r in primary:
        a=dict(zip(r['feature_order'],r['mean_absolute_contributions']));b=dict(zip(r['feature_order'],r['flow_weighted_mean_absolute_contributions']));robust.append(dict(protocol=r['protocol'],comparison='flow versus predictor-group weighting',sample_size=r['sample_size'],represented_flow_mass=r['represented_flow_mass'],**agreement(a,b)))
        for day in sorted({s['day'] for s in r['case_strata']}):
            kept=[s for s in r['case_strata'] if s['day']!=day];n=sum(s['rows'] for s in kept)
            if n:
                b={feature:sum(s['mean_abs'][i]*s['rows'] for s in kept)/n for i,feature in enumerate(r['feature_order'])};robust.append(dict(protocol=r['protocol'],comparison='capture deletion; descriptive sensitivity',excluded_day=day,sample_size=n,**agreement(a,b)))
        for s in r['case_strata']:
            for name,value in zip(r['feature_order'],s['mean_abs']):cases.append(dict(protocol=r['protocol'],day=s['day'],family=s['family'],outcome=s['outcome'],rows=s['rows'],high_confidence_errors=s['high_confidence_errors'],mean_score=s['mean_score'],mean_margin=s['mean_margin'],feature=name,mean_absolute=value))
    write('stability',robust);write('case_contributions',cases)
    diagnostic=load('reports/phase13_diagnostics/error_cases.json');write('enriched_cases',(dict(**{k:v for k,v in r.items() if k not in ('mean_contributions','feature_order')},feature=f,mean_contribution=v) for r in diagnostic for f,v in zip(r['feature_order'],r['mean_contributions'])))
    write('distribution_shift',load('reports/phase13_diagnostics/distribution_shift.json'))
    write('feature_distributions',load('reports/phase13_permutation/feature_distributions.json'))
    novelty=[];hybrid=[];families=[];adaptive=[];synthetic=[]
    for r in components:
        if r['kind']=='novelty':
            for s in r['historical_sample']['strata']:
                for name,value in zip(r['feature_order'],s['contributions']):novelty.append(dict(model=r['model'],protocol=r['protocol'],day=s['day'],family=s['family'],binary_label=s['binary_label'],novel=s['novel'],rows=s['rows'],feature=name,mean_squared_contribution=value/s['rows'],mean_distance=s['distance_sum']/s['rows'],threshold=r['novelty_threshold']))
        elif r['kind']=='hybrid':hybrid.extend(dict(model=r['model'],protocol=r['protocol'],policy=r['policy'],operating_bin=r['operating_bin'],**s) for s in r['decision_paths'])
        elif r['kind']=='family':families.extend(dict(model=r['model'],protocol=r['protocol'],rejection_policy_supported=r['rejection_policy_supported'],cutoff_bin=r['cutoff_bin'],**s) for s in r['outcomes'])
        elif r['kind']=='adaptive':
            if 'coefficients' in r:
                for i,name in enumerate(r['feature_order']):adaptive.append(dict(model=r['model'],policies=';'.join(r['selected_policies']),feature=name,coefficient=r['coefficients'][i],raw_unit_coefficient=r['raw_unit_coefficients'][i],training_std=r['training_std'][i],intercept=r['intercept'],initial=r['frozen_initial']))
                for i,s in enumerate(r['synthetic_explanations']):
                    synthetic.extend(dict(model=r['model'],policies=';'.join(r['selected_policies']),probe=i,feature=f,contribution=v,baseline=s['baseline'],logit=s['logit'],probability=s['probability'],population='fixed synthetic probe; archived explanation') for f,v in zip(r['feature_order'],s['contributions']))
    write('novelty',novelty);write('hybrid',hybrid);write('family_rejection',families);write('adaptive_coefficients',adaptive);write('synthetic_local',synthetic)
    ref=load('reports/phase13_diagnostics/adaptive_reference_probes.json');initial=next(r for r in ref if r['frozen_initial']);paired=[]
    for r in ref:
        changes=[b-a for a,b in zip(initial['probabilities'],r['probabilities'])];paired.append(dict(model=r['model'],policies=';'.join(r['selected_policies']),rows=r['rows'],mean_score=statistics.mean(r['probabilities']),mean_paired_score_change=statistics.mean(changes),max_absolute_score_change=max(map(abs,changes)),changed_fixed_half_decisions=sum((a>=.5)!=(b>=.5) for a,b in zip(initial['probabilities'],r['probabilities'])),population=r['population']))
    write('adaptive_probes',paired)
    costs=[]
    for stage in ('supervised','permutation','components','diagnostics'):
        r=load('reports/phase13_'+stage+'/receipt.json');costs.append(dict(stage=stage,scope='whole stage including input verification and Spark work',seconds=r['seconds'],driver_peak_rss_bytes=r['driver_peak_rss_bytes']))
    for r in supervised:costs.append(dict(stage='model reload',model=r['model'],scope='saved pipeline load',seconds=r['reload_seconds']))
    for r in components:costs.append(dict(stage=r['kind'],model=r['model'],scope='bounded scoring and explanation',seconds=r['seconds']))
    write('cost',costs)
    shap=load('reports/phase13_components/shap_compatibility.json')
    summary={'status':'validated derived aggregates','models':len(supervised)+len(components),'permutation_conditions':len(permutation),'linear_shap_variants':len(stability),'tree_shap_status':shap['status'],'primary_samples':[{k:r[k] for k in ('protocol','sample_size','background_size','represented_flow_mass')} for r in primary],'tables':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'reports').glob('phase13_*.csv')}}
    (ROOT/'reports/phase13_analysis.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
