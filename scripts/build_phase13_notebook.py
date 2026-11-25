"""Bundle checksum-pinned Phase 4 artifacts for exact explanation scoring."""
import argparse,json,base64,lzma
from pathlib import Path
from hashlib import sha256
from build_phase2_notebook import ROOT,cell
from build_phase8_notebook import build
from kaggle_web_api import download_archive

p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args()
phase4=json.loads((ROOT/'manifests/phase4_models.json').read_text());inventory=[];files={}
for protocol,version in (('A',1),('B',2)):
 ref=phase4['kernel_url'].split('/code/')[1]+'/'+str(version)
 with download_archive(ref,32*1024*1024) as archive:
  for model in phase4['protocols'][protocol]['models']:
   if model['training_cohort']!='group_sample':continue
   identifier=protocol+'-'+model['model'];prefix='mmds_phase4/models/'+Path(model['path']).name
   for name,expected in model['sha256'].items():
    content=archive.read(prefix+'/'+name)
    if sha256(content).hexdigest()!=expected:raise ValueError('Archived model identity differs')
    files[identifier+'/'+name]=base64.b64encode(content).decode()
   inventory.append(dict(id=identifier,protocol=protocol,algorithm=model['model'],version=ref,sha256=model['sha256']))
note=build('baseline','B');note['cells'][0]['source']=['# Phase 13 archived supervised explanations']
sources={name:(ROOT/name).read_text() for name in ('src/explainability/exact.py','src/explainability/run_archived.py')}
payload=base64.b64encode(lzma.compress(json.dumps(files).encode())).decode()
code=f'''import base64,lzma,json
archives=Path('/kaggle/temp/phase13/archives')
files=json.loads(lzma.decompress(base64.b64decode({payload!r})))
for relative,encoded in files.items():
 target=archives/relative
 target.parent.mkdir(parents=True,exist_ok=True)
 target.write_bytes(base64.b64decode(encoded))
for relative,source in {sources!r}.items():
 target=project/relative
 target.parent.mkdir(parents=True,exist_ok=True)
 target.write_text(source)
inventory={inventory!r}
'''
note['cells'].insert(-1,cell('code','phase13-source',code))
note['cells'][-1]['source']=["from src.explainability.run_archived import run\n","run(project,Path('/kaggle/input'),archives,inventory,Path('/kaggle/working/mmds_phase13'),Path('/kaggle/temp/phase13/spark'))\n"]
for c in note['cells']:
 if c['cell_type']=='code':compile(''.join(c['source']),c['id'],'exec')
a.output.write_text(json.dumps(note,indent=1)+'\n')
