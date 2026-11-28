"""Integrated archived research and genuinely executable verified inference."""
from pathlib import Path
import sys,json,hashlib,math,csv,io,subprocess
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
import streamlit as st
from src.interactive import evidence,portable,inputs
from dashboard import research_style
ROOT=Path(__file__).resolve().parents[1]
DEMO_WORKSPACES = (
    'Executive overview',
    'Supervised & hybrid',
    'Interactive inference',
    'Clustering & novelty',
    'Frequent & emerging patterns',
    'Historical replay',
    'External validation & scalability',
)
FILTERS=('dataset','protocol','evaluation_protocol','scenario','sensitivity','operating','source_day','day','family','attack_family','policy','model','detector','window','support','minimum_support','workers','workload','matrix','configuration')
NOTES={
 'Supervised & hybrid':'Grouped-random, chronological and holdout protocols answer different questions. Validation budgets do not guarantee future FPR.',
 'Clustering & novelty':'Novelty is distance from a reference population, not attack probability.',
 'Multiclass & open-set':'Conditional/oracle-gated family diagnostics do not recover binary-gate misses. Zero support has undefined metrics.',
 'Frequent & emerging patterns':'Association and temporal emergence do not establish causal attack mechanisms. Support denominators and discretization remain source-specific.',
 'Streaming & drift':'Archived historical microbatch replay and separately labeled synthetic changes are not live network monitoring.',
 'Adaptive learning':'Label release and model activation are retrospective simulations. Guarded refresh can retain its incumbent.',
 'Explainable AI':'Contributions describe model behavior, not causality. Linear SHAP is log-odds interventional attribution. Direct tree SHAP remains unsupported.',
 'External validation & scalability':'Three-feature models are new reduced models, not archived18-feature transfer. Single-machine threads are not cluster nodes. Spark was slower than Pandas on the bounded measured workload.'}
@st.cache_data(show_spinner=False)
def table(entry):return evidence.load(entry)
def identify(data):return hashlib.sha256(data.to_csv(index=False).encode()).hexdigest()[:16]
def overview():
    st.header('Executive overview')
    research_style.hero()
    audit=json.loads((ROOT/'reports/phase14_14B/external_audit.json').read_text());d=json.loads((ROOT/'reports/phase14_14D/receipt.json').read_text());e=json.loads((ROOT/'reports/phase14_14E/receipt.json').read_text())
    cols=st.columns(3);cols[0].metric('Source flows',f"{d['source']['rows']:,}");cols[1].metric('External eligible flows',f"{audit['eligible_rows']:,}");cols[2].metric('Optimization measurements',e['measured_runs'])
    st.subheader('Start exploring')
    destinations=[('01 / PREDICT','Try a model','Enter flow features or upload a CSV to compute a prediction.','Interactive inference','Open inference'),('02 / EVALUATE','Compare the results','Review recall, false positives and the effect of evaluation design.','Supervised & hybrid','Explore models'),('03 / REPLAY','Follow historical traffic','Inspect archived capture batches and their detection evidence.','Historical replay','Open replay')]
    for col,(number,title,description,destination,button) in zip(st.columns(3),destinations):
        with col:
            research_style.tile(number,title,description)
            st.button(button,key='overview_'+destination,on_click=open_workspace,args=(destination,),width='stretch')
    st.warning('Historical source models generalize weakly across captures/datasets. Model scores do not guarantee maliciousness or safety.')
    st.subheader('External validation snapshot')
    st.caption('First 12 archived comparison rows. Source population and benchmark counts come from accepted Phase 14 receipts. Use External validation & scalability for the full evidence.')
    st.dataframe(pd.read_csv(ROOT/'reports/phase14_external_model_comparison.csv')[['model','evaluation_protocol','sensitivity','operating','rows','recall','fpr']].head(12),hide_index=True,width='stretch')
