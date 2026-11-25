"""Audit actual external CSVs on Kaggle; publish aggregates, keep rows private."""
import csv,json,hashlib,time
from pathlib import Path
from functools import reduce
from pyspark.sql import functions as F,types as T
from pyspark import StorageLevel
from src.external_validation.contracts import capture,verified_receipt
from src.ingest.dataset_audit import spark_session,atomic_json
from src.scalability.resource_monitor import Monitor,environment

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def vector_key(names):return F.sha2(F.to_json(F.struct(*[F.col(n).alias(n) for n in names]),{'ignoreNullFields':'false'}),256)
def run(project,input_root,output,scratch):
    start=time.monotonic();output.mkdir(parents=True,exist_ok=True);cfg=json.loads((project/'configs/phase14_external_validation.yaml').read_text());files=sorted(p for p in input_root.rglob('*.csv') if 'WorkingHours' in p.name or 'workingHours' in p.name);assert len(files)==8,[(p.name) for p in files]
    spark=spark_session({'spark':{'master':'local[4]','driver_memory':'8g','shuffle_partitions':16,'input_partition_bytes':67108864}},scratch);spark.conf.set('spark.sql.ansi.enabled','false');results=[];frames=[]
    with Monitor() as monitor:
      try:
        for path in files:
            with path.open(encoding='utf-8-sig',errors='replace',newline='') as f:header=next(csv.reader(f))
            norm=[x.strip() for x in header];assert 'Label' in norm
            cols=['c'+str(i) for i in range(len(header))];schema=T.StructType([T.StructField(n,T.StringType()) for n in cols]);raw=spark.read.text(str(path));line=F.col('value');parts=F.from_csv(line,schema.simpleString(),{'mode':'PERMISSIVE'});raw=raw.select(line.alias('_raw'),parts.alias('parsed'),F.size(F.split(line,',',-1)).alias('_fields')).select('_raw','_fields','parsed.*')
            blank=F.length(F.trim('_raw'))==0;repeated=F.trim(F.col('c0'))==norm[0];malformed=(F.col('_fields')!=len(header));counts=raw.agg(F.count('*').alias('lines'),F.sum(blank.cast('long')).alias('blank'),F.sum(repeated.cast('long')).alias('headers'),F.sum((malformed & ~blank).cast('long')).alias('malformed')).first().asDict()
            typed=raw.withColumn('source_day',F.lit(capture(path.name))).withColumn('source_file',F.lit(path.name)).withColumn('record_fingerprint',F.sha2('_raw',256)).withColumn('_parse_ok',~blank & ~repeated & ~malformed)
            label=F.trim(F.col(cols[norm.index('Label')]));typed=typed.withColumn('original_label',label).withColumn('binary_label',F.when(F.length(label)>0,F.when(F.upper(label)=='BENIGN',0).otherwise(1)))
            mapped=[];audits=[]
            for name,external in cfg['external_columns'].items():
                assert external in norm,(name,external);c=cols[norm.index(external)];v=F.expr('try_cast(`'+c+'` as double)');finite=v.isNotNull() & ~F.isnan(v) & (F.abs(v)!=float('inf')) & (v>=0)
                mapped.append(F.when(finite,v).alias(name));audits.extend([F.sum(F.when(F.trim(c)=='',1).otherwise(0)).alias(name+'_blank'),F.sum(F.isnan(v).cast('long')).alias(name+'_nan'),F.sum((F.abs(v)==float('inf')).cast('long')).alias(name+'_infinite'),F.sum((v<0).cast('long')).alias(name+'_negative')])
            stats=typed.where('_parse_ok').agg(*audits).first().asDict();results.append(dict(file=path.name,bytes=path.stat().st_size,sha256=digest(path),capture_day=capture(path.name),header=norm,duplicate_header_names=sorted({x for x in norm if norm.count(x)>1}),**counts,feature_quality=stats))
            # Raw typed strings retain all columns, original labels and parse flags privately.
            typed.drop('_raw').write.mode('overwrite').parquet(str(output/'raw_typed'/path.stem))
            frames.append(typed.select('source_day','source_file','record_fingerprint','_parse_ok','original_label','binary_label',*mapped))
        frame=reduce(lambda a,b:a.unionByName(b),frames).withColumn('attack_family',F.col('original_label')).withColumn('eligible',F.col('_parse_ok') & F.col('binary_label').isNotNull() & reduce(lambda a,b:a|b,[F.col(n).isNotNull() for n in cfg['common_features']])).drop('_parse_ok')
        frame=frame.withColumn('predictor_key',vector_key(cfg['common_features'])).withColumn('canonical_key',vector_key(cfg['source_features'])).withColumn('chronological_rank',F.when(F.col('source_day')<'2017-07-06',0).when(F.col('source_day')=='2017-07-06',1).otherwise(2)).withColumn('grouped_rank',F.when(F.pmod(F.xxhash64(F.lit(cfg['seed']),'predictor_key'),F.lit(10000))<7000,0).when(F.pmod(F.xxhash64(F.lit(cfg['seed']),'predictor_key'),F.lit(10000))<8500,1).otherwise(2))
        frame.write.mode('overwrite').partitionBy('source_day').parquet(str(output/'canonical'));frame=spark.read.parquet(str(output/'canonical')).persist(StorageLevel.DISK_ONLY);eligible=frame.where('eligible');first=eligible.groupBy('predictor_key').agg(F.min('chronological_rank').alias('earliest_rank'));frame=frame.join(first,'predictor_key','left').withColumn('chronological_retained',F.col('chronological_rank')==F.col('earliest_rank'));frame.write.mode('overwrite').partitionBy('source_day').parquet(str(output/'feature_ready'))
        compact=lambda df:[r.asDict(recursive=True) for r in df.collect()]
        labels=compact(frame.groupBy('source_day','original_label','binary_label','eligible','chronological_rank','chronological_retained','grouped_rank').count());total=sum(x['count'] for x in labels);good=sum(x['count'] for x in labels if x['eligible']);full_groups=eligible.groupBy('canonical_key').agg(F.count('*').alias('rows'),F.countDistinct('binary_label').alias('classes'));common_groups=eligible.groupBy('predictor_key').agg(F.count('*').alias('rows'),F.countDistinct('binary_label').alias('classes'))
        dup={}
        for name,g in [('canonical',full_groups),('predictor',common_groups)]:dup[name]=g.agg(F.count('*').alias('groups'),F.sum((F.col('rows')-1)).alias('duplicate_excess_rows'),F.sum((F.col('classes')>1).cast('long')).alias('conflicting_label_groups')).first().asDict()
        exact=eligible.groupBy('record_fingerprint').count().agg(F.sum(F.col('count')-1).alias('duplicate_excess_rows')).first().asDict();quantiles=eligible.approxQuantile(cfg['source_features'],[0.,.25,.5,.75,1.],.001)
        receipt=dict(status='validated',dataset=cfg['dataset'],dataset_version=1,files=results,source_bytes=sum(x['bytes'] for x in results),physical_lines_including_headers=total,repeated_header_rows=sum(x['headers'] for x in results),physical_data_rows=total-sum(x['headers'] for x in results),eligible_rows=good,excluded_rows=total-sum(x['headers'] for x in results)-good,label_and_split_counts=labels,duplicates=dup,exact=exact,feature_quantiles=dict(zip(cfg['source_features'],quantiles)),timestamp_audit='unsupported: MachineLearningCSV has no event timestamp; capture-day filename only',schema='phase14-external-v1',resources=environment(),spark_version=spark.version,master=spark.sparkContext.master,seconds=time.monotonic()-start)
        verified_receipt(receipt);atomic_json(output/'external_audit.json',receipt);print('PHASE14B EXTERNAL AUDIT COMPLETE',total,good,flush=True)
      finally:spark.stop()
    receipt['memory']=monitor.summary();atomic_json(output/'external_audit.json',receipt)
