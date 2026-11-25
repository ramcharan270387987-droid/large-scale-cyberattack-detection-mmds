"""Prespecified common-feature source transfer and matched target baselines."""
import json,time,math,hashlib
from pathlib import Path
from functools import reduce
from pyspark import StorageLevel
from pyspark.sql import functions as F,Window
from pyspark.ml import PipelineModel
from pyspark.ml.classification import LogisticRegression,RandomForestClassifier
from pyspark.ml.functions import vector_to_array
from pyspark.ml.feature import SQLTransformer,VectorAssembler
from src.ingest.dataset_audit import atomic_json,spark_session
from src.ml.train_supervised import verified_input
from src.sql.traffic_analytics import locate_producer
from src.ml.preprocessing import fit_preprocessing
from src.ml.model_registry import capture
from src.ml.threshold_calibration import choose,curves,at_threshold
from src.external_validation.dataset_audit import vector_key
from src.scalability.resource_monitor import Monitor,environment

def histogram(model,frame):
    scored=model.transform(frame).withColumn('score',vector_to_array('probability')[1]);bins=F.least(F.floor(F.col('score')*2048),F.lit(2047)).cast('int')
    rows=scored.groupBy('source_day','attack_family','binary_label',bins.alias('bin')).count().collect();h={}
    for row in rows:
        h.setdefault(int(row.bin),[0,0])[int(row.binary_label)]+=row['count']
    return h,[r.asDict() for r in rows]
def control_pipeline(train,preprocessor,family):
    if family not in ('duration','majority'):raise ValueError('Unsupported control')
    scale=max(1.,train.approxQuantile('flow_duration',[.99],.001)[0]) if family=='duration' else 1.
    value=f'LEAST(1D,GREATEST(0D,flow_duration_imputed/{scale!r}))' if family=='duration' else '0D'
    return PipelineModel(stages=[preprocessor.stages[0],SQLTransformer(statement=f'SELECT *,1D-({value}) AS _p0,({value}) AS _p1 FROM __THIS__'),VectorAssembler(inputCols=['_p0','_p1'],outputCol='probability')])

def support(frame):return {int(r.binary_label):int(r['count']) for r in frame.groupBy('binary_label').count().collect()}
def role(frame,column,rank,retained=None):
    result=frame.where(F.col(column)==rank)
    return result.where(retained) if retained else result

