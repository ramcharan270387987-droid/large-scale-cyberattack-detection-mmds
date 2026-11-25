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
    design=json.loads((ROOT/'configs/phase12_adaptation.yaml').read_text())
    for model in models:
        family=model['family'];model['hyperparameters']=(design['lr']|{'standardization':False} if family=='LR' else design['rf'])|{'seed':int(model['backend'].split('-seed')[1].split('-')[0]),'positive_class_weight':int(model['backend'].split('-weight')[1])}
        model['feature_registry_version']='phase4-v1'
        model['training_population']='E permanent fitting predictor groups, sampled by predictor key'
        model['training_sample_policy']=model['backend'].split('-sample')[-1].split('-weight')[0]+'/10000'
        model['training_date_range']=[min(json.loads(model['training_days'])),max(json.loads(model['training_days']))]
        model['lifecycle_table']='reports/phase12_model_lifecycle.csv'
        for stage in stages:
            raw=read(stage/'models.csv')
            if any(r['model']==model['model'] for r in raw):
                version=json.loads((stage/'retrieval.json').read_text())['kernel_version']
                receipt=json.loads(model['receipt'])
                model['archive_location']=version+'/'+receipt['artifact']
                break
    csv_write(R/'phase12_model_registry.csv',models)
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
    model_by_id={r['model']:r for r in models};sample_cohorts={};all_families=set()
    for stage in stages:
        receipt=json.loads((stage/'receipt.json').read_text()) if (stage/'receipt.json').exists() else {}
        sample_cohorts.update(receipt.get('sample_cohorts',{}))
        all_families.update(row['attack_family'] for row in receipt.get('cohorts',[]))
    for run in summaries:
        for family in sorted(all_families):grouped.setdefault((run,family),[])
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
                         'first_forward_fit_exposure_capture':first,
                         'first_active_trained_family_index':min((int(w['window']) for w in windows if w['run']==run and json.loads(model_by_id[w['model']].get('family_support','{}')).get(family,0)>0),default=None),
                         'post_fitting_attack_evaluation_support':sum(int(r['tp'])+int(r['fn']) for r in rows if json.loads(model_by_id[r['model']].get('family_support','{}')).get(family,0)>0),
                         'evaluation_support':sum(sum(int(r[k]) for k in ('tp','fp','tn','fn')) for r in rows),'attack_evaluation_support':tp+fn,
                         'benign_evaluation_support':sum(int(r['tn'])+int(r['fp']) for r in rows),'tp':tp,'fn':fn,
                         'recall':tp/(tp+fn) if tp+fn else None,
                         'fp':sum(int(r['fp']) for r in rows),'tn':sum(int(r['tn']) for r in rows),
                         'fpr':sum(int(r['fp']) for r in rows)/sum(int(r['fp'])+int(r['tn']) for r in rows) if sum(int(r['fp'])+int(r['tn']) for r in rows) else None,
                         'served_versions':sorted({r['model'] for r in rows}),
                         'interpretation':'capture/family confounded; exposure must precede activation, no later appearance implies unsupported forward learning'})
    csv_write(R/'phase12_family_metrics.csv',families)
    exposures=[]
    for (run,family),rows in grouped.items():
        summary=summaries[run]
        cohort=sample_cohorts.get(summary['backend'],[])
        eligible=[c for c in cohort if c['attack_family']==family and c['count']>0]
        initial_support=json.loads(model_by_id[summary['initial_model']].get('family_support','{}')).get(family,0)
        forward_days=sorted({w['day'] for w in windows if w['run']==run})
        releases=[forward_days.index(c['source_day'])+int(summary['delay']) for c in eligible if c['source_day'] in forward_days]
        first_release=min(releases,default=None)
        for basis in ('labels-available-before-arrival','family-represented-in-active-training'):
            by_state=defaultdict(list)
            for row in rows:
                represented=json.loads(model_by_id[row['model']].get('family_support','{}')).get(family,0)>0
                available=initial_support>0 or (first_release is not None and int(row['window'])>first_release)
                after=available if basis=='labels-available-before-arrival' else represented
                by_state['after' if after else 'before'].append(row)
            if not rows:by_state['unsupported-no-forward-rows']=[]
            for state,subset in by_state.items():
                count={k:sum(int(r[k]) for r in subset) for k in ('tp','fp','tn','fn')}
                positives=count['tp']+count['fn'];benign=count['tn']+count['fp']
                exposures.append({'run':run,'policy':summary['policy'],'delay':summary['delay'],'family':family,
                    'exposure_basis':basis,'period':state,'first_forward_release_after_prediction_index':first_release,
                    'initial_fitting_support':initial_support,'rows':sum(count.values()),**count,
                    'recall':count['tp']/positives if positives else None,'fpr':count['fp']/benign if benign else None,
                    'versions':sorted({r['model'] for r in subset}),'windows':sorted({int(r['window']) for r in subset}),
                    'interpretation':'No after rows means post-exposure forward learning is unsupported.'})
    csv_write(R/'phase12_family_exposure.csv',exposures)
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
    scoring_rows={}
    for stage in [*stages,R/'phase12_12E_partial_v1']:
        if not (stage/'retrieval.json').exists():continue
        version=json.loads((stage/'retrieval.json').read_text())['kernel_version']
        for row in read(stage/'scoring.csv'):
            row['kernel_version']=row.get('kernel_version') or version
            scoring_rows[(row['kernel_version'],row['model'],row['day'],row['role'])]=row|{'scope':'physical-scoring'}
    performance=list(scoring_rows.values())
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
