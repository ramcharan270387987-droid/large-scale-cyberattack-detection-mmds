"""Isolated Phase14 laboratory over verified aggregate evidence only."""
from pathlib import Path
import hashlib,json
import pandas as pd
import streamlit as st
ROOT=Path(__file__).resolve().parents[1]
SECTIONS={
 'External dataset overview':'phase14_dataset_composition.csv',
 'Dataset provenance':'phase14_dataset_provenance.csv',
 'Feature compatibility':'phase14_feature_mapping.csv',
 'External model comparison':'phase14_external_model_comparison.csv',
 'Frozen versus target-trained':'phase14_generalization_gap.csv',
 'Source versus external generalization':'phase14_source_reference.csv',
 'External confusion matrices':'phase14_external_model_comparison.csv',
 'Attack-family performance':'phase14_external_family_metrics.csv',
 'Distribution differences':'phase14_distribution_support.csv',
 'Distribution shift indices':'phase14_distribution_shift.csv',
 'Failure analysis':'phase14_failure_analysis.csv',
 'Data-volume scaling':'phase14_scalability_summary.csv',
 'Worker scaling':'phase14_worker_scaling.csv',
 'Speedup and efficiency':'phase14_worker_scaling.csv',
 'CSV versus Parquet':'phase14_storage_comparison.csv',
 'Partitioning':'phase14_partition_comparison.csv',
 'Caching':'phase14_cache_comparison.csv',
 'Spark versus Pandas':'phase14_pandas_comparison.csv',
 'Resource consumption':'phase14_resource_usage.csv',
 'Benchmark repetitions':'phase14_scalability_runs.csv',
}
FILTERS=('dataset','evaluation_protocol','sensitivity','operating','domain','condition','matrix','workload','format','workers','partitions','cache','model_family','model','family','sample_kind','feature','metric','configuration','requested_rows','repetition','warmup','status')
LABELS={'evaluation_protocol':'Evaluation protocol','family':'Attack family','requested_rows':'Requested data size','format':'Storage format','workers':'Worker count','partitions':'Partition count','cache':'Cache configuration','sample_kind':'Case selection','matrix':'Experiment matrix'}
DEFAULTS={'evaluation_protocol':'chronological','sensitivity':'primary','operating':'validation_budget','condition':'all','workload':'analytics','workers':4,'sample_kind':'enriched_groups','warmup':False,'matrix':'Spark_Pandas_end_to_end','metric':'recall'}
METRICS=('recall','precision','f1','fpr','pr_auc','roc_auc','median_seconds','seconds','rows_per_second','speedup','efficiency','mean_score','js_bits','psi_natural','outside_source_range','rows','median','interquartile_range','bytes','read_checksum_seconds','query_seconds','tree_rss_sampled_peak','jvm_rss_sampled_peak','python_rss_sampled_peak','cpu_percent_one_core_basis','target_minus_source','source_value','target_trained_value')
RATES={'recall','precision','f1','fpr','pr_auc','roc_auc','efficiency','mean_score'}
def load(section):
    path=ROOT/'reports'/SECTIONS[section]
    return pd.read_csv(path) if path.exists() else pd.DataFrame()
def select(data,column,value):return data if value=='All' else data.loc[data[column].eq(value)]
def default(section,column,choices):
    value=DEFAULTS.get(column,'All')
    if column=='workers' and section in ('Worker scaling','Speedup and efficiency','Spark versus Pandas'):value='All'
    if column=='dataset' and section=='External dataset overview':value='CICIDS2017 mirror'
    if column=='model' and section=='Failure analysis':value='E2-B-common-LR'
    return value if value in choices else 'All'
