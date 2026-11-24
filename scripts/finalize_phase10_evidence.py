"""Reconcile Phase 10 sufficient counts and complete descriptive sensitivity."""
from collections import Counter,defaultdict
from hashlib import sha256
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def read(path):return json.loads((ROOT/path).read_text())
def save(path,data):(ROOT/path).write_text(json.dumps(data,indent=2)+'\n')

stage=read('reports/phase10_stageB/receipt.json')
assert stage['rows']==16232943
assert next(s for s in stage['summaries'] if s['support']==.05)['itemsets']==298
for variant in ('A3','A5','domain'):
 rows=read('reports/phase10_aggregates/'+variant+'.json')
 assert sum(r['count'] for r in rows)==16232943
 assert all(len(r['items'])==len(set(r['items']))==6 for r in rows)
for variant in ('B3','B5'):
 rows=read('reports/phase10_aggregates/'+variant+'.json')
 for rank,n in [(0,13191622),(1,1151256),(2,980109)]:
  assert sum(r['count'] for r in rows if r['split_rank']==rank)==n
for folder in ('phase10_detection','phase10_detection_B5'):
 m=read('reports/'+folder+'/metrics.json')
 tp,tn,fp,fn=[m.get(k,0) for k in ('tp','tn','fp','fn')]
 assert tp+tn+fp+fn==m['rows']==980109
 assert abs(m['fpr']-fp/(fp+tn))<1e-12
 assert abs(m['recall']-tp/(tp+fn))<1e-12
 assert len(read('reports/'+folder+'/frozen.json')['patterns'])==20
rows=read('reports/phase10_analysis/temporal.json')
by_day=defaultdict(dict);by_pattern=defaultdict(list)
for r in rows:
 assert abs(r['support']-r['count']/r['total'])<1e-12
 by_day[r['day']][tuple(r['items'])]=r['support'] if r['support']>=.05 else 0.
 by_pattern[tuple(r['items'])].append(r)
sim=read('reports/phase10_analysis/similarity.json')
for r in sim:
 a,b=by_day[r['first']],by_day[r['second']]
 denominator=sum(max(a[p],b[p]) for p in a)
 r['support_weighted_jaccard']=sum(min(a[p],b[p]) for p in a)/denominator if denominator else None
save('reports/phase10_analysis/similarity.json',sim)
ranges=[]
for pattern,values in by_pattern.items():
 n=sum(r['total'] for r in values);matches=sum(r['count'] for r in values)
 leave=[(matches-r['count'])/(n-r['total']) for r in values]
 ranges.append({'items':pattern,'pooled_support':matches/n,'leave_one_capture_out_min':min(leave),'leave_one_capture_out_max':max(leave),'capture_count':len(values),'interpretation':'Descriptive capture deletion range'})
save('reports/phase10_analysis/capture_sensitivity.json',ranges)
print('PASS transactions, split totals, frozen detection, temporal support and capture sensitivity')
