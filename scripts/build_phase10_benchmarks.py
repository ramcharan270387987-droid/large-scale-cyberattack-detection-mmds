"""Bounded deterministic group-sample FP-Growth benchmarks."""
import json,argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args()
n=json.loads(Path('/tmp/phase10-stageB/phase10.ipynb').read_text())
n['cells'][0]['source']=['# Phase 10 bounded computational benchmarks']
code=''.join(n['cells'][-1]['source'])
code=code.replace("out=Path('/kaggle/working/mmds_phase10_mining')","out=Path('/kaggle/working/mmds_phase10_benchmarks')")
a0=code.index(" data=transform(frame,bins)")
b0=code.index(" atomic_json(out/'registry.json'",a0)
replacement=''' summaries=[]
 for target in (1000000,4000000,8000000):
  fraction=target/16232943
  sampled=frame.where(F.pmod(F.xxhash64(F.lit(23013),F.lit('phase10-benchmark'),'predictor_key'),F.lit(1000000))<int(fraction*1000000))
  tick=monotonic()
  data=transform(sampled,bins).select('items').persist()
  total=data.count()
  construction=monotonic()-tick
  model,summary=mine(data,.05)
  tick=monotonic();rules=model.associationRules.count();rule_seconds=monotonic()-tick
  summary.update(target=target,rows=total,support=.05,transaction_seconds=construction,rule_seconds=rule_seconds,rules=rules)
  summaries.append(summary);data.unpersist()
  atomic_json(out/'progress.json',summaries)
'''
code=code[:a0]+replacement+code[b0:]
code=code.replace("'rows':total,", "'last_sample_rows':total,").replace("PHASE10 mining complete","PHASE10 benchmarks complete")
n['cells'][-1]['source']=code.splitlines(keepends=True)
for c in n['cells']:
 if c['cell_type']=='code':compile(''.join(c['source']),c['id'],'exec')
a.output.write_text(json.dumps(n,indent=1)+'\n')
