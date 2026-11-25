"""Independent archived Phase14 pipeline checks; never fit or retune models.

Also score the same frozen common-feature source models on their retained source
holdout, so a source/external gap is not confounded by switching feature sets.
"""
import json,hashlib,time
from pathlib import Path
from pyspark.sql import functions as F
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
    started=time.monotonic();output.mkdir(parents=True,exist_ok=True);cfg=json.loads((project/'configs/phase14_external_validation.yaml').read_text());design=json.loads((project/'configs/ml_experiments.yaml').read_text());manifest=json.loads((project/'manifests/parquet_layers.json').read_text());clean=json.loads((project/'configs/cleaning.yaml').read_text());spark=session(4,16,scratch);records=[];source_results=[]
    try:
        raw,source_receipt=verified_input(spark,locate_producer(input_root,manifest['independent_mount']['summary_sha256']),manifest,clean);common=cfg['common_features'];source=raw.select('source_day','binary_label','attack_family','original_label','record_fingerprint',*common)
        for n in common:
            v=F.col(n);source=source.withColumn(n,F.when(v.isNotNull() & ~F.isnan(v) & (F.abs(v)!=float('inf')) & (v>=0),v))
        source=source.withColumn('predictor_key',vector_key(common)).withColumn('split_rank',F.when(F.col('source_day').isin(design['protocols']['B']['train']),0).when(F.col('source_day').isin(design['protocols']['B']['validation']),1).otherwise(2));first=source.groupBy('predictor_key').agg(F.min('split_rank').alias('earliest'));source=source.join(first,'predictor_key').where('split_rank=earliest').persist(StorageLevel.DISK_ONLY)
        audit_paths=list(input_root.rglob('external_audit.json'));assert len(audit_paths)==1;target=spark.read.parquet(str(audit_paths[0].parent/'feature_ready')).where('eligible').persist(StorageLevel.DISK_ONLY)
        model_paths=list(input_root.rglob('models.json'));assert len(model_paths)==1,'Attach completed external validation model output';registry=json.loads(model_paths[0].read_text());assert len(registry)==12
        populations=json.loads((model_paths[0].parent/'populations.json').read_text());test=source.where('split_rank=2');assert test.count()==sum(r['count'] for r in populations if r['dataset']=='source' and r['split_rank']==2)
        probes=spark.createDataFrame([(None,None,None),(0.,0.,0.),(1000000.,10.,5.)],','.join(n+' DOUBLE' for n in common))
        for entry in registry:
            folder=model_paths[0].parent/entry['saved']['artifact'];hashes={p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*') if p.is_file() and not p.name.endswith('.crc')};assert hashes==entry['saved']['sha256']
            pipeline=PipelineModel.load(str(folder));first_scores=[list(r[0]) for r in pipeline.transform(probes).select(vector_to_array('probability')).collect()];again=PipelineModel.load(str(folder));second_scores=[list(r[0]) for r in again.transform(probes).select(vector_to_array('probability')).collect()];assert first_scores==second_scores
            if entry['domain']=='source':active=source;column='split_rank';fraction=cfg['source_train_fraction_permyriad']
            else:
                column='chronological_rank' if entry['protocol']=='chronological' else 'grouped_rank';active=target.where('chronological_retained') if entry['protocol']=='chronological' else target;fraction=cfg['target_train_fraction_permyriad']
            train=active.where(F.col(column)==0).where(F.pmod(F.xxhash64(F.lit(cfg['seed']),'predictor_key'),F.lit(10000))<fraction);validation=active.where(F.col(column)==1);training_counts=[r.asDict() for r in train.groupBy('source_day','binary_label').count().collect()];assert sum(x['count'] for x in training_counts)==entry['training_rows'];h,_=histogram(pipeline,validation);expected={int(k):v for k,v in entry['calibration_histogram'].items()};assert h==expected,'Independent calibration histogram differs'
            records.append(dict(model=entry['model'],original_components_verified=len(hashes),independent_runtime_reload=True,probe_scores=first_scores,calibration_histogram_identical=True,training_day_counts=training_counts,threshold_bin_unchanged=entry['threshold_bin'],model_source=entry['saved']['artifact']))
            atomic_json(output/'independent_reload.json',records)
            if entry['domain']=='source':
                h,groups=histogram(pipeline,test)
                for operating,index in [('validation_budget',entry['threshold_bin']),('fixed_half',1024)]:source_results.append(dict(model=entry['model'],domain='source',evaluation_protocol='B-common retained source holdout',operating=operating,threshold_bin=index,metrics=at_threshold(h,index,2048),score_histogram=h,groups=groups,interpretation='Same frozen E2 model and source-only calibration; retrospective source holdout,not an untouched new test'))
                atomic_json(output/'source_reference.json',source_results)
            print('PHASE14 MODEL INDEPENDENTLY VERIFIED',entry['model'],flush=True)
        atomic_json(output/'receipt.json',dict(status='validated',stage='14C-independent',fitting_performed=False,threshold_changes=False,models=len(records),source_references=len(source_results),source=source_receipt,resources=environment(spark),seconds=time.monotonic()-started));print('PHASE14 MODEL VERIFICATION COMPLETE',len(records),flush=True)
    finally:spark.stop()
