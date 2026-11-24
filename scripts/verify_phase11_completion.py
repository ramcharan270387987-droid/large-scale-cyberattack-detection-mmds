"""Read-only validation of the completed Phase 11 evidence package."""
import csv
from hashlib import sha256
import json
from pathlib import Path
import sys
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]

def check(condition,message):
    if not condition:raise ValueError(message)


def verify(require_complete=True):
    manifest=json.loads((ROOT/'manifests/phase11_experiments.json').read_text())
    if require_complete:
        check(manifest['complete'] and not manifest['pending'],'Phase 11 gate remains open')
        check(all(s['status']=='COMPLETE AND VERIFIED' for s in manifest['stages'].values()),'A required stage is unfinished')
    check(not manifest['phase12_started'],'Phase 12 was started')
    receipt=json.loads((ROOT/'reports/phase11_finalization/receipt.json').read_text())
    for name,digest in receipt['table_sha256'].items():
        path=ROOT/'reports/phase11_finalization'/name
        check(sha256(path.read_bytes()).hexdigest()==digest,f'Table hash mismatch {name}')
        with path.open(newline='') as file:rows=list(csv.DictReader(file))
        check(len(rows)==receipt['tables'][name],f'Table row mismatch {name}')
    for name,digest in receipt['input_sha256'].items():
        check(sha256((ROOT/name).read_bytes()).hexdigest()==digest,f'Input changed {name}')
    for row in csv.DictReader((ROOT/'reports/phase11_finalization/association_pairs.csv').open()):
        check(int(row['label_release_batch'])<=int(row['analysis_asof_batch']),'Unavailable labels entered association analysis')
    tests=json.loads((ROOT/'reports/phase11_validation/final_tests.json').read_text())
    check(tests['status']=='PASS' and tests['research_tests']+tests['dashboard_tests']==tests['total_regression_tests'],'Test receipt inconsistent')
    browser=json.loads((ROOT/'reports/phase11_validation/browser_validation.json').read_text())
    check(browser['status']=='PASS' and not browser['page_errors'] and not browser['http_errors'],'Browser errors remain')
    registry=json.loads((ROOT/'manifests/phase11_detectors.json').read_text())
    check(len(registry['detectors'])==6 and not registry['phase12_started'],'Detector registry invalid')
    for section in ('artifacts_sha256','sources_sha256'):
        for name,digest in manifest.get(section,{}).items():
            check(sha256((ROOT/name).read_bytes()).hexdigest()==digest,f'Evidence hash mismatch {name}')
    figures=list((ROOT/'reports/figures').glob('phase11_*.png'))
    for figure in figures:
        with Image.open(figure) as image:image.verify()
        check(figure.name in manifest['figure_sources'],f'Figure source mapping missing {figure.name}')
    return {'status':'PASS','tables':len(receipt['tables']),'figures':len(figures),'regression_tests':tests['total_regression_tests'],'phase12_started':False}


if __name__=='__main__':
    print(json.dumps(verify('--checkpoint' not in sys.argv)))
