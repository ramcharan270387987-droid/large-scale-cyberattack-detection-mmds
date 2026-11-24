# Phase 6 interpretation

Six raw feature histograms, three classifier score distributions and cluster occupancy use frozen training-capture aggregates. Jensen–Shannon divergence is in bits. The novelty comparison uses strict exceedance of the saved K-Means cutoff. Only retrospective performance warnings use binary labels. Random Forest recall was 88.9772% across the retained training captures and 0.2000% across the later captures. The training baseline includes rows used to fit the model and can overstate generalization.

## Later daily shifts

| Day | Largest raw feature shift | Feature JS | Random Forest score JS | Cluster JS | Alert records |
| --- | --- | --- | --- | --- | --- |
| 2018-03-01 | flow_duration | 0.05742 | 0.23164 | 0.04560 | 26 |
| 2018-03-02 | flow_duration | 0.07623 | 0.26602 | 0.09671 | 21 |

Alerts can reflect changing traffic mix or capture conditions. The replay measures observed labeled performance, and establishes neither a change in the predictor–label relationship nor discovery of a novel attack. Daily and intraday alerts can describe the same flows and are counted as separate records. Capture-only rows preserve the observed multiplicity of timestamp anomalies without assigning them an intraday window.

Offline refresh was omitted. Phase 6 preserves both March captures as final holdout, and the collection has no verified schedule for the release of analyst-confirmed labels. Processing timestamps measure the Kaggle run. Original event timestamps remain wall-clock values with unverified timezone.

[Protocol](phase6_replay_protocol.md) · [Streaming results](../reports/phase6_streaming_results.md)
