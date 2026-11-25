"""Verified Phase 2 Spark backend; only compact histogram predictions leave Kaggle."""
import json
import time
from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
from src.adaptation.lifecycle import digest
from src.adaptation.evaluation import BINS,merge


class SparkBackend:
    kind='historical'; min_class=100
    def __init__(self,spark,prepared,names,output,scratch,config,*,family='LR',seed=23013,sample=125,weight=1):
        from pyspark.sql import functions as F
        from src.ml.split_protocols import group_sample
        self.spark=spark; self.names=names; self.output=Path(output); self.scratch=Path(scratch)
        self.name=f'E-{family}-seed{seed}-sample{sample}-weight{weight}'
        self.family=family; self.seed=seed; self.weight=weight
        self.frame=prepared; self.models={}; self.meta={}; self.scored={}; self.physical_fits=0
        self.initial=['2018-02-14','2018-02-15']; self.calibration=['2018-02-16']
        self.forward=['2018-02-20','2018-02-21','2018-02-22','2018-02-23','2018-02-28','2018-03-01','2018-03-02']
        self.train=group_sample(prepared.where('split_rank=0'),{'seed':seed,'group_sample_permyriad':sample}).where('sampled').drop('sampled')
        self.counts={(r.source_day,r.split_rank):r['count'] for r in self.train.groupBy('source_day','split_rank').count().collect()}
        values=self.train.where(F.col('source_day').isin(self.initial)).select('flow_duration')
        self.edges=sorted(set(values.approxQuantile('flow_duration',[i/10 for i in range(1,10)],.001)))
        def bincol():
            c=F.lit(0)
            for edge in self.edges: c=c+F.when(F.col('flow_duration')>edge,1).otherwise(0)
            return c
        self.signal={}
        groups=prepared.groupBy('source_day',bincol().alias('bin')).count().collect()
        for r in groups: self.signal.setdefault(r.source_day,[0]*(len(self.edges)+1))[r.bin]=r['count']
        ref=[0]*(len(self.edges)+1)
        for r in self.train.where(F.col('source_day').isin(self.initial)).groupBy(bincol().alias('bin')).count().collect():ref[r.bin]=r['count']
        self.reference=ref
    def clock(self,day): return datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp()+86400
    def support(self,days,role):
        if role==0:return sum(self.counts.get((d,0),0) for d in days)
        return self.frame.where(f'split_rank={role}').where(self.frame.source_day.isin(days)).count()
    def eval_support(self,day):return sum(self.signal[day])
    def distribution(self,day):return self.signal[day]
    def fit(self,days):
        from pyspark.sql import functions as F
        from pyspark.ml import PipelineModel
        from pyspark.ml.classification import LogisticRegression,RandomForestClassifier
        from src.ml.preprocessing import fit_preprocessing,verify_vectors
        from src.ml.model_registry import capture
        from src.streaming.model_scoring import probe
        key=digest([self.name,days])
        if key in self.models:return key
        start=time.monotonic()
        train=self.train.where(F.col('source_day').isin(days)).persist()
        try:
            support={r.binary_label:r['count'] for r in train.groupBy('binary_label').count().collect()}
            if min(support.get(0,0),support.get(1,0))<100:raise ValueError('Insufficient training class support')
            t=time.monotonic(); unscaled,scaled,details=fit_preprocessing(train,self.names); prep=scaled if self.family=='LR' else unscaled
            vectors=prep.transform(train).withColumn('weight',F.when(F.col('binary_label')==1,self.weight).otherwise(1.)).persist()
            verify_vectors(vectors,len(details['active'])); preprocessing=time.monotonic()-t
            t=time.monotonic()
            estimator=(LogisticRegression(featuresCol='scaled_features',labelCol='binary_label',weightCol='weight',maxIter=12,regParam=.05,standardization=False)
                       if self.family=='LR' else RandomForestClassifier(featuresCol='features',labelCol='binary_label',weightCol='weight',numTrees=12,maxDepth=5,maxBins=24,minInstancesPerNode=30,seed=self.seed))
            classifier=estimator.fit(vectors); training=time.monotonic()-t
            model=PipelineModel(stages=[*prep.stages,classifier]); t=time.monotonic()
            receipt=capture(model,key,self.output,probe(self.spark,self.names)); persistence=time.monotonic()-t
            loaded=PipelineModel.load(str(self.output/receipt['artifact']))
            # Audit actual candidate preprocessing collisions across fitting and nonfitting roles.
            # Exact/canonical/predictor role disjointness is established globally on all rows once.
            from pyspark.ml.functions import vector_to_array
            fitting=prep.transform(train).select(F.lit(0).alias('role'),F.sha2(F.to_json(vector_to_array('features')),256).alias('vector_key'))
            other=prep.transform(self.frame.where('split_rank<>0')).select(F.col('split_rank').alias('role'),F.sha2(F.to_json(vector_to_array('features')),256).alias('vector_key'))
            collisions=(fitting.unionByName(other).groupBy('vector_key').agg(F.min('role').alias('low'),F.max('role').alias('high')).where('low=0 and high>0').count())
            families={r.attack_family:r['count'] for r in train.groupBy('attack_family').count().collect()}
            vectors.unpersist()
            self.models[key]=loaded; self.physical_fits+=1
            self.meta[key]={'model':key,'family':self.family,'backend':self.name,'training_days':days,'rows':sum(support.values()),
                'classes':support,'family_support':families,'features':self.names,'preprocessing':details,
                'preprocessing_seconds':preprocessing,'training_seconds':training,'save_reload_seconds':persistence,
                'fit_seconds':time.monotonic()-start,'receipt':receipt,'independent_reload':True,
                'imputed_cross_role_groups':collisions,'imputed_policy':'diagnostic, no outcome-dependent mask',
                'source_commit':self.source_commit,'preprocessing_fit_role':0}
            if self.meta[key]['fit_seconds']>1800:raise ValueError('Candidate exceeded1800second cap')
            (self.output/'model_metadata.json').write_text(json.dumps(self.meta,allow_nan=False))
            print('FIT_COMPLETE',self.name,key,days,self.meta[key]['fit_seconds'],flush=True)
            return key
        finally:train.unpersist()
    def verify(self,key):
        from pyspark.ml import PipelineModel
        from src.streaming.model_scoring import probe
        from pyspark.ml.functions import vector_to_array
        meta=self.meta[key]; target=self.output/meta['receipt']['artifact']
        for relative,expected in meta['receipt']['sha256'].items():
            if sha256((target/relative).read_bytes()).hexdigest()!=expected:raise ValueError('Model hash mismatch')
        loaded=PipelineModel.load(str(target))
        def scores(model):return [tuple(r[0]) for r in model.transform(probe(self.spark,self.names)).select(vector_to_array('probability')).collect()]
        if scores(loaded)!=scores(self.models[key]):raise ValueError('Independent probe mismatch')
        self.models[key]=loaded
    def score(self,key,day,role):
        from pyspark.sql import functions as F
        from pyspark.ml.functions import vector_to_array
        cache=(key,day,role)
        if cache not in self.scored:
            started=time.monotonic()
            frame=self.frame.where((F.col('source_day')==day)&(F.col('split_rank')==role))
            scored=self.models[key].transform(frame).select('predictor_key','binary_label','attack_family',vector_to_array('probability')[1].alias('score'))
            invalid=F.col('score').isNull()|F.isnan('score')|(F.col('score')<0)|(F.col('score')>1)
            bins=F.when(invalid,-1).otherwise(F.least(F.floor(F.col('score')*BINS),F.lit(BINS-1)))
            # Issued predictions are materialized in private Kaggle scratch before label-release actions.
            path=self.scratch/'predictions'/f'{key}-{day}-{role}'
            scored.withColumn('score_bin',bins).write.mode('error').parquet(str(path))
            materialized=self.spark.read.parquet(str(path))
            rows=materialized.groupBy('attack_family','binary_label','score_bin').count().collect()
            hist={}
            for r in rows:
                if r.score_bin<0:raise ValueError('Invalid prediction scores')
                hist.setdefault(r.attack_family,{}).setdefault(int(r.score_bin),[0,0])[int(r.binary_label)]+=r['count']
            self.scored[cache]=hist
            directory=self.output/'prediction_histograms'; directory.mkdir(exist_ok=True)
            (directory/f'{key}-{day}-r{role}.json').write_text(json.dumps({'model':key,'day':day,'role':role,'family_histograms':hist,
                'prediction_seconds':time.monotonic()-started,'row_predictions_private_scratch':str(path)},allow_nan=False))
        return self.scored[cache]
    def hist(self,key,days,role):return merge([h for d in days for h in self.score(key,d,role).values()])


