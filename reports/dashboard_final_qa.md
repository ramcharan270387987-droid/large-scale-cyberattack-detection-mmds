# MMDS dashboard final QA

The public Streamlit URL supplied by the maintainer could not be reached from Codex Cloud. Chromium reported `ERR_TUNNEL_CONNECTION_FAILED`, and an HTTPS probe received HTTP 403 from the CONNECT proxy. The results below cover a local checkout of `work` running the deployment entry point with the pinned dependencies.

## Evidence checks

| Measure | Reconciled result |
|---|---:|
| Dataset flows | 16,232,943 |
| Benign flows | 13,484,708 |
| Attack flows | 2,748,235 |
| Retained replay flows | 15,322,987 |
| Microbatches | 49 |
| Alert records | 102 |
| High-severity alert records | 62 |
| Replay throughput | 17,770 flows/s, rounded |

All 30 packaged CSVs were checked against the original committed reports. The arithmetic audit reconciled Phase 1 capture and label counts, Phase 2 Parquet counts, Phase 3 daily prevalence and support, Phase 4 confusion-derived metrics and family support, Phase 5 cluster occupancy and novelty rates, and Phase 6 window totals, throughput, severity, and alert eligibility. Phase 6 held-out supervised results matched Phase 4 B. Phase 6 held-out novelty counts and rates matched Phase 5 B P99.

| Supervised protocol | Test flows | Test attack prevalence |
|---|---:|---:|
| A · Grouped random | 2,432,292 | 14.97% |
| B · Chronological | 980,109 | 21.28% |
| C · Web capture holdout | 1,458,218 | 0.05% |

All 36 saved supervised result rows were checked across both evaluation splits. The checks independently recomputed rates from confusion counts. ROC-AUC and PR-AUC were checked against the published evidence and cross-phase results where equivalents exist. Full score vectors were outside the aggregate scope.

| K-Means experiment | Selected k | P95 | P99 | P99.9 |
|---|---:|---:|---:|---:|
| G · Global retrospective | 5 | 13.379028 | 31.042925 | 263.375287 |
| B · Historical reference | 12 | 8.508048 | 16.679406 | 35.317582 |
| C · Web capture holdout | 12 | 8.433428 | 17.880004 | 42.384383 |

Cutoffs are squared distances shown here to six decimal places. All 147 saved novelty rows were reconciled. The audit independently recomputed cluster Jensen–Shannon divergence from retained occupancy and the frozen reference counts. Input-feature and classifier-score shift values use the preserved published aggregates. The monitored quantities describe historical behavior and do not establish concept drift or a newly discovered attack.

## Corrections

- Upgraded Streamlit from 1.58.0 to 1.67.0 after reproducing HTTP 500 on the local favicon. The updated runtime returns HTTP 200.
- Raised table and chart toolbars above their content layers so pointer clicks reach download buttons.
- Added a zero-support state when a family is present as a zero-count source row for a capture. Expanded the missingness selector to the full published feature inventory.
- Named the distribution quantiles and units, exposed destination-port ranking scope, and clarified supervised cutoff and binned ranking metrics.
- Added distinct colors for the 12-cluster fits and a labeled cutoff marker to the novelty histogram. Clarified replay shift units and kept severity colors consistent.
- Made the architecture flow readable at phone width and preserved source cell text in alert exports, including decimal precision.

The original Phase 1–6 reports, manifests, notebooks, data package and model results remain at their verified values. No model was retrained and no Kaggle experiment was rerun.

## Repeat the checks

```sh
python scripts/validate_dashboard_package.py
python scripts/audit_dashboard_evidence.py
python -m unittest discover -s tests -p test_dashboard.py
python scripts/audit_dashboard_browser.py --url http://127.0.0.1:8501 --screenshots /tmp/mmds-dashboard-qa
```

For the browser command, start the pinned Streamlit app first. Use an environment with Playwright and Chromium. The browser audit records failures, checks each evidence link's Git target, exercises browser downloads, and captures the responsive layouts.

## Local Chrome results

| Page | Result | Coverage |
|---|---|---|
| Overview | PASS | Navigation, headline totals, recall comparison and PNG export |
| Dataset explorer | PASS | Ten capture days, family and original label selectors, protocol and port selectors, feature statistics and missingness, zero-support state |
| Spark SQL analytics | PASS | All statistic and workload choices, prevalence and family plots, correlation and timing tables |
| Machine learning | PASS | A/B/C, test and validation, six comparison metrics, all 36 confusion matrices |
| Clustering | PASS | G/B/C selection, five charts, cluster profiles and fit statistics |
| Novelty detection | PASS | All 21 valid experiment, population and cutoff combinations |
| Historical replay | PASS | All 59 saved window selections, eligible counts, novelty flags, five charts, benchmark and recovery tables |
| Alerts explorer | PASS | All filter types, combined filters, disabled empty-state export, exact 62-row high-severity CSV |
| Architecture | PASS | Diagram and documentation targets, mobile navigation and readable sequence |

Chromium passed all nine routes at widths of 1,440, 768 and 390 CSS pixels. The audit checked 17 chart PNG downloads, 19 dataframe CSV downloads, the static confusion matrix, and 36 Git evidence-link targets. The alerts export was compared cell for cell with the original records. A separate mobile check exercised opening the sidebar and navigating to Architecture.

The corrected runtime produced no uncaught JavaScript errors, application exceptions or failed content loads in the audited local routes. Streamlit issued two recoverable relative health and host-configuration probes when opening each non-root route cold. The root health path and favicon returned HTTP 200, and all those routes rendered.

**Automated tests:** 42 research tests and eight dashboard tests passed.

[Desktop overview](../docs/screenshots/final-qa/overview-desktop.png) · [Novelty](../docs/screenshots/final-qa/novelty-desktop.png) · [Phone architecture](../docs/screenshots/final-qa/architecture-mobile.png)
