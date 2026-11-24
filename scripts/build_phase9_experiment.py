"""Build a Phase 9 model experiment from the verified notebook bootstrap."""
import argparse
import json
from pathlib import Path
from build_phase8_notebook import build
from build_phase2_notebook import cell

ROOT = Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('--scenario',choices=['A','B','Web','Bot','Infiltration','DDoS'],default='A')
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
note=build('baseline','B')
sources={name:(ROOT/name).read_text() for name in ('src/ml/phase9_label_registry.py','src/ml/phase9_evaluation.py','src/ml/open_set_rejection.py','src/ml/train_multiclass.py')}
note['cells'].insert(-1,cell('code','phase9-source','sources = '+repr(sources)+'''\nfor relative, source in sources.items():
    target = project / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source)
'''))
note['cells'][-1]['source'] = [f"from src.ml.train_multiclass import run\nrun(project, Path('/kaggle/input'), Path('/kaggle/working/mmds_phase9'), {a.scenario!r})\n"]
a.output.write_text(json.dumps(note,indent=1)+'\n')
