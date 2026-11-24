# Phase 11 advanced drift detection results

## Objectives and protocol

This study compares controlled synthetic change detection with retrospective monitoring of previously examined network captures. The original phase11-v1 protocol and primary results are preserved. The finalization sensitivity plan was committed before its supplemental experiments. Historical distribution changes have no authoritative concept-drift labels.

## Data and signal provenance

The verified Phase 6 Spark evidence represents 15,322,987 retained flows in 49 batches. Four batches have fewer than 100 flows: two capture-only anomaly batches with five and nine flows, and two ordinary intraday batches with 50 and 53. The default historical monitor updates on 45 supported windows. The evaluation subset has 36 supported windows, with attack-dependent metrics absent on some windows. Eighteen primary predictors remain unchanged. No raw dataset was downloaded for this finalization.

## Implementation and experimental populations

River 0.22.0 supplies ADWIN, Page-Hinkley, KSWIN and binary DDM. JS uses base-two logarithms and PSI natural logarithms, with 1e-6 count smoothing. Synthetic reference bins and thresholds use independent calibration seeds. Synthetic evaluation uses seeds 23013–23015, 4096 arrivals and a primary warm-up of 256. DDM targets released binary-error episodes. Other detectors target the observed feature signal, including explicit missingness or prior signals where declared. Native reset semantics remain intact unless the supplemental external-reset policy explicitly reconstructs a detector.

## Synthetic effectiveness and stationary alarms

| Detector | Target episodes | Detected | Missed | Stationary false alarms / 11,520 eligible arrivals | Mean detected delay in arrivals |
|---|---:|---:|---:|---:|---:|
| ADWIN | 27 | 24 | 3 | 0 | 152.14 |
| PageHinkley | 27 | 18 | 9 | 0 | 119.57 |
| KSWIN | 27 | 17 | 10 | 7 | 76.43 |
| DDM | 6 | 6 | 0 | 1 | 26.00 |
| JS | 27 | 24 | 3 | 1 | 129.67 |
| PSI | 27 | 24 | 3 | 3 | 153.43 |
| FixedJS | 27 | 24 | 3 | 0 | 140.33 |

The mean delay averages detected stream/episode summaries and is undefined when no episode is detected. The table uses zero simulated label delay. DDM has a different target set and cannot be ranked directly against feature detectors by this average. KSWIN detects abrupt shifts quickly but produces more stationary alarms than ADWIN or Page-Hinkley. No detector consistently dominates across target mechanisms, missingness policies and cost. Positive shifts in the controlled feature-label relationship are synthetic concept experiments and provide no independent real-traffic confirmation.

## Label timing and historical monitoring

DDM consumes binary errors only after their simulated release at zero, one or three 64-arrival windows. Historical aggregate-error updates respect the analogous replay-window clock. Unreleased labels at stream end remain pending. Historical binary DDM is unsupported because original within-window error order was not saved. Historical KSWIN cannot satisfy its fixed 100-observation warm-up within 49 windows. These are documented methodological limitations, not successful no-drift outcomes.

## Reference and warm-up sensitivity

The supplemental grid contains 162 comparisons across reference lengths or reporting warm-ups of 64, 256 and 512. JS/PSI change their independently calibrated reference. Adaptive methods retain native updates and vary reporting eligibility, including KSWIN’s minimum of 100. This adaptive comparison changes excluded warm-up support, not the internal algorithm. Eligible-arrival denominators are 4096 minus effective warm-up. Repeated alerts within a 512-arrival event horizon are separate from matched detections and excess alerts.

## Reset sensitivity

Native continuation and explicit external reset each detected 21 of 24 recurring episodes across detector/seed combinations and produced nine excess alerts. Explicit reset performed 36 external reconstructions. Native continuation performs no additional reset. Cooldown preserved 21 detected episodes and suppressed one raw alert; all native state updates continued. Thus suppression and resetting are distinct operations. DDM may miss error-rate decreases, consistent with its error-increase orientation.

## Missing-input sensitivity

There are 132 comparisons over random missingness, a consecutive burst, post-change missingness and nonfinite arrivals. Skip and reference-median policies detected all 36 feature targets in their respective grids. Histogram support suppression missed six of 24 targets. The indicator policy targets missingness transitions and missed three of 27 targets. These denominators describe different signals. Delay is in original arrival observations; valid-observation delay and effective update counts are separate columns. No invalid input is silently replaced by zero. Unavailable update results remain distinct from negative alerts.

