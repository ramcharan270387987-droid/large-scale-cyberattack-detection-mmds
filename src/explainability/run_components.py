"""Explain actual novelty, hybrid, family-rejection and adaptive pipeline components."""
from hashlib import sha256
from time import monotonic
from collections import defaultdict
import math
from pyspark import StorageLevel
from pyspark.ml import PipelineModel
from pyspark.ml.functions import vector_to_array
from pyspark.sql import functions as F
from src.ingest.dataset_audit import atomic_json,spark_session
from src.ingest.parquet_pipeline import resource_limits,driver_peak_bytes
from src.ml.phase8_baselines import benchmark_population,json_file
from src.ml.feature_registry import predictor_input,registry
from src.ml.train_supervised import verified_input
from src.ml.novelty_scoring import squared_distance
from src.ml.hybrid_detection import encode_columns,fusion_columns
from src.sql.traffic_analytics import locate_producer,require
from src.streaming.model_scoring import probe
from src.explainability.exact import linear,verify_linear,distance,importance
from src.explainability.components import reject,fusion


def run(project,input_root,archives,inventory,output,scratch):
    start=monotonic();output.mkdir(parents=True,exist_ok=True);scratch.mkdir(parents=True,exist_ok=True)
    design=json_file(project,'configs/ml_experiments.yaml');upstream=json_file(project,'manifests/parquet_layers.json')
    original=json_file(project,'manifests/phase4_models.json');names=registry(design,upstream['feature_columns'])
    spark=spark_session(design,scratch);spark.conf.set('spark.sql.sources.partitionColumnTypeInference.enabled','false')
    results=[];models={};probes=probe(spark,names)
    try:
        require(spark.version=='4.3.0','Unexpected Spark runtime')
        for entry in inventory:
            path=archives/entry['id'];actual={p.relative_to(path).as_posix():sha256(p.read_bytes()).hexdigest() for p in path.rglob('*') if p.is_file()}
            require(actual==entry['sha256'],'Archived component hashes differ')
            models[entry['id']]=PipelineModel.load(str(path))
        raw,receipt=verified_input(spark,locate_producer(input_root,upstream['independent_mount']['summary_sha256']),upstream,json_file(project,'configs/cleaning.yaml'))
        prepared=predictor_input(raw,names,design['version']).persist(StorageLevel.DISK_ONLY)
        populations={};samples={}
        for protocol in ('A','B','C'):
            active,split=benchmark_population(prepared,protocol,design,receipt['days'],original,output)
            populations[protocol]=active
            samples[protocol]=(active.where('split_rank = 2').dropDuplicates(['predictor_key'])
                .orderBy(F.xxhash64(F.lit(23013),'predictor_key'),'record_fingerprint').limit(1000)).persist(StorageLevel.DISK_ONLY)
            samples[protocol].count()
        for entry in inventory:
            model=models[entry['id']];kind=entry['kind'];meta=entry['metadata'];protocol=entry['protocol'];tick=monotonic()
            record=dict(model=entry['id'],kind=kind,protocol=protocol,source_version=entry['version'])
            if kind=='novelty':
                centers=model.stages[-1].clusterCenters();preprocessing=PipelineModel(stages=model.stages[:-1]);cluster=model.stages[-1]
                imputer=next(s for s in model.stages if type(s).__name__=='ImputerModel')
                record['feature_order']=[name.removesuffix('_valid') for name in imputer.getInputCols()]
                require(len(record['feature_order'])==len(centers[0]) and all(name in names for name in record['feature_order']),'Novelty feature order differs')
                for scope,data in (('synthetic_probes',probes),('historical_sample',samples[protocol])):
                    frame=squared_distance(cluster,preprocessing.transform(data))
                    columns=['cluster',vector_to_array(cluster.getFeaturesCol()).alias('x'),'score']
                    if scope=='historical_sample':columns+=['source_day','attack_family','binary_label']
                    scored=frame.select(*columns).collect();strata={};residual=0.;synthetic=[]
                    for row in scored:
                        explained=distance(row.x,centers[row.cluster]);residual=max(residual,abs(explained['squared_distance']-row.score))
                        require(math.isclose(explained['squared_distance'],row.score,rel_tol=1e-8,abs_tol=1e-8),'Centroid distance reconstruction differs')
                        if scope=='synthetic_probes':synthetic.append(dict(cluster=row.cluster,**explained))
                        else:
                            key=(row.source_day,row.attack_family,row.binary_label,row.score>meta['threshold'])
                            stat=strata.setdefault(key,dict(rows=0,distance_sum=0.,contributions=[0.]*len(row.x)))
                            stat['rows']+=1;stat['distance_sum']+=row.score
                            for i,value in enumerate(explained['contributions']):stat['contributions'][i]+=value
                    record[scope]=dict(rows=len(scored),max_absolute_residual=residual,synthetic=synthetic,strata=[dict(day=k[0],family=k[1],binary_label=k[2],novel=k[3],**v) for k,v in strata.items()])
                record['novelty_threshold']=meta['threshold']
            elif kind=='hybrid':
                novelty=models['novelty-'+protocol];km=(PipelineModel(stages=novelty.stages[:-1]),novelty.stages[-1],0.)
                config=json_file(project,'configs/phase8_hybrid_experiments.yaml');winner=meta['selected_hybrid'];base=meta['base']
                scored=fusion_columns(encode_columns(samples[protocol],{base:model},km,meta['reference_grid'],base,meta['calibration'],meta['bins']),config,meta['gates'],meta['learned'])
                rows=scored.select('source_day','attack_family','binary_label','supervised','novelty',winner).collect();counts=defaultdict(int);maximum=0.
                for row in rows:
                    alpha=float(winner.removeprefix('blend_').replace('_','.')) if winner.startswith('blend_') else None
                    expected=fusion(row.supervised,row.novelty,winner,meta['gates'],alpha)
                    maximum=max(maximum,abs(expected-row[winner]));require(math.isclose(expected,row[winner],abs_tol=1e-8),'Hybrid score reconstruction differs')
                    first=row.supervised>=meta['gates']['supervised'];second=row.novelty>=meta['gates']['novelty']
                    decision=min(int(row[winner]*meta['bins']),meta['bins']-1)>=meta['operating_bins'][winner]
                    counts[row.source_day,row.attack_family,row.binary_label,first,second,decision]+=1
                record.update(rows=len(rows),policy=winner,gates=meta['gates'],operating_bin=meta['operating_bins'][winner],max_score_residual=maximum,decision_paths=[dict(day=k[0],family=k[1],binary_label=k[2],supervised_positive=k[3],novelty_positive=k[4],hybrid_positive=k[5],rows=v) for k,v in counts.items()])
            elif kind=='family':
                scored=model.transform(samples[protocol]).select('source_day','attack_family','binary_label',vector_to_array('probability').alias('scores')).collect();counts=defaultdict(int);confidence=defaultdict(lambda:[0.,0.])
                for row in scored:
                    cutoff=meta['threshold_bin']
                    explanation=reject(row.scores,meta['classes'],cutoff if cutoff is not None else 2048)
                    key=(row.source_day,row.attack_family,row.binary_label,explanation['predicted_family'],explanation['rejected'])
                    counts[key]+=1;confidence[key][0]+=explanation['maximum_score'];confidence[key][1]+=explanation['margin'] or 0.
                record.update(rows=len(scored),classes=meta['classes'],cutoff_bin=meta['threshold_bin'],rejection_policy_supported=meta['threshold_bin'] is not None,outcomes=[dict(day=k[0],true_family=k[1],binary_label=k[2],predicted_family=k[3],rejected=k[4],rows=v,mean_maximum_score=confidence[k][0]/v,mean_top_two_margin=confidence[k][1]/v) for k,v in counts.items()],interpretation='Conditional family-stage evidence; binary-gate misses remain separate. A has no archived rejection cutoff in its committed receipt.')
            elif kind=='adaptive':
                estimator=model.stages[-1];imputer=next(s for s in model.stages if type(s).__name__=='ImputerModel');feature_names=imputer.getInputCols()
                record.update(selected_policies=meta['selected_policies'],frozen_initial=meta['frozen_initial'],feature_order=feature_names,training_days=meta['training_days'])
                if hasattr(estimator,'coefficients'):
                    coefficients=list(estimator.coefficients);intercept=estimator.intercept
                    scaler=next(s for s in model.stages if type(s).__name__=='StandardScalerModel');std=list(scaler.std)
                    scored=model.transform(probes).select(vector_to_array(estimator.getFeaturesCol()).alias('x'),vector_to_array('rawPrediction').alias('raw'),vector_to_array('probability').alias('p')).collect();explanations=[]
                    for row in scored:
                        explanation=linear(coefficients,intercept,row.x);verify_linear(explanation,row.raw[1],row.p[1]);explanations.append(explanation)
                    record.update(coefficients=coefficients,intercept=intercept,training_std=std,raw_unit_coefficients=[c/s if s else None for c,s in zip(coefficients,std)],synthetic_explanations=explanations)
                elif hasattr(estimator,'featureImportances'):record['native_importance']=importance(feature_names,list(estimator.featureImportances))
            record['seconds']=monotonic()-tick;results.append(record);atomic_json(output/'components.json',results)
        stability=[]
        for protocol in ('A','B'):
            pipeline=PipelineModel.load(str(archives/(protocol+'-logistic_regression')))
            estimator=pipeline.stages[-1];coefficients=list(estimator.coefficients);intercept=estimator.intercept
            imputer=next(s for s in pipeline.stages if type(s).__name__=='ImputerModel');feature_order=imputer.getInputCols()
            scaler=next(s for s in pipeline.stages if type(s).__name__=='StandardScalerModel');std=list(scaler.std)
            background_vectors={}
            for seed in (23013,23014):
                background=populations[protocol].where('split_rank = 0').dropDuplicates(['predictor_key']).orderBy(F.xxhash64(F.lit(seed),'predictor_key')).limit(64)
                background_vectors[seed]=[r.x for r in pipeline.transform(background).select(vector_to_array(estimator.getFeaturesCol()).alias('x')).collect()]
            for sample_seed in (23013,23014):
                selected=populations[protocol].where('split_rank = 2').dropDuplicates(['predictor_key']).orderBy(F.xxhash64(F.lit(sample_seed),'predictor_key')).limit(1000)
                values=pipeline.transform(selected).select(vector_to_array(estimator.getFeaturesCol()).alias('x'),vector_to_array('rawPrediction').alias('raw'),vector_to_array('probability').alias('p')).collect()
                for sample_size in (100,500,1000):
                    sample=values[:sample_size]
                    for background_seed in (23013,23014):
                        for background_size in (32,64):
                            background=background_vectors[background_seed][:background_size]
                            reference=[sum(v[i] for v in background)/len(background) for i in range(len(coefficients))]
                            explanations=[];maximum=0.;tick=monotonic()
                            for row in sample:
                                explanation=linear(coefficients,intercept,row.x,reference);verify_linear(explanation,row.raw[1],row.p[1]);maximum=max(maximum,abs(explanation['logit']-row.raw[1]));explanations.append(explanation['contributions'])
                            stability.append(dict(protocol=protocol,method='exact interventional linear SHAP',output_space='log-odds',dependence_assumption='interventional empirical training background; no conditional dependence attribution',prediction_parity_verified=True,sample_seed=sample_seed,sample_size=len(sample),background_seed=background_seed,background_size=len(background),feature_order=feature_order,reference_mean=reference,reference_baseline=intercept+sum(c*v for c,v in zip(coefficients,reference)),mean_absolute_contributions=[sum(abs(v[i]) for v in explanations)/len(explanations) for i in range(len(coefficients))],mean_signed_contributions=[sum(v[i] for v in explanations)/len(explanations) for i in range(len(coefficients))],max_logit_residual=maximum,seconds=monotonic()-tick,raw_unit_coefficients=[c/s if s else None for c,s in zip(coefficients,std)],training_std=std))
        atomic_json(output/'linear_shap_stability.json',stability)
        # Evaluate installed SHAP against the exact archived Spark RF representation.
        shap_record=dict(status='unsupported',method='optional direct TreeExplainer compatibility')
        try:
            import shap,numpy as np
            rf_entry=next(e for e in inventory if e['kind']=='hybrid' and e['protocol']=='C')
            rf=models[rf_entry['id']];estimator=rf.stages[-1]
            background=populations['C'].where("split_rank = 0 AND source_day < '2018-02-22'").dropDuplicates(['predictor_key']).orderBy(F.xxhash64(F.lit(23013),'predictor_key')).limit(16)
            transformed=rf.transform(background).select(vector_to_array(estimator.getFeaturesCol()).alias('x')).collect()
            data=rf.transform(samples['C'].limit(16)).select(vector_to_array(estimator.getFeaturesCol()).alias('x'),vector_to_array('probability').alias('p')).collect()
            values=np.array([r.x for r in data]);reference=np.array([r.x for r in transformed]);tick=monotonic()
            explainer=shap.TreeExplainer(estimator,data=reference,model_output='probability',feature_perturbation='interventional')
            explanations=explainer(values);attributions=np.asarray(explanations.values);baselines=np.asarray(explanations.base_values)
            reconstructed=baselines+attributions.sum(axis=1);expected=np.array([r.p for r in data])
            require(reconstructed.shape==expected.shape and np.max(np.abs(reconstructed-expected))<=1e-6,'SHAP prediction/additivity parity differs')
            shap_record=dict(status='validated',shap_version=shap.__version__,model=rf_entry['id'],output_space='probability',background_rows=len(reference),explained_rows=len(values),max_residual=float(np.max(np.abs(reconstructed-expected))),mean_absolute_attributions=np.abs(attributions).mean(axis=0).tolist(),feature_order=next(s for s in rf.stages if type(s).__name__=='ImputerModel').getInputCols(),seconds=monotonic()-tick)
        except Exception as error:
            shap_record.update(reason_type=type(error).__name__,reason=str(error)[:300],interpretation='No SHAP values reported without archived-model compatibility and prediction parity.')
        atomic_json(output/'shap_compatibility.json',shap_record)
        atomic_json(output/'receipt.json',dict(status='validated',stage='13E-components',input=receipt,models=len(results),resources=resource_limits(spark,design,output),driver_peak_rss_bytes=driver_peak_bytes(spark),seconds=monotonic()-start,sha256={p.name:sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()}))
        print('PHASE13 components complete',flush=True)
    finally:spark.stop()
