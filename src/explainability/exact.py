"""Exact archived-model contributions with explicit output spaces."""
from math import exp,fsum,isfinite,isclose


def sigmoid(value):
    if value >= 0:
        return 1 / (1 + exp(-value))
    exponential = exp(value)
    return exponential / (1 + exponential)


def linear(coefficients, intercept, values, reference=None):
    if len(coefficients) != len(values) or not values:
        raise ValueError('Coefficient and feature dimensions differ')
    if not all(isfinite(x) for x in [intercept,*coefficients,*values]):
        raise ValueError('Nonfinite transformed feature or coefficient')
    if reference is None:
        reference = [0.0] * len(values)
    if len(reference) != len(values) or not all(isfinite(x) for x in reference):
        raise ValueError('Invalid reference dimensions or values')
    contributions = [coefficient * (value - baseline) for coefficient,value,baseline in zip(coefficients,values,reference)]
    baseline = intercept + fsum(coefficient * value for coefficient,value in zip(coefficients,reference))
    logit = baseline + fsum(contributions)
    return dict(baseline=baseline,contributions=contributions,logit=logit,probability=sigmoid(logit))


def distance(values, centroid):
    if len(values) != len(centroid) or not values:
        raise ValueError('Centroid and feature dimensions differ')
    if not all(isfinite(x) for x in [*values,*centroid]):
        raise ValueError('Nonfinite transformed feature or centroid')
    contributions = [(value-center)**2 for value,center in zip(values,centroid)]
    return dict(contributions=contributions,squared_distance=fsum(contributions))


def importance(names, values):
    if len(names) != len(values) or len(names) != len(set(names)):
        raise ValueError('Feature importance map differs from model dimensions')
    if any(not isfinite(value) or value < 0 for value in values):
        raise ValueError('Invalid native importance')
    return dict(zip(names,values))


def verify_linear(explanation, logit, probability):
    if not isclose(explanation['logit'],logit,abs_tol=1e-8,rel_tol=1e-8):
        raise ValueError('Logit reconstruction failed')
    if not isclose(explanation['probability'],probability,abs_tol=1e-10,rel_tol=1e-10):
        raise ValueError('Probability reconstruction failed')
