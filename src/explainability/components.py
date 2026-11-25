"""Exact policy components with frozen thresholds and class-coordinate semantics."""
from math import isfinite


def reject(scores, classes, cutoff_bin):
    if len(scores)!=len(classes) or not scores or sorted(classes.values())!=list(range(len(scores))):
        raise ValueError('Class registry and score ordering differ')
    if any(not isfinite(x) or x<0 for x in scores) or abs(sum(scores)-1)>1e-6:
        raise ValueError('Invalid family score vector')
    order=sorted(range(len(scores)),key=lambda i:(-scores[i],i))
    predicted=next(name for name,index in classes.items() if index==order[0])
    uncertainty=1-scores[order[0]]
    unknown=int(uncertainty*2048)>cutoff_bin
    return dict(predicted_family=predicted,maximum_score=scores[order[0]],margin=scores[order[0]]-scores[order[1]] if len(order)>1 else None,rejected=unknown,final_family='UNKNOWN' if unknown else predicted)


def fusion(supervised, novelty, policy, gates=None, alpha=None):
    if not all(isfinite(x) and 0<=x<=1 for x in (supervised,novelty)):
        raise ValueError('Invalid hybrid input score')
    if policy in ('or','and'):
        if gates is None:raise ValueError('Logical policy requires archived gates')
        first=supervised>=gates['supervised'];second=novelty>=gates['novelty']
        return float(first or second) if policy=='or' else float(first and second)
    if alpha is None or not 0<=alpha<=1:raise ValueError('Weighted fusion requires registered weight')
    return alpha*supervised+(1-alpha)*novelty
