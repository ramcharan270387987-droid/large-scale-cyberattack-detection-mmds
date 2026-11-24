# Phase 5 clustering protocol

The frozen `phase5-v1` experiments use the Phase 2 Notebook Output version 1. The run verifies the stored receipt, policy, Parquet metadata, label mapping, all ten dates and the original population before fitting. The clean layer supplies wall-clock timestamps, and the feature-ready layer supplies the canonical input contract. [Configuration](../configs/clustering_experiments.yaml)

| Experiment | Fit reference | Evaluation |
| --- | --- | --- |
| G · global retrospective | All ten capture days | Full capture collection, including the training population. External composition and novelty flags are descriptive. |
| B · historical reference | February 14–22 observed captures | Intermediate February 23 and 28, then later March 1–2. This is the chronological experiment. |
| C · Web capture holdout | The seven Phase 4 C training captures | February 28 validation and February 22–23 test. This capture holdout includes earlier test days and represents a scenario contrast. |

B and C recreate the Phase 4 predictor-group assignment and purge later-split occurrences of a predictor key. They reconcile the retained binary and family counts to the Phase 4 manifests. A digest scope contains the ordered pre-imputation numeric tuple. Provenance and labels cannot alter group assignment. The report records rows removed by purging and retains duplicate multiplicity within the remaining cohorts. Global results include a separate exact-content representative count by cluster.

## Fitting and preprocessing

The 18 shared numerical features use the Phase 4 allowlist. Target labels, protocol, ports, identifiers, timestamps, day, and fingerprints stay outside predictors. Two initial TCP window counts are excluded by the reused policy. Missingness flags are recorded as input diagnostics and omitted from the vector because they can identify capture conditions.

A fixed seed of 23013 and the versioned predictor digest assign entire groups to 250 out of 10,000 buckets for fitting. The next 12 buckets form a disjoint, bounded training-reference probe for silhouette, robustness and calibration. Actual counts and proportions are recorded. B and C sample only their earlier or assigned training split. All retained evaluation records receive a score. The preprocessing pipeline masks nonfinite values, applies signed `log1p(abs(x))`, removes constant or entirely missing reference columns, imputes training medians, then centers and divides by the training standard deviation. Scaling keeps raw byte, time and rate units from dominating distances by magnitude. The signed transform preserves the sign of valid negative values. Only numerical predictors enter the preprocessing fit, and only vectors enter K-Means.

Each experiment fits k = 3, 5, 8 and 12 with Euclidean K-Means, k-means|| initialization, two initialization steps, a 16-iteration budget and tolerance 0.0001. Select the highest squared-Euclidean silhouette on the bounded disjoint reference probe, requiring all training clusters to be occupied and each to account for at least 0.1% of training occurrences. Break ties using the smaller k. Report exact fit WSSSE and cluster sizes alongside the probe-based silhouette. The seed repeat and no-log scaling check reuse the selected k and reference samples. Adjusted Rand index compares the same probe rows without assuming matching cluster IDs. Between-centroid feature variation is descriptive and weighted by fitted cluster sizes. Related packet and byte measurements remain correlated and can weight shared behavior more heavily.

## Novelty and evolution

The novelty proxy is squared Euclidean distance to the assigned nearest centroid in fitted feature space. Reference P95, P99 and P99.9 use Spark approximate percentiles with accuracy 8,192 on the disjoint training-reference probe, without labels. Flags use strict exceedance of the cutoff. P99 is the primary sensitivity point. Label composition, binary precision and recall, benign false-positive rate and family recall are computed after freezing the model and thresholds. Undefined rates remain blank. Family support below 100 is flagged, and counts retain recorded multiplicity.

Compute cluster occupancy by capture day and in observed three-hour wall-clock windows. Only windows exclude timestamp-ineligible rows. Source timezone is unverified. Jensen–Shannon divergence uses base-2 logs against the exact cluster occupancy of the full retained reference population. Zero bins contribute zero to their own KL term, and no smoothing is applied. G uses its all-day aggregate as the descriptive reference, which includes the day being compared. B and C reference their assigned training days only. Counts and occupied-cluster support accompany each value. Capture composition, class mix and grouping dependencies limit statistical interpretation.

Phase 4 comparisons use the saved Random Forest metrics and matched retained-cohort denominators. Phase 4 saved no row-level predictions, so the comparison is aggregate and thresholds differ in purpose. Occupancy differences and high distance can indicate patterns worth investigating. Establishing detection efficacy, novel attack types or concept drift would require a separate validation design.

## Execution

Each experiment runs as a distinct private CPU notebook version with Spark 4.3.0, four local workers, an 8 GiB heap, 48 shuffle partitions and 64 MiB input splits. Persist shared projections to disk and keep the internal probe below 40,000 rows. Emit bounded frequencies and diagnostics only. The notebook saves and reloads the fitted pipeline. Retrieval independently checks model file hashes and preserves the payload only in temporary storage.
