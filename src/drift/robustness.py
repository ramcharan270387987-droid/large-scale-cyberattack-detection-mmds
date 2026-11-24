"""Prespecified distribution-window sensitivity and label-free ensemble ablation."""
from bisect import bisect_left
from collections import defaultdict
import csv,json
from pathlib import Path
from time import perf_counter
from src.drift.advanced_detectors import divergences
from src.drift.synthetic_generators import generate
from src.drift.drift_evaluation import evaluate
from src.drift.run_synthetic import write


def run(primary,output):
    primary,output=Path(primary),Path(output);output.mkdir(parents=True,exist_ok=True)
    frozen=json.loads((primary/'frozen.json').read_text());edges=frozen['reference_bins'];ref=frozen['reference_counts']
    def histogram(values):
        result=[0]*10
        for x in values:result[bisect_left(edges,x)]+=1
        return result
    records=[]
    for window in (32,64,128):
        calibration=[]
        for seed in (13013,13014,13015):
            values=[r['signal'] for r in generate('stationary',seed)]
            calibration.extend(divergences(ref,histogram(values[i:i+window])) for i in range(256,4096,window))
        cutoffs=[sorted(v[i] for v in calibration)[int(.99*(len(calibration)-1))] for i in (0,1)]
        for magnitude in (.5,1.):
            for seed in (23013,23014,23015):
                values=[r['signal'] for r in generate('abrupt',seed,magnitude=magnitude)]
                alerts=[[],[]];tick=perf_counter()
                for end in range(256+window,4097,window):
                    scores=divergences(ref,histogram(values[end-window:end]))
                    for i in (0,1):
                        if scores[i]>cutoffs[i]:alerts[i].append(end-1)
                elapsed=perf_counter()-tick
                for i,name in enumerate(('JS','PSI')):
                    records.append({'detector':name,'window':window,'magnitude':magnitude,'seed':seed,'threshold':cutoffs[i],'seconds':elapsed,**evaluate(alerts[i],[2048],4096)})
    write(output/'sensitivity.csv',records)
    groups=defaultdict(list)
    for row in csv.DictReader((primary/'alerts.csv').open()):
        if row['detector'] in ('ADWIN','PageHinkley','KSWIN','JS','PSI'):
            groups[row['scenario'],int(row['seed'])].append((int(row['alert_index']),row['detector']))
    ablations=[]
    for kind in ('stationary','abrupt','gradual','incremental','recurring','variance','correlation','prior','missingness','error','concept'):
        boundaries=[] if kind in ('stationary','error','concept') else [2048,3072] if kind=='recurring' else [2048]
        for seed in (23013,23014,23015):
            recent=[];alerts=[];last=-65
            for index,name in sorted(groups[kind,seed]):
                recent=[(i,n) for i,n in recent if i>=index-64];recent.append((index,name))
                if len({n for _,n in recent})>=2 and index-last>=64:
                    alerts.append(index);last=index
            ablations.append({'scenario':kind,'seed':seed,'detector':'two-family-64-observation-ensemble',**evaluate(alerts,boundaries,4096)})
            ablations.append({'scenario':kind,'seed':seed,'detector':'no_detector',**evaluate([],boundaries,4096)})
    write(output/'ablations.csv',ablations)
    (output/'receipt.json').write_text(json.dumps({'status':'validated','stage':'11D','sensitivity_rows':len(records),'ablation_rows':len(ablations),'ensemble':'At least two distinct label-free detector families within 64 observations with 64-observation cooldown'},indent=2)+'\n')
    print('PHASE11 robustness complete',flush=True)