## Minimum-support sensitivity

RF and cluster histogram eligibility changes from 49 windows at minimum support one to 45 at 100, 44 at 1000 and 43 at 10000. Saved feature-JS, released error support, capture-level pattern support and family-label support have separate records and units. Zero-support family strata remain unavailable. Suppressed windows have null alert fields. No historical false-alarm rate is inferred without event truth.

## Detector agreement

There are 495 matched synthetic pair/scenario/seed comparisons plus seven compatible historical comparisons. Synthetic pairs use 60 post-warm-up intervals of 64 arrivals. DDM is excluded from feature-signal agreement because it observes a different signal. Exact-interval agreement is distinct from one-to-one positive matches within one interval. Historical comparisons retain only mutually supported windows after native warm-up. JS and PSI share one positive and 35 negative historical histogram intervals, yielding Jaccard and kappa one in that narrow comparison. ADWIN/Page-Hinkley comparisons have 16 supported score-mean intervals and 16, 15 or 13 released-error intervals depending on label delay; all-zero Jaccard and kappa remain undefined. Agreement alone does not establish correctness.

## Association with observed performance

The 144 association summaries cover JS/PSI and eight RF outcome measures at lags zero, one and three, with three label-release assumptions. The paired table records source, outcome, release and analysis clocks. At contemporaneous immediate-label settings, JS/error Pearson is 0.0219 and PSI/error Pearson 0.0232 over 36 paired windows. For recall, Pearson values are 0.4606 and 0.2345 over 22 pairs, while rank associations are 0.0695 and −0.1679. Magnitude and direction depend on the metric and estimator. Row-weighted correlations and one-window before/after changes are descriptive. Capture gaps, changing prevalence, rare-family support and temporal dependence prevent causal or reliable future-failure claims. Family-specific window recall is unsupported by the saved aggregate schema.

## Ensembles, costs and recovery

The existing 66 ensemble/control ablations and 36 window/magnitude sensitivity records remain preserved. The ensemble is fixed at two detector families within 64 arrivals with cooldown. It is not selected on final outcomes. Initialization, update, snapshot and restore times and serialized state bytes are measured in 36 supplemental cost records. Process RSS is a cumulative process high-water mark, not isolated detector allocation. Historical costs are per supported aggregate window. No claim is made that advanced detectors individually processed all retained flows, or that single-node measurements demonstrate multi-node scalability. Four detector states passed trusted snapshot/reload and duplicate-batch checks.

## Dashboard and scientific contribution

The isolated Drift Detection Laboratory presents primary evidence and the supplemental grids, agreement, associations, costs and limitations. All downloads use filtered aggregate tables. The contribution is a reproducible monitoring comparison and explicit information-availability accounting using established detectors. Shift alerts are evidence to investigate, not confirmation of attacks or proof that adaptation will improve outcomes. Phase 12 has not started and requires separate user authorization.

## Reproducibility and limitations

Reuse Kaggle notebook versions 1 and 2 and their hashed receipts. Run `PYTHONPATH=. python -c "from src.drift.finalization import run; run('/tmp/phase11-finalization')"` with the pinned River dependency to reproduce the bounded supplemental experiments. The original protocol, finalization plan, method definitions and registry describe frozen choices and unsupported cases. Regenerate final figures and this report with `python scripts/finalize_phase11_report.py`. Timings vary by host. Synthetic evidence, retrospective historical associations and future independent validation remain separate. The completed experiment manifest records the final gate, test results, hashes and protected-reference verification.

## State clocks, runtime compatibility and browser checks

The state adapter distinguishes arrivals, valid updates and suppressed updates, restores state after a failed batch, and leaves missing counters unknown in legacy snapshots. Additional engineering probes measure duplicate checks, snapshot/restore and alert-metadata construction separately from detector updates. The isolated preview runtime uses Starlette 0.49.3 with Streamlit 1.67.0 to avoid the observed Starlette 1.10.0 static-file failure. Browser evidence includes desktop and mobile screenshots, no HTTP or page errors, and actual 297-record downloads. Reference-score history includes retrospective scoring of the archived RF training population and supports no prospective deployment claim.

## Final validation

The complete regression run passed 100 research tests and 8 dashboard tests. Preview validation covered 2022 supported filter groups and 20 sections. No Phase 12 implementation was started.
