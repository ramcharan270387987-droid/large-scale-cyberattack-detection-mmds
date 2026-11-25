"""Extract selected private pipeline components or independently reload/probe them."""
import argparse,json,hashlib,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('private_directory',type=Path);p.add_argument('--extract');p.add_argument('--receipt',type=Path);p.add_argument('--compare',type=Path);a=p.parse_args();registry=json.loads((ROOT/'reports/phase14_14C/models.json').read_text())
    if a.extract:
        from kaggle_web_api import download_archive
        with download_archive(a.extract,32*1024*1024) as archive:
            for model in registry:
                for relative,expected in model['saved']['sha256'].items():
                    path=Path(relative);assert not path.is_absolute() and '..' not in path.parts;data=archive.read('mmds_phase14/'+model['saved']['artifact']+'/'+relative);assert hashlib.sha256(data).hexdigest()==expected;target=a.private_directory/model['model']/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        print('PRIVATE_MODEL_COMPONENTS_VERIFIED',len(registry));return
    from pyspark.sql import SparkSession
    from pyspark.ml import PipelineModel
    from pyspark.ml.functions import vector_to_array
    spark=SparkSession.builder.master('local[2]').appName('phase14-independent-private-model-reload').config('spark.ui.enabled','false').getOrCreate();spark.sparkContext.setLogLevel('ERROR');records=[]
    try:
        names=['flow_duration','tot_fwd_pkts','tot_bwd_pkts'];probes=spark.createDataFrame([(None,None,None),(0.,0.,0.),(1000000.,10.,5.)],','.join(n+' DOUBLE' for n in names));prior=json.loads(a.compare.read_text()) if a.compare else None
        for meta in registry:
            folder=a.private_directory/meta['model']
            for name,expected in meta['saved']['sha256'].items():assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==expected
            model=PipelineModel.load(str(folder));scores=[list(r[0]) for r in model.transform(probes).select(vector_to_array('probability')).collect()];assert len(scores)==3 and all(len(v)==2 and all(math.isfinite(x) and 0<=x<=1 for x in v) and abs(sum(v)-1)<1e-12 for v in scores)
            if prior:assert scores==next(r['probe_scores'] for r in prior['models'] if r['model']==meta['model'])
            records.append(dict(model=meta['model'],hashes_verified=len(meta['saved']['sha256']),probe_scores=scores));print(meta['model'],'INDEPENDENT_RELOAD_PASS',flush=True)
        receipt=dict(status='PASS',spark=spark.version,fresh_process=True,compared_to_prior_process=bool(prior),models=records)
        assert a.receipt;a.receipt.parent.mkdir(parents=True,exist_ok=True);a.receipt.write_text(json.dumps(receipt,indent=2)+'\n')
    finally:spark.stop()
if __name__=='__main__':main()
