"""Exercise the local Streamlit dashboard with Chromium and Playwright."""

import argparse
import csv
import json
from pathlib import Path
import re
from subprocess import run
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PAGES = {
    "": ("Overview", "Large-Scale Cyberattack Detection", 1, 0),
    "dataset": ("Dataset explorer", "Dataset explorer", 2, 6),
    "analytics": ("Spark SQL analytics", "Spark SQL analytics", 2, 3),
    "models": ("Machine learning", "Machine learning", 1, 2),
    "clustering": ("Clustering", "Clustering and pattern evolution", 5, 2),
    "novelty": ("Novelty detection", "Distance-based novelty", 1, 1),
    "replay": ("Historical replay", "Historical replay and shift monitoring", 5, 4),
    "alerts": ("Alerts explorer", "Alerts explorer", 0, 1),
    "architecture": ("Architecture", "Architecture and methodology", 0, 0),
}
MODEL_NAMES = {
    "majority": "Majority class", "duration_rule": "Duration rule", "random_forest": "Random Forest",
    "logistic_regression": "Logistic Regression", "gradient_boosted_trees": "Gradient-Boosted Trees",
}


def rows(name):
    with (ROOT / "reports" / f"{name}.csv").open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def select(page, label, value):
    expect(page.get_by_test_id("stApp")).to_have_attribute("data-test-script-state", "notRunning")
    combo = page.get_by_role("combobox", name=label, exact=True)
    if str(value) == combo.input_value():
        return
    combo.click()
    if combo.get_attribute("aria-expanded") != "true":
        combo.press("ArrowDown")
    combo.fill(str(value))
    option = page.get_by_role("option", name=str(value), exact=True)
    expect(option).to_be_visible()
    option_id = option.get_attribute("id")
    ids = page.get_by_role("option").evaluate_all("(options) => options.map(option => option.id)")
    for _ in range(len(ids) + 1):
        active = combo.get_attribute("aria-activedescendant")
        if active == option_id:
            break
        combo.press("ArrowUp" if active in ids and ids.index(active) > ids.index(option_id) else "ArrowDown")
    expect(combo).to_have_attribute("aria-activedescendant", option_id)
    combo.press("Enter")
    page.wait_for_function("""([label, value]) => {
        const current = [...document.querySelectorAll('[role=combobox]')].filter(
          el => el.getAttribute('aria-label') === label && el.getClientRects().length);
        return document.querySelector('[data-testid=stApp]')?.dataset.testScriptState === 'notRunning' &&
          current.length === 1 && current[0].value === value && current[0].getAttribute('aria-expanded') === 'false';
    }""", arg=[label, str(value)], timeout=10000)


def metric(page, name, value):
    item = page.get_by_test_id("stMetric").filter(
        has=page.get_by_test_id("stMetricLabel").get_by_text(name, exact=True))
    expect(item.get_by_test_id("stMetricValue")).to_have_text(str(value))


def pc(value):
    return "Undefined" if value == "" else f"{float(value):.2%}"


def window(row):
    return {"daily": "Daily", "capture_only": "Capture day only"}.get(
        row["scope"], f"{row['wall_start']}–{row['wall_end']}")


def navigate(page, slug):
    label, heading, *_ = PAGES[slug]
    page.get_by_test_id("stSidebarNav").get_by_role("link", name=label, exact=True).click()
    expect(page.get_by_role("heading", name=heading, exact=True)).to_be_visible()
    expect(page.get_by_test_id("stException")).to_have_count(0)


def verify_links(page, checked):
    locator = page.get_by_test_id("stMain").locator("a[href*='github.com/'][href*='/blob/']")
    expect(locator.first).to_be_attached()
    expect(page.get_by_test_id("stApp")).to_have_attribute("data-test-script-state", "notRunning")
    for anchor in locator.all():
        url = anchor.get_attribute("href")
        if url in checked:
            continue
        revision, path = urlparse(url).path.split("/blob/", 1)[1].split("/", 1)
        result = run(["git", "cat-file", "-e", f"{revision}:{path}"], cwd=ROOT, capture_output=True)
        assert result.returncode == 0, url
        checked.add(url)


def visit_tab(element):
    index = element.evaluate("""el => {
        const pane = el.closest('[data-testid=stTabPanel]');
        return pane ? [...pane.parentElement.children].filter(x=>x.dataset.testid==='stTabPanel').indexOf(pane) : -1;
    }""")
    if index >= 0:
        element.page.get_by_role("tab").nth(index).click()


