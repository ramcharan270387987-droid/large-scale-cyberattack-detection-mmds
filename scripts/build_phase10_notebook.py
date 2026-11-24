"""Build the first actual Phase 10 discretization stage."""
import argparse
import json
from pathlib import Path
from build_phase8_notebook import build
from build_phase2_notebook import cell, ROOT

p = argparse.ArgumentParser()
p.add_argument('output', type=Path)
a = p.parse_args()
note = build('baseline', 'B')
source = (ROOT / 'src/patterns/discretization.py').read_text()
note['cells'].insert(-1, cell('code', 'phase10-source', 'target = project / "src/patterns/discretization.py"\ntarget.parent.mkdir(parents=True, exist_ok=True)\ntarget.write_text(' + repr(source) + ')\n'))
code = '''from hashlib import sha256
from time import monotonic
from pyspark.sql import functions as F
from src.ingest.dataset_audit import spark_session, atomic_json
from src.ml.phase8_baselines import json_file, benchmark_population
from src.ml.train_supervised import verified_input
from src.ml.feature_registry import predictor_input, registry
from src.sql.traffic_analytics import locate_producer
from src.patterns.discretization import fit, transform
out = Path('/kaggle/working/mmds_phase10')
out.mkdir(parents=True, exist_ok=True)
config = json_file(project, 'configs/ml_experiments.yaml')
upstream = json_file(project, 'manifests/parquet_layers.json')
spark = spark_session(config, Path('/kaggle/temp/phase10/spark'))
spark.conf.set('spark.sql.sources.partitionColumnTypeInference.enabled', 'false')
start = monotonic()
try:
    assert spark.version == '4.3.0'
    data, receipt = verified_input(spark, locate_producer(Path('/kaggle/input'), upstream['independent_mount']['summary_sha256']), upstream, json_file(project, 'configs/cleaning.yaml'))
    names = registry(config, upstream['feature_columns'])
    frame = predictor_input(data, names, config['version']).persist()
    assert frame.count() == 16232943
    active, split = benchmark_population(frame, 'B', config, receipt['days'], json_file(project, 'manifests/phase4_models.json'), out)
    results = {}
    for population, reference in [('A', frame), ('B', active.where('split_rank = 0'))]:
        for bins in (3, 5):
            boundaries = fit(reference, names, bins)
            transactions = transform(reference, boundaries)
            counts = transactions.groupBy(F.size('items').alias('length'), F.size(F.array_distinct('items')).alias('unique')).count().collect()
            assert all(r.length == 18 and r.unique == 18 for r in counts)
            singletons = transactions.select(F.explode('items').alias('item')).groupBy('item').count().collect()
            results[population + str(bins)] = {'boundaries': boundaries, 'rows': sum(r['count'] for r in counts), 'lengths': [r.asDict() for r in counts], 'singletons': [r.asDict() for r in singletons]}
    atomic_json(out / 'discretization.json', results)
    atomic_json(out / 'receipt.json', {'status': 'validated', 'stage': 'A', 'input': receipt, 'split': split, 'spark_version': spark.version, 'seconds': monotonic()-start, 'sha256': sha256((out/'discretization.json').read_bytes()).hexdigest()})
    print('PHASE10 stage A complete', flush=True)
finally:
    spark.stop()
'''
note['cells'][-1]['source'] = code.splitlines(keepends=True)
for c in note['cells']:
    if c['cell_type'] == 'code': compile(''.join(c['source']), c['id'], 'exec')
a.output.write_text(json.dumps(note, indent=1)+'\n')
