# Phase 9 verified checkpoints

The study remains incomplete. Only retrieved and validated stages below support experimental claims.

| Scenario | Version | Model | Known test rows | Accuracy | Macro F1 | Seconds |
|---|---|---|---:|---:|---:|---:|
| A | 2 | rf_capped_10 | 364120 | 0.7405058771833462 | 0.6332995121619363 | 332.7 |
| B | 7 | lr_inverse | 0 | None | None | 331.1 |
| Bot | 9 | rf_capped_10 | 314058 | 0.6819695724993473 | 0.6109909863277436 | 305.6 |
| DDoS | 11 | lr_capped_10 | 109434 | 0.7608330135058574 | 0.697328331234674 | 630.7 |
| Infiltration | 10 | rf_capped_10 | 300984 | 0.7441757701406054 | 0.7665923841550745 | 449.1 |
| Web | 8 | rf_capped_10 | 363966 | 0.7372721627844359 | 0.7530718084372332 | 457.0 |

Zero known-family chronological support means closed-set chronological classification is unsupported. Unknown-family rejection remains a separate result.

All four family holdouts are complete and validated. The [chronological B](phase9_hierarchy/B/results.md) and [retrospective C](phase9_hierarchy/C/results.md) hierarchies are validated. Remaining robustness checks, novelty-model persistence for the original open-set scenarios and final research interpretation are pending.
