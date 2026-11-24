"""Freeze training pattern choices and validation threshold before test aggregation."""
from collections import Counter
import json
import argparse
from pathlib import Path
from analyze_phase10_aggregates import complete_counts
from src.patterns.support import score,select_threshold
from src.patterns.metrics import contrast

parser=argparse.ArgumentParser();parser.add_argument('--configuration',choices=('B3','B5'),default='B3');args=parser.parse_args()
root=Path('reports/phase10_aggregates');out=Path('reports/phase10_detection') if args.configuration=='B3' else Path('reports/phase10_detection_B5');out.mkdir(exist_ok=True)
rows=json.loads((root/(args.configuration+'.json')).read_text())
train=[r for r in rows if r['split_rank']==0];validation=[r for r in rows if r['split_rank']==1]
counts,totals=complete_counts(train)
a=sum(n for (_,label,_),n in totals.items() if label==1);b=sum(totals.values())-a
candidates=[]
for pattern,support in counts.items():
 if len(pattern) not in (2,3) or sum(support.values()) < .05*sum(totals.values()):continue
 ac=sum(n for (_,label,_),n in support.items() if label==1);bc=sum(support.values())-ac
 enrichment=contrast(ac,bc,a,b)['support_ratio']
 if ac>=100 and enrichment is not None and enrichment>=2:candidates.append((enrichment,ac,pattern))
candidates.sort(key=lambda r:(-r[0],-r[1],r[2]))
selected=[]
for enrichment,ac,pattern in candidates:
 if any(set(old).issubset(pattern) and counts[old]==counts[pattern] for old in selected):continue
 selected.append(pattern)
 if len(selected)==20:break
calibration=[dict(r,score=score(r['items'],selected)) for r in validation]
threshold=select_threshold(calibration)
policy={'patterns':selected,'threshold':threshold,'validation_fpr_budget':.01,'discretization':args.configuration,'training_rows':sum(totals.values()),'selection':'training attack/benign support ratio, attack support and canonical ID'}
(out/'frozen.json').write_text(json.dumps(policy,indent=2)+'\n')
# Evaluation is accessed only after the policy is materialized.
results=[];families=Counter();family_totals=Counter();review=0
for r in rows:
 if r['split_rank']!=2:continue
 predicted=score(r['items'],selected)>=threshold
 results.append((r['binary_label'],predicted,r['count']))
 if r['binary_label']==1:
  family_totals[r['attack_family']]+=r['count'];families[r['attack_family']]+=predicted*r['count']
 review+=predicted*r['count']
c=Counter()
for label,predicted,n in results:c['tp' if label and predicted else 'fn' if label else 'fp' if predicted else 'tn']+=n
def div(n,d):return n/d if d else None
n=c.total();metrics={**c,'rows':n,'precision':div(c['tp'],c['tp']+c['fp']),'recall':div(c['tp'],c['tp']+c['fn']),'f1':div(2*c['tp'],2*c['tp']+c['fp']+c['fn']),'fpr':div(c['fp'],c['fp']+c['tn']),'review_rows':review,'coverage':1-review/n,'family_recall':{f:families[f]/v for f,v in family_totals.items()}}
assert n==980109
(out/'metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
print(metrics)
