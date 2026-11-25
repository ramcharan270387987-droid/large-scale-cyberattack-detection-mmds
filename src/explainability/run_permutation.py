"""Matched bounded Spark permutation study with archived models and thresholds."""
from collections import defaultdict
from hashlib import sha256
from time import monotonic
from pyspark import StorageLevel
from pyspark.ml import PipelineModel
from pyspark.ml.functions import vector_to_array
from pyspark.sql import functions as F
from src.ingest.dataset_audit import atomic_json,spark_session
from src.ingest.parquet_pipeline import resource_limits,driver_peak_bytes
from src.ml.phase8_baselines import benchmark_population,json_file
from src.ml.feature_registry import predictor_input,registry
from src.ml.train_supervised import verified_input
from src.sql.traffic_analytics import locate_producer,require
from src.explainability.permutation import permute,evaluate

from src.explainability.sampling import sample_groups


def run(project,input_root,archives,inventory,output,scratch):
    start=monotonic();output.mkdir(parents=True,exist_ok=True);scratch.mkdir(parents=True,exist_ok=True)
    design=json_file(project,'configs/ml_experiments.yaml');upstream=json_file(project,'manifests/parquet_layers.json')
    original=json_file(project,'manifests/phase4_models.json');names=registry(design,upstream['feature_columns'])
    spark=spark_session(design,scratch);spark.conf.set('spark.sql.sources.partitionColumnTypeInference.enabled','false')
    results=[];sample_receipts=[];distributions=[];model_metadata=[]
    try:
        require(spark.version=='4.3.0','Unexpected Spark runtime')
        raw,receipt=verified_input(spark,locate_producer(input_root,upstream['independent_mount']['summary_sha256']),upstream,json_file(project,'configs/cleaning.yaml'))
        prepared=predictor_input(raw,names,design['version']).persist(StorageLevel.DISK_ONLY)
        groups=[('group_counts_sizes',[n for n in names if 'pkts' in n or 'pkt_len' in n]),('group_timing',[n for n in names if 'iat_' in n or n=='flow_duration'])]
        specifications=[(name,[name]) for name in names]+groups
        for protocol in ('A','B'):
            active,split=benchmark_population(prepared,protocol,design,receipt['days'],original,output)
            reference_bounds=None
            for rank,role in ((0,'training_reference'),(2,'evaluation')):
                population=active.where(F.col('split_rank')==rank)
                quantiles=population.approxQuantile(names,[0.,.1,.5,.9,1.],.001)
                support=population.agg(F.count('*').alias('rows'),*[F.count(F.when(F.col(name).isNull(),1)).alias(name) for name in names]).first()
                if rank==0:reference_bounds={name:(values[0],values[-1]) for name,values in zip(names,quantiles)}
                outside=population.agg(*[F.count(F.when((F.col(name)<reference_bounds[name][0])|(F.col(name)>reference_bounds[name][1]),1)).alias(name) for name in names]).first()
                distributions.extend(dict(protocol=protocol,role=role,feature=name,rows=support['rows'],missing=support[name],quantiles=values,outside_training_range=outside[name],training_range=list(reference_bounds[name])) for name,values in zip(names,quantiles))
            atomic_json(output/'feature_distributions.json',distributions)
            selected=sample_groups(active.where('split_rank = 2'),23013,1000).select('source_day','binary_label',*names)
            rows=[r.asDict() for r in selected.collect()]
            require(len(rows)==1000,'Unexpected matched explanation sample size')
            sample_receipts.append(dict(protocol=protocol,rows=len(rows),by_day=[dict(day=day,rows=sum(r['source_day']==day for r in rows)) for day in sorted({r['source_day'] for r in rows})],split=split))
            all_rows=[];conditions={}
            def add(identifier,source,metadata):
                conditions[identifier]=metadata
                for row in source:all_rows.append((identifier,row['source_day'],int(row['binary_label']),*[row[name] for name in names]))
            add('baseline',rows,dict(features=[],seed=None,scope='matched_original'))
            for label,features in specifications:
                for seed in (23013,23014,23015):
                    for within_capture in (False,True):
                        scope='within_capture' if within_capture else 'global'
                        identifier=f'{label}-{seed}-{scope}'
                        add(identifier,permute(rows,features,seed,within_capture),dict(features=features,seed=seed,scope=scope))
            schema='condition STRING, source_day STRING, binary_label INT, '+', '.join(name+' DOUBLE' for name in names)
            frame=spark.createDataFrame(all_rows,schema).persist(StorageLevel.DISK_ONLY)
            require(frame.count()==1000*len(conditions),'Permutation population differs')
            for entry in [e for e in inventory if e['protocol']==protocol]:
                path=archives/entry['id'];hashes={p.relative_to(path).as_posix():sha256(p.read_bytes()).hexdigest() for p in path.rglob('*') if p.is_file()}
                require(hashes==entry['sha256'],'Archived model hashes differ')
                model=PipelineModel.load(str(path));tick=monotonic()
                imputer=next(stage for stage in model.stages if type(stage).__name__=='ImputerModel')
                metadata=dict(model=entry['id'],feature_order=imputer.getInputCols(),training_imputation=imputer.surrogateDF.first().asDict(),feature_column=model.stages[-1].getFeaturesCol(),stage_types=[type(stage).__name__ for stage in model.stages])
                scalers=[stage for stage in model.stages if type(stage).__name__=='StandardScalerModel']
                if scalers:metadata.update(training_std=list(scalers[0].std),with_mean=scalers[0].getWithMean(),with_std=scalers[0].getWithStd())
                model_metadata.append(metadata)
                atomic_json(output/'model_metadata.json',model_metadata)
                scored=model.transform(frame).select('condition','binary_label',F.least(F.floor(vector_to_array('probability')[1]*2048).cast('int'),F.lit(2047)).alias('bin'))
                aggregate=scored.groupBy('condition','binary_label','bin').count().collect()
                histograms=defaultdict(lambda:defaultdict(lambda:[0,0]))
                for row in aggregate:histograms[row.condition][row.bin][row.binary_label]+=row['count']
                original_metrics=evaluate(histograms['baseline'])
                for identifier in conditions:
                    metrics=evaluate(histograms[identifier]);require(metrics['rows']==1000,'Permutation matched rows differ')
                    deltas={key:(original_metrics[key]-metrics[key] if original_metrics[key] is not None and metrics[key] is not None else None) for key in ('pr_auc','roc_auc','recall','precision','f1','fpr')}
                    results.append(dict(model=entry['id'],condition=identifier,protocol=protocol,**conditions[identifier],metrics=metrics,original_minus_permuted=deltas))
                atomic_json(output/'permutation.json',results)
                print('PHASE13 permutation model complete',entry['id'],round(monotonic()-tick,3),flush=True)
            frame.unpersist();active.unpersist()
        atomic_json(output/'receipt.json',dict(status='validated',stage='13C-permutation',input=receipt,samples=sample_receipts,conditions_per_model=len(conditions),rows_per_condition=1000,models=len(inventory),threshold=.5,auc_definition='2048 whole-score bins; step PR and trapezoidal ROC',resources=resource_limits(spark,design,output),driver_peak_rss_bytes=driver_peak_bytes(spark),seconds=monotonic()-start,sha256={p.name:sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()}))
        print('PHASE13 permutation complete',flush=True)
    finally:spark.stop()
