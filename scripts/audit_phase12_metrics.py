"""Independently reconcile reported metrics with retrieved Kaggle score-bin counts."""
import csv,json,math
from pathlib import Path
from collections import defaultdict
from export_phase12_evidence import csv_write
ROOT=Path(__file__).resolve().parents[1]
ROOTS=[Path('/tmp/mmds-phase12/12C-v3/results/mmds_phase12'),Path('/tmp/mmds-phase12/12D/results/mmds_phase12'),
       Path('/tmp/mmds-phase12/12E/results/mmds_phase12'),Path('/tmp/mmds-phase12/12E-resume/results/mmds_phase12')]

def metrics(hist,cut):
    negatives=sum(v[0] for v in hist.values());positives=sum(v[1] for v in hist.values())
    tp=sum(v[1] for k,v in hist.items() if k>=cut);fp=sum(v[0] for k,v in hist.items() if k>=cut)
    tn=negatives-fp;fn=positives-tp
    rate=lambda n,d:n/d if d else None
    return {'tp':tp,'fp':fp,'tn':tn,'fn':fn,'rows':negatives+positives,'precision':rate(tp,tp+fp),'recall':rate(tp,positives),
        'accuracy':rate(tp+tn,negatives+positives),'specificity':rate(tn,negatives),'positive_rate':rate(tp+fp,negatives+positives),
        'f1':rate(2*tp,2*tp+fp+fn),'fpr':rate(fp,negatives),'balanced_accuracy':(tp/positives+tn/negatives)/2 if positives and negatives else None}

def auc(hist):
    n=sum(v[0] for v in hist.values());p=sum(v[1] for v in hist.values())
    if not n or not p:return {'pr_auc':None,'roc_auc':None}
    tp=fp=0;previous_recall=previous_fpr=0.;pr=roc=0.
    for key in sorted(hist,reverse=True):
        fp+=hist[key][0];tp+=hist[key][1];recall=tp/p;fpr=fp/n
        pr+=(recall-previous_recall)*tp/(tp+fp)
        roc+=(fpr-previous_fpr)*(recall+previous_recall)/2
        previous_recall,previous_fpr=recall,fpr
    return {'pr_auc':pr,'roc_auc':roc}

def pooled(items):
    result=defaultdict(lambda:[0,0])
    for h in items:
        for k,v in h.items():result[int(k)][0]+=v[0];result[int(k)][1]+=v[1]
    return dict(result)

HISTOGRAMS={}
def histogram(model,day,role):
    key=(model,day,role)
    if key not in HISTOGRAMS:
        matches=[root/'prediction_histograms'/f'{model}-{day}-r{role}.json' for root in ROOTS]
        values=[]
        for path in matches:
            if path.exists():
                record=json.loads(path.read_text());values.append(pooled(record['family_histograms'].values()))
        if not values:raise ValueError('Missing retrieved histogram '+str(key))
        assert all(v==values[0] for v in values),'Cross-runtime scoring discrepancy '+str(key)
        HISTOGRAMS[key]=values[0]
    return HISTOGRAMS[key]

def check(observed,expected):
    for key,value in expected.items():
        actual=observed[key]
        if value is None:assert actual in ('',None),(key,actual,value)
        else:assert actual not in ('',None) and math.isclose(float(actual),value,rel_tol=1e-12,abs_tol=1e-12),(key,actual,value)

def optimum(hist):
    n=sum(v[0] for v in hist.values());p=sum(v[1] for v in hist.values());assert n and p
    tp=fp=0;best=(0.,-1.,0.,2048);selected=2048
    for threshold in reversed(range(2048)):
        negative,positive=hist.get(threshold,(0,0));tp+=positive;fp+=negative
        if fp/n>.01:continue
        value=(tp/p,tp/(tp+fp) if tp+fp else -1.,-fp/n,threshold)
        if value>best:best=value;selected=threshold
    return selected

def main():
    rows=list(csv.DictReader((ROOT/'reports/phase12_policy_comparison.csv').open()))
    windows=list(csv.DictReader((ROOT/'reports/phase12_prequential_metrics.csv').open()))
    events=list(csv.DictReader((ROOT/'reports/phase12_training_events.csv').open()))
    result=[]
    for row in rows:
        issued=[w for w in windows if w['run']==row['run']];counts=defaultdict(int);hists=[]
        for w in issued:
            h=histogram(w['model'],w['day'],2);m=metrics(h,int(w['threshold_bin']));check(w,m|auc(h));hists.append(h)
            for key in ('tp','fp','tn','fn'):counts[key]+=m[key]
        n=counts['fp']+counts['tn'];p=counts['tp']+counts['fn'];tp=counts['tp'];fp=counts['fp'];fn=counts['fn'];tn=counts['tn']
        independent=dict(counts)|{'rows':n+p,'recall':tp/p,'precision':tp/(tp+fp) if tp+fp else None,
            'accuracy':(tp+tn)/(n+p),'specificity':tn/n,'positive_rate':(tp+fp)/(n+p),
            'f1':2*tp/(2*tp+fp+fn),'fpr':fp/n,'balanced_accuracy':(tp/p+tn/n)/2}|auc(pooled(hists))
        check(row,independent)
        assert math.isclose(float(row['false_alarms_per_million_benign']),1e6*fp/n,rel_tol=1e-12)
        initial=histogram(row['initial_model'],'2018-02-16',1)
        assert optimum(initial)==int(row['initial_threshold_bin'])
        assert metrics(initial,int(row['initial_threshold_bin']))['fpr']<=.01
        result.append({'run':row['run'],'audit':'issued-window and pooled metrics; initial threshold optimum','windows':len(issued),'rows':n+p,'pass':True})
    for event in events:
        if not event.get('candidate_metrics'):continue
        hist=pooled([histogram(event['model'],day,1) for day in json.loads(event['calibration_days'])])
        threshold=int(event['threshold_bin']);assert optimum(hist)==threshold
        check(json.loads(event['candidate_metrics']),metrics(hist,threshold)|auc(hist))
        result.append({'run':event['run'],'audit':'candidate released-calibration metrics and threshold optimum','window':event['window'],'pass':True})
    csv_write(ROOT/'reports/phase12_metric_audit.csv',result)
    receipt={'status':'PASS','policy_scopes':len(rows),'checks':len(result),'unique_retrieved_histograms':len(HISTOGRAMS),
             'definitions':'Tie-grouped2048-bin step PR area; trapezoidal ROC area; counts at issued bin threshold; pooled integer confusion rates.',
             'cross_runtime_histograms_identical':True,'source':'actual retrieved private Kaggle outputs, no raw dataset downloaded'}
    (ROOT/'reports/phase12_validation/metric_audit.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()
