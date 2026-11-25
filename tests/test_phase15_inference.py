import unittest,json,hashlib,tempfile,math,csv,io
from pathlib import Path
from src.interactive import portable,inputs,evidence
ROOT=Path(__file__).resolve().parents[1]
class InteractiveContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=evidence.models();cls.models=[portable.verify(ROOT/r['artifact'],r['sha256']) for r in cls.registry];cls.lr=next(m for m in cls.models if m['kind']=='LR');cls.features=cls.lr['features'];cls.demo=(ROOT/'dashboard/data/phase15_demo.csv').read_bytes()
    def test_registry_and_original_identity(self):
        self.assertEqual({m['kind'] for m in self.models},{'LR','RF','KMeans'})
        original=json.loads((ROOT/'manifests/phase13_models.json').read_text())['supervised']
        for r in self.registry:
            self.assertEqual(r['parity']['status'],'PASS')
            if r['kind']!='KMeans':self.assertEqual(r['source_sha256'],next(m['sha256'] for m in original if m['id']==r['id']))
    def test_missing_and_corrupt_artifacts_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'model.json'
            with self.assertRaises(OSError):portable.verify(p,'0'*64)
            p.write_text('{}')
            with self.assertRaisesRegex(ValueError,'checksum'):portable.verify(p,'0'*64)
    def test_unsupported_model_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'model.json';p.write_text(json.dumps({'schema':'phase15-portable-v1','kind':'fake'}))
            with self.assertRaisesRegex(ValueError,'Unsupported'):portable.verify(p,hashlib.sha256(p.read_bytes()).hexdigest())
    def test_feature_order_enforced(self):
        with self.assertRaises(ValueError):portable.predict(self.lr,{n:0. for n in reversed(self.features)})
    def test_manual_missing_uses_training_values(self):
        values=inputs.parse_values(dict.fromkeys(self.features,''),self.features);result=portable.predict(self.lr,values);self.assertEqual(result['imputed_features'],self.features);self.assertTrue(math.isfinite(result['probability']))
    def test_invalid_manual_domain(self):
        for bad in ('hello','NaN','Infinity',-1,1e13):
            row=dict.fromkeys(self.features,'');row[self.features[0]]=bad
            with self.assertRaises(ValueError):inputs.parse_values(row,self.features)
    def test_csv_alignment_and_invalid_row_retention(self):
        data=self.demo+b'bad,'+b','.join([b'0']*17)+b'\n';rows=inputs.parse_csv(data,self.features);out=inputs.batch(self.lr,rows);self.assertEqual([r['row_number'] for r in out],[1,2,3,4]);self.assertEqual(out[-1]['status'],'invalid');self.assertNotIn('probability',out[-1]);self.assertEqual(out[0]['imputed_count'],18)
    def test_csv_column_contract(self):
        for header in (self.features[:-1],self.features+['extra'],self.features[:-1]+[self.features[0]],list(reversed(self.features))):
            with self.assertRaises(ValueError):inputs.parse_csv((','.join(header)+'\n').encode(),self.features)
    def test_upload_budgets(self):
        with self.assertRaises(ValueError):inputs.parse_csv(b'x'*(inputs.MAX_BYTES+1),self.features)
        with self.assertRaises(ValueError):inputs.parse_csv((','.join(self.features)+'\n'+','.join(['0']*18)+'\n'+','.join(['0']*18)+'\n').encode(),self.features,max_rows=1)
    def test_empty_and_bad_encoding(self):
        for data in (b'',b'\xff',(','.join(self.features)+'\n').encode()):
            with self.assertRaises(ValueError):inputs.parse_csv(data,self.features)
    def test_safe_export(self):
        output=inputs.safe_csv([{'a':'=1+1','b':' @cmd','c':-1.25}]).decode();row=next(csv.DictReader(io.StringIO(output)));self.assertTrue(row['a'].startswith("'"));self.assertTrue(row['b'].startswith("'"));self.assertEqual(row['c'],'-1.25')
    def test_lr_explanation_reconstruction(self):
        result=portable.predict(self.lr,dict.fromkeys(self.features,0.));self.assertAlmostEqual(result['logit'],result['baseline']+math.fsum(result['contributions']));self.assertEqual(result['label'],'ATTACK' if result['probability']>=result['threshold'] else 'BENIGN')
    def test_novelty_decomposition(self):
        model=next(m for m in self.models if m['kind']=='KMeans');r=portable.predict(model,dict.fromkeys(self.features,None));self.assertAlmostEqual(r['squared_distance'],math.fsum(r['contributions']));self.assertEqual(r['label'],'NOVEL' if r['squared_distance']>r['threshold'] else 'REFERENCE-LIKE')
    def test_repeated_predictions_identical(self):
        for model in self.models:
            x=dict.fromkeys(self.features,1.);self.assertEqual(portable.predict(model,x),portable.predict(model,x))
    def test_actual_spark_parity_receipt(self):
        r=json.loads((ROOT/'reports/phase15_validation/parity.json').read_text());self.assertEqual(r['status'],'PASS');self.assertEqual(r['spark'],'4.3.0');self.assertFalse(r['fitting_performed']);self.assertGreaterEqual(sum(x['probes'] for x in r['models']),2400)
    def test_all_evidence_checksums(self):
        c=evidence.catalog();self.assertEqual(len(c['groups']),9)
        for entries in c['groups'].values():
            for e in entries:self.assertFalse(evidence.load(e).empty,e['path'])
