"""Reproducible final Phase 11 tables, figures and scientific report."""
from collections import defaultdict
from pathlib import Path
import csv,json,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1];R=ROOT/'reports';F=R/'phase11_finalization'
def read(name):return list(csv.DictReader((F/name).open()))
def old(name):return list(csv.DictReader((R/name).open()))
def save(fig,name):
 fig.savefig(R/'figures'/('phase11_'+name+'.png'),dpi=125,bbox_inches='tight',metadata={'Software':'MMDS Phase 11'});plt.close(fig)
def mean(rows,key):
 values=[float(r[key]) for r in rows if r.get(key) not in ('',None)]
 return sum(values)/len(values) if values else None

def csvout(name,rows):
 keys=list(dict.fromkeys(k for r in rows for k in r))
 with (F/name).open('w',newline='') as file:
  w=csv.DictWriter(file,fieldnames=keys,lineterminator='\n');w.writeheader();w.writerows(rows)

primary=old('phase11_synthetic/synthetic_metrics.csv');comparison=[]
signals=old('phase11_synthetic/signals.csv')
scenarios=sorted({row['scenario'] for row in signals})
fig,axes=plt.subplots(4,3,figsize=(13,10),layout='constrained')
for ax,scenario in zip(axes.flat,scenarios):
 rows=[row for row in signals if row['scenario']==scenario]
 field='error' if scenario in ('error','concept') else 'signal'
 ax.plot([int(row['index']) for row in rows],[float(row[field]) for row in rows],linewidth=.7)
 if scenario!='stationary':ax.axvline(2048,color='black',linestyle='--',linewidth=.8)
 if scenario=='recurring':ax.axvline(3072,color='black',linestyle='--',linewidth=.8)
 ax.set(title=scenario,xlabel='Original synthetic arrival',ylabel='Binary error' if field=='error' else 'Bounded monitored signal')
for ax in list(axes.flat)[len(scenarios):]:ax.axis('off')
fig.suptitle('Declared synthetic mechanisms · seed 23013 · every 16th arrival; dashed lines mark known episode starts')
save(fig,'synthetic_mechanisms')
for detector in ('ADWIN','PageHinkley','KSWIN','DDM','JS','PSI','FixedJS'):
 rows=[r for r in primary if r['detector']==detector and r['label_delay_windows']=='0'];stationary=[r for r in rows if r['scenario']=='stationary'];events=sum(int(r['true_episodes']) for r in rows)
 comparison.append({'detector':detector,'target':'released binary error episodes' if detector=='DDM' else 'feature-signal episodes','events':events,'detected':sum(int(r['detected_episodes']) for r in rows),'misses':sum(int(r['misses']) for r in rows),'stationary_false_alarms':sum(int(r['false_alarms']) for r in stationary),'stationary_eligible_arrivals':3*(4096-256),'mean_detected_delay_arrivals':mean(rows,'mean_delay_observations'),'mean_processing_seconds_per_stream':mean(rows,'seconds')})
csvout('detector_comparison.csv',comparison)
reference=read('reference.csv');fig,axes=plt.subplots(1,2,figsize=(12,4),layout='constrained')
for detector in ('ADWIN','PageHinkley','KSWIN','DDM','JS','PSI'):
 points=[];false=[]
 for length in (64,256,512):
  # Warm-up uniquely identifies each grid position, including KSWIN's 100 minimum.
  rows=[r for r in reference if r['detector']==detector and int(r['warmup'])==max(length,100 if detector=='KSWIN' else 0)]
  events=sum(int(r['true_episodes']) for r in rows);points.append(sum(int(r['detected_episodes']) for r in rows)/events)
  false.append(mean([r for r in rows if r['scenario']=='stationary'],'false_per_1000'))
 axes[0].plot((64,256,512),points,'o-',label=detector);axes[1].plot((64,256,512),false,'o-',label=detector)
