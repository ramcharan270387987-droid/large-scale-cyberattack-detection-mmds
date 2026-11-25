"""Bundle selected novelty, hybrid, family and activated adaptive artifacts."""
import argparse,json,base64,lzma,csv
from collections import defaultdict
from pathlib import Path
from hashlib import sha256
from build_phase2_notebook import ROOT,cell
from kaggle_web_api import download_archive
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
note=json.loads(a.source.read_text());note['cells'][0]['source']=['# Phase 13 novelty, rejection and adaptive explanation components']
read=lambda name:json.loads((ROOT/name).read_text())
components=[];requests=defaultdict(list);files={}
def register(identifier,kind,protocol,version,prefix,hashes,metadata):
 entry=dict(id=identifier,kind=kind,protocol=protocol,version=version,sha256=hashes,metadata=metadata)
 components.append(entry);requests[version].append((entry,prefix))
phase5=read('manifests/phase5_clustering_models.json');phase8=read('manifests/phase8_models.json')
for protocol,version in (('B',2),('C',3)):
 model=phase5['experiments'][protocol]
 register('novelty-'+protocol,'novelty',protocol,phase5['kernel_url'].split('/code/')[1]+'/'+str(version),'mmds_phase5/model',model['model']['sha256'],{'threshold':model['calibration']['cutoffs']['0.99']})
 model=phase8['populations'][protocol];saved=model['saved_pipelines'][model['base']]
 register('hybrid-'+protocol,'hybrid',protocol,phase8['kernel_url'].split('/code/')[1]+'/'+str(model['kernel_version']),'mmds_phase8/'+saved['artifact'],saved['sha256'],model)
for protocol in ('A','B'):
 model=read('manifests/phase9_'+protocol+'.json')
 threshold=read('reports/phase9_stages/B/phase9_rejection_frozen.json')['maximum']['0.05'] if protocol=='B' else None
 register('family-'+protocol,'family',protocol,model['kernel_url'].split('/code/')[1]+'/'+str(model['kernel_version']),'mmds_phase9/'+model['registry']['artifact'],model['registry']['sha256'],{'classes':model['classes'],'threshold_bin':threshold})
registry=read('manifests/phase12_models.json')['historical_models'];windows=list(csv.DictReader((ROOT/'reports/phase12_prequential_metrics.csv').open()))
initial=next(r['initial_model'] for r in csv.DictReader((ROOT/'reports/phase12_policy_comparison.csv').open()) if r['backend']=='E-LR-seed23013-sample125-weight1' and r['policy']=='P0' and r['delay']=='0')
selected={initial:['P0','P6']}
for policy,backend in (('P1','E-LR-seed23013-sample125-weight1'),('P2','E-LR-seed23013-sample125-weight1'),('P4','E-LR-seed23013-sample125-weight1'),('P1','E-RF-seed23013-sample125-weight1')):
 candidates=[r for r in windows if r['run'].startswith(backend+'-'+policy+'-d0-b3-p2-s2-c2-m200-')]
 if not candidates:continue
 first=candidates[0]['model'];activated=next((r for r in candidates if r['model']!=first),None)
 if activated:selected.setdefault(activated['model'],[]).append(policy+'-'+backend.split('-')[1])
for identifier,policies in selected.items():
 model=next(m for m in registry if m['model']==identifier)
 parts=model['artifact'].split('/');version='/'.join(parts[:3]);prefix='mmds_phase12/'+'/'.join(parts[3:])
 register('adaptive-'+identifier,'adaptive','E',version,prefix,model['component_sha256'],model|{'selected_policies':policies,'frozen_initial':identifier==initial})
for version,entries in requests.items():
 # Reuse locally verified Phase 12 archives where present.
 local={}
 if 'phase-12' in version:
  for entry,prefix in entries:
   candidates=list(Path('/tmp/mmds-phase12').glob('*/results/'+prefix))
   if candidates:local[entry['id']]=candidates[0]
 missing=[(entry,prefix) for entry,prefix in entries if entry['id'] not in local]
 archive=download_archive(version,64*1024*1024) if missing else None
 context=archive if archive is not None else __import__('contextlib').nullcontext()
 with context as opened:
  for entry,prefix in entries:
   for name,expected in entry['sha256'].items():
    content=(local[entry['id']]/name).read_bytes() if entry['id'] in local else opened.read(prefix+'/'+name)
    if sha256(content).hexdigest()!=expected:raise ValueError('Component identity mismatch')
    files[entry['id']+'/'+name]=base64.b64encode(content).decode()
sources={name:(ROOT/name).read_text() for name in ('src/explainability/components.py','src/explainability/run_components.py')}
payload=base64.b64encode(lzma.compress(json.dumps(files).encode())).decode()
code=f'''extra=json.loads(lzma.decompress(base64.b64decode({payload!r})))
for name,encoded in extra.items():
 target=archives/name
 target.parent.mkdir(parents=True,exist_ok=True)
 target.write_bytes(base64.b64decode(encoded))
for name,source in {sources!r}.items():
 target=project/name
 target.parent.mkdir(parents=True,exist_ok=True)
 target.write_text(source)
components={components!r}
'''
note['cells'].insert(-1,cell('code','phase13-components',code))
note['cells'][-1]['source']=["from src.explainability.run_components import run\n","run(project,Path('/kaggle/input'),archives,components,Path('/kaggle/working/mmds_phase13'),Path('/kaggle/temp/phase13/spark'))\n"]
for c in note['cells']:
 if c['cell_type']=='code':compile(''.join(c['source']),c['id'],'exec')
a.output.write_text(json.dumps(note,indent=1)+'\n')
