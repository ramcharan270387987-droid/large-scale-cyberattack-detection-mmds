"""Build one sequential private Phase 12 historical execution stage."""
import argparse,json,subprocess,hashlib
from pathlib import Path
from build_phase8_notebook import build
from build_phase2_notebook import ROOT,cell

def build_stage(stage):
    note=build('baseline','B')
    sources={p.relative_to(ROOT).as_posix():p.read_text() for p in (ROOT/'src/adaptation').glob('*.py')}
    sources['configs/phase12_adaptation.yaml']=(ROOT/'configs/phase12_adaptation.yaml').read_text()
    sources['phase12_source.json']=json.dumps({'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'stage':stage,'sha256':{p:hashlib.sha256(v.encode()).hexdigest() for p,v in sources.items()}})
    note['cells'].insert(-1,cell('code','phase12-sources','sources='+repr(sources)+'''\nfor name, content in sources.items():
 target=project/name
 target.parent.mkdir(parents=True,exist_ok=True)
 target.write_text(content)
'''))
    note['cells'][-1]['source']=[f"from src.adaptation.historical import run\nrun(project,Path('/kaggle/input'),Path('/kaggle/working/mmds_phase12'),Path('/kaggle/temp/mmds_phase12'),{stage!r})\n"]
    note['cells'][0]['source']=[f'# Phase12 {stage}, private CPU, retrospective adaptive research\n']
    for c in note['cells']:
        if c['cell_type']=='code':compile(''.join(c['source']),c['id'],'exec')
    return note
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['12C','12D','12E'],required=True);p.add_argument('--output',type=Path,default=ROOT/'notebooks/phase12_adaptive_learning.ipynb');a=p.parse_args()
    a.output.write_text(json.dumps(build_stage(a.stage),indent=1)+'\n')