def csv_bytes(data):return data.to_csv(index=False,lineterminator='\n').encode('utf-8')
def evidence_id(data):return hashlib.sha256(csv_bytes(data)).hexdigest()[:16]
def chart(data,section):
    available=[m for m in METRICS if m in data]
    if not available:st.caption('This categorical evidence is shown in the table.');return
    preferred='speedup' if section=='Speedup and efficiency' else 'target_minus_source' if section=='Frozen versus target-trained' else available[0]
    metric=st.selectbox('Chart metric',available,index=available.index(preferred) if preferred in available else 0,key=section+'chart_metric');valid=data.copy()
    if 'status' in valid:valid=valid.loc[valid.status.eq('PASS')]
    valid['_value']=pd.to_numeric(valid[metric],errors='coerce');valid=valid.dropna(subset=['_value'])
    if valid.empty:st.caption('Selected metric is undefined or unsupported for these observations.');return
    unit='fraction' if metric in RATES else 'seconds' if metric.endswith('seconds') else 'flows / second' if metric=='rows_per_second' else 'bytes' if metric=='bytes' or metric.endswith('_sampled_peak') else 'bits' if metric=='js_bits' else 'natural-log PSI' if metric=='psi_natural' else 'T(1) / T(p)' if metric=='speedup' else '% of one CPU core' if metric=='cpu_percent_one_core_basis' else 'flows' if metric in ('rows','outside_source_range') else metric.replace('_',' ')
    if metric.endswith('_sampled_peak') or metric=='bytes':valid['_value']/=1024**2;unit='MiB'
    if metric in ('source_value','target_trained_value','target_minus_source') and 'metric' in valid:
        if valid.metric.nunique()>1:st.info('Select one evaluation metric to chart compatible units.');return
        base=valid.metric.iloc[0];unit='fraction' if base in RATES else 'flows' if base=='missed_attacks' else 'false alarms / million benign'
    if metric in ('median','interquartile_range') and 'feature' in valid:
        features=valid.feature.dropna().unique()
        if len(features)>1:st.info('Select one feature to display a magnitude chart with a common unit.');return
        unit='microseconds' if features[0]=='flow_duration' else 'packets'
    preferred_axis={'Worker scaling':'workers','Speedup and efficiency':'workers','CSV versus Parquet':'format','Partitioning':'configuration','Caching':'configuration','Benchmark repetitions':'repetition'}.get(section)
    axis=preferred_axis if preferred_axis in valid else next((c for c in ('actual_rows','workers','model','feature','configuration','family','class_name','dataset','repetition') if c in valid),None)
    if axis is None:st.caption('No supported chart axis in this selection.');return
    contexts=[c for c in ('dataset','evaluation_protocol','sensitivity','operating','model','domain','condition','workload','matrix','configuration','format','workers','partitions','cache','sample_kind') if c in valid and c!=axis]
    valid['_context']=valid[contexts].fillna('N/A').astype(str).agg(' · '.join,axis=1) if contexts else 'Selected evidence'
    import altair as alt
    xtype='Q' if axis in ('actual_rows','workers','repetition') else 'N'
    figure=alt.Chart(valid).mark_circle(size=60).encode(x=alt.X(axis+':'+xtype,title=axis.replace('_',' ')),y=alt.Y('_value:Q',title=metric.replace('_',' ')+' ('+unit+')'),color=alt.Color('_context:N',title='Context',legend=alt.Legend(orient='bottom',labelLimit=80)),tooltip=[*dict.fromkeys([axis,*contexts,*[c for c in ('repetition','warmup','actual_rows','rows','status') if c in valid]]),alt.Tooltip('_value:Q',title=metric+' ('+unit+')')])
    st.altair_chart(figure,width='stretch')
