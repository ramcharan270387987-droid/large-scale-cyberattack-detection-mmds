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