axes[0].set(xlabel='Reference length (JS/PSI) or reporting warm-up arrivals',ylabel='Matched episode fraction',title='Synthetic reference and warm-up sensitivity');axes[1].set(xlabel='Reference length or reporting warm-up arrivals',ylabel='Stationary false alarms per 1000 eligible arrivals');axes[0].legend(fontsize=8,ncols=2);save(fig,'reference_sensitivity')
reset=read('reset.csv');fig,axes=plt.subplots(1,2,figsize=(11,4),layout='constrained');policies=('native_continuation','external_reset','cooldown_64')
for detector in ('ADWIN','PageHinkley','KSWIN','DDM'):
 values=[];false=[]
 for policy in policies:
  rows=[r for r in reset if r['detector']==detector and r['policy']==policy];values.append(sum(int(r['detected_episodes']) for r in rows)/sum(int(r['true_episodes']) for r in rows));false.append(sum(int(r['false_alarms']) for r in rows))
 axes[0].plot(policies,values,'o-',label=detector);axes[1].plot(policies,false,'o-',label=detector)
axes[0].set(ylabel='Matched recurring episode fraction',title='Synthetic reset-policy comparison');axes[1].set(ylabel='Excess alerts over three seeds',title='Native state updates continue during cooldown')
for ax in axes:ax.tick_params(axis='x',rotation=20)
axes[0].legend(fontsize=8);save(fig,'reset_sensitivity')
missing=read('missing.csv');fig,ax=plt.subplots(figsize=(9,4));profiles=sorted({r['profile'] for r in missing})
for policy in sorted({r['policy'] for r in missing}):
 values=[mean([r for r in missing if r['policy']==policy and r['profile']==profile],'mean_delay_observations') for profile in profiles]
 ax.plot(profiles,[v if v is not None else np.nan for v in values],'o-',label=policy)
ax.set(ylabel='Mean matched delay in original arrival observations',title='Synthetic missing inputs · indicator policy targets missingness');ax.tick_params(axis='x',rotation=20);ax.legend(fontsize=8);save(fig,'missing_sensitivity')
support=read('support.csv');fig,ax=plt.subplots(figsize=(7,4))
for signal in ('rf_score_counts_32','cluster_counts'):
 counts=[sum(r['eligible']=='True' for r in support if r['signal']==signal and r['detector']=='JS' and int(r['minimum_support'])==n) for n in (1,100,1000,10000)]
 ax.plot((1,100,1000,10000),counts,'o-',label=signal)
ax.set(xscale='log',xlabel='Minimum valid flow observations per window',ylabel='Eligible replay windows out of 49',title='Historical support eligibility · suppression is unavailable');ax.legend(fontsize=8);save(fig,'support_sensitivity')
agreement=read('agreement.csv');methods=('ADWIN','PageHinkley','KSWIN','JS','PSI','FixedJS');matrix=np.full((6,6),np.nan)
for i,a in enumerate(methods):
 for j,b in enumerate(methods):
  if a==b:matrix[i,j]=1;continue
  rows=[r for r in agreement if r['population']=='synthetic' and {r['first'],r['second']}=={a,b}];shared=sum(int(r['shared_positive']) for r in rows);union=sum(int(r['shared_positive'])+int(r['first_only'])+int(r['second_only']) for r in rows)
  if union:matrix[i,j]=shared/union
fig,ax=plt.subplots(figsize=(7,6));im=ax.imshow(matrix,vmin=0,vmax=1);ax.set(xticks=range(6),yticks=range(6),xticklabels=methods,yticklabels=methods,title='Synthetic label-free alert Jaccard · matched 64-arrival intervals');fig.colorbar(im,ax=ax,label='Shared positive intervals / positive union');save(fig,'agreement_heatmap')
association=read('association.csv');fields=('recall','precision','f1','fpr','error','predicted_rate','pr_auc','prevalence');fig,axes=plt.subplots(1,2,figsize=(12,4),layout='constrained')
for ax,stat in zip(axes,('pearson','spearman')):
 matrix=[]
 for detector in ('JS','PSI'):
  matrix.append([next(float(r[stat]) if r[stat] else np.nan for r in association if r['detector']==detector and r['performance_metric']==metric and r['lag_windows']=='0' and r['label_delay_windows']=='0') for metric in fields])
 im=ax.imshow(matrix,vmin=-1,vmax=1,cmap='coolwarm',aspect='auto');ax.set(xticks=range(len(fields)),xticklabels=fields,yticks=(0,1),yticklabels=('JS','PSI'),title='Historical '+stat+' · lag 0, immediate labels');ax.tick_params(axis='x',rotation=50)
