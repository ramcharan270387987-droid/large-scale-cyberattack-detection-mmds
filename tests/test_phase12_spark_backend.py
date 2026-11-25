"""Actual RF preprocessing, classifier persistence and feature-vector integration."""
import json,tempfile,unittest
from pathlib import Path
from pyspark.sql import SparkSession
from src.adaptation.historical import SparkBackend

class Phase12SparkBackendTests(unittest.TestCase):
    def test_random_forest_validates_both_vectors_and_reloads(self):
        spark=SparkSession.builder.master('local[2]').config('spark.ui.enabled','false').config('spark.sql.shuffle.partitions','4').getOrCreate()
        spark.sparkContext.setLogLevel('ERROR')
        try:
            names=json.loads((Path(__file__).resolve().parents[1]/'configs/ml_experiments.yaml').read_text())['numerical_features']
            days=['2018-02-14','2018-02-15','2018-02-16','2018-02-20','2018-02-21','2018-02-22','2018-02-23','2018-02-28','2018-03-01','2018-03-02']
            rows=[(day,i%3,i%2,'attack' if i%2 else 'Benign',str(i).encode(),*[float((i*(j+1))%37+i%2) for j in range(18)]) for day in days for i in range(600)]
            frame=spark.createDataFrame(rows,['source_day','split_rank','binary_label','attack_family','predictor_key',*names])
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory)
                backend=SparkBackend(spark,frame,names,root,root/'scratch',{},family='RF',sample=10000)
                backend.source_commit='controlled-test'
                key=backend.fit(days[:2]);backend.verify(key)
                hist=backend.hist(key,[days[2]],1)
                self.assertEqual(sum(sum(v) for v in hist.values()),200)
                self.assertEqual(backend.meta[key]['family'],'RF')
                self.assertNotIn('StandardScalerModel',backend.meta[key]['receipt']['preprocessing_stages'])
                self.assertTrue(backend.meta[key]['independent_reload'])
        finally:spark.stop()
