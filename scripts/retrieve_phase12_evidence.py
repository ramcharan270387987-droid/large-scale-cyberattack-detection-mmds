"""Retrieve a completed private Kaggle stage and verify compact model checksums."""
import argparse,hashlib,json
from pathlib import Path,PurePosixPath
from kaggle_web_api import download_archive
from export_phase12_evidence import export,csv_write

def retrieve(version,destination,allow_partial=False):
    destination.mkdir(parents=True,exist_ok=True)
    with download_archive(version,64*1024*1024) as archive:
        entries=archive.infolist()
        for entry in entries:
            relative=PurePosixPath(entry.filename)
            if relative.is_absolute() or '..' in relative.parts:raise ValueError('Unsafe archive path')
            if entry.is_dir():continue
            if entry.file_size>16*1024*1024:raise ValueError('Oversize evidence member')
            target=destination/entry.filename;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(archive.read(entry))
    candidates=list(destination.rglob('phase12_summary.json'))
    if len(candidates)!=1:raise ValueError('Missing unique stage summary')
    summary=json.loads(candidates[0].read_text())
    assert summary['status']=='validated' or (allow_partial and summary['status']=='running' and summary['runs'])
    root=candidates[0].parent
    for key,meta in summary['models'].items():
        assert meta['independent_reload']
        for relative,expected in meta['receipt']['sha256'].items():
            actual=root/meta['receipt']['artifact']/relative
            assert hashlib.sha256(actual.read_bytes()).hexdigest()==expected,(key,relative)
    label=summary['stage']+('_partial_v1' if allow_partial else '')
    compact=Path(__file__).resolve().parents[1]/'reports'/f'phase12_{label}'
    export(summary,compact)
    scoring=[]
    for path in (root/'prediction_histograms').glob('*.json'):
        record=json.loads(path.read_text())
        rows=sum(sum(v) for h in record['family_histograms'].values() for v in h.values())
        scoring.append({'model':record['model'],'day':record['day'],'role':record['role'],'rows':rows,
            'prediction_seconds':record['prediction_seconds'],'flows_per_second':rows/record['prediction_seconds'],
            'scope':'first private materialization and histogram aggregation'})
    csv_write(compact/'scoring.csv',scoring)
    hashes={p.relative_to(destination).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.rglob('*') if p.is_file()}
    (compact/'retrieval.json').write_text(json.dumps({'kernel_version':version,'status':'ERROR_PARTIAL_SCOPES_PRESERVED' if allow_partial else 'COMPLETE','summary_sha256':hashlib.sha256(candidates[0].read_bytes()).hexdigest(),
        'files_sha256':hashes,'models_verified':len(summary['models']),'row_predictions':'private Kaggle scratch; versioned bin/family counts archived in outputs'},indent=2)+'\n')
    print(json.dumps({'stage':summary['stage'],'runs':len(summary['runs']),'models_verified':len(summary['models']),'retained_rows':summary['retained_rows'],'cross_role_groups':summary['cross_role_groups']},indent=2))
    return summary
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('version');p.add_argument('destination',type=Path);p.add_argument('--allow-partial',action='store_true');a=p.parse_args();retrieve(a.version,a.destination,a.allow_partial)
