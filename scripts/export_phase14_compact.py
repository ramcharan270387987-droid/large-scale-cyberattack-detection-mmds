"""Prepare a data-preserving compact export notebook; never copy raw/Parquet/CSV rows.

Used when the proxy permits Kaggle API archives but denies the individual artifact
host. This job copies already computed JSON evidence; it reruns no experiments.
"""
import argparse,json,hashlib
from pathlib import Path
from build_phase2_notebook import notebook,cell
p=argparse.ArgumentParser();p.add_argument('reference');p.add_argument('marker');p.add_argument('directory',type=Path);a=p.parse_args();a.directory.mkdir(parents=True,exist_ok=True)
code="""from pathlib import Path
import json,hashlib,shutil
root=Path('/kaggle/input');out=Path('/kaggle/working/phase14_compact');out.mkdir()
markers=list(root.rglob(MARKER));assert len(markers)==1,[(p.as_posix()) for p in markers]
source=markers[0].parent;records=[]
for path in sorted(source.glob('*.json')):
 assert path.stat().st_size<=8*1024*1024
 data=path.read_bytes();json.loads(data);(out/path.name).write_bytes(data)
 records.append({'file':path.name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
receipt={'status':'validated','source_kernel_version':REFERENCE,'experiment_reexecuted':False,'scope':'top-level compactJSON only; no raw,CSV,Parquet or row-level files','files':records}
(out/'export_receipt.json').write_text(json.dumps(receipt,indent=2)+'\\n')
print('PHASE14 COMPACT EXPORT COMPLETE',len(records),flush=True)
""".replace('MARKER',repr(a.marker)).replace('REFERENCE',repr(a.reference))
if a.marker=='external_audit.json':
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from src.external_validation import label_mapping
    import inspect
    audit_source=inspect.getsource(label_mapping)
    code+=audit_source+'\nlabel_catalog=audit_label_bytes(root)\npath=out/"label_byte_catalog.json"\npath.write_text(json.dumps(label_catalog,indent=2)+"\\n")\nreceipt["files"].append({"file":path.name,"bytes":path.stat().st_size,"sha256":hashlib.sha256(path.read_bytes()).hexdigest()})\n(out/"export_receipt.json").write_text(json.dumps(receipt,indent=2)+"\\n")\nprint("PHASE14 LABEL BYTE AUDIT COMPLETE",label_catalog["rows"],flush=True)\n'
note=notebook([cell('markdown','scope','# Phase14 compact evidence export\nNo experiments are rerun.'),cell('code','export',code)]);(a.directory/'compact.ipynb').write_text(json.dumps(note,indent=1)+'\n')
metadata=dict(id='ramcharan2345/mmds-phase14-compact-evidence',title='MMDS Phase14 Compact Evidence',code_file='compact.ipynb',language='python',kernel_type='notebook',is_private=True,enable_gpu=False,enable_tpu=False,enable_internet=False,dataset_sources=['shadman1028/cicids2017-official-flow-feature-csv-files/1'] if a.marker=='external_audit.json' else [],kernel_sources=[a.reference],competition_sources=[])
(a.directory/'kernel-metadata.json').write_text(json.dumps(metadata,indent=2)+'\n');print('PREPARED export',a.reference)
