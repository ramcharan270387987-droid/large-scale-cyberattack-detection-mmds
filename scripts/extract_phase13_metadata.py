"""Extract ordered preprocessing parameters from a verified private component bundle."""
import argparse,ast,base64,hashlib,json,lzma
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('notebook',type=Path);a=p.parse_args()
note=json.loads(a.notebook.read_text());code=''.join(next(c for c in note['cells'] if c['id']=='phase13-components')['source']);tree=ast.parse(code)
payload=next(n.args[0].value for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='b64decode' and isinstance(n.args[0],ast.Constant) and len(n.args[0].value)>100)
files=json.loads(lzma.decompress(base64.b64decode(payload)));models=json.loads((ROOT/'manifests/phase13_models.json').read_text())['components'];out=[]
for model in models:
    prefix=model['id']+'/';metadata=[]
    for name,encoded in files.items():
        relative=name.removeprefix(prefix)
        if name.startswith(prefix) and '/metadata/part-' in relative:
            data=base64.b64decode(encoded);assert hashlib.sha256(data).hexdigest()==model['sha256'][relative]
            value=json.loads(data);metadata.append(dict(file=relative,sha256=model['sha256'][relative],stage_class=value['class'],parameters=value.get('paramMap',{}),defaults=value.get('defaultParamMap',{})))
    imputer=next(r for r in metadata if r['stage_class'].endswith('ImputerModel'))
    out.append(dict(model=model['id'],feature_order=imputer['parameters']['inputCols'],stage_metadata=metadata))
(ROOT/'reports/phase13_components/preprocessing_metadata.json').write_text(json.dumps(out,indent=2)+'\n');print('Verified archived metadata for',len(out),'component pipelines')
