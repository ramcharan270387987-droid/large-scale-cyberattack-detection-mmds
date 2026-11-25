"""Record a verified stage without marking later stages complete."""
import argparse,json,hashlib,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['12C','12D','12E']);p.add_argument('--version',required=True);a=p.parse_args()
    prefix=ROOT/'reports'/f'phase12_{a.stage}';receipt=json.loads((prefix/'receipt.json').read_text());retrieval=json.loads((prefix/'retrieval.json').read_text())
    assert receipt['status']=='validated' and retrieval['status']=='COMPLETE' and retrieval['kernel_version']==a.version
    assert receipt['retained_rows']==16232943 and not any(receipt['cross_role_groups'].values())
    m=json.loads((ROOT/'manifests/phase12_experiments.json').read_text())
    m.setdefault('historical_stages',{})[a.stage]={'kernel_version':a.version,'status':'COMPLETE','runs':receipt['runs'],'models_verified':retrieval['models_verified'],
       'source_commit':receipt['source_commit'],'summary_sha256':retrieval['summary_sha256'],'elapsed_seconds':receipt['elapsed_seconds'],
       'retained_rows':receipt['retained_rows'],'physical_fits':receipt['physical_fits']}
    m.update(stage=a.stage,next_stage={'12C':'12D','12D':'12E','12E':'12F'}[a.stage],historical_executed=True,complete=False)
    (ROOT/'manifests/phase12_experiments.json').write_text(json.dumps(m,indent=2)+'\n')
    if a.stage=='12C':
        policies=list(csv.DictReader((prefix/'policy_comparison.csv').open()))
        initial=next(row['initial_model'] for row in policies if row['policy']=='P0')
        reference={'kernel_version':a.version,'initial_model':initial,'summary_sha256':retrieval['summary_sha256']}
        (ROOT/'manifests/phase12_frozen_reference.json').write_text(json.dumps(reference,indent=2)+'\n')
    print('VERIFIED_STAGE',a.stage,a.version)
if __name__=='__main__':main()
