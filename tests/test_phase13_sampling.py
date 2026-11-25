import unittest
from pyspark.sql import SparkSession
from src.explainability.sampling import sample_groups

class ExplanationSamplingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spark=SparkSession.builder.master('local[2]').appName('phase13-sample-test').config('spark.sql.shuffle.partitions','4').getOrCreate()

    @classmethod
    def tearDownClass(cls):cls.spark.stop()

    def test_duplicate_representatives_are_repartition_invariant(self):
        rows=[('g1','z','day2','Bot',1,'Bot'),('g1','a','day1','Benign',0,'Benign'),('g2','b','day1','Bot',1,'Bot')]
        frame=self.spark.createDataFrame(rows,'predictor_key STRING,record_fingerprint STRING,source_day STRING,original_label STRING,binary_label INT,attack_family STRING')
        result=sample_groups(frame,23013,2).collect()
        self.assertEqual(result,sample_groups(frame.repartition(4),23013,2).collect())
        group=next(row for row in result if row.predictor_key=='g1')
        self.assertEqual(group.record_fingerprint,'a');self.assertEqual(group.multiplicity,2)
        with self.assertRaises(ValueError):sample_groups(frame,23013,0)
