"""Spark FP-Growth with deterministic bounded summaries."""
from time import monotonic
from pyspark.ml.fpm import FPGrowth, FPGrowthModel
from pyspark.sql import functions as F


def mine(transactions, support, confidence=.7, partitions=48):
    start=monotonic()
    model=FPGrowth(itemsCol='items',minSupport=support,minConfidence=confidence,numPartitions=partitions).fit(transactions)
    itemsets=model.freqItemsets.withColumn('items',F.sort_array('items'))
    summary={r.length:r['count'] for r in itemsets.groupBy(F.size('items').alias('length')).count().collect()}
    return model,{'seconds':monotonic()-start,'itemsets':sum(summary.values()),'lengths':summary}


def export(model, total, limit=500):
    return [dict(items=r.items,count=r.freq,support=r.freq/total) for r in model.freqItemsets.withColumn(
        'items',F.sort_array('items')).orderBy(F.desc('freq'),'items').limit(limit).collect()]


def reload_parity(model, destination, probes):
    model.write().save(str(destination))
    loaded=FPGrowthModel.load(str(destination))
    before=model.transform(probes).select('items','prediction').collect()
    after=loaded.transform(probes).select('items','prediction').collect()
    if before!=after:
        raise ValueError('Reloaded FP-Growth predictions differ')
    return len(before)
