"""Derive Phase14 public tables from actual retrieved evidence, never invent runs."""
import csv,json,hashlib,statistics,math
from pathlib import Path
from collections import defaultdict
from src.scalability.results import speedup
ROOT=Path(__file__).resolve().parents[1]
def load(stage,name):
    if name in ('failure_analysis','failure_analysis_verified'):return json.loads(Path('/tmp/mmds-phase14/'+('14V-private' if name=='failure_analysis_verified' else '14C-private')+'/'+name+'.json').read_text())
    return json.loads((ROOT/'reports'/('phase14_'+stage)/(name+'.json')).read_text())
def write(name,rows):
    rows=list(rows)
    if not rows:raise ValueError('Missing required evidence table: '+name)
    keys=list(dict.fromkeys(k for r in rows for k in r));path=ROOT/'reports'/('phase14_'+name+'.csv')
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,keys,lineterminator='\n');w.writeheader();w.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in rows)
    return path

def summary(rows,keys):
    groups=defaultdict(list)
    for r in rows:
        if r.get('warmup') or r['status']!='PASS':continue
        groups[tuple(r.get(k) for k in keys)].append(r)
    result=[]
    for values,items in groups.items():
        times=[r['seconds'] for r in items];actual={r['actual_rows'] for r in items};assert len(actual)==1
        result.append(dict(zip(keys,values))|dict(actual_rows=next(iter(actual)),repetitions=len(items),median_seconds=statistics.median(times),min_seconds=min(times),max_seconds=max(times),spread_seconds=max(times)-min(times),rows_per_second=next(iter(actual))/statistics.median(times),python_rss_sampled_peak=max(r['python_rss_sampled_peak'] for r in items),jvm_rss_sampled_peak=max(r['jvm_rss_sampled_peak'] for r in items),tree_rss_sampled_peak=max(r['tree_rss_sampled_peak'] for r in items),correctness='PASS'))
    return result

