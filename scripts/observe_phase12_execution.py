"""Independent terminal Kaggle status, metadata and execution-log receipt."""
import argparse,json,hashlib,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def api(*args):return subprocess.run([sys.executable,str(ROOT/'scripts/kaggle_web_api.py'),*args],capture_output=True,text=True,check=True).stdout

def main():
    p=argparse.ArgumentParser();p.add_argument('stage');p.add_argument('version');p.add_argument('directory',type=Path);a=p.parse_args()
    ref,version=a.version.rsplit('/',1);a.directory.mkdir(parents=True,exist_ok=True)
    status=api('kernels','status',ref)
    if 'KernelWorkerStatus.COMPLETE' not in status:raise SystemExit('Notebook is not complete: '+status.strip())
    log_text=api('kernels','logs',a.version);logs=json.loads(log_text)
    (a.directory/'terminal-logs.json').write_text(log_text)
    api('kernels','pull',ref,'-m','-p',str(a.directory/'actual-submission'))
    metadata=json.loads((a.directory/'actual-submission/kernel-metadata.json').read_text())
    assert metadata['id']==ref and metadata['is_private'] is True and metadata['enable_gpu'] is False and metadata.get('enable_tpu',False) is False
    notebook=a.directory/'actual-submission'/metadata['code_file'];times=[float(r['time']) for r in logs]
    contents='\n'.join(r['data'] for r in logs)
    assert 'PHASE12_COMPLETE '+a.stage in contents
    receipt={'status':'COMPLETE','kernel_version':a.version,'url':'https://www.kaggle.com/code/'+ref,
        'private_cpu':True,'metadata':metadata,'notebook_sha256':hashlib.sha256(notebook.read_bytes()).hexdigest(),
        'log_sha256':hashlib.sha256(log_text.encode()).hexdigest(),'log_events':len(logs),
        'first_log_seconds':min(times),'last_log_seconds':max(times),'observed_log_span_seconds':max(times)-min(times),
        'runtime_scope':'Kaggle log offsets include environment setup and postprocessing; Phase12 stage monotonic elapsed is separately recorded',
        'complete_marker':True,'run_complete_markers':contents.count('RUN_COMPLETE '),'fit_complete_markers':contents.count('FIT_COMPLETE '),
        'source_frozen_initial_reload_markers':contents.count('REUSE_VERIFIED_MODEL ')}
    target=ROOT/'reports'/f'phase12_{a.stage}'/'execution.json';target.parent.mkdir(exist_ok=True);target.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k!='metadata'},indent=2))
if __name__=='__main__':main()
