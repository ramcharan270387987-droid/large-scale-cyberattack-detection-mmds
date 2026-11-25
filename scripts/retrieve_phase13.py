"""Retrieve version-pinned compact evidence and terminal logs from private Kaggle."""
import argparse,json,hashlib,subprocess,sys
from pathlib import Path
from kaggle_web_api import download_archive
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('stage');p.add_argument('version',type=int);p.add_argument('scratch',type=Path);a=p.parse_args()
ref='ramcharan2345/mmds-phase-13-explainable-ai/'+str(a.version)
def api(*args):return subprocess.check_output([sys.executable,str(ROOT/'scripts/kaggle_web_api.py'),*args],text=True)
status=api('kernels','status',ref);assert 'KernelWorkerStatus.COMPLETE' in status,status
logs=api('kernels','logs',ref);events=json.loads(logs);contents='\n'.join(r['data'] for r in events)
marker={'supervised':'PHASE13 archived supervised explanations complete','permutation':'PHASE13 permutation complete','components':'PHASE13 components complete','diagnostics':'PHASE13 diagnostics complete'}[a.stage]
assert marker in contents,('missing completion marker',marker)
a.scratch.mkdir(parents=True,exist_ok=True);(a.scratch/'terminal-logs.json').write_text(logs)
public={'supervised':('explanations.json',),'permutation':('permutation.json','feature_distributions.json','model_metadata.json'),'components':('components.json','linear_shap_stability.json','shap_compatibility.json'),'diagnostics':('error_cases.json','error_support.json','distribution_shift.json','adaptive_reference_probes.json')}[a.stage]
out=ROOT/'reports'/('phase13_'+a.stage);out.mkdir(exist_ok=True)
with download_archive(ref,64*1024*1024) as z:
 receipt=json.loads(z.read('mmds_phase13/receipt.json'));assert receipt['status']=='validated'
 for name,expected in receipt['sha256'].items():assert hashlib.sha256(z.read('mmds_phase13/'+name)).hexdigest()==expected,name
 for name in (*public,'receipt.json'):(out/name).write_bytes(z.read('mmds_phase13/'+name))
metadata=json.loads((a.scratch/'kernel-metadata.json').read_text());assert metadata['is_private'] is True and metadata['enable_gpu'] is False
execution=dict(status='COMPLETE',kernel_version=ref,private_cpu=True,completion_marker=marker,log_sha256=hashlib.sha256(logs.encode()).hexdigest(),log_events=len(events),last_log_seconds=max(float(r['time']) for r in events),submitted_source_sha256=hashlib.sha256((a.scratch/'phase13.ipynb').read_bytes()).hexdigest(),artifacts={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in out.iterdir() if f.is_file() and f.name!='execution.json'})
(out/'execution.json').write_text(json.dumps(execution,indent=2)+'\n')
path=ROOT/'manifests/phase13_experiments.json';m=json.loads(path.read_text());m['stages'][a.stage]=dict(kernel_version=a.version,worker_status='COMPLETE',status='validated',**{k:v for k,v in execution.items() if k not in ('status','kernel_version')});path.write_text(json.dumps(m,indent=2)+'\n');print(json.dumps({k:v for k,v in execution.items() if k!='artifacts'},indent=2))
