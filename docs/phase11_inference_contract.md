# Phase 11 inference contract

Use a named detector, pinned library version, frozen configuration, signal identifier and unit declaration. A batch has a stable identifier and preserves event ordering. `DetectorState.batch` ignores a previously processed batch identifier and advances the observation clock only for new batches. Its trusted serialized snapshot restores detector parameters, state, observation clock and processed identifiers.

Label-dependent binary updates require a released error in {0,1}. Aggregate error rates require an explicitly window-level compatible monitor. LabelSchedule retains labels until their simulated release window. An alert identifies a monitored change signal. It carries no attack confirmation or production action authorization. Phase 12 must separately verify its acceptance gate before using any detector for adaptation.
