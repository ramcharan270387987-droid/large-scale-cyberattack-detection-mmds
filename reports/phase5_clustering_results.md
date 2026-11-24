# Phase 5 clustering and pattern evolution

**READY FOR PHASE 6.** All three Spark 4.3.0 Kaggle runs completed. The saved pipelines passed archive checksum and independent reload checks. The frozen models were fitted on predictor-only data and evaluated using post-fit labels. [Kaggle notebook](https://www.kaggle.com/code/ramcharan2345/mmds-phase-5-clustering-pattern-evolution) · [Full manifests](../manifests/phase5_clustering_models.json)

## Input and cohorts

Each run validated the Phase 2 version 1 receipt, cleaning policy, ten dates and 16,232,943 flows, including 13,484,708 benign and 2,748,235 attack. The 18-feature registry contains no labels, identifiers, ports, protocol or day fields. The historical and scenario cohorts match the corresponding Phase 4 retained binary and family counts. [Cohort evidence](phase5_cohorts.csv)

| Experiment | Retained rows | Overlap rows purged | Fit rows | Fit share | Silhouette/calibration rows |
| --- | --- | --- | --- | --- | --- |
| G | 16,232,943 | 0 | 390,702 | 2.4068% | 18,099 |
| B | 15,322,987 | 909,956 | 318,175 | 2.4119% | 14,426 |
| C | 15,373,842 | 859,101 | 323,731 | 2.3940% | 15,229 |

## K-Means and robustness

| Experiment | Selected k | Probe silhouette | Fit WSSSE | Fit time (s) | Seed ARI | Linear vs log ARI |
| --- | --- | --- | --- | --- | --- | --- |
| G | 5 | 0.6179 | 2,224,306.1 | 15.082 | 0.8955 | 0.2900 |
| B | 12 | 0.6289 | 826,131.4 | 13.601 | 0.8504 | 0.2183 |
| C | 12 | 0.6029 | 856,400.4 | 12.038 | 0.7974 | 0.4202 |

The bounded silhouette selected among k = 3, 5, 8 and 12 on a disjoint reference probe. WSSSE is the fitted sample objective. ARI uses the same probe and compares label-free assignments. The linear and signed-log objectives are measured in different feature spaces. [All trial sizes, iterations and memory snapshots](phase5_model_selection.csv)

## External label composition

| Experiment | Largest cluster | Records | Attack share | Highest attack-share cluster | Attack share |
| --- | --- | --- | --- | --- | --- |
| G | 4 | 5,269,424 | 9.5207% | 0 | 35.9252% |
| B | 0 | 3,367,057 | 0.9917% | 1 | 65.5958% |
| C | 1 | 3,315,657 | 0.9757% | 8 | 50.3938% |

Cluster IDs are specific to each fit. Means, distance summaries, external purity, family and original-label counts describe the retained traffic. Global exact-content sensitivity removes 410,707 excess copies only from the representative count. [Cluster profiles](phase5_cluster_profiles.csv) · [Family and original-label composition](phase5_composition.csv) · [Centroids](phase5_centroids.csv)

## Reference-calibrated novelty

| Experiment | Scored rows | Coverage of original population | P99 squared distance | Flag rate | Benign false-positive rate | Attack recall | Precision |
| --- | --- | --- | --- | --- | --- | --- | --- |
| G | 16,232,943 | 100.0000% | 31.043 | 1.1925% | 1.3604% | 0.3690% | 5.2391% |
| B | 980,109 | 71.0391% | 16.679 | 2.1469% | 2.1521% | 2.1278% | 21.0864% |
| C | 1,458,218 | 69.5333% | 17.880 | 1.6753% | 1.6508% | 55.7751% | 1.5023% |

The primary rule flags strict exceedance of the disjoint reference probe P99. G is an all-day retrospective description. B scores later captures and C tests unseen Web attack captures. A flag describes distance in this feature space. [P95, P99 and P99.9 results with family support](phase5_novelty_metrics.csv)

## Execution

| Experiment | Kaggle version | Through model save (s) | Local workers | Driver heap | JVM peak GiB | Log events |
| --- | --- | --- | --- | --- | --- | --- |
| G | 1 | 578.076 | 4 | 8g | 4.42 | 702 |
| B | 2 | 652.492 | 4 | 8g | 5.14 | 735 |
| C | 3 | 657.111 | 4 | 8g | 4.25 | 783 |

Each run used 48 shuffle partitions and 64 MiB input splits. Figures and summaries were retrieved from the saved notebook outputs. [Pattern evolution and comparison](../docs/phase5_pattern_evolution.md)

## Figures

- [G · cluster sizes](figures/phase5_g_cluster_sizes.png)
- [G · cluster attack share](figures/phase5_g_cluster_attack_share.png)
- [G · family heatmap](figures/phase5_g_family_heatmap.png)
- [G · daily occupancy](figures/phase5_g_daily_occupancy.png)
- [G · temporal shift](figures/phase5_g_temporal_shift.png)
- [G · centroid profiles](figures/phase5_g_centroid_profiles.png)
- [G · distance histogram](figures/phase5_g_distance_histogram.png)
- [G · daily novelty](figures/phase5_g_daily_novelty.png)
- [G · binary novelty](figures/phase5_g_binary_novelty.png)
- [B · cluster sizes](figures/phase5_b_cluster_sizes.png)
- [B · cluster attack share](figures/phase5_b_cluster_attack_share.png)
- [B · family heatmap](figures/phase5_b_family_heatmap.png)
- [B · daily occupancy](figures/phase5_b_daily_occupancy.png)
- [B · temporal shift](figures/phase5_b_temporal_shift.png)
- [B · centroid profiles](figures/phase5_b_centroid_profiles.png)
- [B · distance histogram](figures/phase5_b_distance_histogram.png)
- [B · daily novelty](figures/phase5_b_daily_novelty.png)
- [B · binary novelty](figures/phase5_b_binary_novelty.png)
- [B · supervised comparison](figures/phase5_b_supervised_comparison.png)
- [C · cluster sizes](figures/phase5_c_cluster_sizes.png)
- [C · cluster attack share](figures/phase5_c_cluster_attack_share.png)
- [C · family heatmap](figures/phase5_c_family_heatmap.png)
- [C · daily occupancy](figures/phase5_c_daily_occupancy.png)
- [C · temporal shift](figures/phase5_c_temporal_shift.png)
- [C · centroid profiles](figures/phase5_c_centroid_profiles.png)
- [C · distance histogram](figures/phase5_c_distance_histogram.png)
- [C · daily novelty](figures/phase5_c_daily_novelty.png)
- [C · binary novelty](figures/phase5_c_binary_novelty.png)
- [C · supervised comparison](figures/phase5_c_supervised_comparison.png)
