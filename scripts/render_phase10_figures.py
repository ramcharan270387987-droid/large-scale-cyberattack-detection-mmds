"""Render verified mining summaries without rerunning experiments."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path('reports');out=root/'figures';out.mkdir(exist_ok=True)
r=json.loads((root/'phase10_stageB/receipt.json').read_text())
s=r['summaries']
fig,axes=plt.subplots(1,3,figsize=(12,3.7),layout='constrained')
for ax,key,label in zip(axes,('itemsets','rules','seconds'),('Frequent itemsets','Association rules','Measured fit and itemset-count seconds')):
 ax.plot([x['support'] for x in s],[x[key] for x in s],'o-');ax.set(xlabel='Minimum support',ylabel=label)
fig.savefig(out/'phase10_support_sensitivity.png',dpi=150);fig.savefig(out/'phase10_support_sensitivity.svg');plt.close(fig)
primary=next(x for x in s if x['support']==.05)
fig,ax=plt.subplots(figsize=(6,3.5),layout='constrained');ax.bar(list(primary['lengths']),list(primary['lengths'].values()));ax.set(xlabel='Itemset length',ylabel='Frequent itemsets',title='Full-population six-feature FP-Growth at 5% support');fig.savefig(out/'phase10_itemset_lengths.png',dpi=150);fig.savefig(out/'phase10_itemset_lengths.svg');plt.close(fig)
rules=json.loads((root/'phase10_stageB/rules_0.05.json').read_text())
fig,ax=plt.subplots(figsize=(6,3.5),layout='constrained');ax.scatter([r['confidence'] for r in rules],[r['lift'] for r in rules],s=8,alpha=.4);ax.set(xlabel='Confidence',ylabel='Lift',title='Bounded primary rule export');fig.savefig(out/'phase10_confidence_lift.png',dpi=150);fig.savefig(out/'phase10_confidence_lift.svg');plt.close(fig)
