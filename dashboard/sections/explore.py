"""Overview and Phase 3 data views."""

from math import log10
import json

import pandas as pd

import altair as alt
import streamlit as st

from dashboard.components.ui import chart, count, metrics, pct, selector, show, source
from dashboard.data_loader import table


FEATURE_UNITS = {
    "flow_duration": "µs", "flow_iat_mean": "µs", "flow_byts_s": "bytes/s", "flow_pkts_s": "packets/s",
    "pkt_len_mean": "bytes", "total_bytes": "bytes", "total_packets": "packets",
    "tot_fwd_pkts": "packets", "tot_bwd_pkts": "packets",
}


def display_statistics(stats, feature):
    subset = stats[stats.feature == feature].drop(columns="quantiles")
    st.caption(f"Distribution units · {FEATURE_UNITS.get(feature, 'source feature units')}. P10–P99 are approximate.")
    quantiles = pd.DataFrame(stats.loc[subset.index, "quantiles"].map(json.loads).tolist(), index=subset.index,
                             columns=["P10", "P50", "P90", "P99"])
    show(subset.join(quantiles))


def overview(summary):
    d, r = summary["dataset"], summary["replay"]
    totals = d["totals"]
    families = table("phase3_attack_families")
    model = table("phase4_metrics").query("model == 'random_forest' and split == 'test' and training_cohort == 'group_sample'").copy()
    model["Evaluation"] = model["protocol"].map({"A": "Grouped random", "B": "Chronological", "C": "Web holdout"})
    model["Test attack prevalence"] = (model.tp + model.fn) / model.rows
    st.markdown("""<section class="mmds-hero"><div class="mmds-context">MMDS RESEARCH DASHBOARD</div>
<h1>Large-Scale Cyberattack Detection</h1><p>Explore how traffic patterns and detection performance change across historical captures.</p></section>""",
                unsafe_allow_html=True)
    metrics(("Recorded flows", count(totals["canonical_rows"])), ("Benign flows", count(totals["benign"])),
            ("Attack flows", count(totals["attack"])))
    st.caption(f"{len(d['days'])} capture days · {families.attack_family.nunique()} supported attack families · Verified Parquet evidence")
    random, later = (model.set_index("protocol").loc[c] for c in "AB")
    st.markdown(f"""<div class="mmds-finding"><strong>Generalization gap.</strong> Random Forest recall fell from
{pct(random.recall)} on grouped-random traffic to {pct(later.recall)} on later captures at the frozen score threshold.</div>""", unsafe_allow_html=True)
    st.subheader("Random Forest across evaluation cohorts")
    st.caption("Test cohorts differ in attack prevalence. Recall uses the fixed threshold. PR-AUC uses ranked scores.")
    names = model["Evaluation"].tolist()
    chart(alt.Chart(model).mark_bar(cornerRadiusEnd=5, color="#58e0c1").encode(
        x=alt.X("recall:Q", axis=alt.Axis(format="%"), scale=alt.Scale(domain=[0, 1]), title="Attack recall"),
        y=alt.Y("Evaluation:N", sort=names, title=None),
        tooltip=["Evaluation:N", alt.Tooltip("recall:Q", format=".2%"), alt.Tooltip("pr_auc:Q", format=".4f"),
                 alt.Tooltip("Test attack prevalence:Q", format=".2%"), "rows:Q"]).properties(height=177))
    st.subheader("Historical replay at a glance")
    metrics(("Replayed flows", count(r["rows"])), ("Microbatches", count(r["batches"])),
            ("Throughput", f"{r['rows_per_second']:,.0f} flows/s"), ("Alert records", count(r["alerts"]["count"])))
    st.caption("Academic retrospective evaluation for faculty review. Production intrusion detection requires separate validation.")
    st.markdown("**Completed research stages** · Environment validation, data audit, Parquet engineering, Spark SQL, supervised learning, clustering, and historical streaming replay.")
    source("phase3_daily_traffic", "phase3_attack_families", "phase4_metrics", "phase6_performance", "phase6_alerts")


