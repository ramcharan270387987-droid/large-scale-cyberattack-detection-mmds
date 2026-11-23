# MMDS dataset research feasibility

## Leakage review

| Input | Risk | Treatment in evaluation |
| --- | --- | --- |
| Original traffic label and derived class fields | Directly contain the training target | Keep the original multiclass value and the proposed binary target outside the feature vector. Evaluate mapping and unmapped labels explicitly. |
| Timestamp, source filename, and capture day | Can reveal the attack schedule and capture membership | Use these for provenance, split boundaries, event ordering, and drift comparisons. Measure performance with schedule fields withheld. |
| Flow identifiers and IP addresses, where present | Can let a model memorize a host, flow, or capture setup | Preserve these for diagnostics and possible group keys. Keep raw identifiers out of the initial cross-day feature vector; evaluate separate identifier ablations if operational availability is established. |
| Ports, protocol, and session information | May provide deployment-relevant transport context and can also proxy the lab setup | Compare transport-context ablations using held-out captures. Treat port encodings as categorical or otherwise justify their representation. |
| Exact duplicates and feature twins | A row-level random split can expose equivalent measurements to both training and evaluation | Keep audit counts intact. Place copies in the same split and check remaining overlap using compatible feature fingerprints. Retain label conflicts for adjudication. |
| Columns present only in one capture or with per-capture encodings | Missingness and preprocessing can reveal capture identity | Use a reviewed common feature intersection for multi-capture comparisons. Fit encoders, imputers, scalers, and any anomaly thresholds on training partitions only. |

The full-value comparison measured 410,707 excess copies across 107,670 groups. It reported zero groups spanning capture days. Full-value equality includes the timestamp field, so a cross-day split still needs the feature-only overlap check.

## Research verdicts

| Research component | Verdict | Evidence and evaluation conditions |
| --- | --- | --- |
| Binary attack classification | Supported | The proposed mapping covers 13,484,708 benign and 2,748,235 attack rows, and both groups are present on all ten days. Attack prevalence ranges from 0.0345% on February 22 to 65.5883% on February 21. Report per-day false alarm rates and precision-recall results. |
| Multiclass attack-family classification | Partially Supported | The 15 original labels provide benchmark targets. SQL Injection has 87 rows, Brute Force -XSS has 230, and Brute Force -Web has 611. Ten of the 14 attack labels occur on a single day. A closed-set evaluation can cover those labels with within-capture groups. A day-disjoint split cannot place every attack label in both train and test. |
| Random train/test evaluation | Partially Supported | Random sampling can provide a within-dataset baseline. The audit found 410,707 excess exact copies and 22,129 feature fingerprint groups with differing labels. Group duplicates and compatible feature twins before splitting, and report this as a secondary evaluation. |
| Chronological evaluation | Partially Supported | Day-first parsing accepted every timestamp. Fourteen parsed dates fall in January 1970 across the February 14 and 22 files. Partition by verified capture day, flag anomalous times before event-time use, and publish train/validation/test label coverage. Specify how later unseen attacks are scored. |
| Scenario-aware held-out evaluation | Partially Supported | Capture days provide ten observed groups, and attack categories are concentrated by day. The public files do not contain an independent scenario label. Use capture-held-out evaluation with scenario provenance treated as a proxy. Report attacks absent from training and treat the February 20 schema as a distinct risk. |
| K-Means clustering | Supported | The shared 80-column schema provides 77 numeric candidates and one categorical candidate after excluding the label and timestamp. The audit found 59,721 NaNs, 131,799 infinities, and 96 constant feature profiles across captures. Define finite-value and variance policies on training data, scale numeric features, and withhold the target from clustering. |
| Structured Streaming historical replay | Partially Supported | Ten capture days support ordered offline replay with an explicit tie-breaker for second-resolution timestamps. Calendar order uses day-first wall-clock times. Source timezone and clock synchronization are unverified, and the 14 timestamp anomalies need a replay policy. |
| Input-distribution-shift monitoring | Supported | The ten captures and their common schema support an offline comparison across time windows. February 20 supplies about 49% of all rows and adds four capture-specific fields. Use the shared features, distinguish structural missingness from value changes, and track label prevalence separately from input drift. |
| Controlled model-refresh experiments | Partially Supported | The capture sequence supports a retrospective frozen-versus-refresh comparison. Single-day labels, the changing attack mix, and absent label-arrival timing constrain the interpretation. Prespecify when each window's labels become available and measure later-window results before updating. |
| Spark scalability benchmarking | Partially Supported | The exact pass processed 6,886,649,507 bytes and 16,232,943 rows at `local[4]` in 509.978 seconds. The profiling loop at `local[2]` took 2,722.49 seconds and performed different work. Benchmark fixed workloads across input sizes, partitions and worker counts before making scaling claims. |

## Temporal and schema considerations

March 1 and March 2 contain 1,379,675 timestamps that also parse as month-first. The day-first interpretation agrees with the March filenames. The other 14 ambiguous timestamps are the January 1970 outliers. Across the parsed records, day-first dates match filenames for 16,232,929 rows and the alternate month-first parse matches zero. Keep the raw times, flag the January dates, and treat event timestamps as local wall-clock values until the source timezone is established.

Nine captures share one ordered header. February 20 adds `Flow ID`, `Src IP`, `Src Port`, and `Dst IP`. Reserve those fields for provenance or a separate within-capture design. Presence of the extra fields alone can identify that capture. Seven mounted files each have exactly 1,048,576 physical lines. Coverage claims apply to the mounted release, and the audit cannot establish whether the upstream export retained every recorded flow.

Keep the capture day as a provenance key and document which classes are present in each split. Define evaluation for attacks absent from training, and report class support and macro-averaged metrics alongside prevalence-sensitive measures. [Audit evidence](../reports/dataset_audit.md) · [Source schemas](dataset_schema.md)
