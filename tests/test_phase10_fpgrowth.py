import tempfile
import unittest
from pathlib import Path
from pyspark.sql import SparkSession
from src.patterns.frequent_itemsets import mine,export,reload_parity


class FPGrowthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spark=SparkSession.builder.master('local[2]').appName('pattern-fpgrowth-test').config('spark.sql.shuffle.partitions','4').getOrCreate()

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def test_exact_itemsets_rules_and_reload(self):
        frame=self.spark.createDataFrame([(['a','b'],),(['a','b'],),(['a'],),(['b','c'],)],'items ARRAY<STRING>')
        model,summary=mine(frame,.5,.5,2)
        self.assertEqual(summary['itemsets'],3)
        counts={tuple(r['items']):r['count'] for r in export(model,4)}
        self.assertEqual(counts,{('a',):3,('b',):3,('a','b'):2})
        rules=model.associationRules.collect()
        self.assertEqual(len(rules),2)
        self.assertTrue(all(abs(r.confidence-2/3)<1e-12 and abs(r.lift-8/9)<1e-12 for r in rules))
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(reload_parity(model,Path(directory)/'model',frame),4)
