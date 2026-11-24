"""Render measured Phase 11 results with explicit stream units."""
import csv,json
from collections import defaultdict
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1];R=ROOT/'reports'
def read(name):return list(csv.DictReader((R/name).open()))
def save(fig,name):
 fig.savefig(R/'figures'/('phase11_'+name+'.png'),dpi=125,bbox_inches='tight');plt.close(fig)
metrics=read('phase11_synthetic/synthetic_metrics.csv');alerts=read('phase11_synthetic/alerts.csv');signals=read('phase11_synthetic/signals.csv')
methods=('ADWIN','PageHinkley','KSWIN','DDM','JS','PSI','FixedJS')
for method in methods:
 scenario='error' if method=='DDM' else 'abrupt'
 sample=[r for r in signals if r['scenario']==scenario]
 fig,ax=plt.subplots(figsize=(8,3));ax.plot([int(r['index']) for r in sample],[int(r['error']) if method=='DDM' else float(r['signal']) for r in sample],linewidth=.7)
 for r in alerts:
  if r['scenario']==scenario and r['seed']=='23013' and r['detector']==method and r['label_delay_windows']=='0':ax.axvline(int(r['alert_index']),color='#b74d37',alpha=.4)
 ax.axvline(2048,color='black',linestyle='--');ax.set(xlabel='Synthetic observation index',ylabel='Binary error' if method=='DDM' else 'Bounded signal',title=method+' · controlled '+scenario+' · seed 23013');save(fig,method.lower()+'_detections')
for field,title,subset in [('mean_delay_observations','Mean matched detection delay',lambda r:r['label_delay_windows']=='0'),('false_alarms','False alarms on stationary evaluation',lambda r:r['scenario']=='stationary' and r['label_delay_windows']=='0'),('seconds','Measured synthetic processing seconds',lambda r:r['label_delay_windows']=='0')]:
 values=[]
 for method in methods:
  points=[float(r[field]) for r in metrics if r['detector']==method and subset(r) and r[field]!=''];values.append(sum(points)/len(points) if points else float('nan'))
 fig,ax=plt.subplots(figsize=(8,4));ax.bar(methods,values);ax.set(ylabel='Mean false alarms per seed (3840 eligible arrivals)' if field=='false_alarms' else field.replace('_',' '),title=title+(' · detector-specific target sets' if field=='mean_delay_observations' else ''));save(fig,field)
fig,ax=plt.subplots(figsize=(7,4))
for scenario,color in (('error','#176c82'),('concept','#b54e38')):
 for delay in (0,1,3):
  points=[float(r['mean_delay_observations']) for r in metrics if r['detector']=='DDM' and r['scenario']==scenario and int(r['label_delay_windows'])==delay and r['mean_delay_observations']!='']
  if points:ax.scatter([delay]*len(points),points,color=color,label=scenario if delay==0 else None)
ax.set(xlabel='Simulated label delay in 64-observation windows',ylabel='Detection delay in observations',title='DDM label-delay sensitivity');ax.legend();save(fig,'label_delay')
history=read('phase11_historical/historical_alerts.csv')
fig,ax=plt.subplots(figsize=(9,4))
labels=sorted({r['detector']+' / '+r['signal'] for r in history if r['alert']=='True'})
for index,label in enumerate(labels):
 points=[int(r['batch']) for r in history if r['alert']=='True' and r['detector']+' / '+r['signal']==label]
 ax.scatter(points,[index]*len(points),marker='|',s=120)
ax.set(yticks=range(len(labels)),yticklabels=labels,xlabel='Historical replay batch index',title='Retrospective aggregate-window alerts');save(fig,'historical_timeline')
sensitivity=read('phase11_robustness/sensitivity.csv');fig,ax=plt.subplots(figsize=(7,4))
for method in ('JS','PSI'):
 points=[]
 for window in (32,64,128):
  rows=[r for r in sensitivity if r['detector']==method and int(r['window'])==window];points.append(sum(int(r['detected_episodes']) for r in rows)/len(rows))
 ax.plot((32,64,128),points,'o-',label=method)
ax.set(xlabel='Synthetic histogram window observations',ylabel='Episode detection fraction',title='Window and magnitude sensitivity');ax.legend();save(fig,'window_sensitivity')
report=['# Phase 11 drift detection results','','Synthetic evaluation and retrospective historical monitoring have separate targets and units. Stationary calibration seeds differ from all evaluation seeds.','','| Detector | Stationary false alarms, three seeds | Abrupt/error matched delays in observations |','|---|---:|---|']
for method in methods:
 stationary=[r for r in metrics if r['detector']==method and r['scenario']=='stationary' and r['label_delay_windows']=='0']
 scenario='error' if method=='DDM' else 'abrupt';data=[r['mean_delay_observations'] or 'NA' for r in metrics if r['detector']==method and r['scenario']==scenario and r['label_delay_windows']=='0']
 report.append(f"| {method} | {sum(int(r['false_alarms']) for r in stationary)} | {', '.join(data)} |")
report+=['','The synthetic suite contains 297 detector/scenario/label-delay comparisons over three evaluation seeds. DDM targets predictive-error episodes. Other detectors target their observed signal distribution. Alert counts have one-to-one event matching, separate repeated episode alerts and undefined missed-event delays. Faster detection must be assessed alongside excess alarms.','','## Historical evidence','','The saved Spark replay contains 49 batches representing 15,322,987 flows. Two capture-only batches preserve fourteen timestamp anomalies and fail the 100-row monitoring support minimum. Reference batches 0–2 and calibration batches 3–9 precede evaluation. These are aggregate windows. Historical DDM is unsupported without binary error ordering. Historical KSWIN cannot complete its 100-observation warm-up. No historical true-drift labels support efficacy or false-positive claims. Aggregate-error updates respect simulated release delays of zero, one and three windows.','','## Robustness and engineering','','The sensitivity grid contains 36 JS/PSI comparisons over windows 32, 64 and 128, two magnitudes and three seeds. Ensemble and no-detector ablations are separate. All four River states passed snapshot/restore and duplicate-batch suppression checks. Serialized state bytes and bounded update times appear in the evidence tables. They do not measure complete process resident memory or multi-node scalability.','','## Limits and completion','','Distribution shifts, model-score changes and predictive-error changes have distinct interpretations. Historical observations are retrospective and family/day-confounded. Synthetic alerts do not confirm attacks. The experiment manifest is the authoritative completion gate for Phase 12.']
(R/'phase11_results.md').write_text('\n'.join(report)+'\n')
print('Rendered Phase 11 measured figures and report')
