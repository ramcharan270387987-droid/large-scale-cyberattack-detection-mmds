"""Retrieve actual compact export archives; version pins and hashes fail closed."""
import argparse,json,hashlib,subprocess,sys
from pathlib import Path
from kaggle_web_api import download_archive
ROOT=Path(__file__).resolve().parents[1]
def api(*args):return subprocess.check_output([sys.executable,str(ROOT/'scripts/kaggle_web_api.py'),*args],text=True)
def retrieve(reference,destination,export=False):
    status=api('kernels','status',reference);assert 'COMPLETE' in status,status
    logs=api('kernels','logs',reference);events=json.loads(logs);destination.mkdir(parents=True,exist_ok=True);(destination/'execution-logs.json').write_text(logs);checked=[]
    with download_archive(reference,32*1024*1024) as archive:
        prefix='phase14_compact/' if export else 'mmds_phase14/'
        candidates=[x for x in archive.infolist() if x.filename.startswith(prefix) and x.filename.endswith('.json') and len(Path(x.filename).parts)==2]
        assert candidates,'No compact evidence'
        for entry in candidates:
            assert entry.file_size<8*1024*1024;data=archive.read(entry);json.loads(data);private=Path(entry.filename).name in ('failure_analysis.json','failure_analysis_verified.json')
            target=(Path('/tmp/mmds-phase14/'+('14V-private' if Path(entry.filename).name=='failure_analysis_verified.json' else '14C-private'))/Path(entry.filename).name) if private else (destination/Path(entry.filename).name);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);checked.append(dict(file=entry.filename,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),private_only=private))
        if export:
            record=json.loads((destination/'export_receipt.json').read_text());assert record['status']=='validated' and record['experiment_reexecuted'] is False
            for file in record['files']:assert hashlib.sha256((destination/file['file']).read_bytes()).hexdigest()==file['sha256']
    receipt=dict(status='COMPLETE',kernel_version=reference,log_sha256=hashlib.sha256(logs.encode()).hexdigest(),log_events=len(events),files=checked,export_only=export)
    (destination/'retrieval.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('reference');p.add_argument('destination',type=Path);p.add_argument('--export',action='store_true');a=p.parse_args();retrieve(a.reference,a.destination,a.export)
