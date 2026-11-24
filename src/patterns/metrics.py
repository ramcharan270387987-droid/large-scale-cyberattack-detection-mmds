"""Count-derived association and temporal metrics with explicit zero support."""


def divide(numerator, denominator):
    return numerator / denominator if denominator else None


def association(joint, antecedent, consequent, total):
    if not 0 <= joint <= min(antecedent, consequent) <= total or total <= 0:
        raise ValueError('Inconsistent association counts')
    confidence = divide(joint, antecedent)
    expected = antecedent * consequent / total
    conviction = None if confidence is None or consequent == total else (
        float('inf') if confidence == 1 else (1-consequent/total)/(1-confidence))
    return {'support':joint/total,'confidence':confidence,'lift':divide(joint,expected),
            'leverage':joint/total-antecedent*consequent/total**2,'conviction':conviction}


def contrast(attack, benign, attack_total, benign_total):
    a, b = divide(attack,attack_total), divide(benign,benign_total)
    return {'attack_support':a,'benign_support':b,'difference':a-b if a is not None and b is not None else None,
            'support_ratio':a/b if b else (float('inf') if a else None),
            'attack_given_pattern':divide(attack,attack+benign),
            'population_attack_prevalence':divide(attack_total,attack_total+benign_total)}


def emergence(reference, current, reference_total, current_total):
    if min(reference_total,current_total)<=0:
        return {'growth':None,'delta':None,'category':'unsupported'}
    a,b=reference/reference_total,current/current_total
    growth=b/a if a else (float('inf') if b else None)
    delta=b-a
    category='stable'
    if reference and not current: category='disappearing'
    elif not reference and current: category='newly_observed'
    elif current>=100 and delta>=.01 and growth>=5: category='strongly_emerging'
    elif current>=100 and delta>=.01 and growth>=2: category='emerging'
    elif reference>=100 and delta<=-.01 and growth<=.5: category='declining'
    return {'growth':growth,'delta':delta,'category':category}


def jaccard(first, second):
    a,b=set(first),set(second)
    return divide(len(a & b),len(a | b))
