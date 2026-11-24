"""Calibrators fitted on compact binned probability-role predictions only."""

from bisect import bisect_left
from math import exp, log, log1p


def sigmoid(z):
    return 1 / (1 + exp(-max(-35, min(35, z))))


def center(bucket, bins):
    return (bucket + .5) / bins


def platt(histogram, bins):
    # Newton updates with ridge shrinkage and standardized score coordinates.
    count = sum(sum(v) for v in histogram.values())
    if not count or not all(sum(v[i] for v in histogram.values()) for i in range(2)):
        raise ValueError("Calibration requires both classes")
    points = [(2 * center(i, bins) - 1, negative + positive, positive)
              for i, (negative, positive) in histogram.items()]
    ridge = max(1e-6, count * 1e-5)
    a = b = 0.0
    for _ in range(40):
        g0, g1, h00, h01, h11 = 0.0, ridge * b, 1e-8, 0.0, ridge
        for x, n, yes in points:
            p = sigmoid(a + b * x)
            res = p * n - yes
            curvature = n * p * (1 - p)
            g0 += res
            g1 += res * x
            h00 += curvature
            h01 += curvature * x
            h11 += curvature * x * x
        determinant = h00 * h11 - h01 * h01
        da, db = (h11 * g0 - h01 * g1) / determinant, (h00 * g1 - h01 * g0) / determinant
        shrink = max(1, abs(da) / 2, abs(db) / 2)
        a, b = a - da / shrink, b - db / shrink
        if max(abs(da), abs(db)) < 1e-8:
            break
    return {"method": "platt", "intercept": a - b, "slope": 2 * b, "input": "histogram_bin_midpoint"}


def isotonic(histogram):
    if len(histogram) < 3 or not all(sum(v[i] for v in histogram.values()) for i in range(2)):
        raise ValueError("Isotonic calibration requires both classes and three score bins")
    blocks = []
    for key, (negative, positive) in sorted(histogram.items()):
        blocks.append([key, negative + positive, positive])
        while len(blocks) >= 2 and blocks[-2][2] * blocks[-1][1] > blocks[-1][2] * blocks[-2][1]:
            high, n, yes = blocks.pop()
            blocks[-1] = [high, blocks[-1][1] + n, blocks[-1][2] + yes]
    return {"method": "isotonic", "upper_bins": [x[0] for x in blocks],
            "probabilities": [x[2] / x[1] for x in blocks]}


def probability(spec, bucket, bins):
    if spec["method"] == "platt":
        return sigmoid(spec["intercept"] + spec["slope"] * center(bucket, bins))
    return spec["probabilities"][min(bisect_left(spec["upper_bins"], bucket), len(spec["upper_bins"]) - 1)]


def reliability(hist, bins, reliability_bins, epsilon):
    counts = [[0, 0, 0.0] for _ in range(reliability_bins)]
    brier = loss = total = 0
    for bucket, (negative, positive) in hist.items():
        score = center(bucket, bins)
        n = negative + positive
        total += n
        group = counts[min(int(score * reliability_bins), reliability_bins - 1)]
        group[0] += n
        group[1] += positive
        group[2] += n * score
        brier += negative * score**2 + positive * (1-score)**2
        p = max(epsilon, min(1-epsilon, score))
        loss -= positive * log(p) + negative * log1p(-p)
    ece = sum(abs(p - yes) for _, yes, p in counts)
    return ({"rows": total, "brier": brier/total, "log_loss": loss/total, "ece": ece/total} if total else
            {"rows": 0, "brier": None, "log_loss": None, "ece": None}), counts
