"""Full-support error strata, training-bin shifts and matched adaptive probes."""
from collections import defaultdict
from hashlib import sha256
from math import log,fsum
from time import monotonic
from pyspark import StorageLevel
from pyspark.ml import PipelineModel
from pyspark.ml.functions import vector_to_array
from pyspark.sql import functions as F,Window
from src.ingest.dataset_audit import atomic_json,spark_session
from src.ingest.parquet_pipeline import driver_peak_bytes,resource_limits
from src.ml.phase8_baselines import benchmark_population,json_file
from src.ml.feature_registry import predictor_input,registry
from src.ml.train_supervised import verified_input
from src.sql.traffic_analytics import locate_producer,require
from src.explainability.exact import linear,verify_linear
from src.explainability.sampling import sample_groups


def run(project,input_root,archives,inventory,bounds,output,scratch):
    start=monotonic();output.mkdir(parents=True,exist_ok=True)
    design=json_file(project,'configs/ml_experiments.yaml');upstream=json_file(project,'manifests/parquet_layers.json');original=json_file(project,'manifests/phase4_models.json');names=registry(design,upstream['feature_columns'])
    spark=spark_session(design,scratch);spark.conf.set('spark.sql.sources.partitionColumnTypeInference.enabled','false')
    cases=[];shifts=[];adaptive=[];private=[];supports=[]
    try:
        raw,receipt=verified_input(spark,locate_producer(input_root,upstream['independent_mount']['summary_sha256']),upstream,json_file(project,'configs/cleaning.yaml'))
        prepared=predictor_input(raw,names,design['version']).persist(StorageLevel.DISK_ONLY)
        for protocol in ('A','B'):
            active,split=benchmark_population(prepared,protocol,design,receipt['days'],original,output)
            model=PipelineModel.load(str(archives/(protocol+'-logistic_regression')));estimator=model.stages[-1];coefficients=list(estimator.coefficients);imputer=next(s for s in model.stages if type(s).__name__=='ImputerModel');feature_order=imputer.getInputCols()
            scored=model.transform(active.where('split_rank = 2')).withColumn('p',vector_to_array('probability')[1]).withColumn('outcome',F.when(F.col('binary_label')==1,F.when(F.col('p')>=.5,'TP').otherwise('FN')).otherwise(F.when(F.col('p')>=.5,'FP').otherwise('TN'))).persist(StorageLevel.DISK_ONLY)
            support=[r.asDict() for r in scored.groupBy('source_day','attack_family','outcome').count().collect()];supports.append(dict(protocol=protocol,strata=support,eligible_rows=sum(r['count'] for r in support)))
            window=Window.partitionBy('source_day','attack_family','outcome').orderBy(F.xxhash64('record_fingerprint',F.lit(23013)),'record_fingerprint')
            selected=scored.withColumn('case_rank',F.row_number().over(window)).where('case_rank <= 8').orderBy('case_rank','source_day','attack_family','outcome').limit(1000)
            values=selected.select('source_day','attack_family','outcome','p',vector_to_array(estimator.getFeaturesCol()).alias('x'),vector_to_array('rawPrediction').alias('raw')).collect();strata={}
            for index,row in enumerate(values):
                e=linear(coefficients,estimator.intercept,row.x);verify_linear(e,row.raw[1],row.p)
                key=(row.source_day,row.attack_family,row.outcome);stat=strata.setdefault(key,dict(rows=0,high_confidence_errors=0,mean_probability=0.,mean_contributions=[0.]*len(coefficients),max_logit_residual=0.))
                stat['rows']+=1;stat['mean_probability']+=row.p;stat['high_confidence_errors']+=int((row.outcome=='FN' and row.p<=.1) or (row.outcome=='FP' and row.p>=.9));stat['max_logit_residual']=max(stat['max_logit_residual'],abs(e['logit']-row.raw[1]))
                for i,v in enumerate(e['contributions']):stat['mean_contributions'][i]+=v
                private.append(dict(protocol=protocol,case=index,day=row.source_day,family=row.attack_family,outcome=row.outcome,**e))
            for key,stat in strata.items():
                stat['mean_probability']/=stat['rows'];stat['mean_contributions']=[v/stat['rows'] for v in stat['mean_contributions']];cases.append(dict(protocol=protocol,day=key[0],family=key[1],outcome=key[2],feature_order=feature_order,**stat))
            scored.unpersist()
            for feature in names:
                source=next(r for r in bounds if r['protocol']==protocol and r['role']=='training_reference' and r['feature']==feature)
                cuts=sorted(set(source['quantiles'][1:-1]));value=F.col(feature);bucket=F.when(value.isNull(),F.lit(-1)).otherwise(sum((F.when(value>cut,1).otherwise(0) for cut in cuts),F.lit(0)))
                counts=active.withColumn('bucket',bucket).where('split_rank IN (0,2)').groupBy('split_rank','bucket').count().collect();hist={role:{r.bucket:r['count'] for r in counts if r.split_rank==role} for role in (0,2)};totals={role:sum(hist[role].values()) for role in hist};keys=sorted(set(hist[0])|set(hist[2]));js=0.
                for k in keys:
                    p=hist[0].get(k,0)/totals[0];q=hist[2].get(k,0)/totals[2];m=(p+q)/2
                    if p:js+=.5*p*log(p/m,2)
                    if q:js+=.5*q*log(q/m,2)
                shifts.append(dict(protocol=protocol,feature=feature,training_cuts=cuts,missing_bucket=-1,training_counts=hist[0],evaluation_counts=hist[2],training_rows=totals[0],evaluation_rows=totals[2],js_bits=js))
            active.unpersist();atomic_json(output/'error_cases.json',cases);atomic_json(output/'distribution_shift.json',shifts)
        # Reference-derived probes are drawn only from initial-model training days.
        probes=sample_groups(prepared.where("source_day IN ('2018-02-14','2018-02-15')"),23013,32).select('record_fingerprint',*names).persist(StorageLevel.DISK_ONLY)
        for entry in [e for e in inventory if e['kind']=='adaptive']:
            path=archives/entry['id'];require({p.relative_to(path).as_posix():sha256(p.read_bytes()).hexdigest() for p in path.rglob('*') if p.is_file()}==entry['sha256'],'Adaptive archive identity differs')
            model=PipelineModel.load(str(path));estimator=model.stages[-1];imputer=next(s for s in model.stages if type(s).__name__=='ImputerModel');feature_order=imputer.getInputCols();data=model.transform(probes).orderBy('record_fingerprint').select(vector_to_array(estimator.getFeaturesCol()).alias('x'),vector_to_array('probability').alias('p'),vector_to_array('rawPrediction').alias('raw')).collect()
            record=dict(model=entry['id'],selected_policies=entry['metadata']['selected_policies'],frozen_initial=entry['metadata']['frozen_initial'],feature_order=feature_order,rows=len(data),probabilities=[r.p[1] for r in data],population='matched reference-derived probes from initial training days; retrospective model comparison; no issued-decision attribution')
            if hasattr(estimator,'coefficients'):
                explanations=[linear(list(estimator.coefficients),estimator.intercept,r.x) for r in data]
                for r,e in zip(data,explanations):verify_linear(e,r.raw[1],r.p[1])
                record['mean_signed_contributions']=[fsum(e['contributions'][i] for e in explanations)/len(data) for i in range(len(feature_order))];record['max_logit_residual']=max(abs(e['logit']-r.raw[1]) for e,r in zip(explanations,data))
            adaptive.append(record)
        atomic_json(output/'adaptive_reference_probes.json',adaptive);atomic_json(output/'error_support.json',supports);atomic_json(output/'private_error_cases.json',private)
        atomic_json(output/'receipt.json',dict(status='validated',stage='13F-diagnostics',input=receipt,error_case_rows=sum(r['rows'] for r in cases),error_strata=len(cases),distribution_comparisons=len(shifts),adaptive_models=len(adaptive),seconds=monotonic()-start,driver_peak_rss_bytes=driver_peak_bytes(spark),resources=resource_limits(spark,design,output),sha256={p.name:sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()}))
        print('PHASE13 diagnostics complete',flush=True)
    finally:spark.stop()
