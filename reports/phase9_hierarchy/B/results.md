# Chronological B hierarchy

Kaggle version 12 completed. The [receipt](phase9_hierarchical_receipt.json)
and [day-by-family counts](phase9_hierarchical_counts.csv) cover the exact
980,109 retained flows from the original B benchmark. These include 771,584
benign flows and 208,525 attacks. Every attack belongs to a family absent
from the family model's training vocabulary. Known-family metrics remain
undefined.

The family stage reused the version 7 classifier and its frozen maximum-score
rule at the nominal 5% known-validation rejection budget. Binary confusion
counts exactly reproduce the original Phase 4 and Phase 8 receipts.

| Gate | Correct benign | Benign false alarms | Missed attacks | Correct UNKNOWN | False known acceptance | Accuracy | Supported target macro F1 | Review flows |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Phase 4 RF | 766,721 | 4,863 | 208,108 | 342 | 75 | 78.263% | 0.441 | 4,531 |
| Phase 8 calibrated supervised | 771,584 | 0 | 208,525 | 0 | 0 | 78.724% | 0.440 | 0 |
| Phase 8 frozen hybrid | 771,580 | 4 | 208,525 | 0 | 0 | 78.724% | 0.440 | 0 |
| Oracle diagnostic | 771,584 | 0 | 0 | 40,718 | 167,807 | 82.879% | 0.663 | 40,718 |

Review counts include all UNKNOWN decisions, including benign flows sent to
review through a false alarm. The corresponding automatic coverage was
99.538%, 100%, 100% and 95.846%. Supported-target macro F1 averages Benign
and UNKNOWN. The overall accuracy denominator includes all retained rows.

The RF gate rejected 342 of the 417 attacks it passed to the family stage
(82.01%), but only 342 of all 208,525 attacks (0.164%). Conditional rejection
for both Phase 8 gates is undefined because neither passed an attack. Their
end-to-end rejection recall is zero. The oracle bypassed binary mistakes and
rejected 19.53% of attacks, reproducing the family-stage operating point.
It is a diagnostic rather than an available deployment decision.

Spark 4.3.0 ran with four CPUs, an 8 GiB driver heap and 48 shuffle partitions.
The recorded scoring stage took 299.2 seconds. The measured peak driver RSS
was 3,753,791,488 bytes. The retrieved receipt, counts and split diagnostics
total 5,291 bytes.
