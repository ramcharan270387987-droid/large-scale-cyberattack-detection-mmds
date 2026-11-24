"""Download a bounded Phase 9 result and verify its pipeline hashes."""
import argparse
from hashlib import sha256
import json
from pathlib import Path,PurePosixPath
from kaggle_web_api import download_archive

p=argparse.ArgumentParser()
p.add_argument('version')
p.add_argument('destination',type=Path)
a=p.parse_args()
a.destination.mkdir(parents=True,exist_ok=True)
with download_archive(a.version,32*1024*1024) as archive:
    for info in archive.infolist():
        path=PurePosixPath(info.filename)
        if info.is_dir() or '..' in path.parts or path.parts[0]!='mmds_phase9': continue
        relative=Path(*path.parts[1:])
        if relative.suffix=='.crc':continue
        if info.file_size>8*1024*1024:raise ValueError('Oversized result member')
        target=a.destination/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(archive.read(info))
s=json.loads((a.destination/'phase9_summary.json').read_text())
assert s['status']=='validated'
model=a.destination/s['registry']['artifact']
actual={p.relative_to(model).as_posix():sha256(p.read_bytes()).hexdigest() for p in model.rglob('*') if p.is_file()}
assert actual==s['registry']['sha256']
print('Verified retrieved pipeline',s['scenario'],s['model'],s['test'])