fig.colorbar(im,ax=axes,label='Descriptive correlation, 22–36 supported window pairs');save(fig,'performance_association')
costs=read('costs.csv');fig,axes=plt.subplots(1,2,figsize=(10,4),layout='constrained')
for ax,field,title in zip(axes,('state_bytes','snapshot_seconds'),('Serialized state bytes','Snapshot seconds')):
 values=[mean([r for r in costs if r['detector']==detector],field) for detector in methods[:3]+('DDM',)];ax.bar(methods[:3]+('DDM',),values);ax.set(ylabel=title,title='Bounded CPU experiment · '+title)
save(fig,'state_overhead')
scenarios=sorted({r['scenario'] for r in primary});matrix=[]
for detector in ('ADWIN','PageHinkley','KSWIN','DDM','JS','PSI','FixedJS'):
 matrix.append([mean([r for r in primary if r['detector']==detector and r['scenario']==scenario and r['label_delay_windows']=='0'],'mean_delay_observations') for scenario in scenarios])
fig,ax=plt.subplots(figsize=(11,5));im=ax.imshow([[np.nan if v is None else v for v in row] for row in matrix],aspect='auto');ax.set(xticks=range(len(scenarios)),xticklabels=scenarios,yticks=range(7),yticklabels=('ADWIN','PageHinkley','KSWIN','DDM','JS','PSI','FixedJS'),title='Synthetic matched delay · blank means undefined or no target detection');ax.tick_params(axis='x',rotation=40);fig.colorbar(im,ax=ax,label='Arrival observations');save(fig,'delay_by_scenario')
ablations=old('phase11_robustness/ablations.csv')
labels=[];misses=[];excess=[]
for detector in methods+('two-family-64-observation-ensemble','no_detector'):
 rows=[r for r in (ablations if detector in ('two-family-64-observation-ensemble','no_detector') else primary) if r['detector']==detector and r.get('label_delay_windows','0')=='0']
 labels.append(detector);misses.append(sum(int(r['misses']) for r in rows));excess.append(sum(int(r['false_alarms']) for r in rows))
fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained')
axes[0].barh(labels,misses);axes[0].set(xlabel='Missed feature-signal episodes out of 27',title='Matched synthetic detector and control populations')
axes[1].barh(labels,excess);axes[1].set(xlabel='Excess alerts over the same 33 synthetic streams',title='Misses and alarm burden require joint assessment');save(fig,'ensemble_and_misses')
registry=json.loads((ROOT/'manifests/phase11_detectors.json').read_text())
fig,ax=plt.subplots(figsize=(9,5));applicability=[]
for entry in registry['detectors']:
 name=entry['identifier'];applicability.append([1,0 if name in ('KSWIN','DDM') else 1,1 if name in ('ADWIN','PageHinkley') else 0])
ax.imshow(applicability,vmin=0,vmax=1,cmap='Greens',aspect='auto')
for i,row in enumerate(applicability):
 for j,value in enumerate(row):ax.text(j,i,'Validated' if value else 'Unsupported' if j==1 or registry['detectors'][i]['identifier'] in ('DDM','KSWIN') else 'Outside evaluated signal',ha='center',va='center',fontsize=8,color='white' if value else '#243237')
ax.set(xticks=(0,1,2),xticklabels=('Synthetic declared targets','Historical score windows','Released aggregate error rates'),yticks=range(6),yticklabels=[e['identifier'] for e in registry['detectors']],title='Detector applicability · categories express evidence availability');save(fig,'applicability')

