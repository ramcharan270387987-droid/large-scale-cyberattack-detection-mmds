# Phase 8 inference contract

Use Spark 4.3.0 CPU. Call `src.ml.hybrid_detection.inference(frame, model, km, config, frozen)` with the pinned Phase 8 configuration, frozen population receipt, its saved supervised pipeline and the registered K-Means preprocessing and estimator tuple. The caller supplies the 18 named numeric fields in the registry's original order. Inputs are finite doubles or null after Phase 2 cleaning. Reject non-numeric and nonfinite inputs at the adapter boundary. Do not alter the reference grid, calibrator, fusion weights or threshold bins at scoring time.

| Output field | Meaning |
|---|---|
| `model_version` | Phase 8 protocol version and population identifier |
| `supervised_score` | Selected supervised pipeline score |
| `calibrated_probability` | Platt-style calibrated base output for an eligible population |
| `cluster_id` | Identifier within this exact K-Means artifact |
| `centroid_distance_squared` | Squared distance in the archived transformed feature space |
| `novelty_percentile` | Strict-less reference-grid rank |
| `hybrid_score` | Frozen selected fusion score, with no probability guarantee |
| `decision_threshold` | Inclusive lower score-bin edge or an above-one never-positive sentinel |
| `risk_category` | HIGH_RISK, REVIEW_REQUIRED, LOW_RISK, or ABSTAIN |
| `review_required` | Intermediate-risk referral flag |
| `abstention_reason` | `unsupported_input` for an all-missing vector or invalid score |

Select high risk first using the frozen high threshold. Refer scores between the lower review threshold and the high threshold. Low risk is below the review threshold. All-missing or unsupported inputs abstain. Neither high risk nor novelty confirms an attack. The review-workload rate counts review referrals separately from abstentions.

Resolve archive versions and file hashes through the Phase 8 model registry. Baseline artifacts point to their original pinned mirror. Newly fitted models are saved in the private Phase 8 notebook output. Verify file hashes and stage compatibility before loading. Each validated run records same-probe parity for the reopened processing chain and frozen JSON. No raw prediction records or model archives belong in Git.
