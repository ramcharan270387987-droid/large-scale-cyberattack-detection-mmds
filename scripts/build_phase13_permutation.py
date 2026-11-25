"""Extend the exact archived model bundle for the prespecified permutation stage."""
import argparse,json
from pathlib import Path
from build_phase2_notebook import ROOT,cell
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
note=json.loads(a.source.read_text());note['cells'][0]['source']=['# Phase 13 matched permutation importance']
sources={name:(ROOT/name).read_text() for name in ('src/explainability/permutation.py','src/explainability/run_permutation.py','src/explainability/sampling.py')}
note['cells'].insert(-1,cell('code','phase13-permutation-source',f'sources={sources!r}\nfor name,source in sources.items():\n target=project/name\n target.parent.mkdir(parents=True,exist_ok=True)\n target.write_text(source)\n'))
note['cells'][-1]['source']=["from src.explainability.run_permutation import run\n","run(project,Path('/kaggle/input'),archives,inventory,Path('/kaggle/working/mmds_phase13'),Path('/kaggle/temp/phase13/spark'))\n"]
for c in note['cells']:
 if c['cell_type']=='code':compile(''.join(c['source']),c['id'],'exec')
a.output.write_text(json.dumps(note,indent=1)+'\n')
