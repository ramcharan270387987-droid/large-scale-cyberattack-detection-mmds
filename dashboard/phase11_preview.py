"""Isolated Phase 11 laboratory over validated aggregate research evidence."""
import json
from pathlib import Path
import pandas as pd
import streamlit as st
from src.drift.signal_registry import historical_availability

ROOT=Path(__file__).resolve().parents[1]
SECTIONS={
 'Primary synthetic results':'phase11_synthetic/synthetic_metrics.csv',
 'Detector comparison':'phase11_finalization/detector_comparison.csv',
 'Historical alert timeline':'phase11_historical/historical_alerts.csv',
 'Reference and warm-up':'phase11_finalization/reference.csv',
 'Reset policies':'phase11_finalization/reset.csv',
 'Missing inputs':'phase11_finalization/missing.csv',
 'Support thresholds':'phase11_finalization/support.csv',
 'Native support and label clocks':'phase11_finalization/native_support.csv',
 'Detector agreement':'phase11_finalization/agreement.csv',
 'Episode agreement':'phase11_finalization/episode_agreement.csv',
 'Performance associations':'phase11_finalization/association.csv',
 'Before and after alerts':'phase11_finalization/before_after.csv',
 'Ensemble and controls':'phase11_robustness/ablations.csv',
 'Window and magnitude sensitivity':'phase11_robustness/sensitivity.csv',
 'Label-delay effects':'phase11_synthetic/synthetic_metrics.csv',
 'Compute and state costs':'phase11_finalization/costs.csv',
 'Recovery and duplicate costs':'phase11_finalization/engineering_costs.csv',
 'Distribution reference costs':'phase11_finalization/distribution_state_costs.csv',
 'Historical window costs':'phase11_historical/performance.csv',
}
FILTERS=('population','detector','first','second','scenario','seed','profile','policy','signal','performance_metric','metric','lag_windows','label_delay_windows','label_delay','minimum_support','warmup','reference_length','window','magnitude')


def load(section):
    data=pd.read_csv(ROOT/'reports'/SECTIONS[section])
    if section=='Primary synthetic results':
        data['state_bytes']=data['state_bytes'].astype('Int64')
        data.loc[data['detector'].isin(['JS','PSI','FixedJS']),'state_bytes']=pd.NA
    if section=='Label-delay effects':data=data[data['detector'].eq('DDM')]
    if section=='Historical alert timeline':
        registry=json.loads((ROOT/'manifests/phase11_detectors.json').read_text())
        warmup={r['identifier']:r['warmup_observations'] for r in registry['detectors'] if r['identifier'] in ('ADWIN','PageHinkley','KSWIN','DDM')}
        data=pd.DataFrame(historical_availability(data.to_dict('records'),warmup))
        data['alert']=data['alert'].astype('boolean')
    return data


def select(data,column,value):
    return data if value=='All' else data.loc[data[column].eq(value)]


def main():
    st.set_page_config(page_title='Drift Detection Laboratory',layout='wide')
    st.title('Drift Detection Laboratory')
    st.caption('Controlled synthetic experiments and retrospective aggregate replay use different targets and units. Historical true drift boundaries are unknown.')
    section=st.selectbox('Evidence',list(SECTIONS)+['Detector limitations','Study figures'],key='evidence')
    if section=='Detector limitations':
        registry=json.loads((ROOT/'manifests/phase11_detectors.json').read_text())
        data=pd.json_normalize(registry['detectors'])
        detector=st.selectbox('Detector',['All']+data['identifier'].tolist(),key='registry_detector')
        data=select(data,'identifier',detector)
        data=data.astype(object).where(data.notna(),'NA').map(lambda value:json.dumps(value) if isinstance(value,(list,dict)) else str(value))
        st.dataframe(data,hide_index=True)
        st.download_button('Download complete detector registry',json.dumps(registry,indent=2),'phase11_detectors.json','application/json')
        return
    if section=='Study figures':
        figures=sorted((ROOT/'reports/figures').glob('phase11_*.png'))
        figure=st.selectbox('Figure',figures,format_func=lambda p:p.stem.removeprefix('phase11_').replace('_',' '))
        st.image(str(figure))
        st.download_button('Download figure',figure.read_bytes(),figure.name,'image/png')
        return
    data=load(section)
    for column in FILTERS:
        if column in data:
            values=sorted(data[column].dropna().unique().tolist())
            if not values:continue
            label=column.capitalize()+' detector' if column in ('first','second') else column.replace('_',' ').capitalize()
            value=st.sidebar.selectbox(label,['All']+values,key=section+column)
            data=select(data,column,value)
    st.caption('Unavailable values remain blank. Suppressed windows and insufficient warm-up are excluded from efficacy and agreement denominators.')
    if data.empty:
        st.info('No observations match these filters.')
        return
    if 'available' in data and not data['available'].any():
        st.info('This historical combination has insufficient warm-up or support. Its provenance remains visible and its alerts are unavailable.')
    st.dataframe(data,hide_index=True)
    st.download_button('Download filtered evidence',data.to_csv(index=False),'phase11_evidence.csv','text/csv')
    identifiers={'seed','batch','source_batch','update_batch','label_release_batch','label_source_batch','label_delay_windows','minimum_support','warmup','reference_length'}
    numeric=[c for c in data.select_dtypes(include='number') if data[c].notna().any() and c not in identifiers]
    if numeric:
        preferred=('mean_delay_observations','recall','false_per_1000','value','pearson','state_bytes','seconds','misses')
        numeric=[c for c in preferred if c in numeric]+[c for c in numeric if c not in preferred]
        metric=st.selectbox('Chart metric',numeric,key=section+'chart')
        st.bar_chart(data[[metric]].head(100))
        st.caption('Chart shows the selected recorded metric for the first 100 filtered table rows. Consult the table for population, support and units.')
    st.caption('Label delays are simulated. Alerts do not confirm cyberattacks. Historical DDM lacks ordered binary errors, and historical KSWIN cannot meet its frozen 100-window warm-up. Phase 12 requires separate authorization.')


if __name__=='__main__':
    st.navigation([st.Page(main,title='Drift Detection Laboratory')],position='hidden').run()
