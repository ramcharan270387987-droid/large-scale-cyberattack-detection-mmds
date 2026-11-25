"""Matched storage/partition/cache/Pandas and bounded archived-model/mining costs."""
import json,time,hashlib,statistics
from pathlib import Path
from pyspark import StorageLevel
from pyspark.sql import functions as F
from pyspark.ml import PipelineModel
from pyspark.ml.functions import vector_to_array
from pyspark.ml.fpm import FPGrowth
from src.ingest.dataset_audit import atomic_json
from src.scalability.benchmark_runner import session,canonical,equivalent,checksum
from src.scalability.resource_monitor import Monitor,environment
from src.patterns.discretization import transform

def run(project,input_root,output,scratch):
    started=time.monotonic();output.mkdir(parents=True,exist_ok=True);cfg=json.loads((project/'configs/phase14_scalability.yaml').read_text());names=json.loads((project/'configs/ml_experiments.yaml').read_text())['numerical_features'];producers=list(input_root.rglob('benchmark_populations.json'));assert len(producers)==1,'Attach accepted14D output';producer=producers[0];datasets=json.loads(producer.read_text());dataset=datasets[0];path=producer.parent/dataset['path'];spark=session(4,16,scratch);runs=[];formats=[];references={}
    try:
        frame=spark.read.parquet(str(path))
        if dict(frame.dtypes).get('record_fingerprint')=='binary':frame=frame.withColumn('record_fingerprint',F.hex('record_fingerprint'))
        schema=frame.schema;actual=frame.count();assert actual==dataset['actual_rows'];bounds=json.loads((project/'reports/phase10_stageB/registry.json').read_text());output.joinpath('event_logs').mkdir(exist_ok=True)
        def timed(matrix,configuration,rep,fn,rows=actual,reference=None):
            t=time.monotonic();error=None;result=None;status='PASS'
            with Monitor() as mon:
                try:
                    value=fn();result=canonical(value) if isinstance(value,list) else value
                    if reference is not None and not equivalent(result,reference):raise ValueError('Output mismatch against matched configuration')
                except Exception as exc:status='FAILED';error=type(exc).__name__+': '+str(exc)[:2000]
            elapsed=time.monotonic()-t;r=dict(matrix=matrix,configuration=configuration,repetition=rep,actual_rows=rows,seconds=elapsed,rows_per_second=rows/elapsed if rows else None,workers=4,cache_os='uncontrolled',status=status,error=error,result=result,**mon.summary());runs.append(r);atomic_json(output/'optimization_runs.json',runs);print('PHASE14E RUN',matrix,configuration,rep,status,round(elapsed,3),flush=True)
            if status!='PASS':raise ValueError(error)
            return result
        t=time.monotonic();parquetpath=output/'matched_parquet';frame.write.mode('overwrite').option('compression','snappy').parquet(str(parquetpath));parquet_conversion=time.monotonic()-t
        t=time.monotonic();csvpath=output/'matched_csv';frame.write.mode('overwrite').option('header','true').csv(str(csvpath));conversion=time.monotonic()-t
        readers={'parquet':lambda:spark.read.schema(schema).parquet(str(parquetpath)),'csv':lambda:spark.read.schema(schema).option('header','true').csv(str(csvpath))}
        full_reference=canonical(checksum(frame,names));query=lambda f:f.where('flow_duration>1000').groupBy('binary_label').agg(F.count('*').alias('rows'),F.sum('tot_fwd_pkts').alias('packets')).collect();query_reference=canonical(query(frame))
        for fmt,reader in readers.items():
            base=parquetpath if fmt=='parquet' else csvpath;formats.append(dict(format=fmt,actual_rows=actual,bytes=sum(p.stat().st_size for p in base.rglob('*') if p.is_file() and not p.name.startswith('.')),files=len([p for p in base.rglob('*') if p.is_file() and not p.name.startswith('.')]),compression='snappy' if fmt=='parquet' else 'none',conversion_seconds=conversion if fmt=='csv' else parquet_conversion,metadata_encoding='record_fingerprint losslesshex in both formats; identical numerical/label rows',schema=schema.jsonValue()))
            for rep in range(1,4):
                timed('storage_full_read',fmt,rep,lambda:checksum(reader(),names),reference=full_reference)
                timed('storage_projection_filter_query',fmt,rep,lambda:query(reader()),reference=query_reference)
        atomic_json(output/'storage_files.json',formats)
        for partitions in cfg['partition_grid']:
            for rep in range(1,4):
                data=frame.repartition(partitions).persist(StorageLevel.DISK_ONLY)
                timed('partition_materialization',str(partitions),rep,lambda:checksum(data,names),reference=full_reference)
                timed('partition_query_after_materialization',str(partitions),rep,lambda:query(data),reference=query_reference);data.unpersist(blocking=True)
        # Capture pruning and SQL/DataFrame compare identical day and outputs.
        partitioned=output/'capture_partitioned';t=time.monotonic();frame.write.mode('overwrite').partitionBy('source_day').parquet(str(partitioned));atomic_json(output/'capture_layout.json',dict(seconds=time.monotonic()-t,policy='capture-day partitioning',output_files=len(list(partitioned.rglob('*.parquet')))))
        firstday=frame.agg(F.min('source_day')).first()[0];prune=lambda f:f.where(F.col('source_day')==firstday).groupBy('binary_label').count().collect();prune_ref=canonical(prune(frame))
        frame.createOrReplaceTempView('phase14_matched');sql='SELECT binary_label,COUNT(*) AS rows,SUM(tot_fwd_pkts) AS packets FROM phase14_matched WHERE flow_duration>1000 GROUP BY binary_label';atomic_json(output/'sql_plan.json',dict(sql=spark.sql(sql)._jdf.queryExecution().optimizedPlan().toString(),dataframe=frame.where('flow_duration>1000').groupBy('binary_label').agg(F.count('*').alias('rows'),F.sum('tot_fwd_pkts').alias('packets'))._jdf.queryExecution().optimizedPlan().toString()))
        for rep in range(1,4):
            timed('capture_pruning','day='+firstday,rep,lambda:prune(spark.read.parquet(str(partitioned))),reference=prune_ref)
            timed('coalesce_materialized','4',rep,lambda:checksum(frame.coalesce(4),names),reference=full_reference)
            timed('SQL_dataframe','SQL',rep,lambda:spark.sql(sql).collect(),reference=query_reference)
            timed('SQL_dataframe','DataFrame',rep,lambda:query(frame),reference=query_reference)
            timed('cache','none',rep,lambda:query(frame),reference=query_reference)
        cached=frame.persist(StorageLevel.MEMORY_AND_DISK)
        timed('cache','first_materialization_MEMORY_AND_DISK',1,lambda:checksum(cached,names),reference=full_reference)
        for rep in range(1,4):timed('cache','warm_materialized',rep,lambda:query(cached),reference=query_reference)
        cached.unpersist(blocking=True)
        # Matched bounded projected CSV files; no full-source toPandas call.
        import pandas as pd
        columns=cfg['pandas_columns'];pandas_records=[]
        for size in cfg['pandas_rows']:
            t=time.monotonic();selected=frame.orderBy(F.xxhash64(F.lit(cfg['seed']),'record_fingerprint'),'record_fingerprint').limit(size).select(*columns);file=output/('pandas_'+str(size));selected.coalesce(1).write.mode('overwrite').option('header','true').csv(str(file));csvfile=next(file.glob('part-*.csv'));rowcount=selected.count();assert rowcount<=1000000
            pandas_records.append(dict(requested=size,actual_rows=rowcount,preparation_seconds=time.monotonic()-t,bytes=csvfile.stat().st_size));dschema=selected.schema
            def pandas_query():
                df=pd.read_csv(csvfile,dtype={c:'float64' for c in columns});f=df.loc[df.flow_duration>1000];a=f.groupby('binary_label',dropna=False).agg(rows=('binary_label','size'),packets=('tot_fwd_pkts','sum')).reset_index();return [dict(binary_label=int(x.binary_label),rows=int(x.rows),packets=float(x.packets)) for x in a.itertuples()]
            def spark_query():return spark.read.schema(dschema).option('header','true').csv(str(csvfile)).where('flow_duration>1000').groupBy('binary_label').agg(F.count('*').alias('rows'),F.sum('tot_fwd_pkts').alias('packets')).collect()
            ref=canonical(spark_query())
            for rep in range(1,4):
                timed('Spark_Pandas_end_to_end','pandas-'+str(size),rep,pandas_query,rows=rowcount,reference=ref)
                timed('Spark_Pandas_end_to_end','spark-'+str(size),rep,spark_query,rows=rowcount,reference=ref)
            pdf=pd.read_csv(csvfile,dtype={c:'float64' for c in columns});sf=spark.read.schema(dschema).option('header','true').csv(str(csvfile)).persist(StorageLevel.MEMORY_AND_DISK);sf.count()
            def pandas_compute():
                f=pdf.loc[pdf.flow_duration>1000];a=f.groupby('binary_label',dropna=False).agg(rows=('binary_label','size'),packets=('tot_fwd_pkts','sum')).reset_index();return [dict(binary_label=int(x.binary_label),rows=int(x.rows),packets=float(x.packets)) for x in a.itertuples()]
            for rep in range(1,4):
                timed('Spark_Pandas_compute','pandas-'+str(size),rep,pandas_compute,rows=rowcount,reference=ref)
                timed('Spark_Pandas_compute','spark-'+str(size),rep,lambda:query(sf),rows=rowcount,reference=ref)
            sf.unpersist(blocking=True);del pdf
        atomic_json(output/'pandas_inputs.json',pandas_records)
        for family in ('logistic_regression','random_forest'):
            t=time.monotonic();pipeline=PipelineModel.load('/kaggle/temp/phase14_archives/B-'+family);atomic_json(output/('model_reload_'+family+'.json'),dict(seconds=time.monotonic()-t,source='archivedPhase4Bgroup_sample',family=family))
            def inference():
                scored=pipeline.transform(frame);return scored.select('binary_label',vector_to_array('probability')[1].alias('score')).agg(F.count('*').alias('rows'),F.sum('binary_label').alias('attacks'),F.sum('score').alias('score_sum'),F.sum((F.col('score')>=.5).cast('long')).alias('predicted_positive')).collect()
            ref=None
            for rep in range(1,4):
                value=timed('archived_inference',family,rep,inference,reference=ref)
                if ref is None:ref=value
        transactions=transform(frame.orderBy(F.xxhash64(F.lit(cfg['seed']),'record_fingerprint')).limit(100000),bounds).select('items').persist(StorageLevel.DISK_ONLY);transaction_count=transactions.count();assert transaction_count<=100000
        def mining():
            model=FPGrowth(itemsCol='items',minSupport=.05,minConfidence=.7,numPartitions=16).fit(transactions);counts=canonical(model.freqItemsets.groupBy(F.size('items').alias('length')).count().collect());rules=model.associationRules.count();model.write().save(str(output/'fpgrowth_model'));return dict(itemset_counts=counts,rules=rules,transactions=transaction_count)
        timed('pattern_mining','Phase10A3-frozen6-support.05-one_budgeted_fit',1,mining,rows=transaction_count);transactions.unpersist(blocking=True)
        atomic_json(output/'receipt.json',dict(status='validated',stage='14E',input_population=dataset,resources=environment(spark),spark_version=spark.version,measured_runs=len(runs),seconds=time.monotonic()-started,unsupported={'shuffle_bytes':'No enabled event-log parser; not measured','spill_bytes':'No enabled event-log parser; not measured','task_imbalance':'No task metrics retrieved','cache_eviction':'Not observed independently','RDD':'Optional not run','mining_repetitions':'One fit;boundedsecondary budget,not stable scalability evidence'},replay='Reused Phase6 verified49microbatches,15,322,987flows;not newly timed'))
        print('PHASE14E OPTIMIZATION COMPLETE',len(runs),flush=True)
    finally:spark.stop()
