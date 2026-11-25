"""Materialized single-node Spark volume/worker benchmarks on observed source rows."""
import json,time,hashlib,statistics,shutil
from pathlib import Path
from pyspark.ml import PipelineModel
from pyspark.ml.functions import vector_to_array
from pyspark.sql import functions as F
from src.ingest.dataset_audit import atomic_json,spark_session
from src.ml.train_supervised import verified_input
from src.sql.traffic_analytics import locate_producer
from src.scalability.resource_monitor import Monitor,environment

def canonical(rows):
    return sorted([r.asDict(recursive=True) if hasattr(r,'asDict') else r for r in rows],key=lambda r:json.dumps(r,sort_keys=True))
def equivalent(a,b):
    import math
    if isinstance(a,dict):return set(a)==set(b) and all(equivalent(a[k],b[k]) for k in a)
    if isinstance(a,list):return len(a)==len(b) and all(equivalent(x,y) for x,y in zip(a,b))
    if isinstance(a,float) or isinstance(b,float):return a==b or (a is not None and b is not None and math.isclose(a,b,abs_tol=1e-8,rel_tol=1e-8))
    return a==b
def checksum(frame,names):
    return frame.agg(F.count('*').alias('rows'),F.sum('binary_label').alias('attacks'),*[F.sum(F.coalesce(F.col(n),F.lit(0.))).alias(n) for n in names]).collect()
def workload(frame,name,preprocessor=None,names=None):
    if name=='ingest_checksum':return checksum(frame,names)
    if name=='analytics':return frame.groupBy('source_day','binary_label','attack_family').agg(F.count('*').alias('rows'),F.sum('flow_duration').alias('duration_sum')).collect()
    if name=='feature_transform':
        data=preprocessor.transform(frame);values=vector_to_array('scaled_features');return data.select('binary_label',F.aggregate(values,F.lit(0.),lambda a,b:a+b).alias('vector_sum')).agg(F.count('*').alias('rows'),F.sum('binary_label').alias('attacks'),F.sum('vector_sum').alias('vector_sum')).collect()
    raise ValueError('Unregistered benchmark workload')
def session(workers,partitions,scratch):
    s=spark_session({'spark':{'master':f'local[{workers}]','driver_memory':'8g','shuffle_partitions':partitions,'input_partition_bytes':67108864}},scratch);s.conf.set('spark.sql.adaptive.enabled','false');s.conf.set('spark.sql.ansi.enabled','false');assert s.sparkContext.master==f'local[{workers}]';return s
def run(project,input_root,output,scratch):
    started=time.monotonic();output.mkdir(parents=True,exist_ok=True);cfg=json.loads((project/'configs/phase14_scalability.yaml').read_text());source_cfg=json.loads((project/'configs/ml_experiments.yaml').read_text());names=source_cfg['numerical_features'];manifest=json.loads((project/'manifests/parquet_layers.json').read_text());clean=json.loads((project/'configs/cleaning.yaml').read_text());runs=[];datasets=[];references={};spark=session(4,16,scratch)
    try:
        raw,source_receipt=verified_input(spark,locate_producer(input_root,manifest['independent_mount']['summary_sha256']),manifest,clean);assert source_receipt['rows']==16232943
        raw=raw.select('record_fingerprint','source_day','attack_family','binary_label',*names)
        for n in names:
            v=F.col(n);raw=raw.withColumn(n,F.when(v.isNotNull() & ~F.isnan(v) & (F.abs(v)!=float('inf')),v))
        prepare=time.monotonic()
        for requested,fraction in zip(cfg['volumes'],cfg['fractions']):
            frame=raw if fraction==1 else raw.where(F.pmod(F.xxhash64(F.lit(cfg['seed']),'record_fingerprint'),F.lit(1000000))<int(fraction*1000000));path=output/'populations'/str(requested);t=time.monotonic();frame.repartition(16).write.mode('overwrite').option('compression','snappy').parquet(str(path));saved=spark.read.parquet(str(path));counts=canonical(saved.groupBy('source_day','binary_label','attack_family').count().collect());rows=sum(r['count'] for r in counts);datasets.append(dict(requested_rows=requested,actual_rows=rows,fraction=fraction,source_receipt=source_receipt['receipt_sha256'],selection='nested seeded fingerprint hash threshold; original multiplicities retained',path=str(path.relative_to(output)),bytes=sum(p.stat().st_size for p in path.rglob('*.parquet')),files=len(list(path.rglob('*.parquet'))),composition=counts,preparation_seconds=time.monotonic()-t,partitions=16))
        atomic_json(output/'benchmark_populations.json',datasets);pipeline=PipelineModel.load('/kaggle/temp/phase14_archives/B-logistic_regression');prep=PipelineModel(stages=pipeline.stages[:-1]);atomic_json(output/'preparation.json',dict(seconds=time.monotonic()-prepare,source=source_receipt,resources=environment()))
        def execute(dataset,kind,workers,repeat,warmup=False):
            path=output/dataset['path'];t=time.monotonic();status='PASS';result=None;error=None
            with Monitor() as m:
                try:result=canonical(workload(spark.read.parquet(str(path)),kind,prep,names))
                except Exception as exc:status='FAILED';error=type(exc).__name__+': '+str(exc)[:2000]
            elapsed=time.monotonic()-t;key=(dataset['requested_rows'],kind)
            if status=='PASS':
                if key in references and not equivalent(result,references[key]):status='FAILED';error='Output differs from matched reference'
                else:references.setdefault(key,result)
            row=dict(matrix='volume' if workers==4 else 'workers',workload=kind,requested_rows=dataset['requested_rows'],actual_rows=dataset['actual_rows'],format='parquet',workers=workers,partitions=16,aqe=False,cache='none explicit; OS cache uncontrolled',repetition=repeat,warmup=warmup,status=status,error=error,seconds=elapsed,rows_per_second=dataset['actual_rows']/elapsed,input_bytes=dataset['bytes'],result=result,output_sha256=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest() if result else None,**m.summary());runs.append(row);atomic_json(output/'scalability_runs.json',runs);print('PHASE14D RUN',dataset['requested_rows'],kind,workers,repeat,status,round(elapsed,3),flush=True)
            if status!='PASS':raise ValueError(error)
        for dataset in datasets:
            for kind in cfg['core_workloads']:
                execute(dataset,kind,4,0,True)
                for rep in range(1,4):execute(dataset,kind,4,rep)
        spark.stop()
        for workers in (1,2):
            spark=session(workers,16,scratch/str(workers));pipeline=PipelineModel.load('/kaggle/temp/phase14_archives/B-logistic_regression');prep=PipelineModel(stages=pipeline.stages[:-1])
            for kind in ('analytics','feature_transform'):
                execute(datasets[0],kind,workers,0,True)
                for rep in range(1,4):execute(datasets[0],kind,workers,rep)
            spark.stop()
        atomic_json(output/'receipt.json',dict(status='validated',stage='14D',source=source_receipt,populations=len(datasets),measured_runs=sum(not r['warmup'] for r in runs),warmups=sum(r['warmup'] for r in runs),all_correct=all(r['status']=='PASS' for r in runs),resources=environment(),seconds=time.monotonic()-started,model_provenance='ArchivedPhase4B group-sample LR, hash-verified upload manifest; no refit',limits='Single node CPU; no filesystem cache eviction or multi-node claim'))
        print('PHASE14D SCALABILITY COMPLETE',len(runs),flush=True)
    finally:
        try:spark.stop()
        except Exception:pass
