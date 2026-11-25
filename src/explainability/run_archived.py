"""Explain pinned supervised pipelines on deterministic historical group samples."""
from hashlib import sha256
from time import monotonic
import json,math
from pathlib import Path
from pyspark import StorageLevel
from pyspark.ml import PipelineModel
from pyspark.ml.functions import vector_to_array
from pyspark.sql import functions as F,Window
from src.ingest.dataset_audit import atomic_json,spark_session
from src.ingest.parquet_pipeline import resource_limits,driver_peak_bytes
from src.ml.phase8_baselines import benchmark_population,json_file
from src.ml.feature_registry import predictor_input,registry
from src.ml.train_supervised import verified_input
from src.sql.traffic_analytics import locate_producer,require
from src.streaming.model_scoring import probe
from src.explainability.exact import linear,verify_linear,importance


def run(project,input_root,archives,inventory,output,scratch):
    start=monotonic();output.mkdir(parents=True,exist_ok=True);scratch.mkdir(parents=True,exist_ok=True)
    design=json_file(project,'configs/ml_experiments.yaml');upstream=json_file(project,'manifests/parquet_layers.json')
    original=json_file(project,'manifests/phase4_models.json');names=registry(design,upstream['feature_columns'])
    spark=spark_session(design,scratch);spark.conf.set('spark.sql.sources.partitionColumnTypeInference.enabled','false')
    results=[];private=[]
    try:
        require(spark.version=='4.3.0','Unexpected Spark runtime')
        data,receipt=verified_input(spark,locate_producer(input_root,upstream['independent_mount']['summary_sha256']),upstream,json_file(project,'configs/cleaning.yaml'))
        prepared=predictor_input(data,names,design['version']).persist(StorageLevel.DISK_ONLY)
        for protocol in ('A','B'):
            active,split=benchmark_population(prepared,protocol,design,receipt['days'],original,output)
            test=active.where('split_rank = 2')
            eligible=test.count()
            sample=(test.withColumn('multiplicity',F.count('*').over(Window.partitionBy('predictor_key')))
                    .dropDuplicates(['predictor_key']).orderBy(F.xxhash64(F.lit(23013),'predictor_key'),'record_fingerprint').limit(1000)).persist(StorageLevel.DISK_ONLY)
            require(sample.count()<=1000,'Explanation sample exceeds budget')
            for entry in [e for e in inventory if e['protocol']==protocol]:
                path=archives/entry['id'];hashes={p.relative_to(path).as_posix():sha256(p.read_bytes()).hexdigest() for p in path.rglob('*') if p.is_file()}
                require(hashes==entry['sha256'],'Archived model hashes differ')
                tick=monotonic();model=PipelineModel.load(str(path));reload_seconds=monotonic()-tick
                estimator=model.stages[-1];assembler=next(s for s in model.stages if type(s).__name__=='VectorAssembler')
                imputer=next(s for s in model.stages if type(s).__name__=='ImputerModel')
                feature_names=imputer.getInputCols()
                require(all(name in names for name in feature_names),'Unexpected estimator feature input')
                require(assembler.getInputCols()==imputer.getOutputCols(),'Preprocessing feature order differs')
                probes=probe(spark,names)
                before=model.transform(probes).select(vector_to_array('probability').alias('p')).collect()
                opened=PipelineModel.load(str(path));after=opened.transform(probes).select(vector_to_array('probability').alias('p')).collect()
                require(before==after,'Repeated reload probability probes differ')
                record=dict(model=entry['id'],protocol=protocol,algorithm=entry['algorithm'],eligible_test_rows=eligible,feature_order=feature_names,reload_seconds=reload_seconds,reload_probe_rows=len(before),source_version=entry['version'],preprocessing_stages=[type(s).__name__ for s in model.stages[:-1]])
                if hasattr(estimator,'featureImportances'):
                    record['native_importance']=importance(feature_names,list(estimator.featureImportances))
                if type(estimator).__name__=='LogisticRegressionModel':
                    coefficients=list(estimator.coefficients);intercept=estimator.intercept
                    background=(active.where('split_rank = 0').dropDuplicates(['predictor_key'])
                                .orderBy(F.xxhash64(F.lit(23013),'predictor_key')).limit(64))
                    reference_vectors=model.transform(background).select(vector_to_array(estimator.getFeaturesCol()).alias('x')).collect()
                    reference=[sum(r.x[i] for r in reference_vectors)/len(reference_vectors) for i in range(len(coefficients))]
                    tick=monotonic()
                    scored=model.transform(sample).select('source_day','attack_family','binary_label','multiplicity',vector_to_array(estimator.getFeaturesCol()).alias('x'),vector_to_array('probability').alias('p'),vector_to_array('rawPrediction').alias('raw')).collect()
                    strata={};max_logit=max_probability=0.;all_values=[]
                    for row in scored:
                        explanation=linear(coefficients,intercept,row.x);verify_linear(explanation,row.raw[1],row.p[1])
                        centered=linear(coefficients,intercept,row.x,reference);verify_linear(centered,row.raw[1],row.p[1])
                        max_logit=max(max_logit,abs(explanation['logit']-row.raw[1]));max_probability=max(max_probability,abs(explanation['probability']-row.p[1]))
                        predicted=row.p[1]>=design['threshold'];outcome='TP' if row.binary_label and predicted else 'FN' if row.binary_label else 'FP' if predicted else 'TN'
                        key=(row.source_day,row.attack_family,outcome)
                        stat=strata.setdefault(key,dict(rows=0,group_mass=0.,abs_contributions=[0.]*len(coefficients),signed_contributions=[0.]*len(coefficients)))
                        stat['rows']+=1;stat['group_mass']+=row.multiplicity
                        for i,value in enumerate(explanation['contributions']):stat['abs_contributions'][i]+=abs(value);stat['signed_contributions'][i]+=value
                        all_values.append(explanation['contributions'])
                        private.append(dict(model=entry['id'],day=row.source_day,family=row.attack_family,outcome=outcome,contributions=explanation['contributions'],logit=explanation['logit'],probability=row.p[1]))
                    for stat in strata.values():
                        stat['abs_contributions']=[v/stat['rows'] for v in stat['abs_contributions']];stat['signed_contributions']=[v/stat['rows'] for v in stat['signed_contributions']]
                    record.update(coefficients=coefficients,intercept=intercept,output_space='log-odds',method='exact raw and reference-centered linear contributions',background_policy='64 earlier training predictor groups',background_rows=len(reference_vectors),reference_mean=reference,explained_rows=len(scored),max_logit_residual=max_logit,max_probability_residual=max_probability,explanation_seconds=monotonic()-tick,strata=[dict(day=k[0],family=k[1],outcome=k[2],**v) for k,v in strata.items()],mean_absolute_contributions=[sum(abs(values[i]) for values in all_values)/len(all_values) for i in range(len(coefficients))])
                results.append(record);atomic_json(output/'explanations.json',results)
            sample.unpersist();active.unpersist()
        atomic_json(output/'private_local_explanations.json',private)
        atomic_json(output/'receipt.json',dict(status='validated',stage='13B',input=receipt,models=len(results),spark_version=spark.version,resources=resource_limits(spark,design,output),driver_peak_rss_bytes=driver_peak_bytes(spark),seconds=monotonic()-start,sha256={p.name:sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()}))
        print('PHASE13 archived supervised explanations complete',flush=True)
    finally:spark.stop()
