"""Build staged private CPU notebooks; repository notebooks contain no model weights."""
import argparse,json,hashlib,subprocess
from pathlib import Path
from build_phase8_notebook import build
from build_phase2_notebook import cell
ROOT=Path(__file__).resolve().parents[1]
def notebook(stage):
    note=build('baseline','B');note['cells'][0]['source']=[f'# Phase14 {stage}: private research CPU execution']
    paths=list((ROOT/'src/external_validation').glob('*.py'))+list((ROOT/'src/scalability').glob('*.py'))+list((ROOT/'configs').glob('phase14_*.yaml'))
    sources={str(p.relative_to(ROOT)):p.read_text() for p in paths};
    for relative in ('src/patterns/discretization.py','src/explainability/sampling.py','reports/phase10_stageB/registry.json')+ (('reports/phase14_14B/label_byte_catalog.json',) if stage=='14C' else ()):
        sources[relative]=(ROOT/relative).read_text()
    sources['manifests/phase14_experiments.json']=(ROOT/'manifests/phase14_experiments.json').read_text()
    code='phase14_sources='+repr(sources)+'\nfor name,source in phase14_sources.items():\n target=project/name\n target.parent.mkdir(parents=True,exist_ok=True)\n target.write_text(source)\n'
    code+='source_commit='+repr(subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())+'\nprint("PHASE14 SOURCE",source_commit,flush=True)\n'
    note['cells'].insert(-1,cell('code','phase14-source',code))
    module={'14B':'src.external_validation.dataset_audit','14C':'src.external_validation.transfer_evaluation','14D':'src.scalability.benchmark_runner','14E':'src.scalability.optimization','14V':'src.external_validation.verify_models'}[stage]
    note['cells'][-1]['source']=[f"from {module} import run\nrun(project,Path('/kaggle/input'),Path('/kaggle/working/mmds_phase14'),Path('/kaggle/temp/phase14/spark'))\n"]
    for c in note['cells']:
        if c['cell_type']=='code':compile(''.join(c['source']),c['id'],'exec')
    return note
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['14B','14C','14D','14E','14V']);p.add_argument('directory',type=Path);a=p.parse_args();a.directory.mkdir(parents=True,exist_ok=True)
    note=notebook(a.stage);file=a.directory/'phase14.ipynb';file.write_text(json.dumps(note,indent=1)+'\n')
    slugs={'14B':'mmds-phase-14-external-audit','14C':'mmds-phase-14-external-validation','14D':'mmds-phase-14-scalability-benchmark','14E':'mmds-phase-14-execution-optimization','14V':'mmds-phase-14-frozen-model-verification'};slug=slugs[a.stage];kernels=['ramcharan2345/mmds-phase-2-spark-data-engineering/1']
    manifest=json.loads((ROOT/'manifests/phase14_experiments.json').read_text())
    if a.stage in ('14C','14E','14V'):
        dependency='14B' if a.stage=='14C' else '14C' if a.stage=='14V' else '14D'
        pin=manifest['stages'].get(dependency)
        if not pin or (pin.get('status')!='validated' and not (a.stage=='14V' and pin.get('status')=='executed_pending_independent_validation')):raise ValueError('Required producer stage is not validated: '+dependency)
        kernels.append(pin['kernel_version'])
        if a.stage=='14V':kernels.append(manifest['stages']['14B']['kernel_version'])
    metadata=dict(id='ramcharan2345/'+slug,title=slug.replace('-',' ').title(),code_file=file.name,language='python',kernel_type='notebook',is_private=True,enable_gpu=False,enable_tpu=False,enable_internet=True,dataset_sources=['shadman1028/cicids2017-official-flow-feature-csv-files/1'] if a.stage=='14B' else [],kernel_sources=kernels,competition_sources=[])
    if a.stage in ('14D','14E'):
        import base64,lzma
        models=json.loads((ROOT/'manifests/phase13_models.json').read_text())['supervised'];files={};pins=[]
        for entry in models:
            if entry['id'] not in ('B-logistic_regression','B-random_forest'):continue
            folder=Path('/tmp/mmds-independent-models')/entry['id']
            if not folder.exists():
                from kaggle_web_api import download_archive
                original=json.loads((ROOT/'manifests/phase4_models.json').read_text());model=next(x for x in original['protocols']['B']['models'] if x['training_cohort']=='group_sample' and x['model']==entry['algorithm'])
                with download_archive(entry['version'],32*1024*1024) as archive:
                    for relative,expected in entry['sha256'].items():
                        content=archive.read('mmds_phase4/models/'+Path(model['path']).name+'/'+relative);assert hashlib.sha256(content).hexdigest()==expected
                        target=folder/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(content)
            for relative,expected in entry['sha256'].items():
                content=(folder/relative).read_bytes();assert hashlib.sha256(content).hexdigest()==expected
                files[entry['id']+'/'+relative]=base64.b64encode(content).decode()
            pins.append(entry)
        packed=base64.b64encode(lzma.compress(json.dumps(files).encode())).decode()
        code="import base64,lzma,json,hashlib\nprivate_files=json.loads(lzma.decompress(base64.b64decode("+repr(packed)+")))\nfor relative,encoded in private_files.items():\n target=Path('/kaggle/temp/phase14_archives')/relative\n target.parent.mkdir(parents=True,exist_ok=True)\n target.write_bytes(base64.b64decode(encoded))\n"
        code+='model_pins='+repr(pins)+'\nfor pin in model_pins:\n for relative,expected in pin["sha256"].items():\n  assert hashlib.sha256((Path("/kaggle/temp/phase14_archives")/pin["id"]/relative).read_bytes()).hexdigest()==expected\nPath("/kaggle/working/archived_model_pins.json").write_text(json.dumps(model_pins,indent=2))\n'
        note['cells'].insert(-1,cell('code','private-archived-models',code));file.write_text(json.dumps(note,indent=1)+'\n');(a.directory/'model-pins.json').write_text(json.dumps(pins,indent=2)+'\n')
    (a.directory/'kernel-metadata.json').write_text(json.dumps(metadata,indent=2)+'\n');print('PREPARED',a.stage,hashlib.sha256(file.read_bytes()).hexdigest())
