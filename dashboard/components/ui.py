"""Shared evidence display and formatting primitives."""

import altair as alt
import pandas as pd
import streamlit as st

from dashboard.data_loader import evidence, lineage

COLORS = ["#58e0c1", "#ffae79", "#99acff", "#de8bca", "#e6d57a", "#8dc8f3",
          "#c4e299", "#ff7e86", "#bb93f5", "#b99c76", "#56a7a3", "#f1c4d2"]
REPO = "https://github.com/ramcharan270387987-droid/large-scale-cyberattack-detection-mmds"
EXPERIMENTS = {"G": "Global retrospective", "B": "Historical reference", "C": "Web capture holdout"}
PROTOCOLS = {"A": "Grouped random", "B": "Chronological", "C": "Web attack capture holdout"}


def count(value):
    return f"{int(value):,}"


def pct(value):
    return "Undefined" if pd.isna(value) else f"{value:.2%}"


def metrics(*items):
    for column, (label, value) in zip(st.columns(len(items)), items):
        column.metric(label, value)


def source(*names, report=None):
    paths = lineage(*names)
    if report:
        paths.append(report)
    rev = evidence()[0]["source_revision"]
    st.caption("Evidence · " + " · ".join(f"[{path.rsplit('/', 1)[-1]}]({REPO}/blob/{rev}/{path})" for path in paths))


def chart(plot):
    st.altair_chart(plot.configure_view(stroke=None).configure_axis(gridColor="#304044")
                    .configure_range(category=COLORS), width="stretch")


def show(frame, columns=None):
    if frame.empty:
        st.info("No aggregate rows match the selected filters.")
    else:
        st.dataframe(frame if columns is None else frame[columns], hide_index=True, width="stretch")


def selector(label, frame, field, *, all_label=None, key=None):
    values = sorted(frame[field].dropna().unique())
    return st.selectbox(label, ([all_label] if all_label is not None else []) + values, key=key)


def window_labels(frame):
    return frame.apply(lambda r: "Daily" if r["scope"] == "daily" else
                       "Capture day only" if r["scope"] == "capture_only" else
                       f"{r['wall_start']}–{r['wall_end']}", axis=1)
