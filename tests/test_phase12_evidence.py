"""Acceptance reconciliation of real artifacts; required after sequential stages."""
import csv,json,hashlib,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def read(path):return list(csv.DictReader((ROOT/path).open()))

class Phase12EvidenceTests(unittest.TestCase):
    def test_pooled_counts_and_matched_cohorts(self):
        from src.ml.threshold_calibration import metrics
        summaries=read('reports/phase12_policy_comparison.csv');windows=read('reports/phase12_prequential_metrics.csv')
        cohorts={}
        for row in summaries:
            group=[w for w in windows if w['run']==row['run']]
            counts={k:sum(int(w[k]) for w in group) for k in ('tp','tn','fp','fn')}
            for k,v in counts.items():self.assertEqual(v,int(row[k]))
            expected=metrics(counts['tp'],counts['tn'],counts['fp'],counts['fn'])
            for key in ('recall','precision','f1','fpr'):
                if expected[key] is None:self.assertEqual(row[key],'')
                else:self.assertAlmostEqual(expected[key],float(row[key]),places=12)
            key=(row['backend'],row['delay']);cohort=[(w['day'],int(w['tp'])+int(w['fn']),int(w['tn'])+int(w['fp'])) for w in group]
            if key in cohorts:self.assertEqual(cohort,cohorts[key])
            cohorts[key]=cohort
    def test_frozen_initial_model_and_release_termination(self):
        rows=read('reports/phase12_policy_comparison.csv')
        primary=[r for r in rows if r['backend']=='E-LR-seed23013-sample125-weight1']
        self.assertEqual(len({r['initial_model'] for r in primary}),1)
        self.assertEqual(len({r['initial_threshold_bin'] for r in primary}),1)
        self.assertEqual({r['policy'] for r in primary},set('P'+str(i) for i in range(7)))
        for r in rows:self.assertEqual(int(r['pending_label_windows']),int(r['delay']))
    def test_kaggle_receipts_and_leakage(self):
        for stage in ('12C','12D','12E'):
            prefix=ROOT/'reports'/f'phase12_{stage}'
            receipt=json.loads((prefix/'receipt.json').read_text());retrieval=json.loads((prefix/'retrieval.json').read_text())
            self.assertEqual(receipt['status'],'validated');self.assertEqual(retrieval['status'],'COMPLETE')
            self.assertEqual(receipt['retained_rows'],16232943)
            self.assertTrue(all(v==0 for v in receipt['cross_role_groups'].values()))
            self.assertGreater(receipt['input']['rows'],16_000_000)
            if stage!='12C':self.assertTrue(receipt['frozen_reference_reload']['calibration_histogram_identical'])
    def test_figures_hashes_and_preview_gate(self):
        manifest=json.loads((ROOT/'manifests/phase12_experiments.json').read_text())
        for path,expected in manifest['evidence_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),expected,path)
        preview=json.loads((ROOT/'reports/phase12_validation/preview.json').read_text())
        browser=json.loads((ROOT/'reports/phase12_validation/browser.json').read_text())
        self.assertEqual(preview['status'],'PASS');self.assertEqual(browser['status'],'PASS')
        self.assertGreaterEqual(preview['sections'],17);self.assertGreaterEqual(browser['screenshots'],2)
