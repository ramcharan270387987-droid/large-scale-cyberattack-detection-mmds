"""Historical supervised, clustering and novelty evaluations."""

import altair as alt
import pandas as pd
import streamlit as st

from dashboard.components.ui import EXPERIMENTS, PROTOCOLS, chart, count, metrics, pct, show, source
from dashboard.data_loader import table


MODEL_NAMES = {"majority": "Majority class", "duration_rule": "Duration rule", "random_forest": "Random Forest",
               "logistic_regression": "Logistic Regression", "gradient_boosted_trees": "Gradient-Boosted Trees"}


def models_for(data, protocol, split):
    subset = data[(data.protocol == protocol) & (data.split == split)].copy()
    subset["Model"] = subset.model.map(MODEL_NAMES)
    subset.loc[subset.training_cohort == "full_train_refit", "Model"] += " · full-training refit"
    return subset


def confusion(row):
    return pd.DataFrame([[int(row.tn), int(row.fp)], [int(row.fn), int(row.tp)]],
                        index=["Actual benign", "Actual attack"], columns=["Predicted benign", "Predicted attack"])


def supervised(summary):
    st.title("Machine learning")
    left, right = st.columns(2)
    protocol = left.selectbox("Evaluation protocol", list(PROTOCOLS), format_func=lambda x: f"{x} · {PROTOCOLS[x]}")
    split = right.selectbox("Evaluation split", ["test", "validation"], format_func=str.title)
    data = models_for(table("phase4_metrics"), protocol, split)
    support = summary["model_support"][protocol]
    labels = support[split]["labels"]
    n = sum(labels.values())
    metrics(("Training flows before sampling", count(sum(support["train"]["labels"].values()))),
            ("Evaluation flows", count(n)), ("Evaluation attack prevalence", pct(labels.get("1", 0) / n)))
    st.caption(f"Frozen classification threshold {summary['models']['threshold']:.1f}. PR-AUC depends on attack prevalence.")
    if protocol != "A":
        design = summary["protocols"][protocol]
        st.markdown(f"**Capture dates** · Train {', '.join(design['train'])} · {split.title()} {', '.join(design[split])}")
    metric = st.selectbox("Compare metric", ["recall", "precision", "f1", "accuracy", "roc_auc", "pr_auc"],
                          format_func=lambda x: x.upper().replace("_", "-"))
    chart(alt.Chart(data).mark_bar(cornerRadiusEnd=4).encode(x=alt.X(f"{metric}:Q", scale=alt.Scale(domain=[0, 1])),
          y=alt.Y("Model:N", sort="-x", title=None, axis=alt.Axis(labelLimit=210)),
          color=alt.Color("training_cohort:N", title="Training cohort", legend=alt.Legend(orient="bottom")),
          tooltip=["Model:N", alt.Tooltip(f"{metric}:Q", format=".4f"), "rows:Q"]).properties(height=235))
    show(data, ["Model", "training_cohort", "training_rows", "accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc",
                "training_seconds", "prediction_seconds"])
    chosen = st.selectbox("Confusion matrix and attack-family recall", data.Model.tolist(),
                          index=data.Model.tolist().index("Random Forest"))
    row = data[data.Model == chosen].iloc[0]
    left, right = st.columns([1, 2])
    with left:
        st.table(confusion(row))
    with right:
        family = table("phase4_family_recall")
        out = family[(family.protocol == protocol) & (family.split == split) & (family.model == row.model) &
                     (family.training_cohort == row.training_cohort) & (family.level == "family") & (family.binary_label == 1)]
        show(out, ["category", "evaluated_rows", "training_rows", "recall", "support_status"])
    st.caption("Blank scores represent undefined metrics. Read family recall alongside evaluation support.")
    source("phase4_metrics", "phase4_family_recall", report="reports/phase4_supervised_results.md")


def experiment_data(name, experiment):
    data = table(name)
    return data[data.experiment == experiment].copy()


def experiment_picker():
    return st.selectbox("K-Means experiment", list(EXPERIMENTS), format_func=lambda x: f"{x} · {EXPERIMENTS[x]}")


