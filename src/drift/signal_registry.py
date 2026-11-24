"""Information availability and unit declarations for Phase 11 signals."""
SIGNALS={
 'synthetic_signal':{'unit':'observation','labels_required':False},
 'released_error':{'unit':'released observation','labels_required':True},
 'rf_score_histogram':{'unit':'historical replay window','labels_required':False},
 'feature_js':{'unit':'historical replay window','labels_required':False},
 'historical_error_rate':{'unit':'released historical replay window','labels_required':True},
}


def historical_availability(rows,warmup):
    """Attach native eligibility to legacy emission records without changing them."""
    counts={}
    result=[]
    for original in rows:
        row=dict(original)
        key=(row['signal'],str(row.get('label_delay','')),row['detector'])
        counts[key]=counts.get(key,0)+1
        row['available']=row['detector']!='support_check' and counts[key]>=warmup.get(row['detector'],0)
        if not row['available']:
            row['alert']=None
        elif isinstance(row['alert'],str):
            row['alert']=row['alert']=='True'
        if row['evaluation'] in (True,'True'):
            result.append(row)
    return result
