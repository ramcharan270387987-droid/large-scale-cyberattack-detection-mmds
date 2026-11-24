"""Training-derived family IDs with explicit unknown evaluation semantics."""

UNKNOWN = 'UNKNOWN'
FAMILIES = ('Bot', 'Credential brute force', 'DDoS', 'DoS', 'Infiltration', 'Web attack')


def vocabulary(training_support):
    unexpected = set(training_support) - set(FAMILIES)
    if unexpected:
        raise ValueError(f'Unexpected attack families {sorted(unexpected)}')
    return {family: index for index, family in enumerate(sorted(family for family, n in training_support.items() if n > 0))}


def target(family, classes):
    if family not in FAMILIES:
        raise ValueError(f'Unexpected attack family {family}')
    return classes.get(family, UNKNOWN)


def original_contract(policy):
    return [{'original_label': original, 'family': spec['family'], 'binary_label': spec['binary']}
            for original, spec in sorted(policy['label_mapping'].items())]
