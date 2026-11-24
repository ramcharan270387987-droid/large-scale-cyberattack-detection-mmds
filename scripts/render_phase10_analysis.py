"""Publication figures from exact verified aggregate counts."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path('reports');out=root/'figures'
def save(fig,name):
 for suffix in ('png','svg'):fig.savefig(out/('phase10_'+name+'.'+suffix),dpi=150,bbox_inches='tight')
 plt.close(fig)
contrast=json.loads((root/'phase10_analysis/contrast.json').read_text());selected=sorted(contrast,key=lambda r:(-r['enrichment'],r['items']))[:12]
fig,ax=plt.subplots(figsize=(8,5));labels=[' & '.join(r['items']) for r in selected];y=np.arange(len(labels));ax.barh(y-.15,[r['attack_support'] for r in selected],.3,label='Attack');ax.barh(y+.15,[r['benign_support'] for r in selected],.3,label='Benign');ax.set(yticks=y,yticklabels=labels,xlabel='Class-conditional support');ax.legend();save(fig,'attack_benign_contrast')
rows=json.loads((root/'phase10_analysis/temporal.json').read_text());days=sorted({r['day'] for r in rows});patterns=sorted({tuple(r['items']) for r in rows})[:30];lookup={(tuple(r['items']),r['day']):r for r in rows};matrix=[[lookup[p,d]['support'] for d in days] for p in patterns]
fig,ax=plt.subplots(figsize=(9,9));im=ax.imshow(matrix,aspect='auto',cmap='Blues');ax.set(xticks=range(len(days)),xticklabels=[d[5:] for d in days],yticks=range(len(patterns)),yticklabels=[' & '.join(p) for p in patterns],title='First 30 canonical frozen-definition patterns');ax.tick_params(axis='y',labelsize=6);fig.colorbar(im,ax=ax,label='Daily support');save(fig,'daily_support')
sim=json.loads((root/'phase10_analysis/similarity.json').read_text());lookup={(r['first'],r['second']):r['jaccard'] for r in sim};fig,ax=plt.subplots(figsize=(6,5));im=ax.imshow([[lookup[a,b] if lookup[a,b] is not None else np.nan for b in days] for a in days],vmin=0,vmax=1);ax.set(xticks=range(len(days)),xticklabels=[d[5:] for d in days],yticks=range(len(days)),yticklabels=[d[5:] for d in days]);ax.tick_params(axis='x',rotation=45);fig.colorbar(im,ax=ax,label='Jaccard similarity');save(fig,'similarity')
sensitivity=json.loads((root/'phase10_analysis/discretization_duplicate_sensitivity.json').read_text());fig,ax=plt.subplots(figsize=(6,4))
for config in ('A3','A5','domain'):
 points=[r for r in sensitivity if r['configuration']==config];ax.plot([r['support'] for r in points],[r['flow_frequent_patterns'] for r in points],'o-',label=config)
ax.set(xlabel='Minimum support',ylabel='Frequent itemsets');ax.legend();save(fig,'bin_sensitivity')
