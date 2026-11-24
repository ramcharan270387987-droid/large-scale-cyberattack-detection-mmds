"""Contract, presentation and interaction checks for the aggregate dashboard."""

from pathlib import Path
import shutil
import tempfile
import unittest

from streamlit.testing.v1 import AppTest

from dashboard.data_loader import table
from dashboard.sections.models import confusion, experiment_data, models_for, novelty_rows
from dashboard.sections.replay import filter_alerts
from dashboard.components.ui import window_labels
from dashboard.validation import EvidenceError, ROOT, parse_table, verify_package
from scripts.build_dashboard_package import build


class DashboardEvidenceTest(unittest.TestCase):
    def test_sources_and_deterministic_package(self):
        manifest, summary = verify_package(sources=True)
        self.assertEqual(manifest["schema_version"], "dashboard-v1")
        self.assertEqual(summary["dataset"]["totals"]["canonical_rows"], 16232943)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for directory in ("configs", "reports", "manifests"):
                target = root / directory
                target.mkdir()
                for source in {ROOT / p for p in manifest["inputs"] if p.startswith(directory + "/")}:
                    shutil.copyfile(source, target / source.name)
            shutil.copyfile(ROOT / "configs/dashboard.yaml", root / "configs/dashboard.yaml")
            build(root)
            self.assertEqual(verify_package(root, sources=True), (manifest, summary))
            path = root / "dashboard/data/phase3_daily_traffic.csv"
            path.write_bytes(path.read_bytes() + b"\n")
            with self.assertRaisesRegex(EvidenceError, "Checksum mismatch"):
                verify_package(root)
            path.unlink()
            with self.assertRaisesRegex(EvidenceError, "Cannot validate"):
                verify_package(root)

    def test_bad_csv_schema(self):
        for content in (b"bad,id\nx,1\n", b"id,count\n1,2,3\n", b"id,count\n1\n"):
            with self.subTest(content=content), self.assertRaises(EvidenceError):
                parse_table(content, ["id", "count"], "fixture")

    def test_protocol_and_confusion(self):
        rows = models_for(table("phase4_metrics"), "B", "test")
        self.assertEqual(set(rows.protocol), {"B"})
        self.assertEqual(len(rows), 6)
        rf = rows[rows.Model == "Random Forest"].iloc[0]
        matrix = confusion(rf)
        self.assertEqual(matrix.iloc[1, 1], rf.tp)
        self.assertEqual(matrix.values.sum(), rf.rows)
        family = table("phase4_family_recall").query("protocol == 'C' and model == 'random_forest' and split == 'test' and level == 'family'")
        self.assertTrue((family.evaluated_rows == 0).any())

    def test_experiment_and_novelty_isolation(self):
        centroids = experiment_data("phase5_centroids", "G")
        self.assertEqual(set(centroids.experiment), {"G"})
        self.assertEqual(centroids.cluster.nunique(), 5)
        w = novelty_rows(table("phase5_novelty_metrics"), "C", 2, .99).query("scope == 'binary'").iloc[0]
        self.assertAlmostEqual(w.attack_recall, .557751, places=5)
        self.assertAlmostEqual(w.precision, .015023, places=5)

    def test_alert_filters_and_csv_roundtrip(self):
        raw = table("phase6_alerts")
        after = raw.assign(Window=window_labels(raw))
        filtered = filter_alerts(after, "SCORE_SHIFT", "high", "2018-03-02", "All", "All", 10000)
        self.assertTrue(len(filtered) > 0)
        self.assertTrue((filtered.category == "SCORE_SHIFT").all())
        self.assertTrue((filtered.source_day == "2018-03-02").all())
        self.assertTrue((filtered.rows >= 10000).all())
        payload = raw.loc[filtered.index].to_csv(index=False).encode()
        self.assertEqual(len(parse_table(payload, list(raw.columns), "export")), len(filtered))


class DashboardAppTest(unittest.TestCase):
    def page(self, slug=None):
        app = AppTest.from_file(str(ROOT / "dashboard/app.py"), default_timeout=25).run()
        if slug:
            app.switch_page(f"pages/{slug}.py").run()
        self.assertFalse(app.exception)
        return app

    def test_all_routes_and_chart_sources(self):
        headings = {"dataset": "Dataset explorer", "analytics": "Spark SQL analytics", "models": "Machine learning",
                    "clustering": "Clustering and pattern evolution", "novelty": "Distance-based novelty",
                    "replay": "Historical replay and shift monitoring", "alerts": "Alerts explorer",
                    "architecture": "Architecture and methodology"}
        home = self.page()
        self.assertIn("16,232,943", [metric.value for metric in home.metric])
        self.assertIn("15,322,987", [metric.value for metric in home.metric])
        self.assertTrue(home.get("vega_lite_chart"))
        for page, title in headings.items():
            with self.subTest(page=page):
                app = self.page(page)
                self.assertEqual(app.title[0].value, title)
                if page not in ("architecture", "alerts"):
                    self.assertTrue(app.get("vega_lite_chart"))
                if page != "architecture":
                    self.assertTrue(any("Evidence" in cap.value and "/blob/c7dc703" in cap.value for cap in app.caption))

    def test_interactive_protocol_novelty_and_alerts(self):
        app = self.page("models")
        next(box for box in app.selectbox if box.label == "Evaluation protocol").select("B").run()
        self.assertIn("980,109", [x.value for x in app.metric])
        app = self.page("novelty")
        next(box for box in app.selectbox if box.label == "K-Means experiment").select("C").run()
        self.assertIn("55.78%", [x.value for x in app.metric])
        app = self.page("alerts")
        next(box for box in app.selectbox if box.label == "Severity").select("high").run()
        self.assertEqual(app.metric[0].value, "62")
        self.assertEqual(len(app.dataframe[0].value), 62)
        self.assertTrue(app.get("download_button"))


if __name__ == "__main__":
    unittest.main()
