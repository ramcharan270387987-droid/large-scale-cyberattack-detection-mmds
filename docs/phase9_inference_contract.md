# Phase 9 hierarchical inference contract

Contract version `phase9-hierarchy-v1`. This contract specifies the inference
interface for an archived binary gate and a frozen family pipeline. The
experiment manifest records which gate, population and family pipeline have
completed empirical validation.

## Required model metadata

- `binary_model_version` identifies the producing notebook version, exact
  archived pipeline and frozen operating policy.
- `family_model_version` identifies the producing notebook version and
  family pipeline. Its registry supplies the feature order, preprocessing,
  training-derived class-ID mapping and rejection configuration.
- The two model versions are independent. A consumer must resolve the ordered
  family vocabulary against the family model version before decoding scores.

## Per-flow fields

| Field | Meaning |
|---|---|
| `binary_attack_score` | Raw score from the selected binary gate. A hybrid or novelty-derived score has its own scale. |
| `calibrated_attack_probability` | Phase 8 supervised calibrated probability when available, with calibration provenance in the binary model registry. Null for an uncalibrated detector. |
| `binary_decision` | `BENIGN`, `ATTACK` or `ABSTAIN`. Use the archived gate's threshold and tie policy. |
| `predicted_family` | Family at the chosen class ID before rejection. Null if the family stage is skipped. |
| `family_probability_vector` | Scores in ascending training-derived class-ID order. RF emits vote scores. There is no coordinate for `UNKNOWN`. |
| `maximum_family_confidence` | Highest family score. |
| `top_two_probability_margin` | Highest minus second-highest family score. |
| `predictive_entropy` | Shannon entropy normalized by the logarithm of the supported class count. |
| `novelty_score` | Training-reference centroid distance or its training-derived percentile, identified by the registered method. Null when unavailable. |
| `rejection_method`, `rejection_threshold` | Frozen score transform and cutoff. The Phase 9 family rules use uncertainty increasing with rejection risk, and reject only above the frozen integer bin. |
| `unknown_decision` | True when the attack gate passes the flow and the family rejection rule rejects it. |
| `review_required` | True for family UNKNOWN or an abstaining binary gate. A consumer can retain Phase 8 triage review as a separate operational flag. |
| `final_hierarchical_decision` | `BENIGN`, a known family, `UNKNOWN` or `ABSTAIN`. |
| `abstention_or_rejection_reason` | `unsupported_input`, the frozen family rejection method, or null for a routine decision. |

Use the Phase 8 inference contract's model version, supervised score, calibrated
probability, novelty percentile, hybrid score, threshold and triage outputs
with their existing definitions. The Phase 9 evaluation uses the frozen
binary operating point. The Phase 8 lower review threshold defines a separate
triage policy.

When the binary gate returns BENIGN, the final decision is BENIGN and family
outputs are null in deployment. Evaluation may score these attacks in a
separate oracle diagnostic. For an ATTACK decision, accept the known family
unless the rejection condition holds. Preserve missed attacks in the
end-to-end denominator. The rejection budget applies only to known validation
attacks, and the realized test burden must be measured separately.
