"""Deterministic matched permutations and score-bin metrics."""
import random
from collections import defaultdict


def permute(rows, features, seed, within_capture=False):
    result=[dict(row) for row in rows]
    groups=defaultdict(list)
    for index,row in enumerate(rows):
        groups[row['source_day'] if within_capture else 'all'].append(index)
    generator=random.Random(seed)
    for group in sorted(groups):
        indices=groups[group]
        donors=list(indices)
        generator.shuffle(donors)
        for target,donor in zip(indices,donors):
            for feature in features:
                result[target][feature]=rows[donor][feature]
    return result


def evaluate(histogram, threshold=1024):
    negative=sum(values[0] for values in histogram.values())
    positive=sum(values[1] for values in histogram.values())
    tp=sum(values[1] for bucket,values in histogram.items() if bucket>=threshold)
    fp=sum(values[0] for bucket,values in histogram.items() if bucket>=threshold)
    fn=positive-tp
    tn=negative-fp
    ratio=lambda a,b:a/b if b else None
    cumulative_tp=cumulative_fp=0
    prior_recall=prior_fpr=0.0
    pr_auc=roc_auc=0.0
    for bucket in sorted(histogram,reverse=True):
        cumulative_fp+=histogram[bucket][0]
        cumulative_tp+=histogram[bucket][1]
        if positive and negative:
            recall=cumulative_tp/positive
            fpr=cumulative_fp/negative
            pr_auc+=(recall-prior_recall)*cumulative_tp/(cumulative_tp+cumulative_fp)
            roc_auc+=(fpr-prior_fpr)*(recall+prior_recall)/2
            prior_recall,prior_fpr=recall,fpr
    return dict(tp=tp,fp=fp,tn=tn,fn=fn,rows=positive+negative,recall=ratio(tp,positive),precision=ratio(tp,tp+fp),fpr=ratio(fp,negative),f1=ratio(2*tp,2*tp+fp+fn),pr_auc=pr_auc if positive and negative else None,roc_auc=roc_auc if positive and negative else None)
