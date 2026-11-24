# Phase 10 pattern inference contract

Contract version phase10-pattern-v1. The registry identifies the feature order, finite-value policy, frozen reference boundaries, selected patterns and validation-selected threshold. Preserve the original Phase 8 and Phase 9 decision fields when joining pattern evidence to those contracts.

Each input produces deterministic transaction items, matched pattern identifiers, matched rule identifiers where applicable, reference support and enrichment provenance, pattern score, frozen threshold and review indicator. The score is the fraction of selected patterns matched. All cutoffs are right-closed, repeated boundaries are collapsed, missing and invalid numerical values receive explicit MISSING items after the established finite-value mask, and out-of-reference-range values use the endpoint intervals. Metadata, labels, fingerprints and capture dates are excluded from inference items.

The review indicator is score greater than or equal to the frozen threshold. With no eligible patterns the score is zero and validation may select a threshold above one to meet the benign false-alarm budget. Unknown input schemas must return unsupported_input with no score. Pattern evidence has descriptive association provenance and carries no calibration claim as attack probability. A rule match requires every antecedent item. Synthetic transaction parity and frozen-score parity must pass before registry release.

The chronological registry was validated from exact retained signature counts. Its frozen patterns and threshold, model component hashes and independent reload receipt are indexed by the completed Phase 10 manifests.
