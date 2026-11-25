"""Build staged private CPU notebooks; repository notebooks contain no model weights."""
import argparse,json,hashlib,subprocess
from pathlib import Path
from build_phase8_notebook import build
from build_phase2_notebook import cell
ROOT=Path(__file__).resolve().parents[1]
def notebook(stage):
    note=build('baseline','B');note['cells'][0]['source']=[f'# Phase14 {stage}: private research CPU execution']
    paths=list((ROOT/'src/external_validation').glob('*.py'))+list((ROOT/'src/scalability').glob('*.py'))+list((ROOT/'configs').glob('phase14_*.yaml'))
    sources={str(p.relative_to(ROOT)):p.read_text() for p in paths};sources['manifests/phase14_experiments.json']=(ROOT/'manifests/phase14_experiments.json').read_text()
    code='phase14_sources='+repr(sources)+'\nfor name,source in phase14_sources.items():\n target=project/name\n target.parent.mkdir(parents=True,exist_ok=True)\n target.write_text(source)\n'
    code+='source_commit='+repr(subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())+'\nprint("PHASE14 SOURCE",source_commit,flush=True)\n'
    note['cells'].insert(-1,cell('code','phase14-source',code))
    module={'14B':'src.external_validation.dataset_audit','14C':'src.external_validation.transfer_evaluation','14D':'src.scalability.benchmark_runner','14E':'src.scalability.optimization'}[stage]
    note['cells'][-1]['source']=[f"from {module} import run\nrun(project,Path('/kaggle/input'),Path('/kaggle/working/mmds_phase14'),Path('/kaggle/temp/phase14/spark'))\n"]
    for c in note['cells']:
        if c['cell_type']=='code':compile(''.join(c['source']),c['id'],'exec')
    return note
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['14B','14C','14D','14E']);p.add_argument('directory',type=Path);a=p.parse_args();a.directory.mkdir(parents=True,exist_ok=True)
    note=notebook(a.stage);file=a.directory/'phase14.ipynb';file.write_text(json.dumps(note,indent=1)+'\n')
    slugs={'14B':'mmds-phase-14-external-audit','14C':'mmds-phase-14-external-validation','14D':'mmds-phase-14-scalability-benchmark','14E':'mmds-phase-14-execution-optimization'};slug=slugs[a.stage];kernels=['ramcharan2345/mmds-phase-2-spark-data-engineering/1']
    if a.stage=='14C':kernels.append('ramcharan2345/mmds-phase-14-external-audit/1')
    metadata=dict(id='ramcharan2345/'+slug,title=slug.replace('-',' ').title(),code_file=file.name,language='python',kernel_type='notebook',is_private=True,enable_gpu=False,enable_tpu=False,enable_internet=True,dataset_sources=['shadman1028/cicids2017-official-flow-feature-csv-files/1'] if a.stage=='14B' else [],kernel_sources=kernels,competition_sources=[])
    (a.directory/'kernel-metadata.json').write_text(json.dumps(metadata,indent=2)+'\n');print('PREPARED',a.stage,hashlib.sha256(file.read_bytes()).hexdigest())
