"""Export exact bounded transaction signatures for contrast and temporal evidence."""
import argparse,json
from pathlib import Path
from build_phase8_notebook import build
from build_phase2_notebook import ROOT,cell
p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args()
n=build('baseline','B');n['cells'][0]['source']=['# Phase 10 contrast and temporal sufficient counts']
sources={name:(ROOT/name).read_text() for name in ('src/patterns/discretization.py',)}
registries=json.loads((ROOT/'reports/phase10_stageA/discretization.json').read_text())
n['cells'].insert(-1,cell('code','phase10-source',f'sources={sources!r}\nfor name,content in sources.items():\n target=project/name\n target.parent.mkdir(parents=True,exist_ok=True)\n target.write_text(content)\nregistries={registries!r}\n'))
code='''from time import monotonic
from hashlib import sha256
from pyspark.sql import functions as F,Window
from pyspark import StorageLevel
from src.ingest.dataset_audit import spark_session,atomic_json
from src.ingest.parquet_pipeline import driver_peak_bytes,resource_limits
from src.ml.phase8_baselines import json_file,benchmark_population
from src.ml.train_supervised import verified_input
from src.ml.feature_registry import predictor_input,registry
from src.sql.traffic_analytics import locate_producer
from src.patterns.discretization import transform
out=Path('/kaggle/working/mmds_phase10_aggregates');out.mkdir(parents=True,exist_ok=True)
config=json_file(project,'configs/ml_experiments.yaml');upstream=json_file(project,'manifests/parquet_layers.json')
spark=spark_session(config,Path('/kaggle/temp/phase10_aggregates/spark'))
spark.conf.set('spark.sql.sources.partitionColumnTypeInference.enabled','false')
start=monotonic()
try:
 raw,receipt=verified_input(spark,locate_producer(Path('/kaggle/input'),upstream['independent_mount']['summary_sha256']),upstream,json_file(project,'configs/cleaning.yaml'))
 names=registry(config,upstream['feature_columns'])
 frame=predictor_input(raw,names,config['version']).persist(StorageLevel.DISK_ONLY)
 assert frame.count()==16232943
 active,split=benchmark_population(frame,'B',config,receipt['days'],json_file(project,'manifests/phase4_models.json'),out)
 boundaries={k:{name:v['boundaries'][name] for name in names[:6]} for k,v in registries.items()}
 for population in ('A','B'):
  for base in ('3','5'):
   bins=boundaries[population+base]
   data=frame if population=='A' else active
   # Equal predictor-group weights preserve all observed rows with fractional mass.
   weighted=data.withColumn('group_weight',1/F.count('*').over(Window.partitionBy('predictor_key')))
   roles=['source_day','binary_label','attack_family']+(['split_rank'] if population=='B' else [])
   transactions=transform(weighted,bins)
   grouped=transactions.groupBy(*roles,'items').agg(F.count('*').alias('count'),F.sum('group_weight').alias('group_weight'))
   assert grouped.count()<=500000
   rows=[r.asDict() for r in grouped.collect()]
   assert sum(r['count'] for r in rows)==(16232943 if population=='A' else 15322987)
   atomic_json(out/(population+base+'.json'),rows)
 # Domain boundaries are fixed by the committed protocol, using reference thirds for other features.
 domain=dict(registries['B3']['boundaries'])
 for name in names:
  if 'pkts' in name and name in ('tot_fwd_pkts','tot_bwd_pkts') or name.endswith('_flag_cnt'):domain[name]=[0.,1.,10.]
  elif name=='flow_duration' or 'iat_' in name:domain[name]=[0.,1000.,1000000.]
 atomic_json(out/'domain_registry.json',domain)
 transactions=transform(frame,{name:domain[name] for name in names[:6]})
 rows=[r.asDict() for r in transactions.groupBy('source_day','binary_label','attack_family','items').count().collect()]
 assert sum(r['count'] for r in rows)==16232943
 atomic_json(out/'domain.json',rows)
 atomic_json(out/'receipt.json',{'status':'validated','input':receipt,'split':split,'features':names[:6],'seconds':monotonic()-start,'resources':resource_limits(spark,config,out),'driver_peak_rss_bytes':driver_peak_bytes(spark),'sha256':{p.name:sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()}})
 print('PHASE10 aggregates complete',flush=True)
finally:spark.stop()
'''
n['cells'][-1]['source']=code.splitlines(keepends=True)
for c in n['cells']:
 if c['cell_type']=='code':compile(''.join(c['source']),c['id'],'exec')
a.output.write_text(json.dumps(n,indent=1)+'\n')