def run(project,input_root,output,scratch):
    start=time.monotonic();output.mkdir(parents=True,exist_ok=True);cfg=json.loads((project/'configs/phase14_external_validation.yaml').read_text());common=cfg['common_features'];design=json.loads((project/'configs/ml_experiments.yaml').read_text());upstream=json.loads((project/'manifests/parquet_layers.json').read_text());clean=json.loads((project/'configs/cleaning.yaml').read_text())
    spark=spark_session({'spark':{'master':'local[4]','driver_memory':'8g','shuffle_partitions':16,'input_partition_bytes':67108864}},scratch);spark.conf.set('spark.sql.ansi.enabled','false');models={};records=[];registry=[];collisions=[];distributions=[];population=[];failures=[]
    with Monitor() as mon:
      try:
        raw,source_receipt=verified_input(spark,locate_producer(input_root,upstream['independent_mount']['summary_sha256']),upstream,clean)
        for n in cfg['source_features']:
            v=F.col(n);raw=raw.withColumn(n,F.when(v.isNotNull() & ~F.isnan(v) & (F.abs(v)!=float('inf')) & (v>=0),v))
        source=raw.withColumn('predictor_key',vector_key(common)).withColumn('canonical_key',vector_key(cfg['source_features']));source=source.withColumn('split_rank',F.when(F.col('source_day').isin(design['protocols']['B']['train']),0).when(F.col('source_day').isin(design['protocols']['B']['validation']),1).otherwise(2));first=source.groupBy('predictor_key').agg(F.min('split_rank').alias('earliest'));source=source.join(first,'predictor_key').where('split_rank=earliest').persist(StorageLevel.DISK_ONLY)
        producer=list(input_root.rglob('external_audit.json'));assert len(producer)==1,'Attach accepted14B output';audit=json.loads(producer[0].read_text());assert audit['status']=='validated' and audit['dataset']==cfg['dataset']
        from src.external_validation.supplemental_audit import all_columns
        atomic_json(output/'external_full_column_audit.json',all_columns(spark,producer[0].parent,audit))
        target=spark.read.parquet(str(producer[0].parent/'feature_ready')).where('eligible')
        label_catalog=json.loads((project/'reports/phase14_14B/label_byte_catalog.json').read_text())
        assert label_catalog['rows']==audit['physical_data_rows']
        mapping={x['observed_utf8_label']:x['original_label'] for x in label_catalog['labels']};hexes={x['observed_utf8_label']:x['original_label_hex'] for x in label_catalog['labels']}
        from itertools import chain
        mapping_expr=F.create_map(*[F.lit(x) for x in chain.from_iterable(mapping.items())]);hex_expr=F.create_map(*[F.lit(x) for x in chain.from_iterable(hexes.items())])
        target=target.withColumn('observed_utf8_label',F.col('original_label')).withColumn('original_label_hex',hex_expr[F.col('original_label')]).withColumn('original_label',mapping_expr[F.col('original_label')]).withColumn('attack_family',F.col('original_label')).persist(StorageLevel.DISK_ONLY)
        assert target.where('original_label IS NULL OR original_label_hex IS NULL').limit(1).count()==0

        source_keys=source.where('split_rank IN (0,1)').select('predictor_key').distinct();target_tests={}
        for protocol,column,retained in [('chronological','chronological_rank','chronological_retained'),('grouped','grouped_rank',None)]:
            active=target.where(retained) if retained else target
            groups=active.groupBy('predictor_key').agg(F.countDistinct(column).alias('roles'));assert groups.where('roles>1').limit(1).count()==0
            population.extend(dict(dataset='external',protocol=protocol,**r.asDict()) for r in active.groupBy(column,'source_day','binary_label','attack_family').count().collect())
            target_tests[protocol]=role(active,column,2)
        population.extend(dict(dataset='source',protocol='B-common',**r.asDict()) for r in source.groupBy('split_rank','source_day','binary_label','attack_family').count().collect());atomic_json(output/'populations.json',population)
        for key in ('canonical_key','predictor_key'):
            source_set=source.where('split_rank IN (0,1)').select(key).distinct();cross=target.join(source_set,key,'inner');collisions.append(dict(key=key,rows=cross.count(),groups=cross.select(key).distinct().count(),meaning='Feature collision, not proof of same network event'))
        atomic_json(output/'collision_audit.json',collisions)
        # Source-training-derived distributions, including class-conditioned subsets.
        ref=source.where('split_rank=0')
        for n in common:
            q=ref.approxQuantile(n,[0.,.25,.5,.75,1.],.001);cuts=sorted(set(q));v=F.col(n);bucket=F.when(v.isNull(),-1).otherwise(reduce(lambda a,b:a+b,[F.when(v>c,1).otherwise(0) for c in cuts],F.lit(0)))
            for klass in ('all','benign','attack'):
                frames=[ref,target];hist=[]
                for frame in frames:
                    if klass!='all':frame=frame.where(F.col('binary_label')==(0 if klass=='benign' else 1))
                    hist.append({int(r.bucket):r['count'] for r in frame.select(bucket.alias('bucket')).groupBy('bucket').count().collect()})
                a,b=hist;na,nb=sum(a.values()),sum(b.values());keys=sorted(set(a)|set(b));js=psi=None
                if na and nb:
                    js=0.;psi=0.
                    for k in keys:
                        p=a.get(k,0)/na;t=b.get(k,0)/nb;m=(p+t)/2
                        if p:js+=p*math.log2(p/m)/2
                        if t:js+=t*math.log2(t/m)/2
                        ps=(a.get(k,0)+1e-6)/(na+1e-6*len(keys));ts=(b.get(k,0)+1e-6)/(nb+1e-6*len(keys));psi+=(ts-ps)*math.log(ts/ps)
                distributions.append(dict(feature=n,condition=klass,units='microseconds' if n=='flow_duration' else 'packets',source_quantiles=q,source_bins=a,target_bins=b,source_rows=na,target_rows=nb,js_bits=js,psi_natural=psi,target_quantiles=target.approxQuantile(n,[0.,.25,.5,.75,1.],.001) if klass=='all' else None))
        atomic_json(output/'distribution_shift.json',distributions)
        jobs=[('E2','source','B-common',source,'split_rank')]
        for protocol,column,retained in [('chronological','chronological_rank','chronological_retained'),('grouped','grouped_rank',None)]:jobs.append(('E3','target',protocol,target.where(retained) if retained else target,column))
        probes=spark.createDataFrame([(None,None,None),(0.,0.,0.),(1000000.,10.,5.)],','.join(n+' DOUBLE' for n in common))
        for experiment,domain,protocol,active,column in jobs:
            train=role(active,column,0).withColumn('split_rank',F.lit(0));fraction=cfg['source_train_fraction_permyriad'] if domain=='source' else cfg['target_train_fraction_permyriad'];train=train.where(F.pmod(F.xxhash64(F.lit(cfg['seed']),'predictor_key'),F.lit(10000))<fraction).persist(StorageLevel.DISK_ONLY);classes=support(train);assert all(classes.get(k,0)>=cfg['minimum_class_training'] for k in (0,1)),classes
            validation=role(active,column,1);t=time.monotonic();treeprep,lrprep,preprocessing=fit_preprocessing(train,common);prep_seconds=time.monotonic()-t
            for family in ('LR','RF','majority','duration'):
                identifier=f'{experiment}-{protocol}-{family}';prep=lrprep if family=='LR' else treeprep;t=time.monotonic();params=cfg['models'].get(family,{})
                estimator=(LogisticRegression(labelCol='binary_label',featuresCol='scaled_features',standardization=False,tol=1e-5,**params) if family=='LR' else RandomForestClassifier(labelCol='binary_label',featuresCol='features',seed=cfg['seed'],maxBins=24,maxMemoryInMB=192,**params)).fit(prep.transform(train)) if family in ('LR','RF') else None;fit_seconds=time.monotonic()-t
                if estimator is not None:pipeline=PipelineModel(stages=[*prep.stages,estimator])
                else:pipeline=control_pipeline(train,treeprep,family);fit_seconds=time.monotonic()-t
                timings={};saved=capture(pipeline,identifier,output,probes,timings=timings);cal,_=histogram(pipeline,validation);threshold,validation_metrics=choose(curves(cal,2048),cfg['validation_fpr_ceiling']);models[identifier]=pipeline
                record=dict(model=identifier,experiment=experiment,domain=domain,protocol=protocol,features=common,training_support=classes,training_rows=sum(classes.values()),sample_permyriad=fraction,preprocessing=preprocessing,preprocessing_seconds=prep_seconds,fit_seconds=fit_seconds,threshold_bin=threshold,validation_metrics=validation_metrics,calibration_histogram=cal,saved=saved,timings=timings);registry.append(record);atomic_json(output/'models.json',registry)
                protocols=target_tests if domain=='source' else {protocol:target_tests[protocol]}
                for target_protocol,test in protocols.items():
                  if family=='LR':
                    scored=pipeline.transform(test).withColumn('_score',vector_to_array('probability')[1]).withColumn('_outcome',F.when(F.col('binary_label')==1,F.when(F.col('_score')>=threshold/2048,'TP').otherwise('FN')).otherwise(F.when(F.col('_score')>=threshold/2048,'FP').otherwise('TN')))
                    representative=scored.orderBy(F.xxhash64(F.lit(cfg['seed']),'predictor_key'),'record_fingerprint').limit(100)
                    enriched=scored.withColumn('_rank',F.row_number().over(Window.partitionBy('attack_family','_outcome').orderBy(F.xxhash64(F.lit(cfg['seed']),'record_fingerprint')))).where('_rank<=8').limit(200)
                    for kind,subset in [('representative',representative),('enriched',enriched)]:
                        sums={};max_residual=0.
                        for x in subset.select('source_day','attack_family','_outcome','_score',vector_to_array('scaled_features').alias('_x'),vector_to_array('rawPrediction').alias('_raw')).collect():
                            contributions=[float(a*b) for a,b in zip(estimator.coefficients,x._x)];logit=estimator.intercept+math.fsum(contributions);max_residual=max(max_residual,abs(logit-x._raw[1]));assert abs(logit-x._raw[1])<=1e-8
                            key=(x.source_day,x.attack_family,x._outcome);s=sums.setdefault(key,{'rows':0,'score_sum':0.,'high_confidence_errors':0,'signed_sum':[0.]*len(contributions)});s['rows']+=1;s['score_sum']+=x._score;s['high_confidence_errors']+=int((x._outcome=='FN' and x._score<=.1) or (x._outcome=='FP' and x._score>=.9));s['signed_sum']=[a+b for a,b in zip(s['signed_sum'],contributions)]
                        failures.append(dict(model=identifier,evaluation_protocol=target_protocol,sample_kind=kind,threshold_bin=threshold,max_logit_residual=max_residual,strata=[dict(day=k[0],family=k[1],outcome=k[2],rows=v['rows'],mean_score=v['score_sum']/v['rows'],high_confidence_errors=v['high_confidence_errors'],mean_signed_contributions=[z/v['rows'] for z in v['signed_sum']]) for k,v in sums.items()],interpretation='Enriched cases are not prevalence estimates; additive log-odds only'))
                    atomic_json(output/'failure_analysis.json',failures)
                  for sensitivity in ('primary','exclude_source_collisions'):
                    evaluation=test.join(source_keys,'predictor_key','left_anti') if sensitivity!='primary' else test;t=time.monotonic();hist,groups=histogram(pipeline,evaluation);seconds=time.monotonic()-t;count=sum(sum(v) for v in hist.values());assert count>0
                    imputer=next(s for s in pipeline.stages if type(s).__name__=='ImputerModel');imputed=imputer.getOutputCols();train_imputed=imputer.transform(train).withColumn('_imputed_key',vector_key(imputed)).select('_imputed_key').distinct();imputed_cross=imputer.transform(test).withColumn('_imputed_key',vector_key(imputed)).join(train_imputed,'_imputed_key','inner').count() if sensitivity=='primary' else None
                    for operating,index in [('validation_budget',threshold),('fixed_half',1024)]:
                        metrics=at_threshold(hist,index,2048);family_rows=[]
                        for family_name in sorted({x['attack_family'] for x in groups}):
                            h={}
                            for x in groups:
                                if x['attack_family']==family_name:h.setdefault(x['bin'],[0,0])[x['binary_label']]+=x['count']
                            family_rows.append(dict(family=family_name,**at_threshold(h,index,2048)))
                        records.append(dict(model=identifier,experiment=experiment,evaluation_protocol=target_protocol,sensitivity=sensitivity,operating=operating,threshold_bin=index,metrics=metrics,score_histogram=hist,families=family_rows,score_seconds=seconds,rows_per_second=count/seconds,prevalence=sum(v[1] for v in hist.values())/count,imputed_cross_training_rows=imputed_cross,coverage='All eligible retained target-test rows for stated sensitivity',feature_contract='conditional common3; new source/target fits, not archived18 transfer'))
                    atomic_json(output/'external_evaluation.json',records)
                print('PHASE14C MODEL COMPLETE',identifier,sum(classes.values()),flush=True)
            train.unpersist()
        atomic_json(output/'receipt.json',dict(status='validated',source=source_receipt,external_input_sha256=hashlib.sha256(producer[0].read_bytes()).hexdigest(),models=len(registry),evaluation_records=len(records),resources=environment(spark),spark_version=spark.version,master=spark.sparkContext.master,seconds=time.monotonic()-start,unsupported=['E1 exact18-feature archive transfer: unverified extraction semantics','E4/E5 optional not executed','Exact cross-dataset event overlap: original identifiers absent']))
        print('PHASE14C EXTERNAL VALIDATION COMPLETE',len(records),flush=True)
      finally:spark.stop()
    receipt=json.loads((output/'receipt.json').read_text());receipt['memory']=mon.summary();atomic_json(output/'receipt.json',receipt)
