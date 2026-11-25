"""Shared tie-preserving score histogram metrics; nulls retain undefined values."""
import math
from src.ml.threshold_calibration import at_threshold, choose, curves

BINS = 2048


def merge(items):
    result = {}
    for hist in items:
        for index, counts in hist.items():
            row = result.setdefault(int(index), [0, 0])
            row[0] += int(counts[0]); row[1] += int(counts[1])
    return result


def operating(hist):
    if min(sum(v[c] for v in hist.values()) for c in (0,1)) == 0:
        raise ValueError('Missing validation class')
    return choose(curves(hist, BINS), .01)[0]


def evaluate(hist, threshold):
    result = at_threshold(hist, threshold, BINS)
    n = sum(result[k] for k in ('tp','fp','tn','fn'))
    benign = result['fp'] + result['tn']
    result.update(rows=n, false_alarms_per_million_benign=1e6*result['fp']/benign if benign else None,
                  positive_rate=(result['tp']+result['fp'])/n if n else None)
    return result


def guarded(candidate, incumbent, retention_candidate, retention_incumbent):
    checks = [('recall', -.01), ('pr_auc', -.02)]
    for key, limit in checks:
        if candidate.get(key) is None or incumbent.get(key) is None: return False, 'undefined-' + key
        if candidate[key]-incumbent[key] < limit-1e-12: return False, 'validation-' + key
    if candidate['fpr'] > min(.01, incumbent['fpr']+.001)+1e-12: return False, 'validation-fpr'
    if retention_candidate['recall'] < retention_incumbent['recall']-.05-1e-12: return False, 'retention-recall'
    if retention_candidate['fpr'] > retention_incumbent['fpr']+.005+1e-12: return False, 'retention-fpr'
    return True, 'guard-passed'


def js(reference, current):
    import numpy as np
    a=np.asarray(reference,dtype=float); b=np.asarray(current,dtype=float)
    if a.sum()<=0 or b.sum()<=0: return None
    a/=a.sum(); b/=b.sum(); m=(a+b)/2
    return float(sum(np.sum(v[v>0]*np.log2(v[v>0]/m[v>0])) for v in (a,b))/2)
