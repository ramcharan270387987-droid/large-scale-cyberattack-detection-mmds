"""Monitor saved Spark replay aggregates with window-level information clocks."""
import csv,json,pickle
from pathlib import Path
from time import perf_counter
from src.drift.advanced_detectors import create,update,divergences
from src.drift.label_availability import LabelSchedule
from src.drift.run_synthetic import write


def run(root,output):
    root,output=Path(root),Path(output);output.mkdir(parents=True,exist_ok=True)
    rows=list(csv.DictReader((root/'reports/phase6_window_metrics.csv').open()))
    rows=[r for r in rows if r['scope'] in ('intraday','capture_only')]
    rows.sort(key=lambda r:int(json.loads(r['batch_ids'])[0]))
    assert len(rows)==49 and sum(int(r['rows']) for r in rows)==15322987
    histograms=[json.loads(r['rf_score_counts_32']) for r in rows]
    assert all(sum(h)==int(r['rows']) for h,r in zip(histograms,rows))
    reference=[sum(h[i] for h in histograms[:3]) for i in range(32)]
    calibration=[divergences(reference,h) for h in histograms[3:10]]
    js_threshold=max(p[0] for p in calibration);psi_threshold=max(p[1] for p in calibration)
    frozen={'reference_batch_indices':[0,1,2],'calibration_batch_indices':list(range(3,10)),
            'evaluation_batch_indices':list(range(10,49)),'reference_histogram':reference,'JS':js_threshold,'PSI':psi_threshold,
            'unit':'replay window','label_delay_windows':[0,1,3],'DDM':'unsupported for historical binary errors because saved aggregate counts omit within-window error ordering'}
    (output/'frozen.json').write_text(json.dumps(frozen,indent=2)+'\n')
    records=[];performance=[]
    for delay in (0,1,3):
        detectors={name:create(name) for name in ('ADWIN','PageHinkley','KSWIN')}
        label_detectors={name:create(name) for name in ('ADWIN','PageHinkley')}
        scheduler=LabelSchedule(delay)
        for index,(row,histogram) in enumerate(zip(rows,histograms)):
            tick=perf_counter();n=int(row['rows']);mean_score=sum((i+.5)/32*c for i,c in enumerate(histogram))/n
            if n<100:
                records.append({'batch':index,'source_day':row['source_day'],'detector':'support_check','signal':'RF histogram','value':n,'threshold':100,'alert':False,'label_delay':None,'label_source_batch':None,'evaluation':index>=10,'unit':'replay window'})
                continue
            metrics=json.loads(row['classifier_metrics'])['random_forest'];error=(metrics['fp']+metrics['fn'])/n
            scheduler.predict(index,index,error)
            js,psi=divergences(reference,histogram)
            if index>=10 and delay==0:
                for name,value,threshold in [('JS',js,js_threshold),('PSI',psi,psi_threshold),('FixedJS',js,.1)]:
                    records.append({'batch':index,'source_day':row['source_day'],'detector':name,'signal':'RF histogram','value':value,'threshold':threshold,'alert':value>threshold,'label_delay':None,'label_source_batch':None,'evaluation':True,'unit':'replay window'})
            for name,detector in detectors.items():
                alerted=update(detector,mean_score)
                if delay==0:
                    records.append({'batch':index,'source_day':row['source_day'],'detector':name,'signal':'RF score mean','value':mean_score,'threshold':None,'alert':alerted,'label_delay':None,'label_source_batch':None,'evaluation':index>=10,'unit':'replay window'})
            for source_batch,released_error,released_at in scheduler.release(index):
                assert released_at<=index and source_batch<=index-delay
                for name,detector in label_detectors.items():
                    alerted=update(detector,released_error)
                    records.append({'batch':index,'source_day':row['source_day'],'detector':name,'signal':'released RF aggregate error rate','value':released_error,'threshold':None,'alert':alerted,'label_delay':delay,'label_source_batch':source_batch,'evaluation':index>=10,'unit':'released replay window'})
            performance.append({'batch':index,'delay':delay,'rows_represented':n,'seconds':perf_counter()-tick,'state_bytes':sum(len(pickle.dumps(x)) for x in (*detectors.values(),*label_detectors.values()))})
    write(output/'historical_alerts.csv',records);write(output/'performance.csv',performance)
    (output/'receipt.json').write_text(json.dumps({'status':'validated','stage':'11C','windows':49,'rows_represented':15322987,'evaluation_windows':39,'historical_true_drift_labels':False,'unit':'aggregate window','labels_released_after_end':'pending and excluded'},indent=2)+'\n')
    print('PHASE11 historical complete',len(records),flush=True)
