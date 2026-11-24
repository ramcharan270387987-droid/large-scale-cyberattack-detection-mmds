"""Build the Phase 9 input audit using the verified notebook bootstrap."""
import json
from pathlib import Path
from build_phase8_notebook import build

ROOT = Path(__file__).resolve().parents[1]
notebook = build('baseline', 'B')
source = '''from src.ml.run_phase8 import json_file
from src.ingest.dataset_audit import spark_session, atomic_json
from src.ml.train_supervised import verified_input
from src.sql.traffic_analytics import locate_producer, write_rows
from src.ml.feature_registry import registry
from time import monotonic
output = Path('/kaggle/working/mmds_phase9')
output.mkdir(parents=True, exist_ok=True)
config = json_file(project, 'configs/ml_experiments.yaml')
spark = spark_session(config, Path('/kaggle/temp/phase9/spark'))
spark.conf.set('spark.sql.sources.partitionColumnTypeInference.enabled', 'false')
started = monotonic()
try:
    assert spark.version == '4.3.0'
    manifest = json_file(project, 'manifests/parquet_layers.json')
    policy = json_file(project, 'configs/cleaning.yaml')
    receipt = locate_producer(Path('/kaggle/input'), manifest['independent_mount']['summary_sha256'])
    frame, provenance = verified_input(spark, receipt, manifest, policy)
    features = registry(config, manifest['feature_columns'])
    support = [row.asDict() for row in frame.groupBy('source_day', 'original_label', 'attack_family', 'binary_label').count().orderBy('source_day', 'original_label').collect()]
    write_rows(output/'phase9_family_support.csv', support)
    atomic_json(output/'phase9_input_audit.json', {'status':'validated','stage':'input_audit','input':provenance,'features':features,'spark_version':spark.version,'seconds':monotonic()-started,'support':support})
    print('PHASE9 input audit validated', provenance['rows'])
finally:
    spark.stop()
'''
notebook['cells'][-1]['source'] = source.splitlines(keepends=True)
for cell in notebook['cells']:
    if cell['cell_type']=='code': compile(''.join(cell['source']),'<phase9>','exec')
(ROOT/'notebooks/phase9_multiclass_open_set.ipynb').write_text(json.dumps(notebook,indent=1)+'\n')
