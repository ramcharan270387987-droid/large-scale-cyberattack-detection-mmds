# Phase 14 — External validation and computational scalability

## Outcome and reproducibility

This study completes the prespecified external validation and bounded single-machine scalability investigation. It starts from 74e909ac3771dcaf5730437d3567f24c4fa4913b and reuses finalized Phase 13 at ab6e9401b0c9b92e624e5b2b16ec91050a081eb0. Recovered 14D version 1 was accepted without repeating any measured experiment. Stage 14E version 1 supplies the remaining actual optimization/Pandas/inference/mining evidence. The experiment manifest and final independent acceptance receipt are authoritative; source versions, logs, component hashes and raw repetitions are retained. The final remote commit is independently checked after pushing, avoiding a self-referential SHA in this report.

## Research questions and study design

RQ14.1–3 address conditional cross-dataset transfer, target baselines and feature mismatch. RQ14.4–7 cover data volume, worker threads, storage formats, partitions/cache. RQ14.8–10 address bounded Pandas comparison, workload costs and limits of the observed infrastructure. The frozen protocol is docs/phase14_research_protocol.md, prespecified at e0347bc57d650acaec2de83bdee2ad7ca5e8c23a. Documented amendments retain failed attempts, raw label bytes, unit identity checks, independent no-fit verification, corrected error sampling and the secondary grouped sampling-budget deviation. No outcome-driven model, feature, threshold or benchmark selection was introduced.

## Datasets, provenance and engineering

The source is the pinned 16,232,943-flow MMDS release, including 14capture-only flags,13,484,708 benign and 2,748,235 attack flows. It is not represented as the complete official CSE-CIC2018 corpus. Source upstream extraction revision and complete provenance remain unauthenticated.

External dataset shadman1028/cicids2017-official-flow-feature-csv-files/version 1 is an eight-file884,645,759-byte CICIDS2017 mirror with explicit UNB attribution. Capture dates are 3–7July2017. Mirror metadata declares CC BY 4.0 and noncommercial research use; this is not an independently authenticated official-byte or relicensing guarantee. Original attribution is preserved in docs/phase14_external_dataset_provenance.md.

The audit reconciles2,830,751 physical lines as 8 headers plus 2,830,743 eligible data records, with 2,273,097 benign and 557,646 attacks and no excluded data records. Fifteen traffic labels remain separate from the source family map. Three WebAttack labels contain literal UTF8 U+FFFD bytes already present in the mirror; no punctuation was guessed. Exact-observation duplicate excess is 308,381. Canonical 18-vector excess is 834,808with1,343conflicting-label groups; common 3excess is 1,540,628with4,150conflicting-label groups. These definitions are distinct. Private typed/canonical/feature-ready Parquet layers are version-pinned; raw records stay private.

Missing/nonfinite/negative numerical values follow the documented finite mask and train-only imputation. The mapped audit records 115 negative durations,2,867 infinite packet rates,1,358 NaN byte rates and 1,509 infinite byte rates. Full numeric-column diagnostics cover 78 features. Event timestamps are unavailable; capture dates come from filenames and cannot establish within-capture order.

## Feature compatibility and inference contract

Only duration(microseconds), forward packet count and backward packet count are conditionally harmonized, in that exact order. The label-free duration×rate/total-packets identity is within 1%of 1,000,000 for all 16,137,169 supported source and 2,827,761 external rows. This supports a unit convention, not exact extractor equivalence. Fifteen other feature semantics remain unverified. Original archived 18-feature external transfer E1 is unsupported and was not scored by invented zeros or guessed units.

E2 fits new source-only common 3 pipelines and freezes their preprocessing/calibration for target inference. They are not the original 18-feature archived pipelines. E3 fits separate target-only preprocessing/models. The saved artifact registry, ordered schema, original component hashes, missing-value handling and operating bins are described in docs/phase14_inference_contract.md. Six learned LR/RF pipelines and six controls total 12 saved pipelines; 150 component hashes and independent prediction/calibration reload evidence are preserved.

## External protocols, populations and leakage control

