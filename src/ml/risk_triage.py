"""High and lower frozen thresholds for selective automatic decisions."""

from math import isfinite

from src.ml.evaluate_supervised import rate


def risk_category(score, high, lower):
    if score is None or not isfinite(score):
        return "ABSTAIN"
    if score >= high:
        return "HIGH_RISK"
    if score >= lower:
        return "REVIEW_REQUIRED"
    return "LOW_RISK"


def summary(counts):
    high, low, review, abstain = [counts.get(k, (0, 0)) for k in
                                 ("HIGH_RISK", "LOW_RISK", "REVIEW_REQUIRED", "ABSTAIN")]
    auto = sum(high) + sum(low)
    total = auto + sum(review) + sum(abstain)
    attacks = sum(x[1] for x in (high, low, review, abstain))
    negatives = total - attacks
    return {"rows": total, "automatic_coverage": rate(auto, total), "review_rate": rate(sum(review), total),
            "abstain_rate": rate(sum(abstain), total), "automatic_error_rate": rate(high[0] + low[1], auto),
            "high_precision": rate(high[1], sum(high)), "detected_attack_rate": rate(high[1], attacks),
            "referred_or_detected_attack_rate": rate(high[1] + review[1] + abstain[1], attacks),
            "benign_review_burden": rate(review[0], negatives),
            "review_per_100000": 100_000 * sum(review)/total if total else None,
            "category_counts": counts}
