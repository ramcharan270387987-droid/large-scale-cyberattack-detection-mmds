"""Fresh-process Spark reload over retrieved private model files, without data fitting."""
import argparse,json,hashlib,time,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pyspark.sql import SparkSession
from pyspark.ml import PipelineModel
from pyspark.ml.functions import vector_to_array
from src.streaming.model_scoring import probe

def main():
    p=argparse.ArgumentParser();p.add_argument('summary',type=Path);p.add_argument('receipt',type=Path);p.add_argument('--compare',type=Path);a=p.parse_args()
    payload=json.loads(a.summary.read_text());root=a.summary.parent;start=time.monotonic()
    spark=SparkSession.builder.master('local[2]').config('spark.ui.enabled','false').getOrCreate();spark.sparkContext.setLogLevel('ERROR')
    result=[];rollback=None
    try:
        for identifier,meta in payload['models'].items():
            folder=root/meta['receipt']['artifact'];t=time.monotonic()
            for relative,expected in meta['receipt']['sha256'].items():assert hashlib.sha256((folder/relative).read_bytes()).hexdigest()==expected
            model=PipelineModel.load(str(folder));rows=probe(spark,meta['features'])
            scores=[list(r[0]) for r in model.transform(rows).select(vector_to_array('probability')).collect()]
            import math
            assert len(scores)==3 and all(math.isfinite(v) for row in scores for v in row)
            result.append({'model':identifier,'hashes_verified':len(meta['receipt']['sha256']),'probe_scores':scores,'reload_seconds':time.monotonic()-t})
        if a.compare:
            prior=json.loads(a.compare.read_text());expected={r['model']:r['probe_scores'] for r in prior['models']}
            assert all(expected.get(r['model'])==r['probe_scores'] for r in result)
        if a.compare and len(result)>1:
            from tempfile import TemporaryDirectory
            from src.adaptation.lifecycle import Registry
            first,second=result[:2]
            with TemporaryDirectory() as directory:
                registry=Registry(directory)
                for row in (first,second):registry.register(row['model'],payload['models'][row['model']])
                registry.activate(first['model']);registry.activate(second['model'])
                try:registry.activate(first['model'],fail_before_replace=True)
                except RuntimeError:pass
                assert Registry(directory).active==second['model']
                t=time.monotonic();meta=payload['models'][first['model']]
                restored=PipelineModel.load(str(root/meta['receipt']['artifact']))
                probes=probe(spark,meta['features'])
                scores=[list(r[0]) for r in restored.transform(probes).select(vector_to_array('probability')).collect()]
                assert scores==first['probe_scores']
                registry.activate(first['model']);assert Registry(directory).active==first['model']
                rollback={'status':'PASS','injected':True,'source':second['model'],'destination':first['model'],
                          'restored_saved_pipeline_probes_identical':True,'seconds':time.monotonic()-t}
        a.receipt.parent.mkdir(parents=True,exist_ok=True)
        a.receipt.write_text(json.dumps({'status':'PASS','fresh_process':True,'compared_to_independent_process':bool(a.compare),
            'controlled_spark_rollback':rollback,'stage':payload['stage'],'spark_version':spark.version,'models':result,'seconds':time.monotonic()-start},indent=2)+'\n')
        print('FRESH_PROCESS_RELOAD_PASS',payload['stage'],len(result),bool(a.compare))
    finally:spark.stop()
if __name__=='__main__':main()
