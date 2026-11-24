"""Historical replay, shift and alert exploration."""

import json

import altair as alt
import pandas as pd
import streamlit as st

from dashboard.components.ui import chart, count, metrics, pct, selector, show, source, window_labels
from dashboard.data_loader import table


def replay(summary):
    st.title("Historical replay and shift monitoring")
    r = summary["replay"]
    metrics(("Retained flows", count(r["rows"])), ("Microbatches", count(r["batches"])),
            ("Throughput", f"{r['rows_per_second']:,.0f} flows/s"), ("Query elapsed", f"{r['elapsed_seconds']:.1f} s"))
    st.caption("Capture time uses the original wall clock with unverified timezone. Spark processing timestamps are UTC.")
    batches = table("phase6_replay_batches")
    batches["Cumulative flows"] = batches.rows.cumsum()
    a, b = st.columns(2)
    with a:
        chart(alt.Chart(batches).mark_area(color="#58e0c1", opacity=.5, line=True).encode(
            x=alt.X("batch_id:Q", title="Replay batch ID"), y="Cumulative flows:Q",
            tooltip=["batch_id:Q", "source_day:N", "rows:Q", "Cumulative flows:Q"]).properties(height=170))
    with b:
        chart(alt.Chart(batches).mark_bar().encode(x=alt.X("batch_id:O", title="Replay batch ID", axis=alt.Axis(labels=False)),
              y=alt.Y("processing_seconds:Q", title="Batch latency (seconds)"),
              color=alt.Color("source_day:N", title="Capture day", legend=None),
              tooltip=["batch_id:O", "source_day:N", "processing_seconds:Q", "rows_per_second:Q"]).properties(height=170))
    windows = table("phase6_window_metrics")
    windows["Window"] = window_labels(windows)
    a, b = st.columns(2)
    day = a.selectbox("Capture day", sorted(windows.source_day.unique(), reverse=True))
    day_windows = windows[windows.source_day == day]
    selected = b.selectbox("Capture window", day_windows.Window.tolist()[::-1])
    row = day_windows[day_windows.Window == selected].iloc[0]
    novelty = json.loads(row.novelty_metrics)
    metrics(("Window flows", count(row.rows)), ("Timestamp eligible", count(row.eligible)),
            ("K-Means flags", count(novelty["flags"])), ("Novelty rate", pct(novelty["flag_rate"])))
    a, b, c = st.tabs(["Window metrics", "Shift and alerts", "Benchmark and recovery"])
    with a:
        st.subheader("Frozen classifiers")
        scores = pd.DataFrame.from_dict(json.loads(row.classifier_metrics), orient="index").rename_axis("Model").reset_index()
        show(scores, ["Model", "predicted_positive", "tp", "tn", "fp", "fn", "recall", "precision", "pr_auc"])
        left, right = st.columns(2)
        with left:
            rf = pd.DataFrame({"Bin": range(32), "Flows": json.loads(row.rf_score_counts_32)})
            chart(alt.Chart(rf).mark_bar().encode(x=alt.X("Bin:O", title="RF score bin (32 equal bins from 0 to 1)"),
                  y="Flows:Q", tooltip=["Bin:O", "Flows:Q"]).properties(height=165))
        with right:
            clusters = json.loads(row.cluster_counts)
            frame = pd.DataFrame({"Cluster": range(len(clusters)), "Flows": clusters})
            chart(alt.Chart(frame).mark_bar().encode(x=alt.X("Cluster:O"), y="Flows:Q",
                  tooltip=["Cluster:O", "Flows:Q"]).properties(height=165))
        st.caption(f"Mean squared centroid distance {row.mean_distance:.3f} · K-Means cutoff {r['cutoff']:.6f}.")
    with b:
        shift = table("phase6_shift_metrics")
        shift["Window"] = window_labels(shift)
        show(shift[(shift.source_day == day) & (shift.Window == selected)],
             ["category", "detector", "value", "reference_value", "delta", "threshold", "rows", "support"])
        alerts = table("phase6_alerts")
        timeline = alerts.groupby(["source_day", "severity"], as_index=False).size()
        chart(alt.Chart(timeline).mark_bar().encode(x=alt.X("source_day:N", title="Capture day"),
              y=alt.Y("size:Q", title="Alert records"), color="severity:N",
              tooltip=["source_day:N", "severity:N", "size:Q"]).properties(height=165))
        st.caption("Distribution changes and retrospective performance warnings have distinct evidence. These shifts do not establish concept drift.")
    with c:
        show(table("phase6_performance"))
        show(table("phase6_recovery_tests"))
    source("phase6_window_metrics", "phase6_shift_metrics", "phase6_alerts", "phase6_replay_batches",
           "phase6_performance", "phase6_recovery_tests", report="reports/phase6_streaming_results.md")


def filter_alerts(frame, category, severity, day, window, detector, support):
    keep = frame.rows >= support
    for column, value in (("category", category), ("severity", severity), ("source_day", day),
                          ("Window", window), ("detector", detector)):
        if value != "All":
            keep &= frame[column] == value
    return frame.loc[keep].copy()


def alerts(summary):
    st.title("Alerts explorer")
    source_rows = table("phase6_alerts")
    raw = source_rows.copy()
    raw["Window"] = window_labels(raw)
    st.caption(f"{count(summary['replay']['alerts']['count'])} records from offline historical replay. Daily and intraday alerts can cover the same flows.")
    first = st.columns(3)
    category = first[0].selectbox("Category", ["All", *sorted(raw.category.unique())])
    severity = first[1].selectbox("Severity", ["All", *sorted(raw.severity.unique())])
    day = first[2].selectbox("Capture day", ["All", *sorted(raw.source_day.unique())])
    second = st.columns(3)
    window = second[0].selectbox("Window", ["All", *sorted(raw.Window.unique())])
    detector = second[1].selectbox("Detector", ["All", *sorted(raw.detector.unique())])
    support = second[2].number_input("Minimum window support", min_value=0, step=1000)
    rows = filter_alerts(raw, category, severity, day, window, detector, support)
    metrics(("Matching alerts", count(len(rows))), ("High severity", count((rows.severity == "high").sum())),
            ("Label-backed records", count(rows.labels_used.sum())))
    st.download_button("Download filtered alerts CSV", source_rows.loc[rows.index].to_csv(index=False).encode("utf-8"),
                       "mmds-historical-alerts.csv", "text/csv", disabled=rows.empty)
    show(rows, ["source_day", "Window", "category", "detector", "value", "reference_value", "delta",
                "threshold", "rows", "evidence", "severity", "version"])
    st.caption("The novelty threshold is a rate increase, the performance threshold is a recall drop, and shift thresholds are in Jensen–Shannon bits.")
    source("phase6_alerts", "phase6_shift_metrics", report="docs/phase6_drift_interpretation.md")
