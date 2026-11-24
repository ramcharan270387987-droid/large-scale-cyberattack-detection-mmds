"""Exact weighted support sensitivity from verified complete signatures."""
from collections import Counter
from itertools import combinations
import json
from pathlib import Path
root=Path('reports/phase10_aggregates');out=Path('reports/phase10_analysis');summary=[]
for config in ('A3','A5','domain'):
 rows=json.loads((root/(config+'.json')).read_text());flow=Counter();groups=Counter();total=sum(r['count'] for r in rows);group_total=sum(r.get('group_weight',0) for r in rows)
 for row in rows:
  for length in range(1,7):
   for p in combinations(sorted(row['items']),length):
    flow[p]+=row['count'];groups[p]+=row.get('group_weight',0)
 for support in (.1,.05,.02,.01):
  a={p for p,n in flow.items() if n/total>=support}
  b={p for p,n in groups.items() if group_total and n/group_total>=support}
  summary.append({'configuration':config,'support':support,'flow_rows':total,'predictor_groups':group_total if group_total else None,'flow_frequent_patterns':len(a),'group_frequent_patterns':len(b) if group_total else None,'jaccard':len(a&b)/len(a|b) if group_total and a|b else None})
(out/'discretization_duplicate_sensitivity.json').write_text(json.dumps(summary,indent=2)+'\n')
print(summary)
