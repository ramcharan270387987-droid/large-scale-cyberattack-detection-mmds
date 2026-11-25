"""Check exact explanations against real Spark pipeline outputs on synthetic data."""
import unittest
from pyspark.sql import SparkSession
from pyspark.ml import Pipeline
from pyspark.ml.feature import Imputer,VectorAssembler,StandardScaler
from pyspark.ml.classification import LogisticRegression
from pyspark.ml.functions import vector_to_array
from src.explainability.exact import linear,verify_linear

class SparkExplanationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spark=SparkSession.builder.master('local[2]').appName('phase13-synthetic-parity').config('spark.sql.shuffle.partitions','4').getOrCreate()

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def test_training_imputation_scaling_and_probability_parity(self):
        train=self.spark.createDataFrame([(-3.,1.,0.),(-2.,2.,0.),(-1.,3.,0.),(1.,4.,1.),(2.,5.,1.),(3.,6.,1.)],'x DOUBLE,y DOUBLE,label DOUBLE')
        pipeline=Pipeline(stages=[Imputer(inputCols=['x','y'],outputCols=['xi','yi']),VectorAssembler(inputCols=['xi','yi'],outputCol='features'),StandardScaler(inputCol='features',outputCol='scaled'),LogisticRegression(featuresCol='scaled',maxIter=5,regParam=.1)]).fit(train)
        model=pipeline.stages[-1]
        probes=self.spark.createDataFrame([(None,2.),(-100.,3.),(100.,4.)],'x DOUBLE,y DOUBLE')
        rows=pipeline.transform(probes).select(vector_to_array('scaled').alias('x'),vector_to_array('rawPrediction').alias('raw'),vector_to_array('probability').alias('p')).collect()
        for row in rows:verify_linear(linear(list(model.coefficients),model.intercept,row.x),row.raw[1],row.p[1])
        self.assertEqual(pipeline.stages[1].getInputCols(),['xi','yi'])
