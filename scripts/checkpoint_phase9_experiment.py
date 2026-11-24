"""Validate one retrieved stage and publish its compact checkpoint."""
import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
from src.ml.phase9_evaluation import multiclass

p=argparse.ArgumentParser()
p.add_argument('directory',type=Path)
a=p.parse_args()
s=json.loads((a.directory/'results/phase9_summary.json').read_text())
assert s['status']=='validated' and s['input']['rows']==16232943
scenario=s['scenario']
out=Path('reports/phase9_stages')/scenario
out.mkdir(parents=True,exist_ok=True)
source=a.directory/'results'
confusion=source/'phase9_family_confusion.csv'
if confusion.exists():
    rows=list(csv.DictReader(confusion.open()))
    actual,_=multiclass({(int(r['actual']),int(r['predicted'])):int(r['count']) for r in rows},range(len(s['classes'])))
    assert actual==s['test']
for name in source.glob('phase9_*.csv'):
    (out/name.name).write_bytes(name.read_bytes())
for name in source.glob('phase9_*frozen.json'):
    (out/name.name).write_bytes(name.read_bytes())
s['kernel_version']=int((a.directory/'version').read_text())
s['kernel_url']='https://www.kaggle.com/code/ramcharan2345/mmds-phase-9-multiclass-open-set-classification'
s['worker_status']='COMPLETE'
s['log_sha256']=sha256((a.directory/'terminal.json').read_bytes()).hexdigest()
s['source_sha256']=sha256((a.directory/'phase9_multiclass_open_set.ipynb').read_bytes()).hexdigest()
s['tables_sha256']={f.name:sha256(f.read_bytes()).hexdigest() for f in out.iterdir() if f.is_file()}
Path('manifests/phase9_'+scenario+'.json').write_text(json.dumps(s,indent=2)+'\n')
print('Validated compact stage',scenario,s['kernel_version'],s['test'])
