"""Independent confusion/AUC/calibration arithmetic, without fitting or test tuning."""
import json,math,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def metric(hist,cut):
    n=sum(v[0] for v in hist.values());p=sum(v[1] for v in hist.values());tp=sum(v[1] for k,v in hist.items() if k>=cut);fp=sum(v[0] for k,v in hist.items() if k>=cut);tn=n-fp;fn=p-tp;ratio=lambda a,b:a/b if b else None;pr=roc=0.;a=b=0;oldr=oldf=0.
    for k in sorted(hist,reverse=True):
        b+=hist[k][0];a+=hist[k][1]
        if p and n:
            recall=a/p;fpr=b/n;pr+=(recall-oldr)*a/(a+b);roc+=(fpr-oldf)*(recall+oldr)/2;oldr,oldf=recall,fpr
    return dict(tp=tp,fp=fp,tn=tn,fn=fn,rows=p+n,precision=ratio(tp,tp+fp),recall=ratio(tp,p),f1=ratio(2*tp,2*tp+fp+fn),accuracy=ratio(tp+tn,p+n),specificity=ratio(tn,n),balanced_accuracy=(tp/p+tn/n)/2 if p and n else None,fpr=ratio(fp,n),pr_auc=pr if p and n else None,roc_auc=roc if p and n else None)
def check(observed,expected):
    for k,v in expected.items():
        a=observed[k]
        if v is None:assert a is None,(k,a,v)
        else:assert a is not None and math.isclose(float(a),v,rel_tol=1e-11,abs_tol=1e-11),(k,a,v)
def validate():
    directory=ROOT/'reports/phase14_14C';models=json.loads((directory/'models.json').read_text());rows=json.loads((directory/'external_evaluation.json').read_text());assert len(models)==12 and len(rows)==64;assert {x['model'] for x in models}=={prefix+family for prefix in ('E2-B-common-','E3-chronological-','E3-grouped-') for family in ('LR','RF','majority','duration')};identities=set();supports={}
    for r in rows:
        identity=tuple(r[k] for k in ('model','evaluation_protocol','sensitivity','operating'));assert identity not in identities;identities.add(identity);h={int(k):v for k,v in r['score_histogram'].items()};check(r['metrics'],metric(h,r['threshold_bin']));m=r['metrics'];assert all(sum(x[k] for x in r['families'])==m[k] for k in ('tp','fp','tn','fn','rows'));support=(r['evaluation_protocol'],r['sensitivity']);assert supports.setdefault(support,m['rows'])==m['rows']
        if r['operating']=='fixed_half':assert r['threshold_bin']==1024
        else:assert r['threshold_bin']==next(x['threshold_bin'] for x in models if x['model']==r['model'])
    for model in models:
        h={int(k):v for k,v in model['calibration_histogram'].items()};points=[]
        for cut in range(2049):
            m=metric(h,cut)
            if m['fpr'] is not None and m['fpr']<=.01:points.append((m['recall'] if m['recall'] is not None else -1,m['precision'] if m['precision'] is not None else -1,-m['fpr'],cut))
        assert max(points)[-1]==model['threshold_bin'];check(model['validation_metrics'],{k:v for k,v in metric(h,model['threshold_bin']).items() if k in model['validation_metrics']});assert sum(model['training_support'].values())==model['training_rows'];assert model['saved']['reload_probe_rows']==3
    return dict(status='PASS',models=12,unique_evaluation_records=64,independent_confusion_auc_checks=64,validation_threshold_optima=12,matched_populations={str(k):v for k,v in supports.items()},test_threshold_tuning=False)
if __name__=='__main__':print(json.dumps(validate(),indent=2))
