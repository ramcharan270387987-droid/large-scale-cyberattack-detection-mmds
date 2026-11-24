# Phase 11 limitations

The historical corpus was examined in earlier phases. Capture boundaries describe provenance and do not identify true concept changes. Historical alerts have no authoritative true-drift labels, so historical drift recall, precision and false-positive rate are undefined. Association with model errors is descriptive.

Historical binary DDM is unsupported because within-window binary-error ordering was not saved. Aggregate error-rate monitoring remains separate. Historical KSWIN cannot complete its 100-observation warm-up in 49 windows. Low-support capture-only batches are preserved in counts and excluded from updates. Label delays are simulations, and labels released after the last feature window remain pending.

Synthetic mechanisms offer controlled evidence within their declared signal domain. Independent stationary calibration does not guarantee the same alarm rate on other stationary distributions. Correlation monitoring uses a transformed product, and missingness monitoring uses an indicator. No synthetic observation represents a discovered attack. Pickle snapshots must come from trusted experiment code. Snapshot bytes differ from complete resident process memory.
