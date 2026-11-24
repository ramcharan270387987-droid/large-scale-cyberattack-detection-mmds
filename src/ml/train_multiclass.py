"""Resource-bounded Phase 9 attack-family training and frozen evaluation."""
import json
from time import monotonic
from pathlib import Path
from pyspark import StorageLevel
from pyspark.ml import PipelineModel
from pyspark.ml.classification import LogisticRegression, RandomForestClassifier
from pyspark.ml.clustering import KMeans
from pyspark.ml.functions import vector_to_array
from pyspark.sql import functions as F
from src.ingest.dataset_audit import spark_session, atomic_json
from src.ml.train_supervised import verified_input
from src.ml.feature_registry import predictor_input, registry
from src.ml.phase8_baselines import json_file, retain
from src.ml.split_protocols import assign_population, group_sample
from src.ml.preprocessing import fit_preprocessing
from src.ml.phase9_label_registry import vocabulary
from src.ml.phase9_evaluation import multiclass
from src.ml.model_registry import capture
from src.ml.open_set_rejection import cutoff
from src.ml.novelty_scoring import squared_distance
from src.ml.novelty_normalization import reference_grid, percentile_column
from src.streaming.model_scoring import probe
from src.sql.traffic_analytics import locate_producer, write_rows


def earlier_c_attacks(attacks, config):
    """Keep the retained test cohort and split only earlier eligible training groups."""
    cutoff_day = min(config['protocols']['C']['test'])
    prior = attacks.where((F.col('split_rank') == 0) & (F.col('source_day') < cutoff_day)
                          & (F.col('attack_family') != 'Web attack'))
    prior_groups = F.pmod(F.xxhash64(F.lit(config['seed']), F.lit('phase9-C-calibration'),
                                   F.col('predictor_key')), F.lit(10000))
    prior = prior.withColumn('split_rank', F.when(prior_groups < 8500, 0).otherwise(1))
    return prior.unionByName(attacks.where('split_rank == 2'))