def research(group):
    st.header(group);st.info(NOTES.get(group,'Audit counts, original labels and capture populations retain their original evidence definitions.'))
    if group=='Dataset intelligence & SQL':
        with st.expander('Data engineering architecture and verified layers'):st.json(json.loads((ROOT/'manifests/parquet_layers.json').read_text()))
    entries=evidence.catalog()['groups'][group];entry=st.selectbox('Evidence table',entries,format_func=lambda x:x['label'],key='table_'+group)
    try:data=table(entry)
    except (OSError,ValueError) as exc:st.error('Evidence unavailable: '+str(exc));return
    for col in FILTERS:
        if col in data and data[col].map(lambda x:not isinstance(x,(dict,list,tuple,set)) and (isinstance(x,(str,int,float,bool)) or pd.isna(x))).all():
            choices=sorted(data[col].dropna().unique().tolist(),key=str)
            if 1<len(choices)<=100:
                value=st.sidebar.selectbox(col.replace('_',' ').capitalize(),['All']+choices,key=group+entry['path']+col)
                if value!='All':data=data[data[col].eq(value)]
    if data.empty:st.info('No supported evidence for this filter combination.');return
    st.caption(f"Archived evidence · {entry['path']} · SHA256 {entry['sha256'][:16]} · {len(data):,} aggregate rows")
    metrics=[x for x in ('recall','precision','fpr','pr_auc','roc_auc','median_seconds','seconds','rows','count','novelty_rate','support','confidence','lift') if x in data and pd.api.types.is_numeric_dtype(data[x])]
    if metrics:
        metric=st.selectbox('Chart metric',metrics,key='metric_'+group+entry['path']);clean=data.dropna(subset=[metric]);axis=next((x for x in ('model','source_day','day','family','policy','workers','configuration') if x in clean),None)
        if clean.empty:st.caption('Selected metric is undefined for this population.')
        elif axis:
            import altair as alt
            st.altair_chart(alt.Chart(clean.head(3000)).mark_circle().encode(x=alt.X(axis+':N'),y=alt.Y(metric+':Q',title=metric+(' (fraction)' if metric in ('recall','precision','fpr','pr_auc','roc_auc','support','confidence') else ' (seconds)' if 'seconds' in metric else '')),tooltip=[axis,metric]),width='stretch')
    st.dataframe(data,hide_index=True,width='stretch');token=identify(data);st.caption('Evidence ID: '+token)
    st.download_button('Download research CSV',data.to_csv(index=False).encode(),Path(entry['path']).stem+'.csv','text/csv',key='research_'+token,on_click='ignore')
def show_prediction(model,result,values):
    st.subheader('Computed prediction');st.metric('Predicted class',result['label']);metric='probability' if 'probability' in result else 'squared_distance';st.metric('Attack model probability' if metric=='probability' else 'Squared centroid distance',f"{result[metric]:.10g}")
    st.caption(f"Model {result['model']} · {result['source_version']} · Applied threshold {result['threshold']:.10g} · Imputed features {len(result['imputed_features'])}")
    st.warning('Uncalibrated historical model score. This prediction does not guarantee maliciousness or safety. Novelty is not attack probability.')
    if 'contributions' in result:
        contributions=result['contributions'];frame=pd.DataFrame({'feature':model['features'],'contribution':contributions});st.subheader('Exact prediction explanation');st.dataframe(frame,hide_index=True,width='stretch');st.bar_chart(frame.set_index('feature'))
        reconstruction=result.get('baseline',0.)+math.fsum(contributions);expected=result.get('logit',result.get('squared_distance'));assert math.isclose(reconstruction,expected,rel_tol=1e-8,abs_tol=1e-8)
        st.caption(f"Output space: {result['output_space']} · Baseline/intercept: {result.get('baseline',0.):.10g} · Reconstructed output: {reconstruction:.10g}")
    else:st.info('This forest has no validated local tree SHAP. Its archived native global importance is available in Explainable AI; it does not explain this specific prediction.')
    ranges=json.loads((ROOT/'reports/phase13_permutation/feature_distributions.json').read_text());bounds={r['feature']:r['quantiles'] for r in ranges if r['protocol']=='B' and r['role']=='training_reference'}
    outside=[name for name,value in values.items() if value is not None and name in bounds and not bounds[name][0]<=value<=bounds[name][-1]]
    if outside:st.warning('Outside archived source-training min/max: '+', '.join(outside)+'. Reference ranges are descriptive and do not establish deployment validity.')
