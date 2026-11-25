# Model lifecycle

Initial fitting precedes replay. A request is eligible only after its released-label support, cooldown, idempotency and budget checks pass. Candidate preprocessing/fitting/save/reload/validation must succeed. Validation failure keeps the incumbent. Guarded policy adds matched incumbent/candidate validation and retention checks. Acceptance schedules a pending version; actual activation is a distinct future event.

Registry records preserve model key, source commit, feature order, training dates/rows/classes/families, transforms, component hashes, reload receipt and measured costs. Event tables add parent, released calibration dates, threshold, promotion metrics, rejection reason and activation time. Per-window tables identify each version's coverage. Models are immutable private Kaggle outputs. Git never contains fitted weights.

Released-label degradation can restore the previous verified model only for future arrivals. A performance rollback records a natural event; controlled corruption, interrupted updates and duplicate requests are separately labeled injected failures. A restored pipeline is reloaded and its registered probes checked before use. No terminal label flush or retrospective prediction replacement is permitted.
