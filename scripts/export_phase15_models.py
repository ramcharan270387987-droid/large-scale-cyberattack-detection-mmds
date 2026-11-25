"""Derive parameter-only models and verify against exact saved Spark pipelines."""
import json,hashlib,math,random,time
from pathlib import Path
from pyspark.sql import SparkSession
from pyspark.ml import PipelineModel
from pyspark.ml.functions import vector_to_array
from pyspark.sql import functions as F
from src.interactive.portable import predict
ROOT=Path(__file__).resolve().parents[1]
def save(path,data):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2)+'\n')
def node(n):
    if n.getClass().getSimpleName()=='LeafNode':
        counts=list(n.impurityStats().stats());total=sum(counts);return dict(probabilities=[v/total for v in counts])
    split=n.split();assert split.getClass().getSimpleName()=='ContinuousSplit'
    return dict(feature=int(split.featureIndex()),threshold=float(split.threshold()),left=node(n.leftChild()),right=node(n.rightChild()))
def main():
    start=time.monotonic();names=json.loads((ROOT/'configs/ml_experiments.yaml').read_text())['numerical_features'];sup=json.loads((ROOT/'manifests/phase13_models.json').read_text())['supervised'];km=json.loads((ROOT/'manifests/phase5_clustering_models.json').read_text())['experiments']['B'];out=[]
    sources=[('LR',next(m for m in sup if m['id']=='B-logistic_regression'),Path('/tmp/mmds-independent-models/B-logistic_regression')),('RF',next(m for m in sup if m['id']=='B-random_forest'),Path('/tmp/mmds-independent-models/B-random_forest')),('KMeans',dict(id='B-kmeans',version='ramcharan2345/mmds-phase-5-clustering-pattern-evolution/2',sha256=km['model']['sha256']),Path('/tmp/phase15-kmeans/mmds_phase5/model'))]
    spark=SparkSession.builder.master('local[2]').appName('phase15-archived-export-parity').config('spark.ui.enabled','false').getOrCreate();spark.sparkContext.setLogLevel('ERROR');assert spark.version=='4.3.0'
    try:
        for kind,source,folder in sources:
            for name,expected in source['sha256'].items():assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==expected,name
            pipeline=PipelineModel.load(str(folder));imputer=next(s for s in pipeline.stages if type(s).__name__=='ImputerModel');order=imputer.getInputCols();assert [n.removesuffix('_valid') for n in order]==names
            med=imputer.surrogateDF.first().asDict();model=dict(schema='phase15-portable-v1',id=source['id'],kind=kind,features=names,source_version=source['version'],source_sha256=source['sha256'],medians=[med[n] for n in order],preprocessing_stages=[type(s).__name__ for s in pipeline.stages],threshold=.5,scaler=None)
            scalers=[s for s in pipeline.stages if type(s).__name__=='StandardScalerModel']
            if scalers:
                s=scalers[0];model['scaler']=dict(std=list(s.std),mean=list(s.mean),with_mean=s.getWithMean(),with_std=s.getWithStd())
            estimator=pipeline.stages[-1]
            if kind=='LR':model.update(coefficients=list(estimator.coefficients),intercept=estimator.intercept)
            elif kind=='RF':model.update(trees=[node(t._java_obj.rootNode()) for t in estimator.trees],tree_weights=list(estimator.treeWeights))
            else:
                statements=[s.getStatement() for s in pipeline.stages if type(s).__name__=='SQLTransformer'];model['sql_preprocessing']=statements;assert len(statements)==1 and 'log1p' in statements[0];model['input_transform']='signed_log1p';model.update(centers=[list(c) for c in estimator.clusterCenters()],threshold=km['calibration']['cutoffs']['0.99'])
            rng=random.Random(23013);probes=[[None]*18,[0.]*18,[1.]*18,[1e12]*18]+[[rng.uniform(0,1000000) for _ in names] for _ in range(96)]
            # Exercise every exported continuous split at adjacent binary64 values.
            if kind=='RF':
                def boundaries(n):
                    if 'probabilities' not in n:
                        scaler=model['scaler'];i=n['feature'];threshold=n['threshold'];raw=(threshold*(scaler['std'][i] if scaler and scaler['with_std'] else 1)+(scaler['mean'][i] if scaler and scaler['with_mean'] else 0))
                        if 0<=raw<=1e12:
                            for value in (math.nextafter(raw,-math.inf),raw,math.nextafter(raw,math.inf)):
                                x=[0.]*18;x[i]=value;probes.append(x)
                        boundaries(n['left']);boundaries(n['right'])
                for tree in model['trees']:boundaries(tree)
            frame=spark.createDataFrame(probes,', '.join(n+' DOUBLE' for n in names))
            scored=pipeline.transform(frame)
            maximum=0.;decisions=0
            if kind in ('LR','RF'):
                values=scored.select(vector_to_array('probability').alias('p')).collect()
                for raw,row in zip(probes,values):
                    actual=predict(model,dict(zip(names,raw)));maximum=max(maximum,abs(actual['probability']-row.p[1]));assert maximum<=1e-10;assert (actual['label']=='ATTACK')==(row.p[1]>=.5);decisions+=1
            else:
                from src.ml.novelty_scoring import squared_distance
                pre=PipelineModel(stages=pipeline.stages[:-1]);values=squared_distance(estimator,pre.transform(frame)).select('cluster','score').collect()
                for raw,row in zip(probes,values):
                    actual=predict(model,dict(zip(names,raw)));assert actual['cluster']==row.cluster;residual=abs(actual['squared_distance']-row.score);maximum=max(maximum,residual);assert math.isclose(actual['squared_distance'],row.score,rel_tol=1e-8,abs_tol=1e-8);assert (actual['label']=='NOVEL')==(row.score>model['threshold']);decisions+=1
            target=ROOT/'dashboard/models'/('phase15_'+kind.lower()+'.json');save(target,model)
            out.append(dict(id=model['id'],kind=kind,source_phase=5 if kind=='KMeans' else 4,source_version=source['version'],source_sha256=source['sha256'],artifact=str(target.relative_to(ROOT)),sha256=hashlib.sha256(target.read_bytes()).hexdigest(),features=names,threshold=model['threshold'],protocol='B chronological',runtime='standard Python parameter-only execution',explanation='exact logit contributions' if kind=='LR' else 'assigned centroid squared deviations' if kind=='KMeans' else 'native global importance; no local tree SHAP',parity=dict(status='PASS',probes=len(probes),max_absolute_residual=maximum,decisions_equal=decisions),distribution='Owner-authorized derived parameters; no raw training records; source mirror declaresApache2.0',limitations='Historical source-domain model; uncalibrated score; not validated for arbitrary external feature extraction'))
            print(kind,'PARITY_PASS',len(probes),maximum,flush=True)
        save(ROOT/'manifests/phase15_models.json',dict(schema='phase15-models-v1',models=out,unsupported_executable=['hybrid','multiclass','open-set','direct tree SHAP'],artifact_missing_policy='Fail closed; research remains available'))
        save(ROOT/'reports/phase15_validation/parity.json',dict(status='PASS',spark=spark.version,seed=23013,models=[dict(id=r['id'],portable_sha256=r['sha256'],**r['parity']) for r in out],seconds=time.monotonic()-start,private_rows_published=False,fitting_performed=False))
    finally:spark.stop()
if __name__=='__main__':main()