def inference():
    st.header('Interactive inference')
    research_style.guide('1. Choose a model   /   2. Enter manual features or select a CSV batch   /   3. Run inference and review the result')
    registry=evidence.models();entry=st.selectbox('Executable model',registry,format_func=lambda x:x['kind']+' · '+x['id'])
    st.caption('Only archived LR,RF and K-Means are executable. Hybrid,multiclass/open-set and tree SHAP remain research-only.')
    try:model=portable.verify(ROOT/entry['artifact'],entry['sha256'])
    except (OSError,ValueError,KeyError):st.error('Model unavailable or checksum invalid. Inference is disabled; no fallback prediction.');return
    st.caption('Verified portable artifact SHA256 '+entry['sha256'][:16]+' · '+entry['source_version'])
    mode=st.radio('Input mode',['Manual features','CSV batch'])
    if mode=='Manual features':
        preset=st.selectbox('Synthetic demonstration preset',['Missing values','Zero vector','Duration/count fixture'])
        st.info('Synthetic numeric fixtures are not captured traffic and need not be physically consistent. Blank values use stored training medians. Allowed finite domain:0to1e12.')
        base={n:None if preset=='Missing values' else 0. for n in model['features']}
        if preset=='Duration/count fixture':base.update(flow_duration=1000000.,tot_fwd_pkts=10.,tot_bwd_pkts=5.)
        with st.form('manual_'+model['id']+'_'+preset):
            cols=st.columns(3);raw={}
            for i,name in enumerate(model['features']):
                unit='microseconds' if name=='flow_duration' else 'packets' if name in ('tot_fwd_pkts','tot_bwd_pkts') else 'source-registry scalar; extractor-specific'
                raw[name]=cols[i%3].text_input(name,value='' if base[name] is None else str(base[name]),help=name.replace('_',' ')+' · '+unit)
            execute=st.form_submit_button('Run inference')
        if execute:
            try:values=inputs.parse_values(raw,model['features']);show_prediction(model,portable.predict(model,values),values)
            except ValueError as exc:st.error(str(exc))
    else:
        st.caption('Exact ordered feature schema; at most1MiB and500rows. No uploads are sent to external services or used to fit preprocessing. Extra/missing/duplicate columns are rejected. Invalid rows retain their positions.')
        upload=st.file_uploader('Feature CSV',type=['csv']);st.download_button('Download synthetic CSV',(ROOT/'dashboard/data/phase15_demo.csv').read_bytes(),'phase15_demo.csv','text/csv',on_click='ignore')
        token=(model['id'],hashlib.sha256(upload.getvalue()).hexdigest()) if upload is not None else None
        if token:st.caption('Upload ID: '+token[1][:16])
        saved=st.session_state.get('phase15_batch')
        if saved and saved['token']!=token:st.session_state.pop('phase15_batch',None)
        execute=st.button('Predict CSV',disabled=upload is None)
        if upload is not None and execute:
            try:
                rows=inputs.parse_csv(upload.getvalue(),model['features']);result=inputs.batch(model,rows);st.session_state['phase15_batch']={'token':token,'result':result,'error':None}
            except ValueError as exc:st.session_state['phase15_batch']={'token':token,'result':None,'error':str(exc)}
        saved=st.session_state.get('phase15_batch')
        if saved and saved['token']==token:
            if saved['error']:st.error(saved['error'])
            else:
                result=saved['result'];data=pd.DataFrame(result);st.metric('Valid rows scored',sum(r['status']=='valid' for r in result));st.metric('Invalid rows retained',sum(r['status']=='invalid' for r in result));st.dataframe(data,hide_index=True,width='stretch');st.download_button('Download predictions',inputs.safe_csv(result),'predictions.csv','text/csv',key='predictions_'+token[1][:16]+model['id'],on_click='ignore')
                valid=[r for r in inputs.parse_csv(upload.getvalue(),model['features']) if r['status']=='valid']
                if valid:
                    selected=st.selectbox('Explain uploaded row',[r['row_number'] for r in valid]);values=next(r['values'] for r in valid if r['row_number']==selected);st.caption('Computed explanation for uploaded logical row '+str(selected));show_prediction(model,portable.predict(model,values),values)
                else:st.info('No valid uploaded row is available for explanation.')

