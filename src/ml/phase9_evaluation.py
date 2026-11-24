"""Aggregate multiclass metrics with explicit unsupported-class semantics."""


def ratio(n, d):
    return n/d if d else None


def multiclass(counts, classes):
    support = {k: sum(n for (actual, predicted), n in counts.items() if actual == k) for k in classes}
    predicted = {k: sum(n for (actual, predicted), n in counts.items() if predicted == k) for k in classes}
    family = []
    for k in classes:
        tp = counts.get((k,k), 0)
        family.append({'class_id': k, 'support': support[k], 'predicted': predicted[k],
                       'precision': ratio(tp, predicted[k]), 'recall': ratio(tp, support[k]),
                       'f1': ratio(2*tp, support[k]+predicted[k])})
    total = sum(counts.values())
    def mean(key):
        values = [r[key] for r in family if r[key] is not None]
        return sum(values)/len(values) if values else None
    return {'rows': total, 'accuracy': ratio(sum(counts.get((k,k),0) for k in classes), total),
            'macro_precision': mean('precision'), 'macro_recall': mean('recall'), 'macro_f1': mean('f1'),
            'balanced_accuracy': mean('recall'),
            'weighted_f1': ratio(sum(r['support']*(r['f1'] or 0) for r in family),total)}, family
