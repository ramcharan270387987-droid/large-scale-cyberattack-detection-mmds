"""Complete score curves, matched baseline comparison and descriptive persistence."""
import csv,json
from collections import Counter
from pathlib import Path
from datetime import date
from src.patterns.support import score
root=Path('reports');out=root/'phase10_detection'
policy=json.loads((out/'frozen.json').read_text());rows=json.loads((root/'phase10_aggregates/B3.json').read_text())
test=[dict(r,score=score(r['items'],policy['patterns'])) for r in rows if r['split_rank']==2]
pos=sum(r['count'] for r in test if r['binary_label']);neg=sum(r['count'] for r in test if not r['binary_label'])
hist=Counter()
for r in test:hist[r['score'],r['binary_label']]+=r['count']
tp=fp=0;last_fpr=last_tpr=0.;roc=pr=0.;last_recall=0.;last_precision=1.;curves=[]
for value in sorted({key[0] for key in hist},reverse=True):
 tp+=hist[value,1];fp+=hist[value,0];recall=tp/pos;fpr=fp/neg;precision=tp/(tp+fp)
 roc+=(fpr-last_fpr)*(recall+last_tpr)/2
 pr+=(recall-last_recall)*(precision+last_precision)/2
 curves.append(dict(threshold=value,tp=tp,fp=fp,recall=recall,fpr=fpr,precision=precision))
 last_fpr,last_tpr,last_recall,last_precision=fpr,recall,recall,precision
metrics=json.loads((out/'metrics.json').read_text());metrics.update(roc_auc=roc,pr_auc_trapezoidal_at_unique_scores=pr,false_alarms_per_million=metrics['fpr']*1e6,score_cost_note='Offline exact signature scoring; per-flow Spark latency unmeasured')
(out/'metrics.json').write_text(json.dumps(metrics,indent=2)+'\n');(out/'score_curves.json').write_text(json.dumps(curves,indent=2)+'\n')
comparison=[{'model':'pattern_only',**metrics}]
with (root/'phase4_metrics.csv').open() as f:
 for r in csv.DictReader(f):
  if r['protocol']=='B' and r['split']=='test' and int(r['rows'])==980109 and r['training_cohort']!='full_train_refit':comparison.append({'source':'Phase 4 frozen receipt',**r})
with (root/'phase8_model_comparison.csv').open() as f:
 for r in csv.DictReader(f):
  if r['population']=='B' and r['method'] in ('supervised','or'):comparison.append({'source':'Phase 8 frozen receipt',**r})
(out/'matched_comparison.json').write_text(json.dumps(comparison,indent=2)+'\n')
temporal=json.loads((root/'phase10_analysis/temporal.json').read_text());by_pattern={}
for r in temporal:by_pattern.setdefault(tuple(r['items']),[]).append(r)
persistence=[]
for pattern,values in by_pattern.items():
 present=sorted(r['day'] for r in values if r['count'])
 persistence.append({'items':pattern,'first_observed':present[0] if present else None,'last_observed':present[-1] if present else None,'captures_present':len(present),'frequent_captures':sum(r['support']>=.05 for r in values),'persistent':sum(r['support']>=.05 for r in values)>=8})
(root/'phase10_analysis/persistence.json').write_text(json.dumps(persistence,indent=2)+'\n')
days=sorted({r['day'] for r in temporal});(root/'phase10_analysis/capture_gaps.json').write_text(json.dumps([{'previous':a,'current':b,'calendar_days':(date.fromisoformat(b)-date.fromisoformat(a)).days} for a,b in zip(days,days[1:])],indent=2)+'\n')
print('Matched baseline rows',len(comparison),'ROC',roc,'PR trapezoid',pr)

# Standardize to the retained reference binary-class mixture only where both classes exist.
mixture=sum(r['count'] for r in rows if r['split_rank']==0 and r['binary_label']==1)/policy['training_rows']
standardized=[]
for r in temporal:
 conditional=r['conditional'];a,b=conditional['1'],conditional['0']
 standardized.append({'items':r['items'],'day':r['day'],'observed_support':r['support'],'reference_attack_mixture':mixture,'fixed_mixture_support':mixture*a+(1-mixture)*b if a is not None and b is not None else None})
(root/'phase10_analysis/standardized_support.json').write_text(json.dumps(standardized,indent=2)+'\n')