lines=['# Phase 11 advanced drift detection results','','## Objectives and protocol','','This study compares controlled synthetic change detection with retrospective monitoring of previously examined network captures. The original phase11-v1 protocol and primary results are preserved. The finalization sensitivity plan was committed before its supplemental experiments. Historical distribution changes have no authoritative concept-drift labels.','','## Data and signal provenance','','The verified Phase 6 Spark evidence represents 15,322,987 retained flows in 49 batches. Four batches have fewer than 100 flows: two capture-only anomaly batches with five and nine flows, and two ordinary intraday batches with 50 and 53. The default historical monitor updates on 45 supported windows. The evaluation subset has 36 supported windows, with attack-dependent metrics absent on some windows. Eighteen primary predictors remain unchanged. No raw dataset was downloaded for this finalization.','','## Implementation and experimental populations','','River 0.22.0 supplies ADWIN, Page-Hinkley, KSWIN and binary DDM. JS uses base-two logarithms and PSI natural logarithms, with 1e-6 count smoothing. Synthetic reference bins and thresholds use independent calibration seeds. Synthetic evaluation uses seeds 23013–23015, 4096 arrivals and a primary warm-up of 256. DDM targets released binary-error episodes. Other detectors target the observed feature signal, including explicit missingness or prior signals where declared. Native reset semantics remain intact unless the supplemental external-reset policy explicitly reconstructs a detector.','','## Synthetic effectiveness and stationary alarms','','| Detector | Target episodes | Detected | Missed | Stationary false alarms / 11,520 eligible arrivals | Mean detected delay in arrivals |','|---|---:|---:|---:|---:|---:|']
for row in comparison:lines.append(f"| {row['detector']} | {row['events']} | {row['detected']} | {row['misses']} | {row['stationary_false_alarms']} | {row['mean_detected_delay_arrivals']:.2f} |")
lines+=['','The mean delay averages detected stream/episode summaries and is undefined when no episode is detected. The table uses zero simulated label delay. DDM has a different target set and cannot be ranked directly against feature detectors by this average. KSWIN detects abrupt shifts quickly but produces more stationary alarms than ADWIN or Page-Hinkley. No detector consistently dominates across target mechanisms, missingness policies and cost. Positive shifts in the controlled feature-label relationship are synthetic concept experiments and provide no independent real-traffic confirmation.','','## Label timing and historical monitoring','','DDM consumes binary errors only after their simulated release at zero, one or three 64-arrival windows. Historical aggregate-error updates respect the analogous replay-window clock. Unreleased labels at stream end remain pending. Historical binary DDM is unsupported because original within-window error order was not saved. Historical KSWIN cannot satisfy its fixed 100-observation warm-up within 49 windows. These are documented methodological limitations, not successful no-drift outcomes.','','## Reference and warm-up sensitivity','','The supplemental grid contains 162 comparisons across reference lengths or reporting warm-ups of 64, 256 and 512. JS/PSI change their independently calibrated reference. Adaptive methods retain native updates and vary reporting eligibility, including KSWIN’s minimum of 100. This adaptive comparison changes excluded warm-up support, not the internal algorithm. Eligible-arrival denominators are 4096 minus effective warm-up. Repeated alerts within a 512-arrival event horizon are separate from matched detections and excess alerts.','','## Reset sensitivity','','Native continuation and explicit external reset each detected 21 of 24 recurring episodes across detector/seed combinations and produced nine excess alerts. Explicit reset performed 36 external reconstructions. Native continuation performs no additional reset. Cooldown preserved 21 detected episodes and suppressed one raw alert; all native state updates continued. Thus suppression and resetting are distinct operations. DDM may miss error-rate decreases, consistent with its error-increase orientation.','','## Missing-input sensitivity','','There are 132 comparisons over random missingness, a consecutive burst, post-change missingness and nonfinite arrivals. Skip and reference-median policies detected all 36 feature targets in their respective grids. Histogram support suppression missed six of 24 targets. The indicator policy targets missingness transitions and missed three of 27 targets. These denominators describe different signals. Delay is in original arrival observations; valid-observation delay and effective update counts are separate columns. No invalid input is silently replaced by zero. Unavailable update results remain distinct from negative alerts.','','Under the prespecified 512-arrival event horizon, skip generated 18 excess alerts and reference-median imputation 22. The missingness-indicator grid generated two excess alerts over its distinct targets. Histogram support handling generated 445 excess alerts while detecting 18 of 24 targets. Fixed-reference breaches can persist after a change; this event metric records their continuing alert workload. The separate stationary experiments provide the no-change false-alarm benchmark.', '', '## Minimum-support sensitivity','','RF and cluster histogram eligibility changes from 49 windows at minimum support one to 45 at 100, 44 at 1000 and 43 at 10000. Saved feature-JS, released error support, capture-level pattern support and family-label support have separate records and units. Zero-support family strata remain unavailable. Suppressed windows have null alert fields. No historical false-alarm rate is inferred without event truth.','','## Detector agreement','','There are 495 matched synthetic pair/scenario/seed comparisons plus seven compatible historical comparisons. Synthetic pairs use 60 post-warm-up intervals of 64 arrivals. DDM is excluded from feature-signal agreement because it observes a different signal. Exact-interval agreement is distinct from one-to-one positive matches within one interval. Historical comparisons retain only mutually supported windows after native warm-up. JS and PSI share one positive and 35 negative historical histogram intervals, yielding Jaccard and kappa one in that narrow comparison. ADWIN/Page-Hinkley comparisons have 16 supported score-mean intervals and 16, 15 or 13 released-error intervals depending on label delay; all-zero Jaccard and kappa remain undefined. Agreement alone does not establish correctness.','','## Association with observed performance','','The 144 association summaries cover JS/PSI and eight RF outcome measures at lags zero, one and three, with three label-release assumptions. The paired table records source, outcome, release and analysis clocks. At contemporaneous immediate-label settings, JS/error Pearson is 0.0219 and PSI/error Pearson 0.0232 over 36 paired windows. For recall, Pearson values are 0.4606 and 0.2345 over 22 pairs, while rank associations are 0.0695 and −0.1679. Magnitude and direction depend on the metric and estimator. Row-weighted correlations and one-window before/after changes are descriptive. Capture gaps, changing prevalence, rare-family support and temporal dependence prevent causal or reliable future-failure claims. Family-specific window recall is unsupported by the saved aggregate schema.','','## Ensembles, costs and recovery','','The existing 66 ensemble/control ablations and 36 window/magnitude sensitivity records remain preserved. The ensemble is fixed at two detector families within 64 arrivals with cooldown. It is not selected on final outcomes. Initialization, update, snapshot and restore times and serialized state bytes are measured in 36 supplemental cost records. Process RSS is a cumulative process high-water mark, not isolated detector allocation. Historical costs are per supported aggregate window. No claim is made that advanced detectors individually processed all retained flows, or that single-node measurements demonstrate multi-node scalability. Four detector states passed trusted snapshot/reload and duplicate-batch checks.','','## Dashboard and scientific contribution','','The isolated Drift Detection Laboratory presents primary evidence and the supplemental grids, agreement, associations, costs and limitations. All downloads use filtered aggregate tables. The contribution is a reproducible monitoring comparison and explicit information-availability accounting using established detectors. Shift alerts are evidence to investigate, not confirmation of attacks or proof that adaptation will improve outcomes. Phase 12 has not started and requires separate user authorization.','','## Reproducibility and limitations','','Reuse Kaggle notebook versions 1 and 2 and their hashed receipts. Run `PYTHONPATH=. python -c "from src.drift.finalization import run; run(\'/tmp/phase11-finalization\')"` with the pinned River dependency to reproduce the bounded supplemental experiments. The original protocol, finalization plan, method definitions and registry describe frozen choices and unsupported cases. Regenerate final figures and this report with `python scripts/finalize_phase11_report.py`. Timings vary by host. Synthetic evidence, retrospective historical associations and future independent validation remain separate. The completed experiment manifest records the final gate, test results, hashes and protected-reference verification.']
lines += ['', '## State clocks, runtime compatibility and browser checks', '', 'The state adapter distinguishes arrivals, valid updates and suppressed updates, restores state after a failed batch, and leaves missing counters unknown in legacy snapshots. Additional engineering probes measure duplicate checks, snapshot/restore and alert-metadata construction separately from detector updates. The isolated preview runtime uses Starlette 0.49.3 with Streamlit 1.67.0 to avoid the observed Starlette 1.10.0 static-file failure. Browser evidence includes desktop and mobile screenshots, no HTTP or page errors, and actual 297-record downloads. Reference-score history includes retrospective scoring of the archived RF training population and supports no prospective deployment claim.']
validation=R/'phase11_validation/final_tests.json'
if validation.exists():
    verified=json.loads(validation.read_text())
    lines += ['', '## Final validation', '', f"The complete regression run passed {verified['research_tests']} research tests and {verified['dashboard_tests']} dashboard tests. Preview validation covered {verified['supported_filter_groups']} supported filter groups and {verified['preview_sections']} sections. No Phase 12 implementation was started."]
(R/'phase11_results.md').write_text('\n'.join(lines)+'\n')
print('Rendered final Phase 11 report, comparison table and supplemental figures')
