"""Pure benchmark calculations; never synthesize missing experimental records."""
import math,statistics

def speedup(one,current,workers):
    if not (math.isfinite(one) and math.isfinite(current) and one>0 and current>0 and isinstance(workers,int) and workers>0):raise ValueError('Need measured positive matched times and worker count')
    ratio=one/current
    return {'speedup':ratio,'efficiency':ratio/workers}
def summarize(rows):
    if not rows or any(r['status']!='PASS' for r in rows):raise ValueError('Cannot summarize missing/failed runs as performance')
    times=[r['seconds'] for r in rows]
    return dict(repetitions=len(times),median_seconds=statistics.median(times),min_seconds=min(times),max_seconds=max(times),spread_seconds=max(times)-min(times))
