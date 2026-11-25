"""Bounded actual Spark checks for new scoring and benchmark materialization paths."""
import unittest,tempfile
from pathlib import Path
from pyspark.sql import SparkSession,functions as F
from pyspark.ml.functions import vector_to_array
from src.ml.preprocessing import fit_preprocessing
from src.external_validation.transfer_evaluation import control_pipeline,histogram
from src.scalability.benchmark_runner import workload
class Phase14SparkContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spark=SparkSession.builder.master('local[2]').appName('phase14-contracts').config('spark.sql.shuffle.partitions','4').getOrCreate()
        cls.names=['flow_duration','tot_fwd_pkts','tot_bwd_pkts']
        cls.train=cls.spark.createDataFrame([(1.,2.,1.,0),(2.,3.,1.,0),(10.,4.,2.,0),(20.,5.,3.,0),(30.,6.,4.,0)],'flow_duration DOUBLE,tot_fwd_pkts DOUBLE,tot_bwd_pkts DOUBLE,split_rank INT')
        cls.tree,cls.lr,cls.meta=fit_preprocessing(cls.train,cls.names)
    @classmethod
    def tearDownClass(cls):cls.spark.stop()
    def probes(self):
        return self.spark.createDataFrame([(None,2.,1.,0),(1.,3.,1.,0),(100.,4.,2.,1),(1000.,5.,3.,1)],'flow_duration DOUBLE,tot_fwd_pkts DOUBLE,tot_bwd_pkts DOUBLE,binary_label INT').withColumn('source_day',F.lit('2017-07-07')).withColumn('attack_family',F.when(F.col('binary_label')==0,'BENIGN').otherwise('NEW_ATTACK'))
    def test_controls_keep_training_only_imputation_and_scale(self):
        majority=control_pipeline(self.train,self.tree,'majority');duration=control_pipeline(self.train,self.tree,'duration')
        self.assertEqual([r[0][1] for r in majority.transform(self.probes()).select(vector_to_array('probability')).collect()],[0.,0.,0.,0.])
        p=[r[0][1] for r in duration.transform(self.probes()).select(vector_to_array('probability')).collect()]
        self.assertEqual(p[-2:],[1.,1.]);self.assertAlmostEqual(p[0],10./30.)
    def test_new_histogram_consumes_actual_probability_column(self):
        model=control_pipeline(self.train,self.tree,'duration');h,groups=histogram(model,self.probes())
        self.assertEqual(sum(sum(v) for v in h.values()),4);self.assertEqual(sum(v[1] for v in h.values()),2);self.assertEqual(sum(x['count'] for x in groups),4);self.assertEqual(h[2047][1],2)
    def test_materialization_changes_with_features_at_fixed_count(self):
        a=workload(self.probes(),'feature_transform',self.lr,self.names)[0].asDict();b=workload(self.probes().withColumn('flow_duration',F.lit(999999.)),'feature_transform',self.lr,self.names)[0].asDict()
        self.assertEqual(a['rows'],b['rows']);self.assertNotEqual(a['vector_sum'],b['vector_sum'])
    def test_validation_rows_cannot_fit_preprocessing(self):
        with self.assertRaisesRegex(ValueError,'train rows only'):fit_preprocessing(self.train.withColumn('split_rank',F.lit(1)),self.names)
    def test_capture_partition_contract_requires_strings(self):
        with tempfile.TemporaryDirectory() as directory:
            self.train.withColumn('source_day',F.lit('2018-02-14')).write.partitionBy('source_day').parquet(str(Path(directory)/'partitions'))
            self.spark.conf.set('spark.sql.sources.partitionColumnTypeInference.enabled','false')
            restored=self.spark.read.parquet(str(Path(directory)/'partitions'))
            self.assertEqual(dict(restored.dtypes)['source_day'],'string')
