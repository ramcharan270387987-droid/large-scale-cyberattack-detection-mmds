"""Backend-independent predict-before-release replay, with measured activation clocks."""
import time
import json,os
from pathlib import Path
from src.adaptation.lifecycle import Registry, digest, eligible, released, training_window
from src.adaptation.evaluation import evaluate, guarded, merge, operating, js


def run(backend, policy, delay, root, *, budget=3, period=2, sliding=2, cooldown=2, minimum=200, advanced=False):
    registry=Registry(root)
    tag=f'{backend.name}-{policy}-d{delay}-b{budget}-p{period}-s{sliding}-c{cooldown}-m{minimum}-a{advanced}'
    completed=Path(root)/'completed_run.json'
    if completed.exists():
        saved=json.loads(completed.read_text())
        if saved['summary']['run']!=tag:raise ValueError('Replay identity conflict')
        return saved
    current=backend.fit(backend.initial)
    initial=current
    threshold=operating(backend.hist(current,backend.calibration,1))
    initial_threshold=threshold
    current_meta=backend.meta[current]
    registry.register(current,current_meta); registry.activate(current,threshold=threshold)
    windows=[]; triggers=[]; events=[]; thresholds=[]; predictions=[]; family=[]; retention=[]
    arrived=[]; used=set(); attempts=0; last=-999; pending=None; previous=None; previous_threshold=None
    promoted_metrics=evaluate(backend.hist(current,backend.calibration,1),threshold)
    natural_rollbacks=0; score_seconds=0; detector_seconds=0; registry_seconds=0
    registered_metrics={current:promoted_metrics}
    detector=None
    if advanced:
        from river.drift import ADWIN
        detector=ADWIN(delta=.01,clock=32,grace_period=10)
    for index, day in enumerate(backend.forward):
        arrival=backend.clock(day)
        if pending and index>=pending['earliest'] and arrival>=pending['complete']:
            previous,previous_threshold=(None,None) if pending.get('rollback') else (current,threshold)
            current,threshold=pending['model'],pending['threshold']
            promoted_metrics=pending['metrics']
            t=time.monotonic(); registry.activate(current,threshold=threshold); registry_seconds+=time.monotonic()-t
            events[pending['event']]['activation_index']=index
            events[pending['event']]['activation_time']=arrival
            pending=None
        # No label release or training occurs before this scoring call.
        started=time.monotonic()
        hists=backend.score(current,day,2)
        window_score_seconds=time.monotonic()-started
        score_seconds+=window_score_seconds
        aggregate=merge(hists.values()); metric=evaluate(aggregate,threshold)
        row={'run':tag,'policy':policy,'delay':delay,'window':index,'day':str(day),'model':current,
             'threshold_bin':threshold,'score_call_seconds':window_score_seconds,'arrival_time':arrival,'prediction_time':arrival,
             'label_release_index':index+delay,'fit_last_day':str(max(backend.meta[current]['training_days'])),
             'staleness_seconds':arrival-backend.clock(max(backend.meta[current]['training_days'])),**metric}
        windows.append(row); predictions.append((aggregate,threshold))
        for name,hist in hists.items():
            family.append({'run':tag,'policy':policy,'delay':delay,'window':index,'day':str(day),
                           'family':name,'model':current,**evaluate(hist,threshold)})
        started=time.monotonic()
        signal=js(backend.reference,backend.distribution(day))
        detector_seconds+=time.monotonic()-started
        arrived.append(index)
        available=released(arrived,delay,index)
        fit_days=[backend.forward[i] for i in available]
        cal_days=(backend.calibration+fit_days)[-2:]
        new=[d for d in fit_days if d not in used]
        support=backend.support(new,0) if new else 0
        signal_supported=signal is not None and backend.eval_support(day)>=100
        alert=signal_supported and signal>.1
        if detector and signal_supported:
            detector.update(signal)
            alert=bool(detector.drift_detected)
        elif detector:
            alert=False
        requested=(policy in ('P1','P4','P5') and (index+1)%(1 if policy=='P5' else period)==0) or (policy in ('P2','P6') and alert)
        ok,reason=eligible(requested,support,minimum,index,last,cooldown,attempts,budget,index==len(backend.forward)-1)
        if pending: ok,reason=False,'candidate-not-yet-active'
        triggers.append({'run':tag,'policy':policy,'delay':delay,'window':index,'day':str(day),
            'trigger_id':f'{tag}-{index}','detector':'ADWIN' if detector else 'fixed-reference-js',
            'detector_version':'phase11','signal':'input-flow-duration' if backend.kind=='historical' else 'input-x0',
            'granularity':'capture' if backend.kind=='historical' else 'synthetic-window','js':signal,'alert':alert,
            'current_support':backend.eval_support(day),'required_support':100,'warmup_supported':signal_supported and (index>=31 if detector else True),
            'input_supported':signal_supported,'cooldown_active':index-last<cooldown,'duplicate_trigger':False,
            'label_available_indices':available,'new_training_rows':support,'requested':bool(requested),
            'eligible':ok,'reason':reason,'time':arrival})
        # Rollback uses only previously issued, now released forward labels of the active model.
        eligible_windows=[r for r in windows if r['window'] in available and r['model']==current][-2:]
        if policy=='P6' and previous and len(eligible_windows)==2:
            counts={k:sum(r[k] for r in eligible_windows) for k in ('tp','fp','tn','fn')}
            positive=counts['tp']+counts['fn']; negative=counts['tn']+counts['fp']
            if min(positive,negative)>=100 and counts['tp']/positive<=promoted_metrics['recall']-.15 and counts['fp']/negative>=promoted_metrics['fpr']+.02:
                backend.verify(previous)
                pending={'model':previous,'threshold':previous_threshold,'complete':arrival,
                         'earliest':index+1,'event':len(events),'metrics':registered_metrics[previous],'rollback':True}
                events.append({'run':tag,'policy':policy,'delay':delay,'window':index,'action':'rollback','model':previous,
                               'decision':'released-performance-degradation','activation_index':None,'activation_time':None})
                natural_rollbacks+=1
        if policy=='P3' and available and index<len(backend.forward)-1:
            try:
                threshold_hist=backend.hist(current,cal_days,1)
                if min(sum(v[c] for v in threshold_hist.values()) for c in (0,1))<backend.min_class:
                    raise ValueError('Insufficient threshold validation class support')
                selected=operating(threshold_hist)
                thresholds.append({'run':tag,'policy':policy,'delay':delay,'window':index,'old_bin':threshold,'new_bin':selected,
                                   'activation_index':index+1,'calibration_days':list(map(str,cal_days))})
                pending={'model':current,'threshold':selected,'complete':arrival,'earliest':index+1,
                         'event':len(events),'metrics':evaluate(backend.hist(current,cal_days,1),selected)}
                events.append({'run':tag,'policy':policy,'delay':delay,'window':index,'action':'threshold','model':current,
                               'decision':'validation-only','activation_index':None,'activation_time':None})
            except ValueError as exc:
                thresholds.append({'run':tag,'policy':policy,'delay':delay,'window':index,'reason':str(exc)})
        if not ok: continue
        identifier=f'{tag}-{index}'
        if not registry.request(identifier): continue
        attempts+=1; last=index; used.update(new)
        days=training_window(backend.initial,fit_days,'sliding' if policy=='P4' or backend.kind=='synthetic' else 'expanding',sliding)
        record={'run':tag,'policy':policy,'delay':delay,'window':index,'action':'fit','parent':current,
                'training_days':list(map(str,days)),'calibration_days':list(map(str,cal_days)),
                'trigger_time':arrival,'training_start':arrival,'activation_index':None,'activation_time':None}
        started=time.monotonic()
        try:
            candidate=backend.fit(days)
            fit_call_seconds=time.monotonic()-started
            record.update(model=candidate,fit_succeeded=True,charged_fit_seconds=backend.meta[candidate]['fit_seconds'])
            cal=backend.hist(candidate,cal_days,1)
            if min(sum(v[c] for v in cal.values()) for c in (0,1))<backend.min_class:
                raise ValueError('Insufficient validation class support')
            selected=operating(cal); candidate_metrics=evaluate(cal,selected)
            before=evaluate(backend.hist(current,cal_days,1),threshold)
            rc=evaluate(backend.hist(candidate,backend.calibration,1),selected)
            ri=evaluate(backend.hist(current,backend.calibration,1),threshold)
            accept,why=(guarded(candidate_metrics,before,rc,ri) if policy=='P6' else (True,'valid-unguarded'))
            retention.append({'run':tag,'policy':policy,'delay':delay,'window':index,'model':candidate,'incumbent':current,
                              'candidate_recall':rc['recall'],'incumbent_recall':ri['recall'],
                              'candidate_fpr':rc['fpr'],'incumbent_fpr':ri['fpr'],'accepted':accept})
            cost=backend.meta[candidate]['fit_seconds']
            elapsed=time.monotonic()-started
            completion_duration=max(cost,fit_call_seconds)+max(0,elapsed-fit_call_seconds)
            record.update(model=candidate,decision=why,accepted=accept,failed=False,threshold_bin=selected,
                          candidate_metrics=candidate_metrics,incumbent_metrics=before,
                          measured_action_seconds=elapsed,charged_fit_seconds=cost,
                          actual_fit_call_seconds=fit_call_seconds,training_complete=arrival+completion_duration)
            registry.register(candidate,backend.meta[candidate])
            registered_metrics[candidate]=candidate_metrics
            if accept:
                pending={'model':candidate,'threshold':selected,'complete':record['training_complete'],
                         'earliest':index+1,'event':len(events),'metrics':candidate_metrics}
        except Exception as exc:
            record.update(failed=True,accepted=False,decision=type(exc).__name__+': '+str(exc),measured_action_seconds=time.monotonic()-started)
        events.append(record)
    # Pooled confusion counts respect the threshold active when each prediction was issued.
    counts={key:sum(row[key] for row in windows) for key in ('tp','fp','tn','fn')}
    from src.ml.threshold_calibration import metrics
    from src.ml.evaluate_supervised import binned_auc
    pooled=metrics(counts['tp'],counts['tn'],counts['fp'],counts['fn'])
    pooled.update(binned_auc(merge([h for h,t in predictions])))
    summary={'run':tag,'population':backend.kind,'policy':policy,'delay':delay,'model_family':backend.family,
             'backend':backend.name,'budget':budget,'period':period,'sliding':sliding,'cooldown':cooldown,'minimum':minimum,
             'advanced':advanced,**pooled,'rows':sum(r['rows'] for r in windows),'windows':len(windows),
             'pending_label_windows':len(arrived)-len(released(arrived,delay,len(arrived)-1)),
             'alerts':sum(t['alert'] for t in triggers),'eligible_triggers':sum(t['eligible'] for t in triggers),
             'suppressed_triggers':sum(t['requested'] and not t['eligible'] for t in triggers),
             'retrainings':attempts,'successful_retrainings':sum(e.get('fit_succeeded',False) for e in events),
             'failed_retrainings':sum(e.get('action')=='fit' and not e.get('fit_succeeded',False) for e in events),
             'failed_actions':sum(e.get('failed') is True for e in events),
             'promotions':sum(e.get('accepted',False) for e in events),
             'rejections':sum(e.get('accepted') is False and e.get('action')=='fit' for e in events),
             'threshold_updates':len([t for t in thresholds if 'new_bin' in t]),'rollbacks':natural_rollbacks,
             'activated_candidates':sum(e.get('action')=='fit' and e.get('activation_index') is not None for e in events),
             'model_versions_served':len({r['model'] for r in windows}),'mean_staleness_seconds':sum(r['staleness_seconds'] for r in windows)/len(windows),
             'charged_fit_seconds':sum(e.get('charged_fit_seconds',0) for e in events),
             'score_seconds':score_seconds,'detector_seconds':detector_seconds,'registry_seconds':registry_seconds,
             'initial_model':initial,'initial_threshold_bin':initial_threshold,
             'coverage':1.0,'auc_caveat':'Descriptive pooled raw scores across versions; cross-version calibration is not guaranteed.'}
    benign=pooled['fp']+pooled['tn']
    summary['false_alarms_per_million_benign']=1e6*pooled['fp']/benign if benign else None
    result={'summary':summary,'windows':windows,'triggers':triggers,'events':events,'thresholds':thresholds,'family':family,'retention':retention}
    temporary=completed.with_suffix('.pending')
    with temporary.open('w') as stream:
        json.dump(result,stream,allow_nan=False)
        stream.flush();os.fsync(stream.fileno())
    os.replace(temporary,completed)
    return result
