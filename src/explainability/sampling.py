"""Stable representative selection for bounded predictor-group explanations."""
from pyspark.sql import Window,functions as F


def sample_groups(frame, seed, limit):
    if limit<=0:
        raise ValueError('Explanation sample limit must be positive')
    ordering=['record_fingerprint','source_day','original_label','binary_label','attack_family']
    grouped=Window.partitionBy('predictor_key')
    representatives=(frame.withColumn('multiplicity',F.count('*').over(grouped))
                     .withColumn('_explanation_rank',F.row_number().over(grouped.orderBy(*ordering)))
                     .where('_explanation_rank = 1').drop('_explanation_rank'))
    return representatives.orderBy(F.xxhash64(F.lit(seed),'predictor_key'),*ordering).limit(limit)