def replay():
    st.header('Historical replay');st.info('Archived historical replay, not live network capture. Controls select existing observations; no fictional events or retraining occurs.')
    data=pd.read_csv(ROOT/'reports/phase6_replay_batches.csv');daycol=next(c for c in ('source_day','day') if c in data);days=sorted(data[daycol].unique());day=st.selectbox('Capture',days);selected=data[data[daycol]==day];position=st.slider('Replay position',0,max(1,len(selected)-1),0);row=selected.iloc[min(position,len(selected)-1)];st.dataframe(row.astype(str).to_frame('Archived microbatch'),width='stretch');st.caption('Capture flow volume: '+str(int(selected['rows'].sum())) if 'rows' in selected else 'Original microbatch fields shown above')
    batch_id=st.selectbox('Microbatch',selected.batch_id.tolist(),index=min(position,len(selected)-1),key='batch_'+str(day)+'_'+str(position));row=selected[selected.batch_id==batch_id].iloc[0]
    windows=pd.read_csv(ROOT/'reports/phase6_window_metrics.csv');window=windows[(windows.source_day==day)&(windows.window_hour==row.window_hour)&windows.scope.eq('intraday')]
    if not window.empty:
        st.subheader('Archived detection and novelty summary');w=window.iloc[0];st.dataframe(pd.DataFrame(json.loads(w.classifier_metrics)).T,width='stretch');st.json(json.loads(w.novelty_metrics));st.caption('Mean squared novelty distance: '+str(w.mean_distance))
    alerts=pd.read_csv(ROOT/'reports/phase6_alerts.csv');st.subheader('Archived alert evidence');st.dataframe(alerts[(alerts.source_day==day)&(alerts.window_hour==row.window_hour)&alerts.scope.eq('intraday')],hide_index=True,width='stretch')
    shifts=pd.read_csv(ROOT/'reports/phase6_shift_metrics.csv');st.subheader('Archived distribution changes');st.dataframe(shifts[(shifts.source_day==day)&(shifts.window_hour==row.window_hour)&shifts.scope.eq('intraday')],hide_index=True,width='stretch')
    adaptive=pd.read_csv(ROOT/'reports/phase12_prequential_metrics.csv');st.caption('Separate Phase12adaptive experiment; these model versions were not issued by the Phase6replay.');st.dataframe(adaptive[adaptive.day==day][['policy','day','model','threshold_bin','recall','fpr']],hide_index=True,width='stretch')
def provenance():
    st.header('Evidence & reproducibility')
    try:revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True,stderr=subprocess.DEVNULL).strip()
    except (OSError,subprocess.CalledProcessError):revision='Git unavailable; archived evidence checkpoint '+evidence.catalog()['source_checkpoint']
    st.caption('Application checkout '+revision);st.json(json.loads((ROOT/'manifests/phase15_models.json').read_text()))
    docs=sorted(p for p in (ROOT/'docs').glob('*.md') if 'phase' in p.name)+sorted((ROOT/'reports').glob('*results.md'))+sorted((ROOT/'reports').glob('*research_report.md'))
    doc=st.selectbox('Research document',docs,format_func=lambda p:str(p.relative_to(ROOT)));st.markdown(doc.read_text());st.download_button('Download document',doc.read_bytes(),doc.name,'text/markdown',on_click='ignore')
    figures=evidence.catalog()['figures'];entry=st.selectbox('Research figure',figures,format_func=lambda x:Path(x['path']).stem)
    p=ROOT/entry['path']
    if hashlib.sha256(p.read_bytes()).hexdigest()!=entry['sha256']:st.error('Figure checksum mismatch');return
    st.image(str(p));st.download_button('Download figure',p.read_bytes(),p.name,'image/png',on_click='ignore')
def open_workspace(destination):
    st.session_state['workspace']=destination

def main():
    st.set_page_config(page_title='MMDS Advanced Research',layout='wide')
    research_style.apply()
    research_style.sidebar_brand()
    page=st.sidebar.radio('Workspace',DEMO_WORKSPACES,key='workspace')
    st.sidebar.markdown('<div class="mmds-sidebar-note">Evidence before conclusions.<br>Historical research and verified model inference.</div>',unsafe_allow_html=True)
    research_style.page_context()
    try:
        if page=='Executive overview':overview()
        elif page=='Interactive inference':inference()
        elif page=='Historical replay':replay()
        else:research(page)
    except (OSError,ValueError,KeyError) as exc:st.error('Evidence unavailable: '+str(exc))
if __name__=='__main__':
    # Explicit navigation disables automatic discovery of the legacy pages/
    # directory. The evaluator uses only the seven workspaces above.
    st.navigation([st.Page(main,title='MMDS Advanced Research',default=True)],position='hidden').run()