Primary external chronology trainsJuly3–5, validatesJuly6 and evaluatesJuly7. Common-vector earliest-role purging retains multiplicity in its earliest role. The primary chronological test contains 308,939 flows:179,664 benign and 129,275 attacks. Conservative source-exposure exclusion leaves 287,528. Secondary grouped primary/excluded denominators are 508,641/218,235. Every source/target comparison uses matched rows for its declared sensitivity. Cross-dataset canonical/common collisions are feature collisions, not authenticated duplicate network events.

Source common-model training has 169,599 rows; chronological target training172,913; grouped target 287,498. Source group sampling is 125/10000 and chronological target 1000/10000. Shared grouped role/sample hashing gives approximately1/7 of eligible grouped training keys rather than an independent 10%within-role sample. Actual budgets are independently documented; equal training effort is not claimed.

Models use frozen LR12 iterations/regParam.05 and RF12 trees/depth 5/minInstances 30/maxBins 24/seed 23013. Majority and training-duration controls remain separate. Operating bins maximize validation recall subject to benignFPR<=1%, with prespecified ties. Bin2048means never-positive. Fixed0.5results are separate. No target-test outcomes fit preprocessing or choose thresholds. AUC uses 2048whole-score bins:step PR and trapezoidal ROC, not exact continuous-score AUC. Undefined metrics remain null.

## External results and negative findings

| Pipeline | Operating rule | TP | FP | TN | FN | Recall | FPR | F1 | PR area | ROC area |
|---|---|---|---|---|---|---|---|---|---|---|
| E2-B-common-LR | validation_budget | 0 | 0 | 179664 | 129275 | 0 | 0 | 0 | 0.420307 | 0.534453 |
| E2-B-common-LR | fixed_half | 0 | 0 | 179664 | 129275 | 0 | 0 | 0 | 0.420307 | 0.534453 |
| E2-B-common-RF | validation_budget | 14459 | 7643 | 172021 | 114816 | 0.111847 | 0.0425405 | 0.191033 | 0.746094 | 0.823381 |
| E2-B-common-RF | fixed_half | 14491 | 10302 | 169362 | 114784 | 0.112094 | 0.0573404 | 0.188112 | 0.746094 | 0.823381 |
| E3-chronological-LR | validation_budget | 0 | 229 | 179435 | 129275 | 0 | 0.0012746 | 0 | 0.368629 | 0.460811 |
| E3-chronological-LR | fixed_half | 9 | 19950 | 159714 | 129266 | 6.9619e-05 | 0.111041 | 0.000120616 | 0.368629 | 0.460811 |
| E3-chronological-RF | validation_budget | 7028 | 70 | 179594 | 122247 | 0.0543647 | 0.000389616 | 0.10307 | 0.872554 | 0.875103 |
| E3-chronological-RF | fixed_half | 83969 | 3093 | 176571 | 45306 | 0.649538 | 0.0172155 | 0.77628 | 0.872554 | 0.875103 |


Source LR detects zero attacks on the primary chronological external population. Source RF's source-calibrated operating point recalls11.18%but incurs4.254%target benignFPR, exceeding its source-validation ceiling. Target RF improves PR ranking and fixed-half recall(64.95%)but has 1.722%FPR at 0.5; its validation-budget rule reduces recall to 5.44%with 0.039%FPR. Target LR remains weak. Target training therefore does not uniformly improve operational performance. These are historical conditional findings, not production robustness.

All 64evaluation records, original family/capture histograms, threshold comparisons, coverage, calibration and timing remain in the compact evidence and derived tables. Original external families are retained; absent-family metrics remain undefined. Source/external comparisons use independent same-E2-model source holdout diagnostics to avoid mistaking18-versus3-feature changes for pure domain effects. Conservative collision exclusions change denominators and are not silently combined with primary results. Distinct-group error explanations use bounded representative/enriched samples and suppress contribution/score values for strata smaller than5. Their log-odds attributions are descriptive, not causal.

## Volume and worker scalability

14Duses four genuinely nested fingerprint-hash populations, without replicated rows. Three workloads consume actual numeric columns:input checksum, class/day analytics and model preprocessing/vector aggregation. Three repetitions plus separate warmups run atlocal[4],16 partitions, AQEfalse, no explicit cache.48measured runs and 16 warmups pass exact integer and tolerance-based numerical equivalence. Actual medians are:

