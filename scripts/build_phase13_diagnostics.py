"""Extend verified component bundle with prespecified failure/shift diagnostics."""
import argparse,json
from pathlib import Path
from build_phase2_notebook import ROOT,cell
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
n=json.loads(a.source.read_text());sources={name:(ROOT/name).read_text() for name in ('src/explainability/run_diagnostics.py',)};bounds=json.loads((ROOT/'reports/phase13_permutation/feature_distributions.json').read_text())
n['cells'].insert(-1,cell('code','phase13-diagnostics-source',f'sources={sources!r}\nfor name,source in sources.items():\n target=project/name\n target.parent.mkdir(parents=True,exist_ok=True)\n target.write_text(source)\nbounds={bounds!r}\n'))
n['cells'][-1]['source']=["from src.explainability.run_diagnostics import run\n","run(project,Path('/kaggle/input'),archives,components,bounds,Path('/kaggle/working/mmds_phase13'),Path('/kaggle/temp/phase13/spark'))\n"]
for c in n['cells']:
 if c['cell_type']=='code':compile(''.join(c['source']),c['id'],'exec')
a.output.write_text(json.dumps(n,indent=1)+'\n')
