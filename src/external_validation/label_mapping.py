"""Byte-preserving external label catalog; no guessed repair or forced families."""
from collections import Counter
from pathlib import Path

def audit_label_bytes(root):
    counts=Counter();files=sorted(p for p in root.rglob('*.csv') if 'workinghours' in p.name.casefold())
    if len(files)!=8:raise ValueError('Expected exactly eight external CSV files for label byte audit')
    for path in files:
        with path.open('rb') as f:
            next(f)
            for line in f:
                if line.strip():counts[line.rstrip(b'\r\n').rsplit(b',',1)[-1].strip()]+=1
    rows=[];aliases={}
    for value,count in sorted(counts.items()):
        if value.lower()==b'label':continue
        observed=value.decode('utf-8',errors='replace')
        try:decoded=value.decode('utf-8');encoding='UTF-8 strict'
        except UnicodeDecodeError:decoded=value.decode('cp1252');encoding='Windows-1252 label bytes; explicit fallback'
        if observed in aliases and aliases[observed]!=value.hex():raise ValueError('Ambiguous replacement-decoded label, cannot silently map')
        aliases[observed]=value.hex();rows.append(dict(observed_utf8_label=observed,original_label=decoded,original_label_hex=value.hex(),decoding=encoding,count=count,binary_label=None if not value else 0 if value.lower()==b'benign' else 1,family_mapping='external original category; no forced source-family mapping'))
    return dict(status='validated',scope='Raw label byte catalog only; no private flow rows exported',files=len(files),rows=sum(x['count'] for x in rows),labels=rows)
