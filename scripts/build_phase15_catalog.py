"""Inventory existing aggregate evidence without copying historical experiments."""
import ast,json,hashlib,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    groups={}
    def add(group,label,path,mode='csv'):
        p=ROOT/path
        if p.exists():groups.setdefault(group,[]).append(dict(label=label,path=path,format=mode,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    for group,prefixes in [('Dataset intelligence & SQL',('phase1_','phase2_','phase3_','dataset_')),('Supervised & hybrid',('phase4_','phase8_')),('Clustering & novelty',('phase5_',)),('Multiclass & open-set',('phase9_',))]:
        for folder in ('dashboard/data','reports'):
            for p in sorted((ROOT/folder).glob('*.csv')):
                if p.name.startswith(prefixes):add(group,folder+'/'+p.stem.replace('_',' '),str(p.relative_to(ROOT)))
    for phase,group in [(11,'Streaming & drift'),(12,'Adaptive learning'),(13,'Explainable AI'),(14,'External validation & scalability')]:
        module=ast.parse((ROOT/f'dashboard/phase{phase}_preview.py').read_text());sections=ast.literal_eval(next(n.value for n in module.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SECTIONS' for t in n.targets)))
        for label,path in sections.items():add(group,label,'reports/'+path)
    for p in sorted((ROOT/'reports/phase10_analysis').glob('*.json')):add('Frequent & emerging patterns',p.stem.replace('_',' '),str(p.relative_to(ROOT)),'json')
    for folder in ('phase10_stageB','phase10_rule_validation'):
        for p in sorted((ROOT/'reports'/folder).glob('*.json')):
            if p.name not in ('receipt.json','registry.json'):add('Frequent & emerging patterns',folder+' '+p.stem,str(p.relative_to(ROOT)),'json')
    for p in sorted((ROOT/'reports').glob('phase6*.csv')):add('Streaming & drift',p.stem.replace('_',' '),str(p.relative_to(ROOT)))
    # Hierarchical gate and oracle diagnostics are retained in their original tables.
    for p in sorted((ROOT/'reports').rglob('*.csv')):
        if 'phase9' in str(p) and any(s in p.name for s in ('hierarch','oracle','gate','rejection')):add('Multiclass & open-set',str(p.relative_to(ROOT/'reports')),str(p.relative_to(ROOT)))
    figures=[dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted((ROOT/'reports/figures').glob('*.png')) if p.stem.startswith(tuple('phase'+str(i)+'_' for i in range(1,15)))]
    out=dict(schema='phase15-evidence-v1',groups=groups,figures=figures,source_checkpoint='51392548c562d098e3d74b9a0bda4c402bd421d7');(ROOT/'manifests/phase15_evidence.json').write_text(json.dumps(out,indent=2)+'\n');print('Catalogued',sum(map(len,groups.values())),'tables in',len(groups),'research areas')
if __name__=='__main__':main()
