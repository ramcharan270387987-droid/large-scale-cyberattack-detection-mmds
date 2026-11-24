"""Exact support evaluation from complete transaction-signature counts."""
from collections import Counter


def counts(rows, pattern, weight='count'):
    required=set(pattern)
    matched=Counter()
    totals=Counter()
    for row in rows:
        key=(row['source_day'],row['binary_label'],row['attack_family'])
        value=row[weight]
        totals[key]+=value
        if required.issubset(row['items']):matched[key]+=value
    return matched,totals


def score(items, patterns):
    present=set(items)
    return sum(set(pattern).issubset(present) for pattern in patterns)/len(patterns) if patterns else 0.0


def select_threshold(rows, budget=.01):
    negatives=sum(row['count'] for row in rows if row['binary_label']==0)
    if not negatives:raise ValueError('No benign validation support')
    candidates=sorted({row['score'] for row in rows}|{1.000000001})
    eligible=[]
    for threshold in candidates:
        fp=sum(row['count'] for row in rows if row['binary_label']==0 and row['score']>=threshold)
        tp=sum(row['count'] for row in rows if row['binary_label']==1 and row['score']>=threshold)
        if fp/negatives<=budget:eligible.append((tp,-fp,threshold))
    return max(eligible)[2]
