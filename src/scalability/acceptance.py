"""Independent acceptance of saved benchmark repetitions and numerical results."""
import hashlib,json,math
from collections import Counter
from pathlib import Path

def same(a,b):
    if isinstance(a,dict):return isinstance(b,dict) and set(a)==set(b) and all(same(a[k],b[k]) for k in a)
    if isinstance(a,list):return isinstance(b,list) and len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
    if isinstance(a,float) or isinstance(b,float):return a==b or (a is not None and b is not None and math.isclose(a,b,rel_tol=1e-8,abs_tol=1e-8))
    return a==b

def volume(directory):
    directory=Path(directory);runs=json.loads((directory/'scalability_runs.json').read_text());pops=json.loads((directory/'benchmark_populations.json').read_text());receipt=json.loads((directory/'receipt.json').read_text());assert len(runs)==64 and receipt['measured_runs']==48 and receipt['warmups']==16 and receipt['all_correct'];assert len(pops)==4 and pops[-1]['actual_rows']==16232943
    references={};counts=Counter()
    for r in runs:
        assert r['status']=='PASS' and r['seconds']>0 and r['partitions']==16 and r['aqe'] is False
        assert hashlib.sha256(json.dumps(r['result'],sort_keys=True).encode()).hexdigest()==r['output_sha256']
        key=(r['requested_rows'],r['workload']);assert same(references.setdefault(key,r['result']),r['result'])
        assert r['actual_rows']==next(p['actual_rows'] for p in pops if p['requested_rows']==r['requested_rows'])
        assert math.isclose(r['rows_per_second'],r['actual_rows']/r['seconds'],rel_tol=1e-12)
        if not r['warmup']:counts[key+(r['workers'],)]+=1
    assert len(counts)==16 and set(counts.values())=={3}
    return dict(status='PASS',measured_runs=48,warmups=16,populations=[p['actual_rows'] for p in pops])

def optimization(directory):
    directory=Path(directory);runs=json.loads((directory/'optimization_runs.json').read_text());receipt=json.loads((directory/'receipt.json').read_text());assert receipt['status']=='validated' and receipt['stage']=='14E' and len(runs)==receipt['measured_runs']==130
    expected={'storage_logical_identity':2,'storage_full_read':6,'storage_count_metadata_optimization_allowed':6,'storage_projection_checksum':6,'storage_aggregation':6,'storage_projection_filter_query':6,'partition_materialization':9,'partition_query_after_materialization':9,'capture_pruning':3,'coalesce_materialized':3,'SQL_dataframe':6,'cache':7,'Spark_Pandas_input_loading':18,'Spark_Pandas_end_to_end':18,'Spark_Pandas_compute':18,'archived_inference':6,'pattern_mining':1}
    assert Counter(r['matrix'] for r in runs)==expected
    references={};repetitions=Counter()
    for r in runs:
        assert r['status']=='PASS' and r['seconds']>0 and r['actual_rows']>0
        assert math.isclose(r['rows_per_second'],r['actual_rows']/r['seconds'],rel_tol=1e-12)
        assert r['samples']>=2 and r['sample_interval_seconds']==.2 and r['tree_rss_sampled_peak']<=20*1024**3
        matrix=r['matrix'];config=r['configuration'];key=(matrix,)
        if matrix.startswith('Spark_Pandas'):
            size=int(config.split('-')[-1]);assert r['actual_rows']==size and size in (100000,500000,1000000);key=(matrix,size)
            assert r['engine']==('pandas' if config.startswith('pandas-') else 'Spark')
        elif matrix in ('archived_inference','pattern_mining'):key=(matrix,config)
        elif matrix=='cache':key=(matrix,'materialize' if config.startswith('first_') else 'query')
        assert same(references.setdefault(key,r['result']),r['result']),(matrix,config)
        repetitions[(matrix,config)]+=1
    for (matrix,config),count in repetitions.items():assert count==(1 if matrix in ('storage_logical_identity','pattern_mining') or config.startswith('first_materialization') else 3)
    inputs=json.loads((directory/'pandas_inputs.json').read_text());assert [r['actual_rows'] for r in inputs]==[100000,500000,1000000]
    return dict(status='PASS',measured_runs=130,matrices=len(expected),correctness='All compared matched configurations agree; integer counts exact',pandas_populations=[r['actual_rows'] for r in inputs])
