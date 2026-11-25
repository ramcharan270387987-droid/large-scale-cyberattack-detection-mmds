"""Generate only missing conceptual diagrams;reuse existing numerical figures."""
import json,hashlib,shutil
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'deliverables/final_submission/figures'
DIAGRAMS={
'end_to_end':['Pinned provenance\nand audit','Typed/canonical\nSpark Parquet','Leakage-aware\nmodel benchmarks','Patterns,drift\nand adaptation','Verified tables\nand model hashes','Research dashboard\nand submission'],
'data_engineering':['Private raw CSV','Typed strings\nand quality flags','Finite canonical\nfeature mapping','Feature-ready\nParquet layers','Row/label/group\nreconciliation','Versioned receipt\nand content pins'],
'evaluation':['Prespecified\nprotocol','Pinned inputs\nand feature contract','Train-only fitting\nand transforms','Validation-only\ncalibration','Retained held-out\nscoring','Independent numerical\nand artifact checks'],
'leakage_splitting':['Canonical predictor\nequivalence key','Assign random or\ncapture-time roles','Retain earliest role;\npurge later collisions','Fit preprocessing\nonly on training','Freeze validation\noperating threshold','Test denominator\nand collision audit'],
'detection':['Source feature\ncontract','Supervised LR/RF\nprobability branch','Reference K-Means\ndistance branch','Archived calibration\nand logical gates','Frozen hybrid\noperating point','Matched-cohort\nperformance audit'],
'pattern_mining':['Training reference\ncutpoints','Six-feature\ntransactions','FP-Growth\nfrequent itemsets','Association-rule\nsufficient counts','Class/family\ncontrast support','Capture emergence\nwith composition caveat'],
'historical_drift':['Archived capture\nmicrobatches','Frozen supervised\nand novelty models','Window signals\nand support gates','Drift detectors\nand reference state','Timestamped\narchived alerts','Retrospective diagnostics;\nno live capture'],
'adaptive_lifecycle':['Predict using\nactive model','Pending labels\nwith simulated delay','Release labels;\nupdate monitors','Past-only candidate\nfit and calibration','Promotion guard\nor retain incumbent','Future-only activation\nand rollback evidence'],
'explainable_inference':['Bounded manual\nor uploaded CSV','Checksum-verified\noriginal parameters','Stored transform\nand imputation','Actual model score\nand threshold','LR logit / centroid\nreconstruction','New-row explanation\nwith scientific limits'],
'dashboard':['Immutable archived\nresearch evidence','Compact LR/RF/K-Means\nportable artifacts','Schema and\nSHA256 guards','Unified research\nand inference views','Session-only\nbounded predictions','Verified downloads\nand academic demo'],
'external_scalability':['External track:\nconditional common3','Frozen source /\ntarget-only models','Matched target tests;\nseparate sensitivities','Scale track:\nactual source populations','Local threads,formats\ncache and partitions','Bounded Pandas /\ninference / mining']}
def main():
 OUT.mkdir(exist_ok=True);records=[]
 for name,labels in DIAGRAMS.items():
  fig,ax=plt.subplots(figsize=(12,4.2));ax.set_xlim(0,12);ax.set_ylim(0,4.2);ax.axis('off');positions=[(.15,2.4),(4.2,2.4),(8.25,2.4),(8.25,.45),(4.2,.45),(.15,.45)]
  for i,(label,(x,y)) in enumerate(zip(labels,positions)):
   ax.add_patch(FancyBboxPatch((x,y),3.6,1.15,boxstyle='round,pad=.12',linewidth=1.2,edgecolor='#1d536a',facecolor='#edf5f7'));ax.text(x+1.8,y+.575,label.replace(',',', '),ha='center',va='center',fontsize=13,color='#183c4a')
   if i:
    px,py=positions[i-1]
    if py==y:
     a=(px+3.75,py+.575) if x>px else (px-.15,py+.575);b=(x-.15,y+.575) if x>px else (x+3.75,y+.575)
    else:a=(px+1.8,py-.1);b=(x+1.8,y+1.3)
    # External and scaling are separate tracks,not a causal chain between them.
    if not(name=='external_scalability' and i==3):ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=15,color='#557987'))
  fig.tight_layout(pad=.3)
  for ext in ('png','svg'):
   p=OUT/(name+'.'+ext);fig.savefig(p,dpi=180,bbox_inches='tight',metadata={'Date':None} if ext=='svg' else None);records.append(dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),kind='conceptual',source='Diagram node/edge specification in scripts/build_phase16_diagrams.py',name=name))
  plt.close(fig)
 # Reuse measured charts without editing their values or claiming new experiments.
 selected=['phase5_b_distance_histogram','phase6_timeline','phase10_support_sensitivity','phase11_detector_comparison','phase12_policy_comparison','phase13_linear_shap','phase14_external_models','phase14_volume','phase14_workers','phase14_storage','phase14_pandas']
 for stem in selected:
  p=ROOT/'reports/figures'/(stem+'.png')
  if not p.exists():
   prefix=stem.split('_')[0]+'_';options=sorted((ROOT/'reports/figures').glob(prefix+'*.png'));p=options[0] if options else None
  if p:
   target=OUT/p.name;shutil.copy(p,target);records.append(dict(path=str(target.relative_to(ROOT)),source=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),kind='validated numerical chart',name=p.stem))
 (ROOT/'manifests/phase16_figures.json').write_text(json.dumps(records,indent=2)+'\n');(OUT/'diagram_sources.json').write_text(json.dumps(DIAGRAMS,indent=2)+'\n');print('Generated11PNG/SVGdiagrams;reused',sum(r['kind']!='conceptual' for r in records),'validated charts')
if __name__=='__main__':main()
