"""Calibrate on independent stationarity and evaluate bounded synthetic shifts."""
from bisect import bisect_left
import csv,json,pickle
from pathlib import Path
from time import perf_counter
from src.drift.advanced_detectors import create,update,divergences
from src.drift.synthetic_generators import generate,SCENARIOS
from src.drift.drift_evaluation import evaluate
from src.drift.label_availability import LabelSchedule


def write(path,rows):
    keys=list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys,lineterminator='\n');w.writeheader();w.writerows(rows)


def run(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    start=perf_counter();calibration=[];frozen={};bins=64
    for name in ('ADWIN','PageHinkley','KSWIN','DDM'):
        options=[]
        for sensitivity in ('conservative','sensitive') if name!='DDM' else ('conservative',):
            total=0;seconds=0.
            for seed in (13013,13014,13015):
                detector=create(name,sensitivity,seed);tick=perf_counter();alerts=[]
                for row in generate('stationary',seed):
                    value=row['error'] if name=='DDM' else row['signal']
                    if update(detector,value,name=='DDM'):alerts.append(row['index'])
                elapsed=perf_counter()-tick;seconds+=elapsed
                stats=evaluate(alerts,[],4096);total+=stats['false_alarms']
                calibration.append({'detector':name,'sensitivity':sensitivity,'seed':seed,'seconds':elapsed,**stats})
            rate=total/(3*(4096-256))*1000
            options.append((rate>1,rate,seconds,sensitivity))
        frozen[name]=min(options)[-1]
    # Frozen-reference bins and distribution thresholds use independent calibration.
    reference=[r['signal'] for r in list(generate('stationary',13013))[:256]]
    ordered=sorted(reference);edges=[ordered[int(i*len(ordered)/10)] for i in range(1,10)]
    def histogram(values):
        counts=[0]*10
        for x in values:counts[bisect_left(edges,x)]+=1
        return counts
    reference_counts=histogram(reference);distributions=[]
    for seed in (13013,13014,13015):
        values=[r['signal'] for r in generate('stationary',seed)]
        distributions.extend(divergences(reference_counts,histogram(values[i:i+bins])) for i in range(256,len(values),bins))
    for index,name in enumerate(('JS','PSI')):
        values=sorted(row[index] for row in distributions);frozen[name]=values[int(.99*(len(values)-1))]
    frozen.update(reference_bins=edges,reference_counts=reference_counts,window_size=bins)
    (output/'frozen.json').write_text(json.dumps(frozen,indent=2)+'\n')
    print('PHASE11 synthetic configurations frozen',flush=True)
    results=[];events_table=[];signals=[]
    for kind in SCENARIOS:
        boundaries=[] if kind=='stationary' else [2048,3072] if kind=='recurring' else [2048]
        for seed in (23013,23014,23015):
            data=list(generate(kind,seed))
            for name in ('ADWIN','PageHinkley','KSWIN','DDM','JS','PSI','FixedJS'):
                delays=(0,1,3) if name=='DDM' else (0,)
                for delay in delays:
                    tick=perf_counter();alerts=[];detector=create(name,frozen[name],seed) if name in ('ADWIN','PageHinkley','KSWIN','DDM') else None
                    schedule=LabelSchedule(delay)
                    for row in data:
                        i=row['index']
                        if name=='DDM':
                            schedule.predict(i//bins,i,row['error'])
                            for identifier,error,released in schedule.release(i//bins):
                                assert released<=i//bins
                                if update(detector,error,True):alerts.append(i)
                        elif detector:
                            if update(detector,row['signal']):alerts.append(i)
                        elif i>=256+bins-1 and (i+1)%bins==0:
                            js,psi=divergences(reference_counts,histogram([r['signal'] for r in data[i+1-bins:i+1]]))
                            if (js if name!='PSI' else psi)>(.1 if name=='FixedJS' else frozen[name]):alerts.append(i)
                    elapsed=perf_counter()-tick
                    relevant=(kind in ('error','concept')) if name=='DDM' else (kind not in ('error','concept'))
                    stats=evaluate(alerts,boundaries if relevant else [],4096)
                    results.append({'scenario':kind,'seed':seed,'detector':name,'label_delay_windows':delay,'seconds':elapsed,'updates_per_second':4096/elapsed,'state_bytes':len(pickle.dumps(detector)) if detector else 0,**stats})
                    events_table.extend({'scenario':kind,'seed':seed,'detector':name,'label_delay_windows':delay,'alert_index':i} for i in alerts)
            if seed==23013:signals.extend({'scenario':kind,**r} for r in data[::16])
            print('PHASE11 evaluated',kind,seed,flush=True)
    write(output/'synthetic_metrics.csv',results);write(output/'alerts.csv',events_table);write(output/'calibration.csv',calibration);write(output/'signals.csv',signals)
    (output/'receipt.json').write_text(json.dumps({'status':'validated','stage':'11B','rows':len(results),'seconds':perf_counter()-start,'synthetic_only':True,'pending_end_labels_note':'Labels released after the final observation remain pending and are excluded from detector updates'},indent=2)+'\n')
    print('PHASE11 synthetic complete',len(results),flush=True)
