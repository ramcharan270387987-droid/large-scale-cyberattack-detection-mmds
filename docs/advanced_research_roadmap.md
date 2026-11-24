# MMDS advanced research roadmap

The validated Phase 1–7 dashboard is preserved on `work` and tagged `v1.0-mmds-validated-baseline`. Advanced experiments run on `research-v2`.

Phase 8 asks whether calibration, class weighting, novelty and selective review help under traffic shift. The evaluation uses historical flow aggregates and verified CPU notebooks. Its contribution is a leakage-aware comparison and an auditable inference contract. Spark classification, K-Means, probability calibration and score fusion are established methods.

Later work needs independently collected compatible traffic with outcome labels withheld from Phase 8 decisions, enough independent temporal blocks to support uncertainty estimation, and declared operational error budgets. Phase 14 is the intended independent-evaluation stage. Production dashboard integration is deferred to Phase 15. Phase 8 leaves the deployed dashboard unchanged and includes no adaptive learning, multiclass modeling, FP-Growth or explainability implementation.

Prior-work questions for later review include false-alarm-constrained selection under distribution shift, calibration transport across domains, distance-based novelty normalization, and selective classification with correlated flow groups. [Protocol](phase8_research_protocol.md) · [Inference contract](phase8_inference_contract.md)
