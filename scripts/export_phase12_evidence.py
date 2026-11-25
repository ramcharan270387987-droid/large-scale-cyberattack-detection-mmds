"""Reconcile compact replay evidence and export stable CSV tables."""
import csv,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def csv_write(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    if not rows:return
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for r in rows:
            writer.writerow({k:json.dumps(v,sort_keys=True) if isinstance(v,(dict,list)) else v for k,v in r.items()})

def validate(runs):
    for r in runs:
        s=r['summary']
        for k in ('tp','fp','tn','fn','rows'):
            assert sum(w[k] for w in r['windows'])==s[k],(s['run'],k)
        assert s['rows']==sum(s[k] for k in ('tp','fp','tn','fn'))
        for e in r['events']:
            if e.get('activation_index') is not None:
                assert e['activation_index']>e['window']
                assert e['activation_time']>=e.get('training_complete',e.get('trigger_time',0))
            assert all(int(t) <= 6+e['window']-s['delay'] for t in e.get('training_days',[]) if t.isdigit())
    groups={}
    for r in runs:
        s=r['summary']; key=(s['backend'],s['delay'])
        cohort=[(w['day'],w['tp']+w['fn'],w['tn']+w['fp']) for w in r['windows']]
        if key in groups: assert groups[key]==cohort,key
        else:groups[key]=cohort

def export(payload,dest):
    runs=payload['runs'];validate(runs)
    model_rows=payload['models'];model_rows=list(model_rows.values()) if isinstance(model_rows,dict) else model_rows
    for run in runs:
        summary=run['summary']
        for event in run['events']:
            if event.get('action')!='fit':continue
            matching=[m for m in model_rows if m['backend']==summary['backend'] and list(map(str,m['training_days']))==event['training_days']]
            event['fit_succeeded']=bool(matching)
            if matching:
                event['model']=matching[0]['model']
                event['charged_fit_seconds']=matching[0]['fit_seconds']
        summary['charged_fit_seconds']=sum(e.get('charged_fit_seconds',0) for e in run['events'])
        summary['successful_retrainings']=sum(e.get('fit_succeeded',False) for e in run['events'])
        summary['failed_retrainings']=sum(e.get('action')=='fit' and not e.get('fit_succeeded',False) for e in run['events'])
        summary['failed_actions']=sum(e.get('failed') is True for e in run['events'])
        summary['activated_candidates']=sum(e.get('action')=='fit' and e.get('activation_index') is not None for e in run['events'])
    csv_write(dest/'policy_comparison.csv',[r['summary'] for r in runs])
    for key in ('windows','events','triggers','thresholds','family','retention'):
        csv_write(dest/(key+'.csv'),[row for r in runs for row in r[key]])
    models=payload['models']; models=list(models.values()) if isinstance(models,dict) else models
    csv_write(dest/'models.csv',models)
    compact={k:v for k,v in payload.items() if k not in ('runs','models')}
    compact.update(runs=len(runs),unique_models=len(models),validation='pooled counts, matched cohorts and future activations verified')
    (dest/'receipt.json').write_text(json.dumps(compact,indent=2)+'\n')
    return runs
if __name__=='__main__':
    import sys
    path=Path(sys.argv[1]); destination=Path(sys.argv[2]);destination.mkdir(parents=True,exist_ok=True)
    export(json.loads(path.read_text()),destination)
