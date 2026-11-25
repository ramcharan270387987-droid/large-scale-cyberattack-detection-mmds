# Phase 13 implementation amendments

## Deterministic group representatives, 25 November 2026

Before inspecting new historical explanation results, source review identified that Spark dropDuplicates does not choose a stable metadata representative when one predictor group spans captures or labels. All rows within a predictor group have identical registered numerical input, so this does not change the group's model input or exact contribution values. It can change the capture/family assignment of a sampled case.

The corrected implementation chooses the first row by record fingerprint, capture day, original label, binary label and family within each group, then orders groups by the frozen seeded hash. It records source-group multiplicity. The update is an operational determinism correction without model, threshold, feature or budget changes. A repartition-invariance test covers a conflicting-metadata group.

Version 1's global native importance and exact numerical reconstruction remain separately auditable. Capture/family strata from that execution require verification against the corrected representative rule before acceptance. Subsequent stages use the corrected helper. They may recompute the affected aggregate case strata while preserving already validated model identities and global explanations.