def clusters(summary):
    st.title("Clustering and pattern evolution")
    exp = experiment_picker()
    details = summary["clusters"][exp]
    trials = experiment_data("phase5_model_selection", exp)
    chosen = trials[trials.k == details["selected_k"]].iloc[0]
    metrics(("Selected clusters", count(chosen.k)), ("Fit flows", count(chosen.training_rows)),
            ("Probe silhouette", f"{chosen.silhouette:.4f}"), ("Scored flows", count(details["retained_rows"])))
    st.caption("Cluster IDs apply only within the selected fit. The silhouette uses a bounded reference probe.")
    p, o, c = st.tabs(["Profiles and families", "Occupancy and shift", "Centroids and sensitivity"])
    with p:
        profiles = experiment_data("phase5_cluster_profiles", exp)
        profiles["Benign"] = profiles.records - profiles.attacks
        mix = profiles.rename(columns={"attacks": "Attack"}).melt("cluster", ["Benign", "Attack"], var_name="Label", value_name="Flows")
        chart(alt.Chart(mix).mark_bar().encode(x="cluster:O", y="Flows:Q", color="Label:N", tooltip=["cluster:O", "Label:N", "Flows:Q"]))
        family = experiment_data("phase5_composition", exp).groupby(["cluster", "attack_family"], as_index=False)["count"].sum()
        chart(alt.Chart(family).mark_rect().encode(x="cluster:O", y=alt.Y("attack_family:N", title="Family"),
              color=alt.Color("count:Q", scale=alt.Scale(type="sqrt", scheme="teals"), title="Flows"),
              tooltip=["cluster:O", "attack_family:N", "count:Q"]))
        show(profiles, ["cluster", "records", "attack_share", "mean_duration_us", "mean_forward_packets", "mean_forward_bytes", "score_p95"])
    with o:
        occupancy = experiment_data("phase5_cluster_occupancy", exp).query("window_hour == -1")
        chart(alt.Chart(occupancy).mark_bar().encode(x=alt.X("source_day:N", title="Capture day"),
              y=alt.Y("occupancy:Q", axis=alt.Axis(format="%"), title="Occupancy"), color="cluster:N",
              tooltip=["source_day:N", "cluster:N", alt.Tooltip("occupancy:Q", format=".2%"), "records:Q"]))
        shift = experiment_data("phase5_temporal_shift", exp).query("window_hour == -1")
        chart(alt.Chart(shift).mark_line(point=True).encode(x=alt.X("source_day:N", title="Capture day"),
              y=alt.Y("js_divergence_bits:Q", title="Jensen–Shannon divergence (bits)"),
              tooltip=["source_day:N", "js_divergence_bits:Q", "rows:Q", "reference_rows:Q"]))
    with c:
        centers = experiment_data("phase5_centroids", exp)
        chart(alt.Chart(centers).mark_rect().encode(x="cluster:O", y="feature:N",
              color=alt.Color("center:Q", scale=alt.Scale(scheme="redblue", domainMid=0), title="Scaled centroid"),
              tooltip=["cluster:O", "feature:N", "center:Q"]).properties(height=345))
        metrics(("Alternative-seed ARI", f"{details['seed_ari']:.4f}"), ("Linear scaling ARI", f"{details['scale_ari']:.4f}"))
        show(trials, ["k", "silhouette", "wssse", "training_rows", "smallest_share", "empty_clusters", "selected"])
    st.info("Cluster composition and occupancy document traffic structure. Novel attacks and concept drift require separate validation.")
    source("phase5_cluster_profiles", "phase5_composition", "phase5_cluster_occupancy", "phase5_temporal_shift", "phase5_centroids",
           "phase5_model_selection", report="reports/phase5_clustering_results.md")


def novelty_rows(data, exp, rank, cutoff):
    return data[(data.experiment == exp) & (data.split_rank == rank) & (data.percentile == cutoff)]


def novelty(summary):
    st.title("Distance-based novelty")
    exp = experiment_picker()
    choices = {0: "All retrospective flows" if exp == "G" else "Reference", 1: "Validation", 2: "Held-out test"}
    a, b = st.columns(2)
    rank = a.selectbox("Population", [0] if exp == "G" else [2, 1, 0], format_func=choices.get)
    cutoff = b.selectbox("Reference percentile", [0.99, 0.95, 0.999], format_func=lambda p: f"P{p*100:g}")
    data = table("phase5_novelty_metrics")
    row = novelty_rows(data, exp, rank, cutoff)
    binary = row[row.scope == "binary"].iloc[0]
    metrics(("Squared-distance cutoff", f"{binary.threshold:.3f}"), ("Flag rate", pct(binary.flag_rate)),
            ("Benign false-positive rate", pct(binary.benign_fpr)), ("Attack recall", pct(binary.attack_recall)),
            ("Precision", pct(binary.precision)))
    st.caption(f"{count(binary['rows'])} evaluated flows · {count(binary.attacks)} attack · {count(binary['flags'])} flags. Flags use strict exceedance.")
    web = novelty_rows(data, "C", 2, 0.99).query("scope == 'binary'").iloc[0]
    st.markdown(f"**Web capture holdout at P99** · {pct(web.attack_recall)} attack recall and {pct(web.precision)} precision.")
    histogram = experiment_data("phase5_score_histogram", exp).query("split_rank == @rank")
    histogram["Label"] = histogram.binary_label.map({0: "Benign", 1: "Attack"})
    histogram["Log-distance bin start"] = histogram.score_bin / 4
    histogram["Within-label share"] = histogram["count"] / histogram.groupby("Label")["count"].transform("sum")
    chart(alt.Chart(histogram).mark_line(point=True).encode(
        x=alt.X("Log-distance bin start:Q", title="log(1 + squared distance), bin start"),
        y=alt.Y("Within-label share:Q", axis=alt.Axis(format="%")), color="Label:N",
        tooltip=["Label:N", "Log-distance bin start:Q", "count:Q", alt.Tooltip("Within-label share:Q", format=".2%")]))
    st.subheader("Family support")
    show(row[row.scope == "family"], ["family", "attacks", "flags", "attack_recall", "support_status"])
    st.info("Reference-distance flags can prioritize inspection. The held-out results do not validate a production detection decision or a comparison at matched operating points.")
    source("phase5_novelty_metrics", "phase5_score_histogram", report="docs/phase5_pattern_evolution.md")
