"""Derive independently count-based metrics from complete primary itemsets."""
import json,math
from pathlib import Path
from src.patterns.metrics import association
root=Path('reports/phase10_stageB')
items=json.loads((root/'items_0.05.json').read_text())
receipt=json.loads((root/'receipt.json').read_text())
assert len(items)==next(s['itemsets'] for s in receipt['summaries'] if s['support']==.05)
counts={frozenset(row['items']):row['count'] for row in items}
rows=[]
for rule in json.loads((root/'rules_0.05.json').read_text()):
 a,b=frozenset(rule['antecedent']),frozenset(rule['consequent'])
 joint=counts[a|b];metrics=association(joint,counts[a],counts[b],receipt['rows'])
 for key in ('confidence','lift','support'):
  assert math.isclose(metrics[key],rule[key],rel_tol=1e-12,abs_tol=1e-12)
 rows.append({'antecedent':sorted(a),'consequent':sorted(b),'joint_count':joint,'antecedent_count':counts[a],'consequent_count':counts[b],**metrics})
out=Path('reports/phase10_rule_validation');out.mkdir(exist_ok=True)
(out/'count_metrics.json').write_text(json.dumps(rows,indent=2)+'\n')
print('Validated metrics from itemset counts for',len(rows),'archived rules; direct transaction verification pending')
