"""Run compact historical replay and robustness evidence on private Kaggle CPU."""
import json
from pathlib import Path
from build_phase8_notebook import build
from build_phase2_notebook import cell,ROOT

note=build('baseline','B')
sources={p.relative_to(ROOT).as_posix():p.read_text() for p in (ROOT/'src/drift').glob('*.py')}
for name in ('reports/phase6_window_metrics.csv','reports/phase6_shift_metrics.csv','reports/phase6_replay_batches.csv','reports/phase11_synthetic/alerts.csv','reports/phase11_synthetic/frozen.json'):
 sources[name]=(ROOT/name).read_text()
note['cells'].insert(-1,cell('code','phase11-history',"subprocess.run([sys.executable, '-m', 'pip', 'install', 'river==0.22.0'], check=True)\n"+'sources='+repr(sources)+'''\nfor name, content in sources.items():
 target=project/name
 target.parent.mkdir(parents=True,exist_ok=True)
 target.write_text(content)
'''))
note['cells'][-1]['source']=["from src.drift.historical_monitoring import run as history\nfrom src.drift.robustness import run as robustness\nhistory(project, Path('/kaggle/working/mmds_phase11_historical'))\nrobustness(project/'reports/phase11_synthetic',Path('/kaggle/working/mmds_phase11_robustness'))\n"]
for c in note['cells']:
 if c['cell_type']=='code':compile(''.join(c['source']),c['id'],'exec')
(ROOT/'notebooks/phase11_historical_robustness.ipynb').write_text(json.dumps(note,indent=1)+'\n')
