"""Reproducible final aggregate tables from stage CSVs and verified receipts."""
import csv,json,math,hashlib,sys
from pathlib import Path
from collections import defaultdict
from export_phase12_evidence import csv_write
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));R=ROOT/'reports'

def read(path):return list(csv.DictReader(path.open())) if path.exists() else []
def number(v):return float(v) if v not in ('',None) else None

def main():
    stages=[R/f'phase12_{s}' for s in ('12C','12D','12E')]
    mapping={'policy_comparison':'policy_comparison','prequential_metrics':'windows','training_events':'events',
             'trigger_events':'triggers','model_registry':'models','threshold_history':'thresholds',
             'retention':'retention','family_windows':'family'}
    tables={}
    for target,source in mapping.items():
        rows=[r for stage in stages for r in read(stage/(source+'.csv'))]
        if target=='model_registry':rows=list({r['model']:r for r in rows}.values())
        tables[target]=rows;csv_write(R/f'phase12_{target}.csv',rows)
    policies=tables['policy_comparison'];windows=tables['prequential_metrics'];models=tables['model_registry']
    summaries={r['run']:r for r in policies}
    baselines={(r['backend'],r['delay']):r for r in policies if r['policy']=='P0'}
    comparisons=[]
    for r in policies:
        baseline=baselines.get((r['backend'],r['delay']))
        if baseline:
            delta_tp=int(r['tp'])-int(baseline['tp']);delta_fp=int(r['fp'])-int(baseline['fp'])
            comparisons.append(r|{'additional_tp':delta_tp,'additional_fp':delta_fp,
                'charged_seconds_per_additional_tp':float(r['charged_fit_seconds'])/delta_tp if delta_tp>0 else None,
                'charged_seconds_per_avoided_fp':float(r['charged_fit_seconds'])/(-delta_fp) if delta_fp<0 else None})
    csv_write(R/'phase12_robustness.csv',comparisons)
    csv_write(R/'phase12_label_delay.csv',[r for r in policies if r['backend']=='E-LR-seed23013-sample125-weight1' and r['budget']=='3'])
    # Final-label diagnostic and released-only diagnostic stay distinct.
    released=[]
    from src.ml.threshold_calibration import metrics
    for run,s in summaries.items():
        eligible=[w for w in windows if w['run']==run and int(w['label_release_index'])<int(s['windows'])]
        c={k:sum(int(w[k]) for w in eligible) for k in ('tp','tn','fp','fn')}
        released.append({'run':run,'scope':'released-by-last-arrival','released_windows':len(eligible),**metrics(c['tp'],c['tn'],c['fp'],c['fn'])})
    csv_write(R/'phase12_released_only_metrics.csv',released)
    # Family, coverage, and exposure are derived without pooling incompatible populations.
    grouped=defaultdict(list)
    for row in tables['family_windows']:grouped[(row['run'],row['family'])].append(row)
    model_by_id={r['model']:r for r in models};sample_cohorts={}
    for stage in stages:
        receipt=json.loads((stage/'receipt.json').read_text()) if (stage/'receipt.json').exists() else {}
        sample_cohorts.update(receipt.get('sample_cohorts',{}))
    families=[]
    for (run,family),rows in grouped.items():
        s=summaries[run];initial=model_by_id[s['initial_model']]
        support=json.loads(initial.get('family_support','{}')).get(family,0)
        sampled=[c for c in sample_cohorts.get(s['backend'],[]) if c['attack_family']==family]
        forward_days=sorted({w['day'] for w in windows if w['run']==run})
        released_days=set(forward_days[:len(forward_days)-int(s['delay'])] if int(s['delay']) else forward_days)
        forward=[c for c in sampled if c['source_day'] in released_days]
        tp=sum(int(r['tp']) for r in rows);fn=sum(int(r['fn']) for r in rows)
        first=min((c['source_day'] for c in forward if c['count']>0),default=None)
        families.append({'run':run,'policy':s['policy'],'delay':s['delay'],'backend':s['backend'],'family':family,
                         'initial_training_support':support,'newly_released_training_support':sum(c['count'] for c in forward),
                         'first_forward_fit_exposure_capture':first,'evaluation_support':tp+fn,'tp':tp,'fn':fn,
                         'recall':tp/(tp+fn) if tp+fn else None,'served_versions':sorted({r['model'] for r in rows}),
                         'interpretation':'capture/family confounded; exposure must precede activation, no later appearance implies unsupported forward learning'})
    csv_write(R/'phase12_family_metrics.csv',families)
    coverage=[]
    for run,s in summaries.items():
        grouped_windows=defaultdict(list)
        for w in windows:
            if w['run']==run:grouped_windows[w['model']].append(w)
        for model,rows in grouped_windows.items():
            coverage.append({'run':run,'policy':s['policy'],'model':model,'windows':len(rows),'rows':sum(int(w['rows']) for w in rows),
                             'window_indices':[int(w['window']) for w in rows],'days':[w['day'] for w in rows]})
    csv_write(R/'phase12_version_coverage.csv',coverage)
    lifecycle=[]
    for s in policies:
        observed=[w for w in windows if w['run']==s['run']]
        decisions=[e for e in tables['training_events'] if e['run']==s['run']]
        identifiers={w['model'] for w in observed}|{e['model'] for e in decisions if e.get('model')}
        for identifier in identifiers:
            issued=[w for w in observed if w['model']==identifier]
            events=[e for e in decisions if e.get('model')==identifier]
            lifecycle.append({'run':s['run'],'model':identifier,'initial':identifier==s['initial_model'],
                'served_windows':[int(w['window']) for w in issued],
                'parent_models':sorted({e.get('parent','') for e in events if e.get('parent')}),
                'threshold_bins':sorted({int(w['threshold_bin']) for w in issued}),
                'promotion_calibration_populations':[e.get('calibration_days') for e in events],
                'decisions':[e.get('decision') for e in events],
                'status':'served-forward' if issued else 'accepted-pending' if any(e.get('accepted')=='True' for e in events) else 'rejected',
                'last_inference_day':max((w['day'] for w in issued),default=None)})
    csv_write(R/'phase12_model_lifecycle.csv',lifecycle)
    performance=[r|{'scope':'physical-scoring'} for stage in stages for r in read(stage/'scoring.csv')]
    for r in models:
        performance.append({'scope':'physical-fit','model':r['model'],'backend':r['backend'],'rows':r['rows'],
            **{k:r.get(k) for k in ('fit_seconds','preprocessing_seconds','training_seconds','save_reload_seconds')}})
    for r in policies:
        performance.append({'scope':'counterfactual-policy','run':r['run'],'backend':r['backend'],'policy':r['policy'],
            **{k:r.get(k) for k in ('charged_fit_seconds','score_seconds','detector_seconds','registry_seconds','rows')},
            'scoring_flows_per_second':None,
            'cache_caveat':'cached histogram calls are included; individual first-materialization durations reside in notebook outputs'})
    csv_write(R/'phase12_performance.csv',performance)
    synthetic=read(R/'phase12_synthetic/policy_comparison.csv');csv_write(R/'phase12_synthetic_metrics.csv',synthetic)
    sw=read(R/'phase12_synthetic/windows.csv');recovery=[]
    for s in synthetic:
        rows=[w for w in sw if w['run']==s['run']]
        before=[w for w in rows if int(w['day'])<22]
        pre_tp=sum(int(w['tp']) for w in before);pre_fn=sum(int(w['fn']) for w in before)
        target=pre_tp/(pre_tp+pre_fn)-.05 if pre_tp+pre_fn else None
        post=[w for w in rows if int(w['day'])>=22];recovered=None
        for i in range(len(post)-2):
            group=post[i:i+3];tp=sum(int(w['tp']) for w in group);fn=sum(int(w['fn']) for w in group)
            if target is not None and tp+fn and tp/(tp+fn)>=target:
                recovered=int(group[-1]['day'])-22;break
        recovery.append({'run':s['run'],'mechanism':s['backend'].split('-seed')[0],'policy':s['policy'],'delay':s['delay'],
            'prechange_recall':None if target is None else target+.05,'recovery_windows':recovered,
            'definition':'first postchange 3-window block ending with pooled recall >= prechange recall-.05; stationary and input shifts are controls, not loss/recovery proof'})
    csv_write(R/'phase12_synthetic_recovery.csv',recovery)
    print('Final tables',len(policies),'historical policies',len(synthetic),'synthetic runs')
if __name__=='__main__':main()
