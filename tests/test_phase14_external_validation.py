import unittest
from src.external_validation.contracts import COMMON,label,capture,require_mapping,verified_receipt
class ExternalContractTests(unittest.TestCase):
    def test_labels_preserve_unknown_attack(self):
        self.assertEqual(label(' BENIGN '),0);self.assertEqual(label('Unknown new attack'),1);self.assertIsNone(label(''));self.assertIsNone(label('Label'))
    def test_capture_is_not_invented_time(self):
        self.assertEqual(capture('Friday-WorkingHours-Morning.pcap_ISCX.csv'),'2017-07-07')
        with self.assertRaises(ValueError):capture('undated.csv')
    def test_order_and_unsupported_exact(self):
        cfg={'common_features':list(COMMON),'source_features':list(COMMON)};self.assertTrue(require_mapping(COMMON,cfg))
        with self.assertRaises(ValueError):require_mapping(list(reversed(COMMON)),cfg)
        with self.assertRaises(ValueError):require_mapping(COMMON,cfg,exact=True)
    def test_receipt_requires_reconciliation_and_pins(self):
        r={'status':'validated','dataset_version':1,'files':[{'bytes':1,'sha256':'a'*64}]*8,'physical_data_rows':12,'eligible_rows':10,'excluded_rows':2};self.assertTrue(verified_receipt(r));r['eligible_rows']=11
        with self.assertRaises(ValueError):verified_receipt(r)

class LabelByteTests(unittest.TestCase):
    def test_non_utf8_labels_are_preserved_without_guessing_families(self):
        import tempfile
        from pathlib import Path
        from src.external_validation.label_mapping import audit_label_bytes
        with tempfile.TemporaryDirectory() as temp:
            for i in range(8):(Path(temp)/f'Friday-WorkingHours-{i}.csv').write_bytes(b'x,Label\n1,BENIGN\n2,Web Attack \x96 XSS\n')
            r=audit_label_bytes(Path(temp));self.assertEqual(r['rows'],16);a=next(x for x in r['labels'] if x['binary_label']==1);self.assertEqual(bytes.fromhex(a['original_label_hex']),b'Web Attack \x96 XSS');self.assertEqual(a['original_label'],'Web Attack – XSS');self.assertIn('Windows-1252',a['decoding'])