| Actual flows | Numeric checksum s | Analytics s | Feature transform s |
|---|---|---|---|
| 1000860 | 0.942887 | 0.741611 | 3.63679 |
| 3998178 | 1.48661 | 0.86291 | 8.7739 |
| 7998515 | 2.2437 | 1.14346 | 12.6707 |
| 16232943 | 3.93776 | 1.81335 | 21.0757 |


Worker sensitivity uses the same approximate1Mpopulation and newSparkContexts in a shared notebookJVM:

| Workload | Threads | Median s | Speedup T1/Tp | Efficiency |
|---|---|---|---|---|
| analytics | 4 | 0.741611 | 0.957028 | 0.239257 |
| feature_transform | 4 | 3.63679 | 1.00245 | 0.250613 |
| analytics | 1 | 0.709743 | 1 | 1 |
| feature_transform | 1 | 3.6457 | 1 | 1 |
| analytics | 2 | 0.458344 | 1.54849 | 0.774247 |
| feature_transform | 2 | 2.75461 | 1.32349 | 0.661745 |


Four workers are not consistently faster. Warm JVM, short actions, uncontrolled filesystem cache and shared hardware preclude a general linear-scaling or optimal-worker claim. local[1]/[2]/[4]are threads on one machine, not multi-node clusters. Full16,232,943 rows were measured in the primary matrix; bounded secondary comparisons do not replace that core requirement.

## Storage, partition and cache measurements

14Euses the accepted14D1,000,860-row population. Both matchedCSV andParquet preserve identical numerical values, labels, multiplicities and lossless hexadecimal fingerprints. Logical-row digests, numeric sums andquery outputs pass correctness parity. Conversion is separate from read/query timing. Count-only metadata optimization is explicitly labeled and never substituted for a forced numeric read.

| Format | Bytes | Conversion s | Full numeric read s | Projected query s |
|---|---|---|---|---|
| parquet | 116203334 | 6.57791 | 0.626799 | 0.398523 |
| csv | 217833168 | 3.33495 | 1.92177 | 1.2544 |


| Matrix | Configuration | Rows | Repetitions | Median s |
|---|---|---|---|---|
| partition_materialization | 4 | 1000860 | 3 | 3.01877 |
| partition_query_after_materialization | 4 | 1000860 | 3 | 0.406834 |
| partition_materialization | 16 | 1000860 | 3 | 2.66868 |
| partition_query_after_materialization | 16 | 1000860 | 3 | 0.328335 |
| partition_materialization | 48 | 1000860 | 3 | 2.88296 |
| partition_query_after_materialization | 48 | 1000860 | 3 | 0.408467 |
| cache | none | 1000860 | 3 | 0.428303 |
| cache | first_materialization_MEMORY_AND_DISK | 1000860 | 1 | 3.10564 |
| cache | warm_materialized | 1000860 | 3 | 0.291111 |
| archived_inference | logistic_regression | 1000860 | 3 | 1.90268 |
| archived_inference | random_forest | 1000860 | 3 | 2.22452 |
| pattern_mining | Phase10A3-frozen6-support.05-one_budgeted_fit | 100000 | 1 | 3.02524 |


Partition materialization costs are separated from subsequent queries; capture pruning and coalescing are retained. SQL and DataFrame consume identical filtered aggregation outputs. Cache first-materialization is one explicit action; uncached/warm queries have three retained repetitions. Cache amortization uses materialization/(uncached minus warm), defined only when warm queries are faster. The observed break-even is 23 queries under this measured boundary; it is not a deployment guarantee or eviction observation. OS cache was not flushed.

## Bounded Spark versus Pandas

Exactly matched projected CSV rows, dtypes, filters, grouping and numerically consumed results are compared at 100k/500k/1M. All three repetitions are retained for each engine and boundary:

| Matched flows | Timing boundary | Pandas median s | Spark median s | Spark/Pandas time |
|---|---|---|---|---|
| 100000 | input_loading | 0.0280377 | 0.215526 | 7.68701 |
| 100000 | end_to_end | 0.0320017 | 0.254853 | 7.96373 |
| 100000 | compute | 0.010115 | 0.118304 | 11.6959 |
| 500000 | input_loading | 0.114861 | 0.450503 | 3.92217 |
| 500000 | end_to_end | 0.118059 | 0.357022 | 3.0241 |
| 500000 | compute | 0.0187425 | 0.130041 | 6.93832 |
| 1000000 | input_loading | 0.235318 | 0.719309 | 3.05675 |
| 1000000 | end_to_end | 0.242245 | 0.616481 | 2.54486 |
| 1000000 | compute | 0.0292257 | 0.147055 | 5.0317 |


