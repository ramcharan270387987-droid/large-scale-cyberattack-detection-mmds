"""Mine full eligible transactions using the recovered registry."""
import json,argparse
from pathlib import Path
from build_phase8_notebook import build
from build_phase2_notebook import ROOT,cell
p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args()
n=build('baseline','B');n['cells'][0]['source']=['# Phase 10 full-population frequent pattern mining']
sources={name:(ROOT/name).read_text() for name in ('src/patterns/discretization.py','src/patterns/frequent_itemsets.py','src/patterns/metrics.py')}
registry=json.loads((ROOT/'reports/phase10_stageA/discretization.json').read_text())['A3']
n['cells'].insert(-1,cell('code','phase10-source',f'sources={sources!r}\nfor name,content in sources.items():\n target=project/name\n target.parent.mkdir(parents=True,exist_ok=True)\n target.write_text(content)\nregistry={registry!r}\n'))
code='''from time import monotonic
from hashlib import sha256
from pyspark.sql import functions as F
from src.ingest.dataset_audit import spark_session,atomic_json
from src.ingest.parquet_pipeline import driver_peak_bytes,resource_limits
from src.ml.phase8_baselines import json_file
from src.ml.train_supervised import verified_input
from src.ml.feature_registry import predictor_input,registry as feature_names
from src.sql.traffic_analytics import locate_producer
from src.patterns.discretization import transform
from src.patterns.frequent_itemsets import mine,export,reload_parity
out=Path('/kaggle/working/mmds_phase10_mining');out.mkdir(parents=True,exist_ok=True)
config=json_file(project,'configs/ml_experiments.yaml')
spark=spark_session(config,Path('/kaggle/temp/phase10_mining/spark'))
spark.conf.set('spark.sql.sources.partitionColumnTypeInference.enabled','false')
start=monotonic()
try:
 upstream=json_file(project,'manifests/parquet_layers.json')
 raw,receipt=verified_input(spark,locate_producer(Path('/kaggle/input'),upstream['independent_mount']['summary_sha256']),upstream,json_file(project,'configs/cleaning.yaml'))
 names=feature_names(config,upstream['feature_columns'])
 frame=predictor_input(raw,names,config['version'])
 bins={name:registry['boundaries'][name] for name in names[:6]}
 data=transform(frame,bins).select('items').persist()
 total=data.count();assert total==16232943
 summaries=[]
 for support in (.1,.05,.02,.01):
  model,summary=mine(data,support)
  summary.update(support=support,rows=total)
  items=export(model,total)
  rules=model.associationRules.orderBy(F.desc('confidence'),'antecedent','consequent')
  summary['rules']=rules.count()
  atomic_json(out/('items_'+str(support)+'.json'),items)
  atomic_json(out/('rules_'+str(support)+'.json'),[r.asDict() for r in rules.limit(500).collect()])
  if support==.05:
   summary['reload_rows']=reload_parity(model,out/'model',data.limit(3))
  summaries.append(summary)
  atomic_json(out/'progress.json',summaries)
  if summary['itemsets']>100000 or summary['seconds']>900:break
 atomic_json(out/'registry.json',bins)
 hashes={p.relative_to(out).as_posix():sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file() and not p.name.endswith('.crc')}
 atomic_json(out/'receipt.json',{'status':'validated','stage':'B','input':receipt,'rows':total,'features':names[:6],'summaries':summaries,'seconds':monotonic()-start,'resources':resource_limits(spark,config,out),'driver_peak_rss_bytes':driver_peak_bytes(spark),'sha256':hashes})
 print('PHASE10 mining complete',flush=True)
finally:spark.stop()
'''
n['cells'][-1]['source']=code.splitlines(keepends=True)
for c in n['cells']:
 if c['cell_type']=='code':compile(''.join(c['source']),c['id'],'exec')
a.output.write_text(json.dumps(n,indent=1)+'\n')
