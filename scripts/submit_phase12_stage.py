"""Prepare a sequential Kaggle stage; refuse duplicate running/completed submissions."""
import argparse,csv,io,json,subprocess,sys,re,hashlib,base64,zipfile,lzma
from pathlib import Path
from build_phase12_notebook import build_stage
ROOT=Path(__file__).resolve().parents[1]
SLUGS={'12C':'mmds-phase-12-adaptive-learning-model-refresh','12D':'mmds-phase12-12d-adaptive-research','12E':'mmds-phase-12-robustness-completion'}

def api(*args):
    return subprocess.run([sys.executable,str(ROOT/'scripts/kaggle_web_api.py'),*args],check=True,capture_output=True,text=True).stdout

def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['12D','12E']);p.add_argument('directory',type=Path);p.add_argument('--prepare-only',action='store_true');a=p.parse_args()
    slug=SLUGS[a.stage];ref='ramcharan2345/'+slug
    existing=list(csv.DictReader(io.StringIO(api('kernels','list','--mine','--page-size','100','--csv'))))
    if any(row.get('ref')==ref for row in existing):
        status=api('kernels','status',ref)
        raise SystemExit('Existing stage requires explicit receipt review before resubmission: '+status.strip())
    frozen=json.loads((ROOT/'manifests/phase12_frozen_reference.json').read_text())
    a.directory.mkdir(parents=True,exist_ok=True)
    note=build_stage(a.stage)
    if a.stage=='12E':
        # Private upload only. This payload is never written to a repository notebook.
        source=Path('/tmp/mmds-phase12-synthetic-final/synthetic_results.json')
        payload=json.loads(source.read_text());buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w',zipfile.ZIP_STORED) as archive:
            archive.writestr('models.json',json.dumps(payload['models'],indent=2))
            for meta in payload['models']:
                file=Path(meta['archive']);assert hashlib.sha256(file.read_bytes()).hexdigest()==meta['sha256']
                archive.writestr(meta['model']+'.pkl',file.read_bytes())
            resume_path=ROOT/'manifests/phase12_resume.json'
            if resume_path.exists():
                pin=json.loads(resume_path.read_text());resume_root=Path(pin['local_resume_directory'])
                previous=(resume_root/'phase12_summary.json').read_bytes()
                assert hashlib.sha256(previous).hexdigest()==pin['summary_sha256']
                archive.writestr('resume/phase12_summary.json',previous)
                frozen=json.loads((ROOT/'manifests/phase12_frozen_reference.json').read_text())
                c_models={row['model'] for row in csv.DictReader((ROOT/'reports/phase12_12C/models.csv').open())}
                resume_summary=json.loads(previous)
                for identifier,meta in resume_summary['models'].items():
                    if identifier in c_models:continue
                    folder=resume_root/meta['receipt']['artifact']
                    for file in folder.rglob('*'):
                        if file.is_file():archive.write(file,'resume/'+file.relative_to(resume_root).as_posix())
                for file in (resume_root/'registries').rglob('*.json'):
                    archive.write(file,'resume/registries/'+file.relative_to(resume_root/'registries').as_posix())
                for file in (resume_root/'prediction_histograms').glob('*.json'):
                    record=json.loads(file.read_text())
                    if record['role']!=2:continue
                    record['origin_kernel_version']=pin['kernel_version']
                    archive.writestr('resume/prediction_histograms/'+file.name,json.dumps(record))
        data=buffer.getvalue();packed=lzma.compress(data,preset=9);expected=hashlib.sha256(data).hexdigest()
        from build_phase2_notebook import cell
        code="import base64,hashlib,lzma\nprivate_models=lzma.decompress(base64.b64decode("+repr(base64.b64encode(packed).decode())+"))\nassert hashlib.sha256(private_models).hexdigest()=="+repr(expected)+"\nPath('/kaggle/working/phase12_synthetic_models.zip').write_bytes(private_models)\nimport zipfile,io\nwith zipfile.ZipFile(io.BytesIO(private_models)) as resume_archive:\n for entry in resume_archive.infolist():\n  if entry.filename.startswith('resume/') and not entry.is_dir():\n   relative=Path(entry.filename).relative_to('resume')\n   assert not relative.is_absolute() and '..' not in relative.parts\n   target=Path('/kaggle/temp/phase12_resume')/relative\n   target.parent.mkdir(parents=True,exist_ok=True)\n   target.write_bytes(resume_archive.read(entry))\nprint('SYNTHETIC_MODEL_ARCHIVE_PRESERVED',len(private_models))\n"
        note['cells'].insert(-1,cell('code','private-synthetic-model-archive',code))
        (a.directory/'private-model-upload.json').write_text(json.dumps({'models':len(payload['models']),'bytes':len(data),'upload_packed_bytes':len(packed),'sha256':expected},indent=2))
    for item in note['cells']:
        if item['cell_type']=='code':compile(''.join(item['source']),item['id'],'exec')
    (a.directory/'phase12_adaptive_learning.ipynb').write_text(json.dumps(note,indent=1)+'\n')
    metadata={'id':ref,'title':slug.replace('-',' ').title(),'code_file':'phase12_adaptive_learning.ipynb',
        'language':'python','kernel_type':'notebook','is_private':True,'enable_gpu':False,'enable_tpu':False,'enable_internet':True,
        'dataset_sources':[],'competition_sources':[],
        'kernel_sources':['ramcharan2345/mmds-phase-2-spark-data-engineering/1',frozen['kernel_version']]}
    (a.directory/'kernel-metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    if a.prepare_only:
        print('PREPARED',a.directory,(a.directory/'phase12_adaptive_learning.ipynb').stat().st_size)
        return
    response=api('kernels','push','-p',str(a.directory))
    match=re.search(r'https://www.kaggle.com/code/([^\s]+)',response)
    version=re.search(r'Kernel version (\d+)',response)
    (a.directory/'submission-receipt.json').write_text(json.dumps({'requested_ref':ref,'actual_ref':match[1] if match else None,'version':int(version[1]) if version else None},indent=2))
    print(response,end='')
if __name__=='__main__':main()