def native_widgets(page, charts, frames):
    charts_locator = page.get_by_test_id("stVegaLiteChart")
    expect(charts_locator).to_have_count(charts)
    for panel in charts_locator.all():
        visit_tab(panel)
        expect(panel.get_by_role("img").first).to_be_visible()
        canvas = panel.get_by_role("img").first
        assert canvas.bounding_box()["width"] > 10
        panel.hover()
        toolbar = panel.locator("..")
        with page.expect_download() as item:
            toolbar.get_by_role("button", name="Download as PNG").click()
        with open(item.value.path(), "rb") as file:
            assert file.read(8) == b"\x89PNG\r\n\x1a\n"
    frame_locator = page.get_by_test_id("stDataFrame")
    expect(frame_locator).to_have_count(frames)
    for frame in frame_locator.all():
        visit_tab(frame)
        expect(frame.locator("canvas").first).to_be_visible()
        frame.hover()
        with page.expect_download() as item:
            frame.get_by_role("button", name="Download as CSV").click()
        with open(item.value.path(), newline="", encoding="utf-8-sig") as file:
            records = list(csv.reader(file))
            assert len(records) >= 2
    for tab in page.get_by_role("tablist").all():
        first = tab.get_by_role("tab").first
        if first.is_visible():
            first.click()


def test_dataset(page):
    source = rows("phase3_daily_traffic")
    for row in source:
        select(page, "Capture day", row["source_day"])
        metric(page, "Flows in capture selection", f"{int(row['records']):,}")
        metric(page, "Benign", f"{int(row['benign']):,}")
        metric(page, "Attack", f"{int(row['attacks']):,}")
    select(page, "Capture day", "All days")
    select(page, "Attack family", "Bot")
    select(page, "Original label", "Bot")
    select(page, "Capture day", "2018-02-14")
    expect(page.get_by_text("The selected family has no recorded flows on this capture day.")).to_be_visible()
    page.get_by_role("tab", name="Protocols and ports").click()
    select(page, "Protocol code", "6")
    select(page, "Destination port", "8080")
    page.get_by_role("tab", name="Feature quality").click()
    select(page, "Numerical feature", "flow_duration")
    expect(page.get_by_text(re.compile("Distribution units · µs"))).to_be_visible()
    select(page, "Numerical feature", "active_max")
    expect(page.get_by_text(re.compile("Phase 3 published missingness"))).to_be_visible()


def test_analytics(page):
    for option in ("Packet count", "Byte volume", "Flow duration (µs)"):
        select(page, "Flow statistic", option)
    for option in sorted({r["workload"] for r in rows("phase3_query_performance")}):
        select(page, "Workload", option)


def test_models(page):
    data = rows("phase4_metrics")
    for key, name in (("A", "Grouped random"), ("B", "Chronological"), ("C", "Web attack capture holdout")):
        select(page, "Evaluation protocol", f"{key} · {name}")
        for split in ("Test", "Validation"):
            select(page, "Evaluation split", split)
            subset = [r for r in data if r["protocol"] == key and r["split"] == split.lower()]
            for model in subset:
                label = MODEL_NAMES[model["model"]]
                if model["training_cohort"] == "full_train_refit":
                    label += " · full-training refit"
                select(page, "Confusion matrix and attack-family recall", label)
                metric(page, "Evaluation flows", f"{int(model['rows']):,}")
                support = (int(model["tp"]) + int(model["fn"])) / int(model["rows"])
                metric(page, "Evaluation attack prevalence", f"{support:.2%}")
                cells = page.get_by_test_id("stTable").locator("tbody td")
                expect(cells).to_have_text([model[k] for k in ("tn", "fp", "fn", "tp")])
    for score in ("Precision", "F1", "Accuracy", "ROC-AUC", "PR-AUC", "Recall"):
        select(page, "Compare metric", score)
        expect(page.get_by_test_id("stVegaLiteChart").locator("svg").get_by_text(score, exact=True)).to_be_visible()


def test_cluster_novelty(page, slug):
    cuts = rows("phase5_novelty_metrics")
    fit = rows("phase5_model_selection")
    for code, name in (("G", "Global retrospective"), ("B", "Historical reference"), ("C", "Web capture holdout")):
        select(page, "K-Means experiment", f"{code} · {name}")
        if slug == "clustering":
            row = next(r for r in fit if r["experiment"] == code and r["selected"] == "True")
            metric(page, "Selected clusters", row["k"])
            metric(page, "Fit flows", f"{int(row['training_rows']):,}")
            metric(page, "Probe silhouette", f"{float(row['silhouette']):.4f}")
            continue
        cohort = {"0": "All retrospective flows"} if code == "G" else {"0": "Reference", "1": "Validation", "2": "Held-out test"}
        for rank, name in cohort.items():
            select(page, "Population", name)
            for cutoff in ("0.95", "0.99", "0.999"):
                select(page, "Reference percentile", f"P{float(cutoff)*100:g}")
                row = next(r for r in cuts if (r["experiment"], r["split_rank"], r["percentile"], r["scope"]) ==
                           (code, rank, cutoff, "binary"))
                metric(page, "Squared-distance cutoff", f"{float(row['threshold']):.3f}")
                for label, field in (("Flag rate", "flag_rate"), ("Benign false-positive rate", "benign_fpr"),
                                     ("Attack recall", "attack_recall"), ("Precision", "precision")):
                    metric(page, label, pc(row[field]))


