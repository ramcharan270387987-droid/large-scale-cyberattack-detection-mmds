"""Freeze public Phase15 runtime/model/evidence with no circular receipt hash."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=ROOT/'manifests/phase15_experiments.json';m=json.loads(p.read_text());paths=[ROOT/'README.md',ROOT/'dashboard/advanced_app.py',ROOT/'dashboard/data/phase15_demo.csv',ROOT/'reports/phase15_results.md']
    for pattern in ('docs/phase15*','dashboard/models/phase15*','src/interactive/*.py','scripts/*phase15*.py','tests/test_phase15*.py','manifests/phase15*.json','reports/phase15_validation/*'):paths.extend(ROOT.glob(pattern))
    paths=[x for x in paths if x.is_file() and x!=p and x.name!='acceptance.json'];m['evidence_sha256']={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(set(paths))};m['complete']=False;m['stages']['15E']['status']='verification_pending';p.write_text(json.dumps(m,indent=2)+'\n');print('Frozen',len(m['evidence_sha256']),'public artifacts')
if __name__=='__main__':main()
