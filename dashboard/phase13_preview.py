"""Isolated retrospective explainability laboratory using verified aggregates."""
import json
from pathlib import Path
import pandas as pd
import streamlit as st
ROOT=Path(__file__).resolve().parents[1]
SECTIONS={
 'Global feature importance':'phase13_global_importance.csv',
 'Local synthetic explanation':'phase13_synthetic_local.csv',
 'False-positive and false-negative cases':'phase13_enriched_cases.csv',
 'Family and capture contributions':'phase13_case_contributions.csv',
 'Permutation importance':'phase13_permutation_summary.csv',
 'Chronological feature distributions':'phase13_feature_distributions.csv',
 'Reference-bin distribution shift':'phase13_distribution_shift.csv',
 'K-Means novelty decomposition':'phase13_novelty.csv',
 'Hybrid decision explanation':'phase13_hybrid.csv',
 'Open-set family explanation':'phase13_family_rejection.csv',
 'Adaptive coefficient comparison':'phase13_adaptive_coefficients.csv',
 'Adaptive matched probes':'phase13_adaptive_probes.csv',
 'Explanation stability':'phase13_stability.csv',
 'Ranking agreement':'phase13_rank_agreement.csv',
 'Computational cost':'phase13_cost.csv',
}
FILTERS=('model','protocol','day','family','outcome','method','scope','metric','probe','policies','feature')
LABELS={'day':'Capture day','family':'Attack family','probe':'Synthetic probe'}
def load(section):
    path=ROOT/'reports'/SECTIONS[section]
    return pd.read_csv(path) if path.exists() else pd.DataFrame()
def select(data,column,value):return data if value=='All' else data.loc[data[column].eq(value)]
def main():
    st.set_page_config(page_title='Explainability Research Laboratory',layout='wide')
    st.title('Explainability Research Laboratory')
    st.caption('Phase13 · archived retrospective evidence · bounded explanation samples · attribution describes model behavior and association')
    section=st.selectbox('Evidence',list(SECTIONS)+['Scientific limitations','Study figures'])
    if section=='Scientific limitations':st.markdown((ROOT/'docs/phase13_limitations.md').read_text());return
    if section=='Study figures':
        figures=sorted((ROOT/'reports/figures').glob('phase13_*.png'))
        if not figures:st.info('Verified figures are not yet available.');return
        figure=st.selectbox('Figure',figures,format_func=lambda p:p.stem.replace('phase13_','').replace('_',' '));st.image(str(figure));st.download_button('Download figure',figure.read_bytes(),figure.name,'image/png');return
    data=load(section)
    if data.empty:st.info('No supported observations for this evidence selection.');return
    for column in FILTERS:
        if column in data:
            choices=sorted(data[column].dropna().unique().tolist())
            if choices:
                value=st.sidebar.selectbox(LABELS.get(column,column.replace('_',' ').capitalize()),['All']+choices,key=section+column)
                data=select(data,column,value)
    if data.empty:st.info('No supported observations for this filter combination.');return
    st.caption(f'{len(data):,} aggregate evidence rows. Blank values mean undefined or unsupported; displayed scores are proportions unless units are stated.')
    if section=='Local synthetic explanation':st.info('Fixed synthetic probe scored by an archived pipeline. Contributions add to its intercept in log-odds. This display is an archived explanation.')
    if section=='Open-set family explanation':st.info('Conditional family-stage evidence. A has no archived rejection policy; earlier binary-gate misses remain misses. Zero known-family support has undefined closed-set recall.')
    if section=='False-positive and false-negative cases':st.info('At most8 selected cases per capture/family/outcome. Full eligible denominators are separate; enriched cases do not estimate prevalence.')
    if section=='Explanation stability':st.info('Descriptive seed, background, sample-size, weighting and capture-deletion sensitivity; these are not independent-flow confidence intervals.')
    numeric=[c for c in ('contribution','value','mean','mean_absolute','mean_contribution','js_bits','mean_squared_contribution','rows','mean_paired_score_change','raw_unit_coefficient','spearman','seconds') if c in data]
    if numeric:
        metric=st.selectbox('Chart metric',numeric,key=section+'metric');axis=next((c for c in ('feature','day','model','protocol','stage','comparison') if c in data),None)
        if axis:
            chart=data[[axis,metric]].dropna(subset=[metric])
            if chart.empty:st.caption('Selected metric is undefined for these observations.')
            else:
                import altair as alt
                st.altair_chart(alt.Chart(chart).mark_circle(size=42).encode(x=alt.X(axis+':N',title=axis.replace('_',' ')),y=alt.Y(metric+':Q',title=metric.replace('_',' ')),tooltip=list(chart.columns)),width='stretch')
    st.dataframe(data,hide_index=True,width='stretch');st.download_button('Download filtered CSV',data.to_csv(index=False),SECTIONS[section],'text/csv')
if __name__=='__main__':st.navigation([st.Page(main,title='Explainability Research Laboratory')],position='hidden').run()
