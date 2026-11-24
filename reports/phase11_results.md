# Phase 11 drift detection results

Synthetic evaluation and retrospective historical monitoring have separate targets and units. Stationary calibration seeds differ from all evaluation seeds.

| Detector | Stationary false alarms, three seeds | Abrupt/error matched delays in observations |
|---|---:|---|
| ADWIN | 0 | 63.0, 63.0, 63.0 |
| PageHinkley | 0 | 142.0, 140.0, 134.0 |
| KSWIN | 7 | 12.0, 19.0, 24.0 |
| DDM | 1 | 47.0, 47.0, 62.0 |
| JS | 1 | 63.0, 63.0, 63.0 |
| PSI | 3 | 63.0, 63.0, 63.0 |
| FixedJS | 0 | 63.0, 63.0, 63.0 |

The synthetic suite contains 297 detector/scenario/label-delay comparisons over three evaluation seeds. DDM targets predictive-error episodes. Other detectors target their observed signal distribution. Alert counts have one-to-one event matching, separate repeated episode alerts and undefined missed-event delays. Faster detection must be assessed alongside excess alarms.

## Historical evidence

The saved Spark replay contains 49 batches representing 15,322,987 flows. Two capture-only batches preserve fourteen timestamp anomalies and fail the 100-row monitoring support minimum. Reference batches 0–2 and calibration batches 3–9 precede evaluation. These are aggregate windows. Historical DDM is unsupported without binary error ordering. Historical KSWIN cannot complete its 100-observation warm-up. No historical true-drift labels support efficacy or false-positive claims. Aggregate-error updates respect simulated release delays of zero, one and three windows.

## Robustness and engineering

The sensitivity grid contains 36 JS/PSI comparisons over windows 32, 64 and 128, two magnitudes and three seeds. Ensemble and no-detector ablations are separate. All four River states passed snapshot/restore and duplicate-batch suppression checks. Serialized state bytes and bounded update times appear in the evidence tables. They do not measure complete process resident memory or multi-node scalability.

## Limits and completion

Distribution shifts, model-score changes and predictive-error changes have distinct interpretations. Historical observations are retrospective and family/day-confounded. Synthetic alerts do not confirm attacks. The experiment manifest is the authoritative completion gate for Phase 12.