def test_replay(page):
    for label, value in (("Retained flows", "15,322,987"), ("Microbatches", "49"), ("Throughput", "17,770 flows/s")):
        metric(page, label, value)
    for row in rows("phase6_window_metrics"):
        select(page, "Capture day", row["source_day"])
        select(page, "Capture window", window(row))
        metric(page, "Window flows", f"{int(row['rows']):,}")
        metric(page, "Timestamp eligible", f"{int(row['eligible']):,}")
        metric(page, "K-Means flags", f"{json.loads(row['novelty_metrics'])['flags']:,}")


def test_alerts(page, directory):
    data = rows("phase6_alerts")
    metric(page, "Matching alerts", "102")
    metric(page, "High severity", "62")
    select(page, "Severity", "high")
    metric(page, "Matching alerts", "62")
    with page.expect_download() as item:
        page.get_by_role("button", name="Download filtered alerts CSV").click()
    item.value.save_as(directory / "high-severity-alerts.csv")
    with open(item.value.path(), newline="", encoding="utf-8") as file:
        assert list(csv.DictReader(file)) == [r for r in data if r["severity"] == "high"]
    select(page, "Severity", "All")
    f = data[0]
    for label, name in (("Category", "category"), ("Capture day", "source_day"), ("Detector", "detector"), ("Window", "Window")):
        select(page, label, window(f) if name == "Window" else f[name])
    expected = [r for r in data if all(r[k] == f[k] for k in ("category", "source_day", "detector")) and window(r) == window(f)]
    metric(page, "Matching alerts", f"{len(expected):,}")
    control = page.get_by_role("spinbutton", name="Minimum window support")
    control.fill("16000000")
    control.press("Enter")
    metric(page, "Matching alerts", "0")
    expect(page.get_by_role("button", name="Download filtered alerts CSV")).to_be_disabled()


def audit(base, directory, chromium):
    directory.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chromium, headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 950})
        page.set_default_timeout(10000)
        failures, recovering, links = [], [], set()

        def response(res):
            if res.status >= 400:
                if res.status == 404 and re.fullmatch(r"/[a-z]+/_stcore/(host-config|health)", urlparse(res.url).path):
                    recovering.append(urlparse(res.url).path)
                else:
                    failures.append(f"{res.status} {res.url}")

        page.on("response", response)
        page.on("pageerror", lambda exc: failures.append(str(exc)))
        page.on("console", lambda msg: failures.append(msg.text) if msg.type == "error" and
                not msg.text.startswith("Failed to load resource:") else None)
        assert page.goto(base).ok
        expect(page.get_by_role("heading", name=PAGES[""][1], exact=True)).to_be_visible()
        for slug, (_, _, charts, frames) in PAGES.items():
            navigate(page, slug)
            verify_links(page, links)
            native_widgets(page, charts, frames)
            if slug == "dataset":
                test_dataset(page)
            elif slug == "analytics":
                test_analytics(page)
            elif slug == "models":
                test_models(page)
            elif slug in ("clustering", "novelty"):
                test_cluster_novelty(page, slug)
            elif slug == "replay":
                test_replay(page)
            elif slug == "alerts":
                test_alerts(page, directory)
            page.evaluate("document.querySelector('[data-testid=stMain]').scrollTo(0,0)")
            page.screenshot(path=directory / f"{slug or 'overview'}-desktop.png")
            print(f"PASS desktop {slug or 'overview'} · {charts} charts and {frames} dataframes", flush=True)
        for width in (390, 768):
            page.set_viewport_size({"width": width, "height": 860})
            for slug, (_, heading, _, _) in PAGES.items():
                assert page.goto(f"{base}/{slug}").ok
                expect(page.get_by_role("heading", name=heading, exact=True)).to_be_visible()
                expect(page.get_by_test_id("stException")).to_have_count(0)
                assert page.evaluate("""() => { const el=document.querySelector('[data-testid=stMain]');
                      return el.scrollWidth <= el.clientWidth+1; }"""), (slug, width)
                clipped = page.get_by_test_id("stMetricValue").locator("[data-testid=stMarkdownContainer]").evaluate_all(
                    "(values) => values.filter(e=>e.clientWidth && e.scrollWidth>e.clientWidth+2).map(e=>e.textContent)")
                assert not clipped, (slug, width, clipped)
                if slug == "architecture" and width == 390:
                    expect(page.locator(".mmds-architecture-mobile")).to_be_visible()
                if width == 390:
                    page.screenshot(path=directory / f"{slug or 'overview'}-mobile.png")
                print(f"PASS {width}px {slug or 'overview'}", flush=True)
        assert page.request.get(f"{base}/_stcore/health").ok
        assert page.request.get(f"{base}/favicon.png").ok
        assert not failures, failures
        assert len(links) >= 30, links
        print(f"PASS browser requests and UI errors. {len(links)} Git evidence links verified; "
              f"{len(recovering)} recoverable Streamlit deep-link probes.", flush=True)
        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8501")
    parser.add_argument("--screenshots", type=Path, required=True)
    parser.add_argument("--chromium", default="/usr/bin/chromium")
    args = parser.parse_args()
    audit(args.url.rstrip("/"), args.screenshots, args.chromium)
