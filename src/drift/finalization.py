"""Bounded supplemental Phase 11 experiments and exact agreement accounting."""
from bisect import bisect_left
from collections import defaultdict
from itertools import combinations
from math import isfinite,sqrt
from pathlib import Path
import csv,json,pickle,random,resource
from time import perf_counter
from src.drift.advanced_detectors import create,update,divergences
from src.drift.synthetic_generators import generate
from src.drift.drift_evaluation import evaluate
from src.drift.run_synthetic import write

NATIVE_WARMUP={'ADWIN':10,'PageHinkley':30,'KSWIN':100,'DDM':30}


def supported_alert(value,support,minimum,threshold):
    return value>threshold if support>=minimum and value is not None else None


def agreement(first,second):
    if len(first)!=len(second) or not first:raise ValueError('Matched nonempty intervals required')
    a=sum(x and y for x,y in zip(first,second));b=sum(x and not y for x,y in zip(first,second));c=sum(not x and y for x,y in zip(first,second));d=len(first)-a-b-c;n=len(first)
    expected=((a+b)*(a+c)+(c+d)*(b+d))/n**2
    return {'intervals':n,'shared_positive':a,'first_only':b,'second_only':c,'shared_negative':d,
            'agreement':(a+d)/n,'jaccard':a/(a+b+c) if a+b+c else None,
            'kappa':((a+d)/n-expected)/(1-expected) if expected!=1 else None,
            'positive_agreement':2*a/(2*a+b+c) if 2*a+b+c else None,
            'negative_agreement':2*d/(2*d+b+c) if 2*d+b+c else None}


def tolerance_matches(first,second,tolerance=1):
    remaining=set(second);matched=0
    for i in sorted(first):
        choices=[j for j in remaining if abs(i-j)<=tolerance]
        if choices:remaining.remove(min(choices,key=lambda j:(abs(i-j),j)));matched+=1
    return matched


def correlation(x,y,weights=None):
    if len(x)<3 or len(x)!=len(y):return None
    weights=weights or [1]*len(x);total=sum(weights)
    mx=sum(a*w for a,w in zip(x,weights))/total;my=sum(b*w for b,w in zip(y,weights))/total
    xx=sum(w*(a-mx)**2 for a,w in zip(x,weights));yy=sum(w*(b-my)**2 for b,w in zip(y,weights))
    return sum(w*(a-mx)*(b-my) for a,b,w in zip(x,y,weights))/sqrt(xx*yy) if xx*yy else None


def ranks(values):
    ordered=sorted(enumerate(values),key=lambda p:p[1]);result=[0.]*len(values);start=0
    while start<len(ordered):
        end=start+1
        while end<len(ordered) and ordered[end][1]==ordered[start][1]:end+=1
        for index,_ in ordered[start:end]:result[index]=(start+end-1)/2
        start=end
    return result


def histogram(values,edges):
    result=[0]*(len(edges)+1)
    for value in values:
        if isfinite(value):result[bisect_left(edges,value)]+=1
    return result