def run(project,input_root,output,scratch,stage):
    from pyspark.sql import functions as F
    from src.ingest.dataset_audit import spark_session,atomic_json
    from src.ingest.parquet_pipeline import driver_peak_bytes
    from src.ml.train_supervised import verified_input
    from src.ml.feature_registry import predictor_input,registry
    from src.ml.split_protocols import assign_population,crossing_groups
    from src.sql.traffic_analytics import locate_producer
    from src.adaptation.prequential_runner import run as replay
    output.mkdir(parents=True,exist_ok=True); scratch.mkdir(parents=True,exist_ok=True)
    load=lambda p:json.loads((project/p).read_text())
    config=load('configs/phase12_adaptation.yaml'); config['spark']={'master':'local[4]','driver_memory':'8g','shuffle_partitions':48,'input_partition_bytes':67108864}
    spark=spark_session(config,scratch); spark.conf.set('spark.sql.sources.partitionColumnTypeInference.enabled','false'); spark.sparkContext.setLogLevel('WARN')
    start=time.monotonic(); summary={'stage':stage,'status':'running','source_commit':load('phase12_source.json')['commit'],'config':config,'runs':[],'models':{}}
    atomic_json(output/'phase12_summary.json',summary)
    try:
        parquet=load('manifests/parquet_layers.json'); design=load('configs/ml_experiments.yaml')
        receipt=locate_producer(input_root,parquet['independent_mount']['summary_sha256'])
        raw,summary['input']=verified_input(spark,receipt,parquet,load('configs/cleaning.yaml'))
        names=registry(design,parquet['feature_columns'])
        prepared=predictor_input(raw.where('temporal_eligibility'),names,design['version'])
        assigned=assign_population(prepared,'A',design,summary['input']['days'])
        # Physical partitioning prunes repeated per-capture candidate/scoring reads.
        cache=scratch/'assigned'; assigned.write.partitionBy('source_day','split_rank').parquet(str(cache))
        frame=spark.read.parquet(str(cache))
        summary['cohorts']=[r.asDict() for r in frame.groupBy('source_day','split_rank','binary_label','attack_family').count().collect()]
        summary['cross_role_groups']={key:crossing_groups(frame,key).count() for key in ('record_fingerprint','split_feature_key','predictor_key')}
        if any(summary['cross_role_groups'].values()):raise ValueError('Prohibited role leakage')
        summary['retained_rows']=sum(r['count'] for r in summary['cohorts']); summary['purged_rows']=16232943-summary['retained_rows']
        summary['features']=names
        specs=[]
        if stage=='12C':specs=[('LR',23013,125,1,p,0,{}) for p in ('P0','P1','P4','P5')]
        elif stage=='12D':
            specs=[('LR',23013,125,1,p,0,{}) for p in ('P2','P3','P6')]
            specs += [('LR',23013,125,1,p,0,{'budget':6}) for p in ('P1','P2')]
        elif stage=='12E':
            specs=[('LR',23013,125,1,p,d,{}) for d in (1,3) for p in ('P0','P1','P2','P3','P4','P5','P6')]
            specs += [('RF',23013,125,1,p,0,{}) for p in ('P0','P1','P4')]
            specs += [('LR',23014,125,1,p,1,{}) for p in ('P0','P1')]
            specs += [('LR',23013,62,1,p,0,{}) for p in ('P0','P1')]
            specs += [('LR',23013,125,5,p,0,{}) for p in ('P0','P1')]
            specs += [('LR',23013,125,1,'P4',0,{'sliding':3}),('LR',23013,125,1,'P2',0,{'cooldown':0}),('LR',23013,125,1,'P2',0,{'minimum':400})]
        backends={}
        for family,seed,sample,weight,policy,delay,opts in specs:
            key=(family,seed,sample,weight)
            if key not in backends:
                backends[key]=SparkBackend(spark,frame,names,output,scratch,config,family=family,seed=seed,sample=sample,weight=weight)
                backends[key].source_commit=summary['source_commit']
            backend=backends[key]
            result=replay(backend,policy,delay,output/'registries'/digest([key,policy,delay,opts]),**opts)
            summary['runs'].append(result);summary['models'].update(backend.meta)
            summary['physical_fits']=sum(b.physical_fits for b in backends.values())
            atomic_json(output/'phase12_summary.json',summary)
            print('RUN_COMPLETE',result['summary'],flush=True)
        for backend in backends.values():
            for key in backend.models:backend.verify(key)
        summary.update(status='validated',elapsed_seconds=time.monotonic()-start,spark_version=spark.version,
                       driver_peak_rss_bytes=driver_peak_bytes(spark),resource={'master':spark.sparkContext.master,'defaultParallelism':spark.sparkContext.defaultParallelism})
        atomic_json(output/'phase12_summary.json',summary)
        print('PHASE12_COMPLETE',stage,flush=True)
    finally:spark.stop()