def explorer(summary):
    st.title("Dataset explorer")
    st.caption(f"Canonical flows from the verified Parquet snapshot · {summary['dataset']['policy']}")
    daily = table("phase3_daily_traffic")
    family = table("phase3_attack_families")
    labels = table("phase3_original_labels")
    left, middle, right = st.columns(3)
    day = left.selectbox("Capture day", ["All days", *summary["dataset"]["days"]])
    attack = middle.selectbox("Attack family", ["All families", *sorted(family.attack_family.unique())])
    subset = labels if attack == "All families" else labels[labels.attack_family == attack]
    label = right.selectbox("Original label", ["All labels", *sorted(subset.original_label.unique())])
    daily = daily if day == "All days" else daily[daily.source_day == day]
    metrics(("Flows in capture selection", count(daily.records.sum())), ("Benign", count(daily.benign.sum())),
            ("Attack", count(daily.attacks.sum())))
    volume = daily.melt("source_day", ["benign", "attacks"], var_name="Label", value_name="Flows")
    chart(alt.Chart(volume).mark_bar().encode(x=alt.X("source_day:N", title="Capture day"), y="Flows:Q", color="Label:N",
          tooltip=["source_day:N", "Label:N", alt.Tooltip("Flows:Q", format=",")]).properties(height=245))
    a, b, c = st.tabs(["Families and labels", "Protocols and ports", "Feature quality"])
    with a:
        by_day = table("phase3_family_by_day")
        if day != "All days":
            by_day = by_day[by_day.source_day == day]
        if attack != "All families":
            by_day = by_day[by_day.attack_family == attack]
        if not by_day.records.sum():
            st.info("The selected family has no recorded flows on this capture day.")
        else:
            chart(alt.Chart(by_day).mark_bar().encode(
                x=alt.X("records:Q", title="Flows"), y=alt.Y("attack_family:N", title="Attack family"),
                color=alt.Color("source_day:N", title="Capture day"),
                tooltip=["source_day:N", "attack_family:N", "records:Q"]).properties(height=230))
        st.caption("Original-label evidence is aggregated across its recorded capture days.")
        show(subset if label == "All labels" else subset[subset.original_label == label])
    with b:
        for name, title, columns in (("protocols", "Protocol composition", ["population", "attack_family", "protocol", "records"]),
                                      ("destination_ports", "Ranked destination ports", ["population", "scope", "attack_family", "dst_port",
                                                                                         "records", "population_records", "rank"])):
            st.subheader(title)
            data = table("phase3_" + name)
            if attack != "All families":
                data = data[data.attack_family == attack]
            field = "protocol" if name == "protocols" else "dst_port"
            data = data.assign(**{field: data[field].astype("Int64")})
            selected = selector("Protocol code" if field == "protocol" else "Destination port", data, field,
                                all_label="Show all")
            if selected != "Show all":
                data = data[data[field] == selected]
            st.caption("Study-wide aggregate for the selected family. Counts are flows. Port and protocol values are source codes.")
            show(data, columns)
    with c:
        stats = table("phase3_feature_statistics")
        missingness = table("phase3_feature_missingness")
        feature = st.selectbox("Numerical feature", sorted(set(stats.feature) | set(missingness.feature)))
        if feature in set(stats.feature):
            display_statistics(stats, feature)
        else:
            st.info("Phase 3 published missingness for this feature. Distribution summaries are available for selected features.")
        missing = missingness[missingness.feature == feature].copy()
        missing["Missing rate"] = missing.missing / missing.records
        show(missing)
        st.subheader("Duplicate and quality audit")
        show(table("phase3_duplicate_quality"))
    source("phase3_daily_traffic", "phase3_family_by_day", "phase3_original_labels", "phase3_protocols", "phase3_destination_ports",
           "phase3_feature_statistics", "phase3_feature_missingness", "phase3_duplicate_quality")


def analytics(summary):
    st.title("Spark SQL analytics")
    daily = table("phase3_daily_traffic")
    family = table("phase3_family_by_day")
    a, b = st.columns(2)
    with a:
        st.subheader("Attack prevalence by day")
        chart(alt.Chart(daily).mark_line(point=True, strokeWidth=3).encode(
            x=alt.X("source_day:N", title="Capture day"),
            y=alt.Y("attack_share:Q", axis=alt.Axis(format="%"), title="Attack share"),
            tooltip=["source_day:N", "attacks:Q", "records:Q", alt.Tooltip("attack_share:Q", format=".2%")]))
    with b:
        st.subheader("Family support")
        family = family.assign(log_flows=family.records.map(lambda v: log10(max(v, 1))))
        chart(alt.Chart(family).mark_rect().encode(x=alt.X("source_day:N", title="Capture day"),
              y=alt.Y("attack_family:N", title="Attack family"), color=alt.Color("log_flows:Q", title="Log₁₀ flows", scale=alt.Scale(scheme="teals")),
              tooltip=["source_day:N", "attack_family:N", "records:Q"]))
    stat = table("phase3_feature_statistics")
    feature = st.selectbox("Flow statistic", ["flow_duration", "total_packets", "total_bytes"],
                           format_func={"flow_duration": "Flow duration (µs)", "total_packets": "Packet count", "total_bytes": "Byte volume"}.get)
    display_statistics(stat, feature)
    left, right = st.columns(2)
    with left:
        st.subheader("Feature correlations")
        st.caption("Pearson coefficient and pairwise valid flow counts.")
        show(table("phase3_correlations"))
    with right:
        st.subheader("SQL and DataFrame runtime")
        runtime = table("phase3_query_performance")
        work = selector("Workload", runtime, "workload")
        show(runtime[runtime.workload == work])
        r = summary["sql"]["resources"]
        st.caption(f"Spark {r['spark_version']} · {r['master']} · {r['driver_memory']} driver heap · seconds per run.")
    st.info("These descriptive differences summarize the capture collection. Detection mechanisms and concept drift require additional evidence.")
    source("phase3_daily_traffic", "phase3_family_by_day", "phase3_feature_statistics", "phase3_correlations",
           "phase3_query_performance", report="reports/phase3_analytics.md")
