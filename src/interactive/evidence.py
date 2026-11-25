"""Immutable allowlisted aggregate loading and source verification."""
import json,hashlib,io
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
def catalog():return json.loads((ROOT/'manifests/phase15_evidence.json').read_text())
def load(entry):
    path=ROOT/entry['path'];data=path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=entry['sha256']:raise ValueError('Research evidence checksum mismatch')
    if entry['format']=='csv':return pd.read_csv(io.BytesIO(data))
    data=json.loads(data)
    if isinstance(data,list) and all(isinstance(x,dict) for x in data):return pd.json_normalize(data)
    if isinstance(data,dict):
        for key in ('rules','itemsets','summaries','results','rows'):
            if isinstance(data.get(key),list) and data[key] and isinstance(data[key][0],dict):return pd.json_normalize(data[key])
        return pd.DataFrame([{'field':k,'value':json.dumps(v,ensure_ascii=False)} for k,v in data.items()])
    return pd.DataFrame({'value':data if isinstance(data,list) else [data]})
def models():return json.loads((ROOT/'manifests/phase15_models.json').read_text())['models']
