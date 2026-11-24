"""Architecture and research methodology."""

import streamlit as st

from dashboard.components.ui import REPO, metrics
from dashboard.data_loader import evidence
from dashboard.validation import ROOT


def architecture(summary):
    st.title("Architecture and methodology")
    st.caption("Spark research workflow with an aggregate-only Streamlit presentation layer.")
    st.image(str(ROOT / "dashboard/assets/architecture.svg"), width="stretch")
    r = summary["sql"]["resources"]
    metrics(("Spark version", r["spark_version"]), ("Research workers", r["default_parallelism"]),
            ("Evidence contract", evidence()[0]["schema_version"]))
    st.markdown("""
### Evaluation design

- **A · Grouped random.** Groups of identical cleaned predictor tuples stay in one split.
- **B · Chronological.** Reference captures precede validation and March evaluation. Later split occurrences of an overlapping predictor group are purged.
- **C · Web capture holdout.** Web captures are held out as an unseen scenario. Calendar ordering differs from the chronological protocol.

The frozen predictors exclude labels, timestamps, capture identifiers, destination ports and protocol. Fitted preprocessing uses the training population. Family metrics include observed support and flag absent or sparse cohorts.

### Scientific scope

Novelty is the distance to the nearest frozen centroid. Distribution alerts identify changes in the historical capture collection. Establishing a change in the relationship between features and the target requires separate evidence.

### Reproducibility

PySpark and MLlib ran on private Kaggle CPU notebooks. This dashboard reads compact, checksum-verified outputs with Streamlit and Altair. The machine-learning view exposes verified historical predictions in aggregate.
""")
    st.markdown(f"[System architecture]({REPO}/blob/work/docs/system_architecture.md) · "
                f"[Final project report]({REPO}/blob/work/docs/final_project_report.md) · "
                f"[Dashboard package manifest]({REPO}/blob/work/manifests/dashboard_package.json)")
