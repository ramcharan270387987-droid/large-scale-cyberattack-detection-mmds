"""Build the private bounded Phase 11 synthetic experiment notebook."""
import json
from pathlib import Path
from build_phase8_notebook import build
from build_phase2_notebook import cell,ROOT

note=build('baseline','B')
sources={p.relative_to(ROOT).as_posix():p.read_text() for p in (ROOT/'src/drift').glob('*.py')}
note['cells'].insert(-1,cell('code','phase11-sources',"subprocess.run([sys.executable, '-m', 'pip', 'install', 'river==0.22.0'], check=True)\n"+'sources = '+repr(sources)+'''\nfor name, content in sources.items():
    target=project/name
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(content)
'''))
note['cells'][-1]['source']=["from src.drift.run_synthetic import run\nrun(Path('/kaggle/working/mmds_phase11_synthetic'))\n"]
for c in note['cells']:
 if c['cell_type']=='code':compile(''.join(c['source']),c['id'],'exec')
(ROOT/'notebooks/phase11_advanced_drift.ipynb').write_text(json.dumps(note,indent=1)+'\n')
