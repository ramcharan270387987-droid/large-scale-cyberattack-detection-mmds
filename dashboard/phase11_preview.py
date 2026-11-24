"""Isolated research evidence for Phase 11."""
import json
from pathlib import Path
import pandas as pd
import streamlit as st
ROOT=Path(__file__).resolve().parents[1]


def main():
 st.set_page_config(page_title='Drift Detection Laboratory',layout='wide')
 st.title('Drift Detection Laboratory')
 sections={'Synthetic experiments':'phase11_synthetic/synthetic_metrics.csv','Historical monitoring':'phase11_historical/historical_alerts.csv','Sensitivity':'phase11_robustness/sensitivity.csv','Ablations':'phase11_robustness/ablations.csv','Window costs':'phase11_historical/performance.csv'}
 section=st.radio('Evidence',list(sections),horizontal=True)
 data=pd.read_csv(ROOT/'reports'/sections[section])
 if 'detector' in data:
  detector=st.selectbox('Detector',['All']+sorted(data['detector'].unique()))
  if detector!='All':data=data[data['detector']==detector]
 if 'scenario' in data:
  scenario=st.selectbox('Synthetic scenario',['All']+sorted(data['scenario'].unique()))
  if scenario!='All':data=data[data['scenario']==scenario]
 st.dataframe(data,hide_index=True)
 st.download_button('Download filtered evidence',data.to_csv(index=False),'phase11_evidence.csv','text/csv')
 st.caption('Synthetic experiments and retrospective aggregate replay have different targets and units. Historical true drift events are unknown. Label delays are simulated. Alerts do not confirm cyberattacks.')


if __name__=='__main__':main()
