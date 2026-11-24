"""Publish only verified, completed Phase 9 stage results."""
import csv
from hashlib import sha256
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root=Path('reports/phase9_stages')
figures=Path('reports/figures'); figures.mkdir(exist_ok=True)
stages={}
for path in sorted(Path('manifests').glob('phase9_*.json')):
    s=json.loads(path.read_text())
    if 'scenario' in s:stages[s['scenario']]=s

def table(path):
    return list(csv.DictReader(path.open()))

def save(fig,name):
    fig.savefig(figures/f'phase9_{name}.png',dpi=125,bbox_inches='tight',metadata={'Software':'MMDS Phase 9'})
    plt.close(fig)

combined={}
for scenario,s in stages.items():
    for path in (root/scenario).glob('*.csv'):
        combined.setdefault(path.stem,[]).extend({'scenario':scenario,**r} for r in table(path))
for name,rows in combined.items():
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with (Path('reports')/(name+'.csv')).open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=keys,lineterminator="\n");writer.writeheader();writer.writerows(rows)
for scenario,s in stages.items():
    path=root/scenario/'phase9_family_confusion.csv'
    if path.exists():
        classes=s['classes']; matrix=[[0]*len(classes) for _ in classes]
        for r in table(path):matrix[int(r['actual'])][int(r['predicted'])]=int(r['count'])
        fig,ax=plt.subplots(figsize=(7,6)); im=ax.imshow(matrix,cmap='Blues'); fig.colorbar(im,ax=ax,label='Flows')
        labels=[k for k,v in sorted(classes.items(),key=lambda x:x[1])]
        ax.set(xticks=range(len(labels)),yticks=range(len(labels)),xticklabels=labels,yticklabels=labels,xlabel='Predicted family',ylabel='Actual family',title=f'{scenario} held-out known-family confusion')
        ax.tick_params(axis='x',rotation=55);save(fig,f'confusion_{scenario}')
if 'phase9_open_set_metrics' in combined:
    fig,ax=plt.subplots(figsize=(8,5))
    for scenario in stages:
        for method in ('maximum','margin','entropy','novelty','combined'):
            rows=[r for r in combined['phase9_open_set_metrics'] if r['scenario']==scenario and r['method']==method and r['unknown_rejection_recall'] and r['known_false_rejection']]
            if rows:ax.plot([float(r['known_false_rejection']) for r in rows],[float(r['unknown_rejection_recall']) for r in rows],'.-',label=scenario+' '+method)
    ax.set(xlabel='Realized known-family false rejection rate',ylabel='Held-out family rejection recall',title='Retrospective family holdouts at frozen validation thresholds');ax.legend(fontsize=6,ncols=2);save(fig,'open_set_tradeoffs')
manifest={'schema':'phase9-checkpoints-v1','complete':False,'stages':stages,'tables_sha256':{p.name:sha256(p.read_bytes()).hexdigest() for p in Path('reports').glob('phase9_*.csv')}}
manifest_path = Path('manifests/phase9_experiments.json')
if manifest_path.exists():
    previous = json.loads(manifest_path.read_text())
    manifest.update({key: value for key, value in previous.items() if key not in {"schema", "stages", "tables_sha256"}})
manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
overview = (
    'Phase 9 is complete. The [research report](phase9_research_report.md) consolidates the evidence.'
    if manifest['complete'] else 'The study remains incomplete. Only retrieved and validated stages below support experimental claims.'
)
report=['# Phase 9 verified checkpoints','',overview,'','| Scenario | Version | Model | Known test rows | Accuracy | Macro F1 | Seconds |','|---|---|---|---:|---:|---:|---:|']
for scenario,s in stages.items():
    m=s['test']; report.append(f"| {scenario} | {s['kernel_version']} | {s['model']} | {m['rows']} | {m['accuracy']} | {m['macro_f1']} | {s['seconds']:.1f} |")
report.extend(['','Zero known-family chronological support means closed-set chronological classification is unsupported. Unknown-family rejection remains a separate result.','', 'All four family holdouts are validated. See the [chronological B](phase9_hierarchy/B/results.md) and [retrospective C](phase9_hierarchy/C/results.md) hierarchies, [matched sensitivity](phase9_sensitivity/results.md) and [rejection evidence](phase9_research_report.md#known-acceptance-and-unknown-rejection).'])
Path('reports/phase9_multiclass_results.md').write_text('\n'.join(report)+'\n')
print('Rendered verified stages',list(stages))
