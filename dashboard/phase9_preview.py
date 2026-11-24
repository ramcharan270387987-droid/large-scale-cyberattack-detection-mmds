"""Isolated Streamlit preview of verified aggregate Phase 9 evidence."""

from io import BytesIO
import json

import pandas as pd
import streamlit as st

from dashboard.hybrid_preview import ROOT, REPORTS, evidence


def load_table(filename, digest):
    return pd.read_csv(BytesIO(evidence(REPORTS / filename, digest)))


def main():
    st.set_page_config(page_title="Phase 9 attack-family evaluation", layout="wide")
    st.title("Phase 9 attack-family evaluation")
    try:
        manifest = json.loads((ROOT / "manifests/phase9_experiments.json").read_text())
        stages = manifest["stages"]
        scenario = st.selectbox("Evaluation population", ["A", "B", "Web", "Bot", "Infiltration", "DDoS"])
        stage = stages[scenario]
        st.caption(f"Kaggle version {stage['kernel_version']} · Selected classifier {stage['model']}")
        closed, rejection, hierarchy, capture = st.tabs(
            ["Closed-set classification", "Unknown rejection", "Hierarchy", "Capture-day support"])
        with closed:
            metrics = load_table("phase9_closed_set_metrics.csv", manifest["tables_sha256"]["phase9_closed_set_metrics.csv"])
            st.dataframe(metrics.loc[metrics.scenario.eq(scenario)].drop(columns="scenario"), hide_index=True)
            if stage["test"]["rows"] == 0:
                st.info("This evaluation contains zero training-supported families. Closed-set metrics are undefined.")
            else:
                families = load_table("phase9_per_family.csv", manifest["tables_sha256"]["phase9_per_family.csv"])
                confusion = load_table("phase9_family_confusion.csv", manifest["tables_sha256"]["phase9_family_confusion.csv"])
                labels = {index: family for family, index in stage["classes"].items()}
                selected = families.loc[families.scenario.eq(scenario)].copy()
                selected["family"] = selected.class_id.map(labels)
                st.dataframe(selected.drop(columns=["scenario", "class_id"]), hide_index=True)
                matrix = confusion.loc[confusion.scenario.eq(scenario)].pivot(index="actual", columns="predicted", values="count")
                matrix = matrix.reindex(index=labels, columns=labels).fillna(0).astype(int)
                st.dataframe(matrix.rename(index=labels, columns=labels))
        with rejection:
            scores = load_table("phase9_open_set_metrics.csv", manifest["tables_sha256"]["phase9_open_set_metrics.csv"])
            selected = scores.loc[scores.scenario.eq(scenario)].drop(columns="scenario")
            if selected.empty:
                st.info("This population has no verified open-set operating points.")
            else:
                st.dataframe(selected, hide_index=True)
                st.caption("Thresholds were calibrated on known validation attacks. Rejection of a held-out family is retrospective.")
            st.caption("The table contains frozen operating points. A full risk–coverage curve requires score-distribution evidence.")
        with hierarchy:
            staged = manifest.get("hierarchy", {}).get(scenario)
            if staged is None:
                st.info("This population has no verified hierarchical receipt.")
            else:
                st.dataframe(pd.DataFrame.from_dict(staged["results"], orient="index").drop(columns="counts"))
                st.caption("The oracle gate uses the binary ground truth as a diagnostic.")
        with capture:
            support = load_table("phase9_family_support.csv", manifest["tables_sha256"]["phase9_family_support.csv"])
            matrix = support.loc[support.binary_label.eq(1)].pivot_table(
                index="attack_family", columns="source_day", values="count", aggfunc="sum", fill_value=0)
            st.dataframe(matrix)
            st.caption("Each attack family occurs on one or two capture days. Capture conditions can influence prediction and rejection.")
        st.caption("The dataset is retrospective and has no independent external confirmation.")
    except (OSError, KeyError, ValueError) as exc:
        st.error(f"Phase 9 evidence is unavailable. {exc}")


if __name__ == "__main__":
    main()