def main():
    st.set_page_config(page_title='External Validation and Scalability Laboratory',layout='wide')
    st.title('External Validation and Scalability Laboratory');st.caption('Phase14 · archived research evidence · conditional common-feature transfer · single-machine Kaggle CPU')
    section=st.selectbox('Evidence',list(SECTIONS)+['Research limitations','Study figures'])
    if section=='Research limitations':st.markdown((ROOT/'docs/phase14_limitations.md').read_text());return
    if section=='Study figures':
        files=sorted((ROOT/'reports/figures').glob('phase14_*.png'))
        if not files:st.info('Verified figures are not available yet.');return
        figure=st.selectbox('Figure',files,format_func=lambda p:p.stem.removeprefix('phase14_').replace('_',' '));st.image(str(figure));format=st.selectbox('Download format',['PNG','SVG']);path=figure.with_suffix('.'+format.lower());st.download_button('Download figure',path.read_bytes(),path.name,'image/png' if format=='PNG' else 'image/svg+xml',on_click='ignore');return
    data=load(section)
    if data.empty:st.info('No supported evidence rows are available for this section.');return
    for column in FILTERS:
        if column not in data:continue
        choices=sorted(data[column].dropna().unique().tolist())
        if not choices:continue
        options=['All']+choices;value=st.sidebar.selectbox(LABELS.get(column,column.replace('_',' ').capitalize()),options,index=options.index(default(section,column,choices)),key=section+column);data=select(data,column,value)
    if data.empty:st.info('No supported evidence rows match this filter combination.');return
    st.caption(f'Evidence ID: {evidence_id(data)} · Rows: {len(data)}')
    st.caption('CSV preserves raw fractions and bytes. Blank metrics mean undefined or unsupported. Chart contexts remain separate.')
    if 'status' in data and data.status.ne('PASS').any():st.warning('Failed or resource-limited configurations remain in the table and download; performance charts use successful runs.')
    if 'support_status' in data and data.support_status.str.startswith('absent').any():st.info('Some selected families have zero evaluation support; their performance metrics are undefined.')
    if section in ('External model comparison','Frozen versus target-trained','External confusion matrices'):st.info('Common3 uses newly source-trained E2 and target-trained E3 models. Exact archived18-feature external transfer is unsupported. Validation FPR budgets do not guarantee future FPR.')
    if section=='Failure analysis':st.info('Distinct-group representative and enriched diagnostic samples; enrichment is not prevalence. Values for strata with fewer than5cases are suppressed.')
    if section in ('Worker scaling','Speedup and efficiency'):st.info('local[1],local[2],local[4] are threads on one machine. Speedup=T(1)/T(p); efficiency=speedup/p. SparkContexts share their notebook JVM.')
    if section in ('CSV versus Parquet','Caching','Spark versus Pandas','Data-volume scaling'):st.info('OS filesystem cache is uncontrolled. Materialization, repeated computation and startup have separate timing scopes.')
    if section=='Resource consumption':st.info('Memory is sampled every0.2seconds. JVM RSS,Python RSS and process-tree RSS are distinct; configured heap is not measured RSS. CPU utilization uses one-core=100%.')
    if section=='External confusion matrices':
        values=list(data.index);chosen=st.selectbox('Matrix context',values,format_func=lambda i:f"{data.loc[i,'model']} · {data.loc[i,'evaluation_protocol']} · {data.loc[i,'operating']} · {data.loc[i,'sensitivity']}");row=data.loc[chosen];st.table(pd.DataFrame([[int(row.tn),int(row.fp)],[int(row.fn),int(row.tp)]],index=['Actual benign','Actual attack'],columns=['Predicted benign','Predicted attack']));st.caption(f'Confusion population: {int(row.rows):,} retained flows')
    else:chart(data,section)
    st.dataframe(data,hide_index=True,width='stretch');st.download_button('Download filtered CSV',csv_bytes(data),SECTIONS[section],'text/csv',on_click='ignore')
    if section=='Caching':
        path=ROOT/'reports/phase14_cache_break_even.csv'
        if path.exists():
            with st.expander('Cache break-even calculation'):st.dataframe(pd.read_csv(path),hide_index=True)
if __name__=='__main__':st.navigation([st.Page(main,title='External Validation and Scalability Laboratory')],position='hidden').run()
