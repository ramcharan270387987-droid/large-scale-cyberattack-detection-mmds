"""Translate bounded evaluation rates into workload and hypothetical PPV."""


def scenario_ppv(tpr, fpr, prevalence):
    if tpr is None or fpr is None:
        return None
    yes, false = tpr * prevalence, fpr * (1-prevalence)
    return yes/(yes + false) if yes + false else None


def burden(row, prevalences):
    fpr = row["fpr"]
    return {f"false_per_{n}": fpr*n if fpr is not None else None for n in (10_000, 100_000, 1_000_000)} | {
        "detected_per_100000": row["tp"] / row["rows"] * 100_000 if row["rows"] else None,
        "scenario_ppv": {str(p): scenario_ppv(row["recall"], fpr, p) for p in prevalences},
    }
