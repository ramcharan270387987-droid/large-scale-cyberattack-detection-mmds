"""Write final scientific findings from measured, hash-registered evidence."""
import json,csv,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(stage,name):return json.loads((ROOT/'reports'/('phase14_'+stage)/(name+'.json')).read_text())
def read(name):return list(csv.DictReader((ROOT/'reports'/('phase14_'+name+'.csv')).open()))
def table(headers,rows):return '| '+' | '.join(headers)+' |\n|'+'|'.join('---' for _ in headers)+'|\n'+'\n'.join('| '+' | '.join(str(x) for x in row)+' |' for row in rows)+'\n'
def f(value):return 'undefined' if value is None or value=='' else f'{float(value):.6g}'
def main():
    external=load('14C','external_evaluation');models=load('14C','models');opt=read('optimization_summary');pandas=read('pandas_comparison');volume=read('scalability_summary');workers=read('worker_scaling');storage=read('storage_comparison');cache=read('cache_break_even');figs=json.loads((ROOT/'manifests/phase14_figures.json').read_text());audit=load('14B','external_audit');matrix=read('resource_usage')
    selected=[r for r in external if r['evaluation_protocol']=='chronological' and r['sensitivity']=='primary' and r['model'].endswith(('-LR','-RF'))]
    metrics=table(['Pipeline','Operating rule','TP','FP','TN','FN','Recall','FPR','F1','PR area','ROC area'],[[r['model'],r['operating'],*[r['metrics'][k] for k in ('tp','fp','tn','fn')],*[f(r['metrics'][k]) for k in ('recall','fpr','f1','pr_auc','roc_auc')]] for r in selected])
    volumes=table(['Actual flows','Numeric checksum s','Analytics s','Feature transform s'],[[r['actual_rows'],*[f(next(x['median_seconds'] for x in volume if x['actual_rows']==r['actual_rows'] and x['workload']==w)) for w in ('ingest_checksum','analytics','feature_transform')]] for r in volume if r['workload']=='analytics'])
    work=table(['Workload','Threads','Median s','Speedup T1/Tp','Efficiency'],[[r['workload'],r['workers'],f(r['median_seconds']),f(r['speedup']),f(r['efficiency'])] for r in workers])
    pdrows=[]
    for rows in (100000,500000,1000000):
        for mode in ('input_loading','end_to_end','compute'):
            items=[r for r in pandas if r['matrix']=='Spark_Pandas_'+mode and int(r['actual_rows'])==rows];spark=next(r for r in items if r['configuration'].startswith('spark-'));pd=next(r for r in items if r['configuration'].startswith('pandas-'));pdrows.append([rows,mode,f(pd['median_seconds']),f(spark['median_seconds']),f(float(spark['median_seconds'])/float(pd['median_seconds']))])
    pdtable=table(['Matched flows','Timing boundary','Pandas median s','Spark median s','Spark/Pandas time'],pdrows)
    st=table(['Format','Bytes','Conversion s','Full numeric read s','Projected query s'],[[r['format'],r['bytes'],f(r['conversion_seconds']),f(r['read_checksum_seconds']),f(r['query_seconds'])] for r in storage])
    oth=table(['Matrix','Configuration','Rows','Repetitions','Median s'],[[r['matrix'],r['configuration'],r['actual_rows'],r['repetitions'],f(r['median_seconds'])] for r in opt if r['matrix'] in ('archived_inference','pattern_mining','cache','partition_materialization','partition_query_after_materialization')])
    text=f'''# Phase 14 — External validation and computational scalability

## Outcome and reproducibility

This study completes the prespecified external validation and bounded single-machine scalability investigation. It starts from74e909ac3771dcaf5730437d3567f24c4fa4913b and reuses finalized Phase13 atab6e9401b0c9b92e624e5b2b16ec91050a081eb0. Recovered14Dversion1 was accepted without repeating any measured experiment. Stage14Eversion1 supplies the remaining actual optimization/Pandas/inference/mining evidence. The experiment manifest and final independent acceptance receipt are authoritative;source versions,logs,component hashes and raw repetitions are retained. The final remote commit is independently checked after pushing,avoiding a self-referential SHA in this report.

## Research questions and study design

RQ14.1–3 address conditional cross-dataset transfer,target baselines and feature mismatch. RQ14.4–7 cover data volume,worker threads,storage formats,partitions/cache. RQ14.8–10 address bounded Pandas comparison,workload costs and limits of the observed infrastructure. The frozen protocol is docs/phase14_research_protocol.md,prespecified ate0347bc57d650acaec2de83bdee2ad7ca5e8c23a. Documented amendments retain failed attempts,raw label bytes,unit identity checks,independent no-fit verification,corrected error sampling and the secondary grouped sampling-budget deviation. No outcome-driven model,feature,threshold or benchmark selection was introduced.

## Datasets,provenance and engineering

The source is the pinned16,232,943-flow MMDS release,including14capture-only flags,13,484,708benign and2,748,235attack flows. It is not represented as the complete officialCSE-CIC2018corpus. Source upstream extraction revision and complete provenance remain unauthenticated.

External dataset shadman1028/cicids2017-official-flow-feature-csv-files/version1 is an eight-file884,645,759-byte CICIDS2017mirror with explicit UNB attribution. Capture dates are3–7July2017. Mirror metadata declaresCCBY4.0 and noncommercial research use;this is not an independently authenticated official-byte or relicensing guarantee. Original attribution is preserved in docs/phase14_external_dataset_provenance.md.

The audit reconciles2,830,751physical lines as8headers plus2,830,743eligible data records,with2,273,097benign and557,646attacks and no excluded data records. Fifteen traffic labels remain separate from the source family map. Three WebAttack labels contain literalUTF8 U+FFFDbytes already present in the mirror;no punctuation was guessed. Exact-observation duplicate excess is308,381. Canonical18-vector excess is834,808with1,343conflicting-label groups;common3excess is1,540,628with4,150conflicting-label groups. These definitions are distinct. Private typed/canonical/feature-ready Parquet layers are version-pinned;raw records stay private.

Missing/nonfinite/negative numerical values follow the documented finite mask and train-only imputation. The mapped audit records115negative durations,2,867infinite packet rates,1,358NaN byte rates and1,509infinite byte rates. Full numeric-column diagnostics cover78features. Event timestamps are unavailable;capture dates come from filenames and cannot establish within-capture order.

## Feature compatibility and inference contract

Only duration(microseconds),forward packet count and backward packet count are conditionally harmonized,in that exact order. The label-free duration×rate/total-packets identity is within1%of1,000,000for all16,137,169supported source and2,827,761external rows. This supports a unit convention,not exact extractor equivalence. Fifteen other feature semantics remain unverified. Original archived18-feature external transfer E1 is unsupported and was not scored by invented zeros or guessed units.

E2 fits new source-only common3pipelines and freezes their preprocessing/calibration for target inference. They are not the original18-feature archived pipelines. E3 fits separate target-only preprocessing/models. The saved artifact registry,ordered schema,original component hashes,missing-value handling and operating bins are described in docs/phase14_inference_contract.md. Six learned LR/RF pipelines and six controls total12saved pipelines;150component hashes and independent prediction/calibration reload evidence are preserved.

## External protocols,populations and leakage control

Primary external chronology trainsJuly3–5,validatesJuly6 and evaluatesJuly7. Common-vector earliest-role purging retains multiplicity in its earliest role. The primary chronological test contains308,939flows:179,664benign and129,275attacks. Conservative source-exposure exclusion leaves287,528. Secondary grouped primary/excluded denominators are508,641/218,235. Every source/target comparison uses matched rows for its declared sensitivity. Cross-dataset canonical/common collisions are feature collisions,not authenticated duplicate network events.

Source common-model training has169,599rows;chronological target training172,913;grouped target287,498. Source group sampling is125/10000 and chronological target1000/10000. Shared grouped role/sample hashing gives approximately1/7of eligible grouped training keys rather than an independent10%within-role sample. Actual budgets are independently documented;equal training effort is not claimed.

Models use frozen LR12iterations/regParam.05 and RF12trees/depth5/minInstances30/maxBins24/seed23013. Majority and training-duration controls remain separate. Operating bins maximize validation recall subject to benignFPR<=1%,with prespecified ties. Bin2048means never-positive. Fixed0.5results are separate. No target-test outcomes fit preprocessing or choose thresholds. AUC uses2048whole-score bins:step PR and trapezoidal ROC,not exact continuous-score AUC. Undefined metrics remain null.

## External results and negative findings

{metrics}

Source LR detects zero attacks on the primary chronological external population. Source RF's source-calibrated operating point recalls11.18%but incurs4.254%target benignFPR,exceeding its source-validation ceiling. Target RF improves PR ranking and fixed-half recall(64.95%)but has1.722%FPR at0.5;its validation-budget rule reduces recall to5.44%with0.039%FPR. Target LR remains weak. Target training therefore does not uniformly improve operational performance. These are historical conditional findings,not production robustness.

All64evaluation records,original family/capture histograms,threshold comparisons,coverage,calibration and timing remain in the compact evidence and derived tables. Original external families are retained;absent-family metrics remain undefined. Source/external comparisons use independent same-E2-model source holdout diagnostics to avoid mistaking18-versus3-feature changes for pure domain effects. Conservative collision exclusions change denominators and are not silently combined with primary results. Distinct-group error explanations use bounded representative/enriched samples and suppress contribution/score values for strata smaller than5. Their log-odds attributions are descriptive,not causal.

## Volume and worker scalability

14Duses four genuinely nested fingerprint-hash populations,without replicated rows. Three workloads consume actual numeric columns:input checksum,class/day analytics and model preprocessing/vector aggregation. Three repetitions plus separate warmups run atlocal[4],16partitions,AQEfalse,no explicit cache.48measured runs and16warmups pass exact integer and tolerance-based numerical equivalence. Actual medians are:

{volumes}

Worker sensitivity uses the same approximate1Mpopulation and newSparkContexts in a shared notebookJVM:

{work}

Four workers are not consistently faster. Warm JVM,short actions,uncontrolled filesystem cache and shared hardware preclude a general linear-scaling or optimal-worker claim. local[1]/[2]/[4]are threads on one machine,not multi-node clusters. Full16,232,943rows were measured in the primary matrix;bounded secondary comparisons do not replace that core requirement.

## Storage,partition and cache measurements

14Euses the accepted14D1,000,860-row population. Both matchedCSV andParquet preserve identical numerical values,labels,multiplicities and lossless hexadecimal fingerprints. Logical-row digests,numeric sums andquery outputs pass correctness parity. Conversion is separate from read/query timing. Count-only metadata optimization is explicitly labeled and never substituted for a forced numeric read.

{st}

{oth}

Partition materialization costs are separated from subsequent queries;capture pruning and coalescing are retained. SQL and DataFrame consume identical filtered aggregation outputs. Cache first-materialization is one explicit action;uncached/warm queries have three retained repetitions. Cache amortization uses materialization/(uncached minus warm),defined only when warm queries are faster. The observed break-even is {cache[0]['break_even_queries'] or 'undefined'} queries under this measured boundary;it is not a deployment guarantee or eviction observation. OS cache was not flushed.

## Bounded Spark versus Pandas

Exactly matched projected CSV rows,dtypes,filters,grouping and numerically consumed results are compared at100k/500k/1M. All three repetitions are retained for each engine and boundary:

{pdtable}

Input-loading includes parsing plus the same consumed numeric checksum. End-to-end includes parsing/filter/aggregation. Compute uses already loaded Pandas data and materialized Spark data. SparkContext startup is separately recorded;Python/Pandas import/setup is not an independently isolated engine-startup measurement. There is no full16MtoPandas conversion. These results compare a bounded workload on observed hardware;they cannot establish universalSpark superiority. Execution order,OS cache and startup differences remain visible limitations.

## Workload costs,resources and variability

Archived Phase4B18-feature LR/RF inference forces actual probability sums and positive decisions,with three repetitions. These are internal source benchmark models,not the unsupported external18-feature transfer. The bounded Phase10A3 FP-Growth cost uses at most100ktransactions and original6feature discretization/minSupport.05;one fit is explicitly budgeted cost evidence,not stable mining scalability. Source/target fitting costs come from completed14C;Phase6replay reuses49microbatches and15,322,987flows rather than retiming completed work.

Kaggle observes fourCPUquota threads,8GiBdriver heap and30GiBcontainer memory on virtualizedIntelXeon2.20GHz hardware. RSS is sampled every0.2seconds,with Python,JVM and process-tree peaks separate;configured heap is not measuredRSS. CPU process-tree deltas are reported only when process membership is stable. Actual shuffle/spill/task imbalance/eviction metrics remain unavailable. Resource limits reserve3GiBscratch and stop subsequent heavy work above20GiBsampled treeRSS. Whole-stage receipts and raw repetitions record observed versions and resources. Local Python3.12validation and KagglePython3.13execution are not claimed identical.

## Persistence,figures and laboratory

Versioned outputs and the experiment/model/dataset manifests preserve provenance and SHA256s. Independent14Vreconstructs stored calibration histograms and verifies same-model source holdout,training support,unit identities and imputed-vector collisions without refitting. Original local fresh-process reload receipts cover all12pipelines. Raw datasets,serialized weights and detailed private case records stay private.

There are{figs['unique_figures']}publication figure families inPNG/SVG,covering all24prespecified scientific topics through combined panels. Each has actual table provenance and SHA256. The isolated Phase14Streamlit laboratory provides20evidence sections,filters,denominators,undefined/empty states,confusion matrices,resource units andPNG/SVG/filteredCSVdownloads. It displays archived evidence;there is no deployment or livePhase15inference flow. Actual desktop/mobile and byte-identical filtered download checks are retained in reports/phase14_validation.

## Acceptance and limitations

The final suite preserves161existing tests and adds3benchmark-evidence acceptance tests. Final regression,independent arithmetic and benchmark acceptance,artifact hashes,figure provenance,preview/browser checks,manifest/report consistency and protected Git references must all pass before the experiment manifest is marked complete. The final receipt is reports/phase14_validation/acceptance.json.

Limitations include conditional extractor semantics,unverified upstream byte chain,historical testbed selection,coarse-vector purging,disclosed grouped training budgets,correlated flows,finite captures,approximate AUC,bounded/enriched explanations,shared warmed hardware,uncontrolledOS cache,sampled resource peaks,one mining fit and unisolated Python/Pandas import overhead. No causal,production,multi-node,billion-row or universal performance conclusion is made. Exact18-feature external transfer and optional novelty/hybrid/adaptive transfer remain unsupported/omitted under the frozen protocol.

## Research contribution and continuation boundary

The study combines auditable common-feature external validation with matched numerical workload benchmarks on actual full-volume source data. It separates model changes,calibration,feature compatibility and dataset selection from operational detection claims,and distinguishes volume/worker/storage/cache effects. Negative findings are retained alongside correctness evidence. Completion prepares review ofPhase15;noPhase15orPhase16implementation is included.
'''
    import re
    text=re.sub(r'\b(Phase)(1[0-6])\b',r'\1 \2',text)
    text=re.sub(r'\b(All|all|Only|only|uses|has|total|There are|at|to|from|and|plus|of|with|contains|preserves|adds)(?=\d)',r'\1 ',text)
    (ROOT/'reports/phase14_research_report.md').write_text(text);print('Wrote scientific report')
if __name__=='__main__':main()
