"""Prepare a sequential Kaggle stage; refuse duplicate running/completed submissions."""
import argparse,csv,io,json,subprocess,sys
from pathlib import Path
from build_phase12_notebook import build_stage
ROOT=Path(__file__).resolve().parents[1]
SLUGS={'12C':'mmds-phase-12-adaptive-learning-model-refresh','12D':'mmds-phase-12-drift-threshold-adaptation','12E':'mmds-phase-12-delayed-label-robustness'}

def api(*args):
    return subprocess.run([sys.executable,str(ROOT/'scripts/kaggle_web_api.py'),*args],check=True,capture_output=True,text=True).stdout

def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['12D','12E']);p.add_argument('directory',type=Path);a=p.parse_args()
    slug=SLUGS[a.stage];ref='ramcharan2345/'+slug
    existing=list(csv.DictReader(io.StringIO(api('kernels','list','--mine','--page-size','100','--csv'))))
    if any(row.get('ref')==ref for row in existing):
        status=api('kernels','status',ref)
        raise SystemExit('Existing stage requires explicit receipt review before resubmission: '+status.strip())
    frozen=json.loads((ROOT/'manifests/phase12_frozen_reference.json').read_text())
    a.directory.mkdir(parents=True,exist_ok=True)
    (a.directory/'phase12_adaptive_learning.ipynb').write_text(json.dumps(build_stage(a.stage),indent=1)+'\n')
    metadata={'id':ref,'title':'MMDS Phase12 '+a.stage+' Adaptive Research','code_file':'phase12_adaptive_learning.ipynb',
        'language':'python','kernel_type':'notebook','is_private':True,'enable_gpu':False,'enable_tpu':False,'enable_internet':True,
        'dataset_sources':[],'competition_sources':[],
        'kernel_sources':['ramcharan2345/mmds-phase-2-spark-data-engineering/1',frozen['kernel_version']]}
    (a.directory/'kernel-metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(api('kernels','push','-p',str(a.directory)),end='')
if __name__=='__main__':main()
