"""Freeze completed public evidence without circular acceptance/checkpoint hashes."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    path=ROOT/'manifests/phase14_experiments.json';manifest=json.loads(path.read_text());files=[]
    files.extend(p for p in (ROOT/'reports').glob('phase14_*') if p.is_file())
    for directory in (ROOT/'reports').glob('phase14_*'):
        if directory.is_dir():files.extend(p for p in directory.rglob('*') if p.is_file() and p.name not in ('acceptance.json','final_remote.json'))
    files.extend((ROOT/'reports/figures').glob('phase14_*'))
    files.extend((ROOT/'docs').glob('phase14*'))
    files.extend((ROOT/'manifests').glob('phase14*.json'))
    files=[p for p in files if p!=path and p.is_file()]
    manifest['complete']=False;manifest.pop('verdict',None)
    manifest['evidence_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(files))};manifest['stages']['14F']=dict(status='verification_pending',figures=json.loads((ROOT/'manifests/phase14_figures.json').read_text())['unique_figures'],tests=164,report='reports/phase14_research_report.md');manifest['next_stage']='Final independent acceptance';path.write_text(json.dumps(manifest,indent=2)+'\n');print('Frozen',len(manifest['evidence_sha256']),'public files')
if __name__=='__main__':main()
