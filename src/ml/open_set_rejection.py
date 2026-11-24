"""Pure score calculations and conservative known-only rejection calibration."""

from math import isfinite, log


def uncertainty(scores):
    values = tuple(scores)
    if len(values) < 2 or any(not isfinite(x) or x < 0 for x in values) or abs(sum(values)-1) > 1e-6:
        raise ValueError('Expected a normalized finite class-score vector with at least two classes')
    ordered = sorted(values, reverse=True)
    return {'maximum': ordered[0], 'margin': ordered[0]-ordered[1],
            'entropy': -sum(x*log(x) for x in values if x)/log(len(values))}


def cutoff(known_histogram, budget):
    """Reject scores strictly above cutoff, retaining all boundary ties."""
    if not 0 <= budget <= 1 or not known_histogram or any(n <= 0 for n in known_histogram.values()):
        raise ValueError('Known calibration support and a valid budget are required')
    total = sum(known_histogram.values())
    rejected = 0
    threshold = max(known_histogram)
    for score in sorted(known_histogram, reverse=True):
        if rejected + known_histogram[score] > budget*total:
            return score
        rejected += known_histogram[score]
        threshold = score
    return threshold