def main():
    audit=load('14B','external_audit');labels=load('14B','label_byte_catalog');models=load('14C','models');evaluation=load('14C','external_evaluation');runs=load('14D','scalability_runs');optimization=load('14E','optimization_runs')
    write('dataset_composition',[dict(dataset='MMDS source',class_name=k,rows=v,total=16232943,prevalence=v/16232943) for k,v in [('BENIGN',13484708),('ATTACK',2748235)]]+[dict(dataset='CICIDS2017 mirror',class_name=k,rows=v,total=audit['eligible_rows'],prevalence=v/audit['eligible_rows']) for k,v in [('BENIGN',sum(x['count'] for x in labels['labels'] if x['binary_label']==0)),('ATTACK',sum(x['count'] for x in labels['labels'] if x['binary_label']==1))]])
    write('dataset_provenance',[dict(dataset='MMDS source release',reference='saisathwikregula/mmds-dataset-23013/1',rows=16232943,capture_period='February–March2018',provenance='Pinned10file source audit andPhase2producer;upstream mirror description absent',license='Apache2.0 declared in mirror metadata;full upstream chain unverified'),dict(dataset='CICIDS2017 mirror',reference='shadman1028/cicids2017-official-flow-feature-csv-files/1',rows=2830743,capture_period='3–7July2017',provenance='UNBcollection documentation;8rawstylefiles;observedSHA256s;no official digest chain',license='Mirror declaresCCBY4.0;official research use requires citation')])
    write('external_populations',load('14C','populations'));write('cross_dataset_collisions',load('14C','collision_audit'));write('full_column_audit',load('14C','external_full_column_audit')['features']);write('distribution_shift',load('14C','distribution_shift'))
    external=[];families=[];curves=[];calibration=[]
    for r in evaluation:
        m=r['metrics'];den=m['fp']+m['tn'];same=next(x['metrics']['rows'] for x in evaluation if x['model']==r['model'] and x['evaluation_protocol']==r['evaluation_protocol'] and x['sensitivity']=='primary' and x['operating']==r['operating']);context={k:r[k] for k in ('model','experiment','evaluation_protocol','sensitivity','operating','threshold_bin')}
        external.append(context|m|dict(dataset='CICIDS2017 mirror',false_alarms_per_million_benign=1e6*m['fp']/den if den else None,positive_prediction_rate=(m['tp']+m['fp'])/m['rows'],missed_attacks=m['fn'],prevalence=r['prevalence'],coverage_of_retained_test=m['rows']/same,score_seconds=r['score_seconds'],rows_per_second=r['rows_per_second'],feature_count=3,feature_contract=r['feature_contract']))
        families.extend(context|f|{'support_status':'observed'} for f in r['families'])
        observed={x['family'] for x in r['families']}
        for label in labels['labels']:
            if label['original_label'] not in observed:families.append(context|dict(family=label['original_label'],rows=0,tp=0,fp=0,tn=0,fn=0,recall=None,precision=None,fpr=None,f1=None,pr_auc=None,roc_auc=None,support_status='absent in this retained test;metrics undefined'))
        if r['sensitivity']=='primary' and r['operating']=='validation_budget':
            hist={int(k):v for k,v in r['score_histogram'].items()};p=sum(v[1] for v in hist.values());n=sum(v[0] for v in hist.values());tp=fp=0
            curves.append(context|dict(score_bin=2048,recall=0. if p else None,fpr=0. if n else None,precision=None,kind='no-positive point'))
            for b in sorted(hist,reverse=True):
                fp+=hist[b][0];tp+=hist[b][1];curves.append(context|dict(score_bin=b,recall=tp/p if p else None,fpr=fp/n if n else None,precision=tp/(tp+fp),kind='2048-bin whole-score tie'))
            bins=defaultdict(lambda:[0,0,0.])
            for b,(no,yes) in hist.items():
                v=bins[min(19,b*20//2048)];v[0]+=no;v[1]+=yes;v[2]+=(no+yes)*(b+.5)/2048
            for b,(no,yes,scores) in bins.items():calibration.append(context|dict(reliability_bin=b,rows=no+yes,observed_attack_rate=yes/(no+yes),mean_probability_bin_midpoint_approx=scores/(no+yes),probability_approximation='Original2048-bin midpoint; absolute per-score error<=1/4096'))
    write('external_model_comparison',external);write('external_family_metrics',families);write('external_curves',curves);write('calibration',calibration)
    gaps=[]
    for r in external:
        if not r['model'].startswith('E3-'):continue
        family=r['model'].rsplit('-',1)[1];source=next(x for x in external if x['model']=='E2-B-common-'+family and all(x[k]==r[k] for k in ('evaluation_protocol','sensitivity','operating')));assert all(r[k]==source[k] for k in ('rows','prevalence'))
        for metric in ('precision','recall','f1','fpr','pr_auc','roc_auc','missed_attacks','false_alarms_per_million_benign'):
            a,b=source.get(metric),r.get(metric);gaps.append(dict(dataset=r['dataset'],evaluation_protocol=r['evaluation_protocol'],sensitivity=r['sensitivity'],operating=r['operating'],model_family=family,metric=metric,rows=r['rows'],source_value=a,target_trained_value=b,target_minus_source=b-a if a is not None and b is not None else None,relative_change=(b-a)/abs(a) if a not in (None,0) and b is not None else None,interpretation='Matched external test observations; target-trained versus source-only common3,not a causal shift effect'))
    write('generalization_gap',gaps)
    write('training_populations',[dict(model=r['model'],**r['sampling']) for r in load('14V','independent_reload')]);write('model_cost',[{k:r[k] for k in ('model','experiment','domain','protocol','training_rows','training_support','sample_permyriad','fit_seconds','preprocessing_seconds','threshold_bin','timings','preprocessing')} for r in models]);write('source_reference',[r|r['metrics'] for r in load('14V','source_reference')]);write('unit_consistency',load('14V','unit_consistency'));write('imputed_overlap',load('14V','imputed_overlap_audit'));write('distribution_support',load('14V','distribution_support'))
    errors=[]
    for r in load('14V','failure_analysis_verified'):
        for s in r['strata']:
            # Do not publish reconstructable feature/contribution records from singleton strata.
            safe=s['rows']>=5
            errors.append({k:r[k] for k in ('model','evaluation_protocol','sample_kind','threshold_bin','max_logit_residual')}|s|dict(mean_score=s['mean_score'] if safe else None,mean_signed_contributions=s['mean_signed_contributions'] if safe else None,attribution_visible=safe,suppression='Values suppressed for strata<5; counts retained' if not safe else 'Aggregated stratum >=5'))
    write('failure_analysis',errors)
    write('scalability_runs',runs);volume=summary([r for r in runs if r['workers']==4],['workload','requested_rows','format','workers','partitions','cache']);write('scalability_summary',volume)
    workers=summary([r for r in runs if r['requested_rows']==1000000 and r['workload'] in ('analytics','feature_transform')],['workload','workers','partitions','format','cache'])
    for r in workers:
        baseline=next(x for x in workers if x['workload']==r['workload'] and x['workers']==1);assert baseline['actual_rows']==r['actual_rows'];r.update(speedup(baseline['median_seconds'],r['median_seconds'],r['workers']))
    write('worker_scaling',workers);write('optimization_runs',optimization);opt=summary(optimization,['matrix','configuration','workers']);write('optimization_summary',opt)
    storage=load('14E','storage_files')
    for r in storage:
        for matrix,col in [('storage_full_read','read_checksum_seconds'),('storage_count_metadata_optimization_allowed','count_seconds'),('storage_projection_checksum','projection_seconds'),('storage_aggregation','aggregation_seconds'),('storage_projection_filter_query','query_seconds')]:r[col]=next(x['median_seconds'] for x in opt if x['matrix']==matrix and x['configuration']==r['format'])
        r['tree_rss_sampled_peak']=max(x['tree_rss_sampled_peak'] for x in opt if x['configuration']==r['format'])
    write('storage_comparison',storage);write('partition_comparison',[r for r in opt if r['matrix'].startswith('partition_') or r['matrix'] in ('capture_pruning','coalesce_materialized')]);write('pandas_comparison',[r for r in opt if r['matrix'].startswith('Spark_Pandas')]);write('cache_comparison',[r for r in opt if r['matrix']=='cache'])
    uncached=next(r['median_seconds'] for r in opt if r['matrix']=='cache' and r['configuration']=='none');warm=next(r['median_seconds'] for r in opt if r['matrix']=='cache' and r['configuration']=='warm_materialized');materialization=next(r['median_seconds'] for r in opt if r['matrix']=='cache' and r['configuration'].startswith('first_materialization'));write('cache_break_even',[dict(actual_rows=storage[0]['actual_rows'],uncached_query_seconds=uncached,warm_query_seconds=warm,materialization_seconds=materialization,break_even_queries=math.ceil(materialization/(uncached-warm)) if uncached>warm else None,interpretation='Materialization/(uncached minus warm);undefined when caching does not reduce query time;OS cache uncontrolled')])
    resources=[]
    for stage,items in [('14D',runs),('14E',optimization)]:
        resources.extend(dict(stage=stage,workload=r.get('workload',r.get('matrix')),configuration=r.get('configuration'),actual_rows=r.get('actual_rows'),workers=r.get('workers'),repetition=r.get('repetition'),warmup=r.get('warmup',False),**{k:v for k,v in r.items() if k.endswith('_sampled_peak') or k.startswith('cpu_')}) for r in items)
    write('resource_usage',resources)
    status=dict(status='verified derived aggregates',tables={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'reports').glob('phase14_*.csv')},external_records=len(evaluation),scalability_runs=len(runs),optimization_runs=len(optimization));(ROOT/'reports/phase14_analysis.json').write_text(json.dumps(status,indent=2)+'\n');print(json.dumps({k:v for k,v in status.items() if k!='tables'}))
if __name__=='__main__':main()
