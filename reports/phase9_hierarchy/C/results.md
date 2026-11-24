# Retrospective C hierarchy

Kaggle version 13 completed on the exact retained Phase 4 and Phase 8 C test
population of 1,458,218 flows. It contained 1,457,560 benign flows and 658
Web attacks. The earlier-only family classifier supported credential brute
force, DDoS and DoS. All test attacks were unknown to it, so closed-set
family accuracy and known-family recall are undefined.

| Gate | Correct benign | Benign false alarms | Missed attacks | Correct UNKNOWN | False known acceptance | Accuracy | Supported target macro F1 | Review flows |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Phase 4 RF | 1,445,591 | 11,969 | 642 | 0 | 16 | 99.134% | 0.498 | 1,544 |
| Phase 8 calibrated supervised | 1,457,541 | 19 | 658 | 0 | 0 | 99.954% | 0.500 | 0 |
| Phase 8 frozen hybrid | 1,449,945 | 7,615 | 550 | 0 | 108 | 99.433% | 0.499 | 452 |
| Oracle diagnostic | 1,457,560 | 0 | 0 | 9 | 649 | 99.955% | 0.513 | 9 |

All three archived gates had zero end-to-end unknown recall. The Phase 8
hybrid passed 108 attacks to the family stage, all falsely accepted as
known. The supervised gate passed none, leaving conditional family-stage
performance undefined. The oracle rejected 1.37% of attacks. High overall
accuracy reflects the 99.95% benign prevalence. Automatic coverage was
99.894%, 100%, 99.969% and 99.999%, respectively. Review counts include
benign false alarms sent to UNKNOWN review. Supported-target macro F1
averages Benign and UNKNOWN.

The family model and reference K-Means pipeline are in the private version
13 output under `mmds_phase9_hierarchy/family/models`. Their checksums
matched the retrieved [classifier](family/phase9_summary.json) and
[novelty](family/phase9_novelty_registry.json) registries. The manifest
records the [day-by-family counts](phase9_hierarchical_counts.csv) and
[receipt](phase9_hierarchical_receipt.json).

The stage used Spark 4.3.0, four CPUs, an 8 GiB driver heap and 48 shuffle
partitions. It took 468.7 seconds, with 4,532,752,384 bytes measured peak
driver RSS. The classifier and novelty model contain 25,305 and 20,254 bytes
of registered payloads. The retrieved compact outputs total 24,546 bytes.

The archived binary gates retain the original retrospective C design,
including later training or calibration dates. The family stage uses the
[earlier-only amendment](../../../docs/phase9_c_methodological_amendment.md).