Input-loading includes parsing plus the same consumed numeric checksum. End-to-end includes parsing/filter/aggregation. Compute uses already loaded Pandas data and materialized Spark data. SparkContext startup is separately recorded; Python/Pandas import/setup is not an independently isolated engine-startup measurement. There is no full16MtoPandas conversion. These results compare a bounded workload on observed hardware; they cannot establish universalSpark superiority. Execution order, OS cache and startup differences remain visible limitations.

## Workload costs, resources and variability

Archived Phase4B18-feature LR/RF inference forces actual probability sums and positive decisions, with three repetitions. These are internal source benchmark models, not the unsupported external18-feature transfer. The bounded Phase10A3 FP-Growth cost uses at most100ktransactions and original 6 feature discretization/minSupport.05; one fit is explicitly budgeted cost evidence, not stable mining scalability. Source/target fitting costs come from completed14C; Phase6replay reuses49 microbatches and 15,322,987 flows rather than retiming completed work.

Kaggle observes fourCPUquota threads,8GiBdriver heap and 30GiBcontainer memory on virtualizedIntelXeon2.20GHz hardware. RSS is sampled every0.2 seconds, with Python, JVM and process-tree peaks separate; configured heap is not measuredRSS. CPU process-tree deltas are reported only when process membership is stable. Pandas actions share the resident Spark JVM; their process-tree RSS is an environment peak, not isolated Pandas memory or incremental engine allocation. Actual shuffle/spill/task imbalance/eviction metrics remain unavailable. Resource limits reserve3GiBscratch and stop subsequent heavy work above20GiBsampled treeRSS. Whole-stage receipts and raw repetitions record observed versions and resources. Local Python 3.12validation and KagglePython3.13execution are not claimed identical.

## Persistence, figures and laboratory

Versioned outputs and the experiment/model/dataset manifests preserve provenance and SHA256s. Independent14Vreconstructs stored calibration histograms and verifies same-model source holdout, training support, unit identities and imputed-vector collisions without refitting. Original local fresh-process reload receipts cover all 12 pipelines. Raw datasets, serialized weights and detailed private case records stay private.

There are 17publication figure families inPNG/SVG, covering all 24prespecified scientific topics through combined panels. Each has actual table provenance and SHA256. The isolated Phase14Streamlit laboratory provides20evidence sections, filters, denominators, undefined/empty states, confusion matrices, resource units andPNG/SVG/filteredCSVdownloads. It displays archived evidence; there is no deployment or livePhase15inference flow. Actual desktop/mobile and byte-identical filtered download checks are retained in reports/phase14_validation.

## Acceptance and limitations

The final suite preserves 161existing tests and adds 3benchmark-evidence acceptance tests. Final regression, independent arithmetic and benchmark acceptance, artifact hashes, figure provenance, preview/browser checks, manifest/report consistency and protected Git references must all pass before the experiment manifest is marked complete. The final receipt is reports/phase14_validation/acceptance.json.

Limitations include conditional extractor semantics, unverified upstream byte chain, historical testbed selection, coarse-vector purging, disclosed grouped training budgets, correlated flows, finite captures, approximate AUC, bounded/enriched explanations, shared warmed hardware, uncontrolledOS cache, sampled resource peaks, one mining fit and unisolated Python/Pandas import overhead. No causal, production, multi-node, billion-row or universal performance conclusion is made. Exact18-feature external transfer and optional novelty/hybrid/adaptive transfer remain unsupported/omitted under the frozen protocol.

## Research contribution and continuation boundary

The study combines auditable common-feature external validation with matched numerical workload benchmarks on actual full-volume source data. It separates model changes, calibration, feature compatibility and dataset selection from operational detection claims, and distinguishes volume/worker/storage/cache effects. Negative findings are retained alongside correctness evidence. Completion prepares review ofPhase15; noPhase15orPhase16implementation is included.
