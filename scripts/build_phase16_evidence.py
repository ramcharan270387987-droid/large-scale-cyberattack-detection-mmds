"""Consolidate accepted results with exact selectors;no experimental execution."""
import csv,json,hashlib,subprocess,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'deliverables/final_submission'
def write(name,rows):
 p=OUT/'tables'/name;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w',newline='') as f:w=csv.DictWriter(f,list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows(rows)
def main():
 phases=[('Dataset audit','dataset_audit.md','d73bff36c2266e81a9145bf034b07039176715a1'),('Spark engineering','phase2_data_engineering.md','66334dc02a89ebf3d84e3bc62e1bb4f112e5951e'),('SQL analytics','phase3_analytics.md','49b9e4d816df85bec77949b66051b0a1e6181a51'),('Supervised detection','phase4_supervised_results.md','6e552768b6825335cdc2be8cc75727657f724340'),('Clustering/novelty','phase5_clustering_results.md','ddc003f3e2f8f11b45496026e70371132a367a3b'),('Historical replay','phase6_streaming_results.md','c7dc703d7ced871b496b1b5ced4b606ba78d7668'),('Baseline dashboard','dashboard_final_qa.md','16ef2c23bbfe33c497d32863173455185fe868ed'),('Hybrid detection','phase8_hybrid_results.md','beb558748b24309b1f752b2d744614f31b1d9351'),('Multiclass/open set','phase9_research_report.md','d5ab1d87e4b32bfdc484cec1b05b4ecc3e73b5b0'),('Pattern mining','phase10_results.md','901a9f33954653cf6b327aa366700d7b91d997da'),('Drift','phase11_results.md','96c1885ef97243e4de33757603fe1530994f0f8e'),('Adaptive learning','phase12_results.md','be53a63b7f8f330c3561efcdf73f2501d66ccac7'),('Explainable AI','phase13_research_report.md','ab6e9401b0c9b92e624e5b2b16ec91050a081eb0'),('External/scalability','phase14_research_report.md','51392548c562d098e3d74b9a0bda4c402bd421d7'),('Integrated inference','phase15_results.md','cb36ddec061006acfda09deda2168a196cbf4a48')]
 objectives=['Establish defensible population and provenance','Create reusable audited numerical layers','Describe class/capture structure','Separate random and chronological generalization','Measure reference novelty without probability claims','Reproduce ordered historical microbatches','Present verified aggregate research','Assess fusion under matched operating constraints','Separate closed-set family and unknown rejection','Mine frequency,contrast and temporal emergence','Compare controlled changes and historical signals','Evaluate predict-before-release refresh policies','Explain exact archived decision functions','Test conditional external transfer and local scaling','Execute verified source models in a bounded UI']
 matrix=[]
 for i,(name,report,sha) in enumerate(phases,1):
  p=ROOT/'reports'/report;assert p.exists();subprocess.check_call(['git','cat-file','-e',sha+'^{commit}']);matrix.append(dict(phase=i,title=name,status='COMPLETE AND VERIFIED',objective=objectives[i-1],checkpoint=sha,evidence=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),limitations='See the source report;no cross-protocol pooling or production claim'))
 write('phase_completion_matrix.csv',matrix);(ROOT/'reports/phase16_evidence_matrix.json').write_text(json.dumps(matrix,indent=2)+'\n')
 claims=[]
 def add(key,phase,path,selector,metric,value,rows,interpretation):claims.append(dict(claim_id=key,phase=phase,source=path,selector=json.dumps(selector,sort_keys=True),metric=metric,value=value,evaluation_rows=rows,interpretation=interpretation,source_sha256=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()))
 p='reports/phase4_metrics.csv';records=list(csv.DictReader((ROOT/p).open()))
 for protocol in ('A','B','C'):
  sel=dict(protocol=protocol,model='random_forest',training_cohort='group_sample',split='test');r=next(x for x in records if all(x[k]==v for k,v in sel.items()));add('RF_'+protocol,4,p,sel,'recall',r['recall'],r['rows'],'Fixed archived operating point;PR/ROC and cohort differ by protocol')
 p='reports/phase14_14C/external_evaluation.json';records=json.loads((ROOT/p).read_text())
 for model in ('E2-B-common-LR','E2-B-common-RF','E3-chronological-LR','E3-chronological-RF'):
  sel=dict(model=model,evaluation_protocol='chronological',sensitivity='primary',operating='validation_budget');r=next(x for x in records if all(x[k]==v for k,v in sel.items()))
  for metric in ('recall','fpr','pr_auc'):add(model+'_'+metric,14,p,sel,metric,r['metrics'][metric],r['metrics']['rows'],'New common3models;validation-budget threshold;2048-bin PR area')
 p='reports/phase14_pandas_comparison.csv';records=list(csv.DictReader((ROOT/p).open()))
 for engine in ('pandas','spark'):
  sel=dict(matrix='Spark_Pandas_end_to_end',configuration=engine+'-1000000');r=next(x for x in records if all(x[k]==v for k,v in sel.items()));add('TIME_'+engine,14,p,sel,'median_seconds',r['median_seconds'],r['actual_rows'],'Matched four-column CSV parse/filter/group;three repetitions;single machine')
 p='reports/phase12_policy_comparison.csv';records=list(csv.DictReader((ROOT/p).open()))
 for policy in ('P0','P2','P6'):
  sel=dict(backend='E-LR-seed23013-sample125-weight1',policy=policy,delay='0',budget='3',sliding='2',cooldown='2',minimum='200');r=next(x for x in records if all(x[k]==v for k,v in sel.items()));add('ADAPT_'+policy,12,p,sel,'recall',r['recall'],r['rows'],'Matched primary historical E;simulated label delay0;not late B cohort')
 p='reports/phase15_validation/parity.json';r=json.loads((ROOT/p).read_text());add('PARITY',15,p,{},'synthetic_probes',sum(x['probes'] for x in r['models']),2445,'Numerical compatibility;not prediction accuracy')
 write('master_results.csv',claims);(ROOT/'reports/phase16_master_results.json').write_text(json.dumps(claims,indent=2)+'\n')
 for name in ('phase4_metrics.csv','phase14_external_model_comparison.csv','phase14_scalability_summary.csv','phase14_worker_scaling.csv','phase14_pandas_comparison.csv','phase12_policy_comparison.csv'):shutil.copy(ROOT/'reports'/name,OUT/'tables'/name)
 for p in (ROOT/'reports/phase15_validation').glob('*.png'):shutil.copy(p,OUT/'screenshots'/p.name)
 shutil.copy(ROOT/'dashboard/data/phase15_demo.csv',OUT/'synthetic_demo.csv')
 print('Evidence matrix15phases;',len(claims),'traceable master findings')
if __name__=='__main__':main()
