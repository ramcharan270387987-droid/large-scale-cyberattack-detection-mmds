"""Validate exact signatures and derive contrast and temporal support."""
from collections import Counter,defaultdict
from itertools import combinations
from hashlib import sha256
import json,math
from pathlib import Path
from src.patterns.metrics import association,contrast,emergence,jaccard
root=Path('reports/phase10_aggregates')
output=Path('reports/phase10_analysis');output.mkdir(exist_ok=True)

def save(name,data):
 (output/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

def complete_counts(rows):
 counts=defaultdict(Counter);totals=Counter()
 for row in rows:
  key=(row['source_day'],row['binary_label'],row['attack_family'])
  totals[key]+=row['count']
  for length in range(1,7):
   for pattern in combinations(sorted(row['items']),length):counts[pattern][key]+=row['count']
 return counts,totals

if __name__=='__main__':
 rows=json.loads((root/'A3.json').read_text());counts,totals=complete_counts(rows)
 assert sum(totals.values())==16232943
 attacks=sum(n for (_,label,_),n in totals.items() if label==1);benign=sum(totals.values())-attacks
 assert attacks==2748235
 patterns=sorted((p for p,c in counts.items() if sum(c.values())>=.05*16232943),key=lambda p:(-sum(counts[p].values()),p))
 assert len(patterns)==298
 contrast_rows=[];family_rows=[]
 for p in patterns:
  a=sum(n for (_,label,_),n in counts[p].items() if label==1);b=sum(counts[p].values())-a
  result=contrast(a,b,attacks,benign)
  result['enrichment']=result['attack_given_pattern']/(attacks/(attacks+benign))
  contrast_rows.append({'items':p,'attack_count':a,'benign_count':b,**result})
 for family in sorted({family for (_,label,family) in totals if label}):
  total=sum(n for (_,_,f),n in totals.items() if f==family)
  eligible=[]
  for p,c in counts.items():
   n=sum(n for (_,_,f),n in c.items() if f==family)
   if n>=100 and n/total>=.1:
    b=sum(n for (_,label,_),n in c.items() if label==0)
    other=sum(n for (_,label,f),n in c.items() if label==1 and f!=family)
    eligible.append({'items':p,'count':n,'family_total':total,'family_support':n/total,'benign_support':b/benign,'other_attack_support':other/(attacks-total)})
  eligible.sort(key=lambda r:(-r['count'],r['items']))
  family_rows.append({'family':family,'total':total,'eligible_patterns':len(eligible),'export':eligible[:500]})
 save('contrast',contrast_rows);save('families',family_rows)
 rules=json.load(open('reports/phase10_stageB/rules_0.05.json'))
 verified=[]
 def support(pattern):return sum(counts[tuple(sorted(pattern))].values())
 for rule in sorted(rules,key=lambda r:(sorted(r['antecedent']),sorted(r['consequent'])))[:20]:
  a,b=rule['antecedent'],rule['consequent'];m=association(support(set(a)|set(b)),support(a),support(b),16232943)
  assert all(math.isclose(m[k],rule[k],abs_tol=1e-12) for k in ('confidence','lift','support'))
  verified.append({'antecedent':a,'consequent':b,**m})
 save('direct_rule_verification',verified)
 # Fixed-reference B item definitions applied to the full retained B population.
 rows=json.loads((root/'B3.json').read_text());reference=[r for r in rows if r['split_rank']==0]
 ref_counts,ref_totals=complete_counts(reference);all_counts,all_totals=complete_counts(rows)
 ref_n=sum(ref_totals.values());days=sorted({key[0] for key in all_totals})
 chosen=sorted((p for p,c in ref_counts.items() if sum(c.values())/ref_n>=.05),key=lambda p:(-sum(ref_counts[p].values()),p))[:500]
 day_mining=[]
 union=set(chosen)
 for day in days:
  den=sum(n for (d,_,_),n in all_totals.items() if d==day)
  frequent=[(p,sum(n for (d,_,_),n in c.items() if d==day)) for p,c in all_counts.items()]
  frequent=sorted(((p,n) for p,n in frequent if n/den>=.05),key=lambda item:(-item[1],item[0]))
  union.update(p for p,_ in frequent[:500])
  day_mining.append({'day':day,'total':den,'frequent_patterns':len(frequent),'export':[{'items':p,'count':n} for p,n in frequent[:500]]})
 chosen=sorted(union)
 save('day_mining',day_mining)
 temporal=[];sets={day:set() for day in days}
 for pattern in chosen:
  ref=sum(ref_counts.get(pattern,{}).values())
  for day in days:
   n=sum(n for (d,_,_),n in all_totals.items() if d==day)
   count=sum(n for (d,_,_),n in all_counts[pattern].items() if d==day)
   if count/n>=.05:sets[day].add(pattern)
   conditional={}
   for label in (0,1):
    den=sum(n for (d,l,_),n in all_totals.items() if d==day and l==label)
    num=sum(n for (d,l,_),n in all_counts[pattern].items() if d==day and l==label)
    conditional[str(label)]=num/den if den else None
   temporal.append({'items':pattern,'day':day,'count':count,'total':n,'support':count/n,'reference_count':ref,'reference_total':ref_n,'conditional':conditional,**emergence(ref,count,ref_n,n)})
 save('temporal',temporal)
 save('similarity',[{'first':a,'second':b,'jaccard':jaccard(sets[a],sets[b])} for a in days for b in days])
 print('Validated 20 direct rules and derived contrast, family and fixed-reference temporal evidence')
