# Phase12 operational protocol amendments

## Amendment1, 2026-11-25, capture-only timestamp policy

The frozen protocol requires preserving the prior timestamp-anomaly eligibility policy. Source inspection of docs/phase6_replay_protocol.md confirms that fourteen flagged records remain in capture-day-only replay buckets. The first Phase12 implementation applied a stricter temporal_eligibility filter and omitted them from its capture-level cohort. This was implemented before fitting in commit6d494b8, but it does not fully preserve the inherited capture-only policy.

The primary replay will therefore include all16,232,943 verified feature-ready observations and retain every original eligibility flag. All arrivals remain simultaneous capture-day blocks. No intraday position or valid event time is assigned to the fourteen flagged observations. Their predictor-group roles use the same frozen hash rule as all other observations. This correction follows the explicit inherited policy, without choosing a mask from predictive outcomes.

Version1 of the notebook has a separate support-lookup defect and is rejected. Version2 correctly executes the fourteen-row-exclusion stricter time-eligible sensitivity cohort of16,232,929 rows, but is not the primary policy-preserving experiment. Its source/output receipt and completed metrics remain separately recorded. Version3 is the replacement primary Stage12C. No hypotheses, model parameters, threshold budget, trigger threshold, labels, seeds, role assignments or scheduling rules change. Later stages use the corrected cohort and its exact frozen initial saved pipeline. Do not pool the stricter sensitivity with the primary population.

The correction was documented before fitting the replacement primary models or evaluating later stages. Negative results from the stricter cohort are retained. Any differences caused by the fourteen observations will be reported as population coverage, not adaptation improvement.
