"""Verify durable private synthetic models after actual Kaggle output retrieval."""
import argparse,hashlib,json,pickle,time,zipfile
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('archive',type=Path);p.add_argument('--kernel-version',required=True);a=p.parse_args();start=time.monotonic()
    with zipfile.ZipFile(a.archive) as archive:
        models=json.loads(archive.read('models.json'))
        probes=np.vstack([np.zeros(18),np.arange(18),np.full(18,np.nan)])
        for meta in models:
            payload=archive.read(meta['model']+'.pkl')
            assert hashlib.sha256(payload).hexdigest()==meta['sha256']
            loaded=pickle.loads(payload)
            assert loaded.predict_proba(probes).tolist()==meta['reload_probe']
    receipt={'status':'PASS','kernel_version':a.kernel_version,'private_output':'phase12_synthetic_models.zip',
             'sha256':hashlib.sha256(a.archive.read_bytes()).hexdigest(),'models':len(models),'independent_retrieved_reload':True,
             'registered_probes_identical':True,'seconds':time.monotonic()-start}
    (ROOT/'reports/phase12_validation/synthetic_private_retrieval.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