def run(project, input_root, output, scenario='A', hierarchy=None):
    output.mkdir(parents=True, exist_ok=True)
    config = json_file(project,'configs/ml_experiments.yaml')
    spark = spark_session(config,Path('/kaggle/temp/phase9/spark'))
    spark.conf.set('spark.sql.sources.partitionColumnTypeInference.enabled','false')
    start = monotonic()
    try:
        upstream = json_file(project,'manifests/parquet_layers.json')
        frame, receipt = verified_input(spark,locate_producer(input_root,upstream['independent_mount']['summary_sha256']),upstream,json_file(project,'configs/cleaning.yaml'))
        names = registry(config,upstream['feature_columns'])
        prepared = predictor_input(frame,names,config['version'])
        holdouts = {'Web':'Web attack','Bot':'Bot','Infiltration':'Infiltration','DDoS':'DDoS'}
        withheld = holdouts.get(scenario)
        assigned = assign_population(prepared,'A' if withheld else scenario,config,receipt['days'])
        if withheld:
            excluded = assigned.where(F.col('attack_family') == withheld).select('predictor_key').distinct()
            known = assigned.where(F.col('attack_family') != withheld).join(excluded,'predictor_key','left_anti')
            unknown = assigned.where(F.col('attack_family') == withheld).withColumn('split_rank',F.lit(2))
            assigned = known.unionByName(unknown)
        active, overlap = retain(assigned)
        attacks = active.where('binary_label = 1')
        if scenario == 'C':
            if hierarchy is None:
                raise ValueError("C is reserved for the earlier-only hierarchical experiment")
            attacks = earlier_c_attacks(attacks, config)
        attacks = attacks.persist(StorageLevel.DISK_ONLY)
        training = attacks.where('split_rank = 0')
        support = {r['attack_family']:r['count'] for r in training.groupBy('attack_family').count().collect()}
        classes = vocabulary(support)
        mapping = F.create_map(*[v for k,i in classes.items() for v in (F.lit(k),F.lit(i))])
        attacks = attacks.withColumn('label',mapping[F.col('attack_family')].cast('double'))
        sample = group_sample(attacks.where('split_rank = 0'),config).where('sampled').persist(StorageLevel.DISK_ONLY)
        sample_support = {r['attack_family']:r['count'] for r in sample.groupBy('attack_family').count().collect()}
        if set(sample_support) != set(classes): raise ValueError('Training sample lacks a supported family')
        _, prep, preprocessing = fit_preprocessing(sample,names)
        train = prep.transform(sample).persist(StorageLevel.DISK_ONLY)
        validation = attacks.where('split_rank = 1 AND label IS NOT NULL')
        test = attacks.where('split_rank = 2 AND label IS NOT NULL')
        tables = []
        candidates = []
        for algorithm in ('lr','rf'):
            for weighting in ('unweighted','inverse','capped_10'):
                weights = {family:(1.0 if weighting=='unweighted' else min(10.0,len(support) and sum(support.values())/(len(support)*n)) if weighting=='capped_10' else sum(support.values())/(len(support)*n)) for family,n in support.items()}
                weight_map = F.create_map(*[v for family,w in weights.items() for v in (F.lit(family),F.lit(w))])
                weighted = train.withColumn('class_weight',weight_map[F.col('attack_family')])
                estimator = (LogisticRegression(family='multinomial',featuresCol='scaled_features',maxIter=12,regParam=.05,standardization=False,weightCol='class_weight') if algorithm=='lr' else RandomForestClassifier(featuresCol='features',numTrees=12,maxDepth=5,maxBins=24,minInstancesPerNode=30,maxMemoryInMB=192,seed=23013,weightCol='class_weight'))
                tick = monotonic()
                fitted = estimator.fit(weighted)
                model = PipelineModel(stages=[*prep.stages,fitted])
                elapsed = monotonic()-tick
                counts = {(int(r['label']),int(r['prediction'])):r['count'] for r in model.transform(validation).groupBy('label','prediction').count().collect()}
                metrics, _ = multiclass(counts,range(len(classes)))
                name = algorithm+'_'+weighting
                tables.append({'model':name,'partition':'validation','fit_seconds':elapsed,**metrics})
                candidates.append((metrics['macro_f1'],metrics['balanced_accuracy'],-elapsed,name,model))
                print('PHASE9 fitted',scenario,name,flush=True)
        selected = max(candidates,key=lambda x:x[:3])
        atomic_json(output/'phase9_frozen.json',{'model':selected[3],'classes':classes,'selection':'validation macro F1','features':names,'preprocessing':preprocessing})
        print('PHASE9 frozen',scenario,selected[3],flush=True)
        model = selected[4]
        cluster = KMeans(k=12,seed=23013,maxIter=12,featuresCol='features',predictionCol='cluster').fit(train)
        reference = squared_distance(cluster,train).select(F.col('score').alias('distance'))
        grid = reference_grid(reference)
        # High values consistently indicate uncertainty. Whole-bin ties remain accepted.
        def rejection_scores(data):
            scored = model.transform(data).withColumn('scores',vector_to_array('probability'))
            ordered = F.reverse(F.array_sort('scores'))
            entropy = -F.aggregate(F.col('scores'),F.lit(0.0),lambda acc,x: acc+F.when(x>0,x*F.log(x)).otherwise(0.0))/F.log(F.lit(float(len(classes))))
            scored = squared_distance(cluster,scored).withColumn('novelty',percentile_column(F.col('score'),grid))
            return scored.withColumn('maximum',1-ordered[0]).withColumn('margin',1-(ordered[0]-ordered[1])).withColumn('entropy',entropy).withColumn('combined',F.greatest(F.col('novelty'),1-ordered[0]))
        rejection = []
        validation_scores = rejection_scores(validation).persist(StorageLevel.DISK_ONLY)
        thresholds = {}
        for method in ('maximum','margin','entropy','novelty','combined'):
            histogram = {r['bin']:r['count'] for r in validation_scores.withColumn('bin',F.floor(F.col(method)*2048)).groupBy('bin').count().collect()}
            thresholds[method] = {str(b):cutoff(histogram,b) for b in (.01,.05,.1)}
        atomic_json(output/'phase9_rejection_frozen.json',thresholds)
        print('PHASE9 rejection frozen',scenario,flush=True)
        all_test = rejection_scores(attacks.where('split_rank = 2')).persist(StorageLevel.DISK_ONLY)
        for method, rules in thresholds.items():
            for budget, threshold in rules.items():
                aggregate = all_test.withColumn('rejected',F.floor(F.col(method)*2048)>threshold).withColumn('known',F.col('label').isNotNull()).withColumn('correct',F.col('label')==F.col('prediction')).groupBy('known','rejected','correct').count().collect()
                known_total = sum(r['count'] for r in aggregate if r['known'])
                unknown_total = sum(r['count'] for r in aggregate if not r['known'])
                rejected_known = sum(r['count'] for r in aggregate if r['known'] and r['rejected'])
                rejected_unknown = sum(r['count'] for r in aggregate if not r['known'] and r['rejected'])
                accepted = sum(r['count'] for r in aggregate if not r['rejected'])
                correct = sum(r['count'] for r in aggregate if r['known'] and not r['rejected'] and r['correct'])
                rejection.append({'method':method,'budget':budget,'threshold_bin':threshold,'known_support':known_total,'unknown_support':unknown_total,'known_false_rejection':rejected_known/known_total if known_total else None,'unknown_rejection_recall':rejected_unknown/unknown_total if unknown_total else None,'coverage':accepted/(known_total+unknown_total),'accepted_correct_family_rate':correct/accepted if accepted else None})
        write_rows(output/'phase9_open_set_metrics.csv',rejection)
        counts = {(int(r['label']),int(r['prediction'])):r['count'] for r in model.transform(test).groupBy('label','prediction').count().collect()}
        metrics, families = multiclass(counts,range(len(classes)))
        tables.append({'model':selected[3],'partition':'test',**metrics})
        keys = dict.fromkeys(k for row in tables for k in row)
        write_rows(output/'phase9_closed_set_metrics.csv',[{k:row.get(k) for k in keys} for row in tables])
        if counts:
            write_rows(output/'phase9_family_confusion.csv',[{'actual':a,'predicted':b,'count':n} for (a,b),n in sorted(counts.items())])
        write_rows(output/'phase9_per_family.csv',families)
        saved = capture(model,selected[3],output,probe(spark,names))
        atomic_json(output/'phase9_summary.json',{'status':'validated','scenario':scenario,'input':receipt,'classes':classes,'training_support':support,'sample_support':sample_support,'overlap':overlap,'model':selected[3],'registry':saved,'seconds':monotonic()-start,'test':metrics})
        print('PHASE9 complete',scenario,flush=True)
        if hierarchy is not None:
            saved_novelty = capture(PipelineModel(stages=[*prep.stages, cluster]), 'family_kmeans', output,
                                    probe(spark,names), kmeans=True)
            atomic_json(output/'phase9_novelty_registry.json',
                        {'registry': saved_novelty, 'reference_grid': grid, 'features': names,
                         'classes': classes, 'thresholds': thresholds, 'spark_version': spark.version})
            hierarchy(spark, active, names, config, receipt, model, classes, thresholds)
    finally:
        spark.stop()
