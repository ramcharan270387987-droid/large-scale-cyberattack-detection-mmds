"""Synthetic checks for the exact version 1 discretization implementation."""
import unittest
from pyspark.sql import SparkSession
from src.patterns.discretization import fit, transform
from src.ml.feature_registry import finite, registry


class Phase10DiscretizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spark = SparkSession.builder.master('local[2]').appName('phase10-tests').config('spark.sql.shuffle.partitions','4').getOrCreate()

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def test_reference_fit_and_frozen_outside_values(self):
        reference = self.spark.createDataFrame([(float(i),) for i in range(9)], 'x DOUBLE')
        cuts = fit(reference, ['x'], 3)
        self.assertEqual(cuts, {'x': [2.0, 5.0]})
        later = self.spark.createDataFrame([(-100.0,), (2.0,), (5.0,), (100.0,), (None,)], 'x DOUBLE')
        expected = [['x=BIN_0'], ['x=BIN_0'], ['x=BIN_1'], ['x=BIN_2'], ['x=MISSING']]
        self.assertEqual([r.items for r in transform(later,cuts).collect()], expected)
        self.assertEqual(cuts, {'x': [2.0,5.0]})
        self.assertEqual(transform(later,cuts).count(),later.count())

    def test_zero_constant_missing_invalid_and_unique(self):
        raw = self.spark.createDataFrame([(0.0,7.0)]*20+[(1.0,7.0),(None,None),(float('nan'),float('inf'))], 'x DOUBLE, y DOUBLE')
        frame = raw.select(finite('x').alias('x'),finite('y').alias('y'))
        cuts = fit(frame,['x','y'],5)
        self.assertEqual(cuts, {'x':[0.0],'y':[7.0]})
        first = [r.items for r in transform(frame,cuts).collect()]
        self.assertEqual(first, [r.items for r in transform(frame,cuts).collect()])
        self.assertTrue(all(len(items)==len(set(items))==2 for items in first))
        self.assertEqual(first[-1],['x=MISSING','y=MISSING'])
        self.assertEqual(first[-2],['x=MISSING','y=MISSING'])
        self.assertTrue(all(sum(item.startswith(name+'=') for item in items)==1 for name in ('x','y') for items in first))

    def test_prohibited_registry(self):
        for name in ('source_day','attack_family','binary_label','predictor_key'):
            with self.assertRaises(ValueError): registry({'numerical_features':[name]},[name])
