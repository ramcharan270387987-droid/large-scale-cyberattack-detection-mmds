"""Independent archived Phase14 pipeline checks; never fit or retune models.

Also score the same frozen common-feature source models on their retained source
holdout, so a source/external gap is not confounded by switching feature sets.
"""
import json,hashlib,time,math
from pathlib import Path
from pyspark.sql import functions as F,Window
from pyspark.ml import PipelineModel
from pyspark.ml.functions import vector_to_array
from pyspark import StorageLevel
from src.ingest.dataset_audit import atomic_json
from src.ml.train_supervised import verified_input
from src.sql.traffic_analytics import locate_producer
from src.external_validation.dataset_audit import vector_key
from src.external_validation.transfer_evaluation import histogram
from src.ml.threshold_calibration import at_threshold
from src.scalability.benchmark_runner import session
from src.scalability.resource_monitor import environment,Monitor

def run(project,input_root,output,scratch):
    started=time.monotonic();output.mkdir(parents=True,exist_ok=True);cfg=json.loads((project/'configs/phase14_external_validation.yaml').read_text());design=json.loads((project/'configs/ml_experiments.yaml').read_text());manifest=json.loads((project/'manifests/parquet_layers.json').read_text());clean=json.loads((project/'configs/cleaning.yaml').read_text());spark=session(4,16,scratch);records=[];source_results=[];overlaps=[];seen_preprocessing=set();training_cache={};failures=[]
    try:
        raw,source_receipt=verified_input(spark,locate_producer(input_root,manifest['independent_mount']['summary_sha256']),manifest,clean);common=cfg['common_features'];source=raw.select('source_day','binary_label','attack_family','original_label','record_fingerprint',*common)
        for n in common:
            v=F.col(n);source=source.withColumn(n,F.when(v.isNotNull() & ~F.isnan(v) & (F.abs(v)!=float('inf')) & (v>=0),v))
        source=source.withColumn('predictor_key',vector_key(common)).withColumn('split_rank',F.when(F.col('source_day').isin(design['protocols']['B']['train']),0).when(F.col('source_day').isin(design['protocols']['B']['validation']),1).otherwise(2));first=source.groupBy('predictor_key').agg(F.min('split_rank').alias('earliest'));source=source.join(first,'predictor_key').where('split_rank=earliest').persist(StorageLevel.DISK_ONLY)
        audit_paths=list(input_root.rglob('external_audit.json'));assert len(audit_paths)==1;target=spark.read.parquet(str(audit_paths[0].parent/'feature_ready')).where('eligible').persist(StorageLevel.DISK_ONLY)
        unit_checks=[]
        for name,frame in [('source',raw),('external',target)]:
            count=F.col('tot_fwd_pkts')+F.col('tot_bwd_pkts');ratio=F.col('flow_duration')*F.col('flow_pkts_s')/count;eligible=(F.col('flow_duration')>0) & (F.col('flow_pkts_s')>0) & (count>0) & (F.abs(ratio)!=float('inf')) & ~F.isnan(ratio)
            values=frame.where(eligible).select(ratio.alias('implied_units_per_second'));support=values.count();q=values.approxQuantile('implied_units_per_second',[.01,.5,.99],.001);matches=values.where(F.abs(F.col('implied_units_per_second')/1000000.-1)<=.01).count()
            unit_checks.append(dict(dataset=name,eligible_rows=support,within_one_percent_microsecond_identity=matches,fraction=matches/support if support else None,quantiles=q,definition='duration * packets_per_second / (forward_count+reverse_count); expected1000000 for microseconds',label_information_used=False))
        atomic_json(output/'unit_consistency.json',unit_checks)
        assert all(r['eligible_rows']>=1000 and r['fraction']>=.95 for r in unit_checks),'Duration/rate unit consistency not established;do not silently reinterpret units'
        distribution_support=[]
        for feature in common:
            reference=source.where('split_rank=0');bounds=reference.agg(F.min(feature).alias('low'),F.max(feature).alias('high')).first();low,high=bounds.low,bounds.high
            for condition in ('all','benign','attack'):
                for domain,population in [('source_training',reference),('external_all',target)]:
                    if condition!='all':population=population.where(F.col('binary_label')==(0 if condition=='benign' else 1))
                    counts=population.agg(F.count('*').alias('rows'),F.sum(F.col(feature).isNull().cast('long')).alias('missing'),F.sum(((F.col(feature)<low)|(F.col(feature)>high)).cast('long')).alias('outside_source_range')).first().asDict();q=population.approxQuantile(feature,[0.,.25,.5,.75,1.],.001)
                    distribution_support.append(dict(feature=feature,domain=domain,condition=condition,source_minimum=low,source_maximum=high,quantiles=q,median=q[2] if q else None,interquartile_range=q[3]-q[1] if q else None,**counts))
        atomic_json(output/'distribution_support.json',distribution_support)
        model_paths=list(input_root.rglob('models.json'));assert len(model_paths)==1,'Attach completed external validation model output';registry=json.loads(model_paths[0].read_text());assert len(registry)==12
        populations=json.loads((model_paths[0].parent/'populations.json').read_text());test=source.where('split_rank=2');assert test.count()==sum(r['count'] for r in populations if r['dataset']=='source' and r['split_rank']==2)
        probes=spark.createDataFrame([(None,None,None),(0.,0.,0.),(1000000.,10.,5.)],','.join(n+' DOUBLE' for n in common))
        for entry in registry:
            folder=model_paths[0].parent/entry['saved']['artifact'];hashes={p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*') if p.is_file() and not p.name.endswith('.crc')};assert hashes==entry['saved']['sha256']
            pipeline=PipelineModel.load(str(folder));first_scores=[list(r[0]) for r in pipeline.transform(probes).select(vector_to_array('probability')).collect()];again=PipelineModel.load(str(folder));second_scores=[list(r[0]) for r in again.transform(probes).select(vector_to_array('probability')).collect()];assert first_scores==second_scores
            if entry['domain']=='source':active=source;column='split_rank';fraction=cfg['source_train_fraction_permyriad']
            else:
                column='chronological_rank' if entry['protocol']=='chronological' else 'grouped_rank';active=target.where('chronological_retained') if entry['protocol']=='chronological' else target;fraction=cfg['target_train_fraction_permyriad']
            train=active.where(F.col(column)==0).where(F.pmod(F.xxhash64(F.lit(cfg['seed']),'predictor_key'),F.lit(10000))<fraction);validation=active.where(F.col(column)==1);training_key=(entry['domain'],entry['protocol'])
            if training_key not in training_cache:
                day_counts=[r.asDict() for r in train.groupBy('source_day','binary_label').count().collect()];eligible_train=active.where(F.col(column)==0);group_count=train.select('predictor_key').distinct().count();eligible_groups=eligible_train.select('predictor_key').distinct().count();eligible_rows=eligible_train.count();training_cache[training_key]=dict(day_counts=day_counts,sampled_predictor_groups=group_count,eligible_training_groups=eligible_groups,eligible_training_rows=eligible_rows,observed_group_fraction=group_count/eligible_groups,observed_flow_fraction=sum(x['count'] for x in day_counts)/eligible_rows)
            sampling=training_cache[training_key];training_counts=sampling['day_counts'];assert sum(x['count'] for x in training_counts)==entry['training_rows'];h,_=histogram(pipeline,validation);expected={int(k):v for k,v in entry['calibration_histogram'].items()};assert h==expected,'Independent calibration histogram differs'
            preprocessing_key=hashlib.sha256(json.dumps({'domain':entry['domain'],'protocol':entry['protocol'],'preprocessing':entry['preprocessing']},sort_keys=True).encode()).hexdigest()
            if preprocessing_key not in seen_preprocessing:
                seen_preprocessing.add(preprocessing_key);imputer=next(x for x in pipeline.stages if type(x).__name__=='ImputerModel');imputed=imputer.getOutputCols()
                sets={}
                for name,population in [('training',train),('validation',validation)]:sets[name]=imputer.transform(population).withColumn('_imputed_key',vector_key(imputed)).select('_imputed_key').distinct().persist(StorageLevel.DISK_ONLY)
                pair=sets['training'].join(sets['validation'],'_imputed_key').count();overlaps.append(dict(preprocessing_key=preprocessing_key,domain=entry['domain'],protocol=entry['protocol'],first='training',second='validation',imputed_collision_groups=pair))
                external_tests={'chronological':target.where('chronological_retained AND chronological_rank=2'),'grouped':target.where('grouped_rank=2')}
                tests={'source_holdout':test,**external_tests} if entry['domain']=='source' else {entry['protocol']:external_tests[entry['protocol']]}
                for scope,evaluation in tests.items():
                    keys=imputer.transform(evaluation).withColumn('_imputed_key',vector_key(imputed)).select('_imputed_key').distinct().persist(StorageLevel.DISK_ONLY)
                    for role,reference in sets.items():overlaps.append(dict(preprocessing_key=preprocessing_key,domain=entry['domain'],protocol=entry['protocol'],first=role,second=scope,imputed_collision_groups=reference.join(keys,'_imputed_key').count(),meaning='Diagnostic preprocessing collision,not exact event duplication'))
                    keys.unpersist()
                for reference in sets.values():reference.unpersist()
                atomic_json(output/'imputed_overlap_audit.json',overlaps)
            records.append(dict(model=entry['model'],preprocessing_key=preprocessing_key,original_components_verified=len(hashes),independent_runtime_reload=True,probe_scores=first_scores,calibration_histogram_identical=True,training_day_counts=training_counts,sampling=sampling,threshold_bin_unchanged=entry['threshold_bin'],model_source=entry['saved']['artifact']))
            atomic_json(output/'independent_reload.json',records)
            if entry['domain']=='source':
                score_start=time.monotonic();h,groups=histogram(pipeline,test);score_seconds=time.monotonic()-score_start
                for operating,index in [('validation_budget',entry['threshold_bin']),('fixed_half',1024)]:source_results.append(dict(model=entry['model'],domain='source',evaluation_protocol='B-common retained source holdout',operating=operating,threshold_bin=index,metrics=at_threshold(h,index,2048),score_histogram=h,groups=groups,score_seconds=score_seconds,rows_per_second=sum(sum(v) for v in h.values())/score_seconds,interpretation='Same frozen E2 model and source-only calibration; retrospective source holdout,not an untouched new test'))
                atomic_json(output/'source_reference.json',source_results)
            if entry['model'].endswith('-LR'):
                from src.explainability.sampling import sample_groups
                external_tests={'chronological':target.where('chronological_retained AND chronological_rank=2'),'grouped':target.where('grouped_rank=2')}
                contexts=external_tests if entry['domain']=='source' else {entry['protocol']:external_tests[entry['protocol']]}
                estimator=pipeline.stages[-1];threshold=entry['threshold_bin']
                for context,population in contexts.items():
                    scored=pipeline.transform(population).withColumn('_score',vector_to_array('probability')[1]);scored=scored.withColumn('_positive',F.least(F.floor(F.col('_score')*2048),F.lit(2047))>=threshold).withColumn('_outcome',F.when(F.col('binary_label')==1,F.when(F.col('_positive'),'TP').otherwise('FN')).otherwise(F.when(F.col('_positive'),'FP').otherwise('TN')))
                    representative=sample_groups(scored,cfg['seed'],100)
                    within=Window.partitionBy('attack_family','_outcome','predictor_key').orderBy('record_fingerprint','source_day','original_label');distinct=scored.withColumn('_group_representative',F.row_number().over(within)).where('_group_representative=1');rank=Window.partitionBy('attack_family','_outcome').orderBy(F.xxhash64(F.lit(cfg['seed']),'record_fingerprint'),'record_fingerprint');enriched=distinct.withColumn('_case_rank',F.row_number().over(rank)).where('_case_rank<=8').limit(200)
                    for kind,subset in [('representative_groups',representative),('enriched_groups',enriched)]:
                        sums={};residual=0.
                        for x in subset.select('source_day','attack_family','_outcome','_score',vector_to_array('scaled_features').alias('_x'),vector_to_array('rawPrediction').alias('_raw')).collect():
                            contributions=[float(a*b) for a,b in zip(estimator.coefficients,x._x)];error=abs(estimator.intercept+math.fsum(contributions)-x._raw[1]);assert error<=1e-8;residual=max(residual,error);key=(x.source_day,x.attack_family,x._outcome);v=sums.setdefault(key,dict(rows=0,score_sum=0.,high_confidence_errors=0,signed=[0.]*len(contributions)));v['rows']+=1;v['score_sum']+=x._score;v['high_confidence_errors']+=int((x._outcome=='FN' and x._score<=.1) or (x._outcome=='FP' and x._score>=.9));v['signed']=[a+b for a,b in zip(v['signed'],contributions)]
                        failures.append(dict(model=entry['model'],evaluation_protocol=context,sample_kind=kind,threshold_bin=threshold,max_logit_residual=residual,strata=[dict(day=k[0],family=k[1],outcome=k[2],rows=v['rows'],mean_score=v['score_sum']/v['rows'],high_confidence_errors=v['high_confidence_errors'],mean_signed_contributions=[z/v['rows'] for z in v['signed']]) for k,v in sums.items()],interpretation='Deterministic group representatives;enrichment is not prevalence;bin2048 never predicts positive'))
                        atomic_json(output/'failure_analysis_verified.json',failures)
            print('PHASE14 MODEL INDEPENDENTLY VERIFIED',entry['model'],flush=True)
        atomic_json(output/'receipt.json',dict(status='validated',stage='14C-independent',fitting_performed=False,threshold_changes=False,models=len(records),source_references=len(source_results),source=source_receipt,resources=environment(spark),seconds=time.monotonic()-started));print('PHASE14 MODEL VERIFICATION COMPLETE',len(records),flush=True)
    finally:spark.stop()