def calibration(length,window=64):
    reference=[r['signal'] for r in list(generate('stationary',13013))[:length]];ordered=sorted(reference)
    edges=[ordered[int(i*length/10)] for i in range(1,10)];ref=histogram(reference,edges);scores=[]
    for seed in (13013,13014,13015):
        values=[r['signal'] for r in generate('stationary',seed)]
        scores.extend(divergences(ref,histogram(values[i:i+window],edges)) for i in range(length,4096-window+1,window))
    thresholds=[sorted(s[k] for s in scores)[int(.99*(len(scores)-1))] for k in (0,1)]
    return edges,ref,thresholds,ordered[len(ordered)//2]


def binary_errors(kind,seed):
    rng=random.Random(seed+49000)
    return [int(rng.random()<(.45 if kind!='stationary' and 2048<=i<(3072 if kind=='recurring' else 4096) else .05)) for i in range(4096)]


def reference_and_reset(output):
    frozen=json.loads(Path('reports/phase11_synthetic/frozen.json').read_text());rows=[];costs=[]
    for length in (64,256,512):
        edges,ref,thresholds,_=calibration(length)
        for kind in ('stationary','abrupt','recurring'):
            for seed in (23013,23014,23015):
                data=[r['signal'] for r in generate(kind,seed)]
                events=[] if kind=='stationary' else [2048,3072] if kind=='recurring' else [2048]
                for method in ('ADWIN','PageHinkley','KSWIN','DDM','JS','PSI'):
                    warmup=max(length,NATIVE_WARMUP.get(method,0));alerts=[];tick=perf_counter()
                    detector=create(method,frozen[method],seed) if method in NATIVE_WARMUP else None
                    values=binary_errors(kind,seed) if method=='DDM' else data
                    for i,value in enumerate(values):
                        if detector:
                            if update(detector,value,method=='DDM'):alerts.append(i)
                        elif i+1>=length+64 and (i+1-length)%64==0:
                            score=divergences(ref,histogram(values[i+1-64:i+1],edges))[0 if method=='JS' else 1]
                            if score>thresholds[0 if method=='JS' else 1]:alerts.append(i)
                    elapsed=perf_counter()-tick
                    rows.append({'experiment':'reference','detector':method,'reference_length':length if not detector else None,'warmup':warmup,'scenario':kind,'seed':seed,'signal':'released binary error' if method=='DDM' else 'bounded feature','seconds':elapsed,**evaluate(alerts,events,4096,warmup)})
    write(output/'reference.csv',rows)
    resets=[]
    for method in NATIVE_WARMUP:
        for seed in (23013,23014,23015):
            for policy in ('native_continuation','external_reset','cooldown_64'):
                tick=perf_counter();detector=create(method,frozen[method],seed);initialization=perf_counter()-tick
                values=binary_errors('recurring',seed) if method=='DDM' else [r['signal'] for r in generate('recurring',seed)]
                alerts=[];raw=external=suppressed=0;last=-65;tick=perf_counter()
                for i,value in enumerate(values):
                    if update(detector,value,method=='DDM'):
                        raw+=1
                        if policy!='cooldown_64' or i-last>=64:alerts.append(i);last=i
                        else:suppressed+=1
                        if policy=='external_reset':detector=create(method,frozen[method],seed);external+=1
                elapsed=perf_counter()-tick;tick=perf_counter();snapshot=pickle.dumps(detector);snapshot_time=perf_counter()-tick
                tick=perf_counter();restored=pickle.loads(snapshot);restore_time=perf_counter()-tick
                # The same future probe must produce identical next-state decisions.
                assert update(detector,values[-1],method=='DDM')==update(restored,values[-1],method=='DDM')
                resets.append({'detector':method,'seed':seed,'policy':policy,'raw_detections':raw,'external_resets':external,'suppressed_alerts':suppressed,'seconds':elapsed,'state_bytes':len(snapshot),**evaluate(alerts,[2048,3072],4096)})
                costs.append({'detector':method,'seed':seed,'policy':policy,'unit':'observation','updates':4096,'initialization_seconds':initialization,'update_seconds':elapsed,'snapshot_seconds':snapshot_time,'restore_seconds':restore_time,'state_bytes':len(snapshot),'peak_process_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
    write(output/'reset.csv',resets);write(output/'costs.csv',costs)


def missing_inputs(output):
    frozen=json.loads(Path('reports/phase11_synthetic/frozen.json').read_text());edges,ref,thresholds,median=calibration(256);rows=[]
    for seed in (23013,23014,23015):
        original=[r['signal'] for r in generate('abrupt',seed)]
        for profile in ('random_10_percent','burst_2048_2304','postchange_40_percent','nonfinite_every_20'):
            rng=random.Random(seed+71000);values=[]
            for i,value in enumerate(original):
                missing=(rng.random()<.1 if profile=='random_10_percent' else 2048<=i<2304 if profile=='burst_2048_2304' else i>=2048 and rng.random()<.4 if profile=='postchange_40_percent' else i%20==0)
                values.append((float('inf') if i%40==0 else float('nan')) if missing else value)
            missing_count=sum(not isfinite(v) for v in values)
            for policy in ('skip','reference_median','missing_indicator','support_48_of_64'):
                methods=('JS','PSI') if policy=='support_48_of_64' else ('ADWIN','PageHinkley','KSWIN')
                for method in methods:
                    detector=create(method,frozen[method],seed) if method in NATIVE_WARMUP else None
                    alerts=[];updates=0;suppressed=0;valid_indices=[];tick=perf_counter();window_support=[]
                    for i,value in enumerate(values):
                        valid=isfinite(value)
                        if valid:valid_indices.append(i)
                        if detector:
                            if policy=='skip' and not valid:suppressed+=1;continue
                            observed=float(not valid) if policy=='missing_indicator' else value if valid else median
                            updates+=1
                            if update(detector,observed):alerts.append(i)
                        elif i>=319 and (i+1)%64==0:
                            chunk=[v for v in values[i+1-64:i+1] if isfinite(v)];window_support.append(len(chunk))
                            if len(chunk)<48:suppressed+=1;continue
                            updates+=1;score=divergences(ref,histogram(chunk,edges))[0 if method=='JS' else 1]
                            if score>thresholds[0 if method=='JS' else 1]:alerts.append(i)
                    events=([2048,2304] if profile=='burst_2048_2304' else [2048] if profile=='postchange_40_percent' else []) if policy=='missing_indicator' else [2048]
                    stats=evaluate(alerts,events,4096)
                    delay_updates=None
                    if events:
                        matched=[i for i in alerts if events[0]<=i<events[0]+512]
                        if matched:delay_updates=sum(events[0]<=i<=min(matched) for i in valid_indices)
                    rows.append({'profile':profile,'policy':policy,'detector':method,'seed':seed,'arrival_observations':4096,'valid_observations':4096-missing_count,'missing_fraction':missing_count/4096,'detector_updates':updates,'suppressed_updates':suppressed,'delay_valid_observations':delay_updates,'minimum_valid_window_support':min(window_support) if window_support else None,'seconds':perf_counter()-tick,**stats})
    write(output/'missing.csv',rows)


def historical_support(output):
    raw=list(csv.DictReader(open('reports/phase6_window_metrics.csv')));raw=[r for r in raw if r['scope'] in ('intraday','capture_only')];raw.sort(key=lambda r:json.loads(r['batch_ids'])[0]);rows=[]
    for field in ('rf_score_counts_32','cluster_counts'):
        hist=[json.loads(r[field]) for r in raw];reference=[sum(h[i] for h in hist[:3]) for i in range(len(hist[0]))]
        for minimum in (1,100,1000,10000):
            calibrated=[divergences(reference,h) for r,h in zip(raw[3:10],hist[3:10]) if int(r['rows'])>=minimum]
            thresholds=[max(v[k] for v in calibrated) for k in (0,1)] if calibrated else [None,None]
            for index,(r,h) in enumerate(zip(raw,hist)):
                scores=divergences(reference,h)
                for k,name in enumerate(('JS','PSI')):
                    rows.append({'signal':field,'unit':'replay window','detector':name,'batch':index,'source_day':r['source_day'],'minimum_support':minimum,'actual_support':int(r['rows']),'eligible':int(r['rows'])>=minimum and thresholds[k] is not None,'evaluation':index>=10,'value':scores[k],'threshold':thresholds[k],'alert':supported_alert(scores[k],int(r['rows']),minimum,thresholds[k]) if thresholds[k] is not None else None})
    shifts=list(csv.DictReader(open('reports/phase6_shift_metrics.csv')))
    for r in shifts:
        if r['scope'] not in ('intraday','capture_only') or r['category']!='INPUT_SHIFT':continue
        for minimum in (1,100,1000,10000):
            n=int(r['rows']);value=float(r['value']);threshold=float(r['threshold'])
            rows.append({'signal':'feature_js/'+r['detector'],'unit':'replay window','detector':'JS','batch':json.loads(r['batch_ids'])[0],'source_day':r['source_day'],'minimum_support':minimum,'actual_support':n,'eligible':n>=minimum,'value':value,'threshold':threshold,'alert':supported_alert(value,n,minimum,threshold)})
    for delay in (0,1,3):
        for index,r in enumerate(raw):
            metrics=json.loads(r['classifier_metrics'])['random_forest'];n=int(r['rows'])
            for minimum in (1,100,1000,10000):
                rows.append({'signal':'released_RF_error','unit':'released replay window','detector':'support eligibility only','batch':index+delay,'label_source_batch':index,'label_delay':delay,'minimum_support':minimum,'actual_support':n,'eligible':n>=minimum and index+delay<len(raw),'value':(metrics['fp']+metrics['fn'])/n,'alert':None})
    for r in json.load(open('reports/phase10_analysis/temporal.json')):
        # Capture-level pattern observations retain the full pattern denominator.
        if r['items']!=['flow_duration=BIN_0']:continue
        for minimum in (1,100,1000,10000):
            rows.append({'signal':'pattern_support/flow_duration=BIN_0','unit':'capture','detector':'support eligibility only','source_day':r['day'],'minimum_support':minimum,'actual_support':r['total'],'eligible':r['total']>=minimum,'value':r['support'],'alert':None})
    for r in csv.DictReader(open('reports/phase3_family_by_day.csv')):
        for minimum in (1,100,1000,10000):
            rows.append({'signal':'released_family_support/'+r['attack_family'],'unit':'capture','detector':'support eligibility only','source_day':r['source_day'],'minimum_support':minimum,'actual_support':int(r['records']),'eligible':int(r['records'])>=minimum,'alert':None})
    write(output/'support.csv',rows)


def agreements(output):
    grouped=defaultdict(dict)
    for r in csv.DictReader(open('reports/phase11_synthetic/alerts.csv')):
        if r['label_delay_windows']!='0' or r['detector']=='DDM':continue
        key=r['scenario'],r['seed'];grouped[key].setdefault(r['detector'],set()).add(int(r['alert_index'])//64)
    methods=('ADWIN','PageHinkley','KSWIN','JS','PSI','FixedJS');rows=[]
    for scenario in ('stationary','abrupt','gradual','incremental','recurring','variance','correlation','prior','missingness','error','concept'):
        for seed in ('23013','23014','23015'):
            for a,b in combinations(methods,2):
                first=grouped[scenario,seed].get(a,set())&set(range(4,64));second=grouped[scenario,seed].get(b,set())&set(range(4,64))
                rows.append({'population':'synthetic','scenario':scenario,'seed':seed,'first':a,'second':b,'signal':'bounded feature','interval_unit':'64 arrivals','tolerance_intervals':1,'tolerance_positive_matches':tolerance_matches(first,second),**agreement([i in first for i in range(4,64)],[i in second for i in range(4,64)])})
    history=defaultdict(lambda:defaultdict(dict))
    for r in csv.DictReader(open('reports/phase11_historical/historical_alerts.csv')):
        if r['evaluation']!='True' or r['detector'] in ('KSWIN','support_check'):continue
        history[r['signal'],r['label_delay']][r['detector']][int(r['batch'])]=r['alert']=='True'
    for (signal,delay),detectors in history.items():
        for a,b in combinations(sorted(detectors),2):
            indices=sorted(set(detectors[a])&set(detectors[b]));first=[detectors[a][i] for i in indices];second=[detectors[b][i] for i in indices]
            if indices:rows.append({'population':'historical','signal':signal,'label_delay':delay,'first':a,'second':b,'interval_unit':'replay window',**agreement(first,second)})
    write(output/'agreement.csv',rows)


def performance_associations(output):
    raw=[r for r in csv.DictReader(open('reports/phase6_window_metrics.csv')) if r['scope'] in ('intraday','capture_only')];raw.sort(key=lambda r:json.loads(r['batch_ids'])[0]);metrics=[]
    for r in raw:
        m=json.loads(r['classifier_metrics'])['random_forest'];m.update(error=(m['fp']+m['fn'])/m['rows'],fpr=m['fp']/(m['fp']+m['tn']) if m['fp']+m['tn'] else None,prevalence=int(r['attacks'])/int(r['rows']));metrics.append(m)
    histories=list(csv.DictReader(open('reports/phase11_historical/historical_alerts.csv')));rows=[];before=[]
    for detector in ('JS','PSI'):
        scores={int(r['batch']):r for r in histories if r['detector']==detector and r['signal']=='RF histogram' and r['evaluation']=='True'}
        for metric in ('recall','precision','f1','fpr','error','predicted_rate','pr_auc','prevalence'):
            for lag in (0,1,3):
                for delay in (0,1,3):
                    pairs=[(float(r['value']),metrics[i+lag][metric],int(raw[i+lag]['rows'])) for i,r in scores.items() if i+lag+delay<len(raw) and int(raw[i+lag]['rows'])>=100 and metrics[i+lag][metric] is not None]
                    x=[p[0] for p in pairs];y=[p[1] for p in pairs]
                    rows.append({'detector':detector,'performance_metric':metric,'lag_windows':lag,'label_delay_windows':delay,'eligible_pairs':len(pairs),'excluded_windows':len(scores)-len(pairs),'pearson':correlation(x,y),'spearman':correlation(ranks(x),ranks(y)),'row_weighted_pearson':correlation(x,y,[p[2] for p in pairs]) if pairs else None,'interpretation':'Retrospective descriptive association, no independent-replication or causal inference'})
            for i,r in scores.items():
                if r['alert']!='True' or i<=0 or i+1>=len(raw):continue
                a,b=metrics[i-1][metric],metrics[i+1][metric]
                before.append({'detector':detector,'alert_batch':i,'metric':metric,'before':a,'after':b,'difference':b-a if a is not None and b is not None else None,'after_label_release_batch':i+1,'label_delay_assumption':0})
    write(output/'association.csv',rows);write(output/'before_after.csv',before)


def run(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True);start=perf_counter()
    for action in (reference_and_reset,missing_inputs,historical_support,agreements,performance_associations):
        action(output);print('PHASE11 finalization',action.__name__,'complete',flush=True)
    (output/'receipt.json').write_text(json.dumps({'status':'validated','scope':'Phase 11 supplemental local CPU experiments','seconds':perf_counter()-start,'tables':{p.name:sum(1 for _ in csv.DictReader(p.open())) for p in output.glob('*.csv')}},indent=2)+'\n')
