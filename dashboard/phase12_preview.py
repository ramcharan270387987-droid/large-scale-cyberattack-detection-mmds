"""Isolated aggregate-only adaptive-learning research preview."""
import json
from pathlib import Path
import pandas as pd
import streamlit as st
ROOT=Path(__file__).resolve().parents[1]
SECTIONS={
 'Static versus adaptive comparison':'phase12_policy_comparison.csv',
 'Drift and retraining eligibility':'phase12_trigger_events.csv',
 'Prediction and label availability':'phase12_prequential_metrics.csv',
 'Active model version and coverage':'phase12_version_coverage.csv',
 'Model history':'phase12_model_registry.csv',
 'Model lifecycle decisions':'phase12_model_lifecycle.csv',
 'Candidate promotion and rejection':'phase12_training_events.csv',
 'Threshold history':'phase12_threshold_history.csv',
 'Attack-family performance':'phase12_family_metrics.csv',
 'Training-window and delay comparisons':'phase12_robustness.csv',
 'Retention and forgetting':'phase12_retention.csv',
 'Synthetic benchmark':'phase12_synthetic_metrics.csv',
 'Synthetic recovery':'phase12_synthetic_recovery.csv',
 'Computational cost':'phase12_performance.csv',
 'Released-label-only diagnostics':'phase12_released_only_metrics.csv',
 'Rollback and controlled faults':'phase12_faults.csv',
}
FILTERS=('policy','model_family','delay','backend','window','day','model','family','mechanism','scope')

def load(section):
    path=ROOT/'reports'/SECTIONS[section]
    data=pd.read_csv(path) if path.exists() and path.stat().st_size else pd.DataFrame()
    if section.startswith('Synthetic') and 'backend' in data:
        data['mechanism']=data['backend'].str.split('-seed').str[0]
    return data

def select(data,column,value):return data if value=='All' else data.loc[data[column].eq(value)]

def main():
    st.set_page_config(page_title='Adaptive Learning and Model Registry',layout='wide')
    st.title('Adaptive Learning and Model Registry')
    st.caption('Retrospective research preview · historical and synthetic populations are separate · no live autonomous retraining')
    section=st.selectbox('Evidence',list(SECTIONS)+['Research limitations','Study figures'],key='evidence')
    if section=='Research limitations':
        st.markdown((ROOT/'docs/phase12_research_protocol.md').read_text())
        return
    if section=='Study figures':
        figures=sorted((ROOT/'reports/figures').glob('phase12_*.png'))
        if not figures:st.info('Verified figures are not yet available.');return
        figure=st.selectbox('Figure',figures,format_func=lambda p:p.stem.replace('phase12_','').replace('_',' '))
        st.image(str(figure));st.download_button('Download figure',figure.read_bytes(),figure.name,'image/png');return
    data=load(section)
    if data.empty:st.info('No supported observations for this evidence selection.');return
    for column in FILTERS:
        if column in data:
            values=sorted(data[column].dropna().unique().tolist())
            if values:
                value=st.sidebar.selectbox(column.replace('_',' ').capitalize(),['All']+values,key=section+column)
                data=select(data,column,value)
    if data.empty:st.info('No supported observations for this filter combination.');return
    st.caption(f'{len(data):,} aggregate evidence rows. Blank values are undefined or unsupported. Percentages in tables are proportions; chart axes identify units.')
    if section=='Drift and retraining eligibility':
        st.info('Seven historical captures cannot support KSWIN warm-up100. DDM has no genuine ordered error stream. JS alerts indicate input distribution changes, without verified historical concept-drift boundaries.')
    if section=='Rollback and controlled faults':st.warning('Controlled fault injections are separate from natural historical rollback counts.')
    numeric=[c for c in ('recall','precision','f1','fpr','pr_auc','charged_fit_seconds','training_seconds','score_seconds','new_training_rows') if c in data and pd.api.types.is_numeric_dtype(data[c])]
    if numeric:
        metric=st.selectbox('Chart metric',numeric,key=section+'metric')
        axis=next((c for c in ('day','window','policy','model','fault') if c in data),None)
        if axis:
            chart=data[[axis,metric]].dropna(subset=[metric]).copy()
            if chart.empty:st.info('Selected metric is undefined for these observations.')
            else:
                # Keep each evidence row; aggregation is deliberately disabled.
                import altair as alt
                rate=metric in ('recall','precision','f1','fpr','pr_auc')
                st.altair_chart(alt.Chart(chart).mark_circle(size=45).encode(x=alt.X(axis+':N',title=axis.replace('_',' ')),
                    y=alt.Y(metric+':Q',title=metric.replace('_',' ')+(' (proportion)' if rate else ' (seconds)' if 'seconds' in metric else ' (rows)')),
                    tooltip=list(chart.columns)),width='stretch')
    st.dataframe(data,hide_index=True,width='stretch')
    st.download_button('Download filtered CSV',data.to_csv(index=False),SECTIONS[section],'text/csv')

if __name__=='__main__':
    st.navigation([st.Page(main,title='Adaptive Learning and Model Registry')],position='hidden').run()
