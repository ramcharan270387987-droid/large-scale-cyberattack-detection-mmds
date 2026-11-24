"""Isolated Phase 10 evidence explorer."""
import json
from pathlib import Path
import pandas as pd
import streamlit as st

ROOT=Path(__file__).resolve().parents[1]

def main():
 st.set_page_config(page_title='Frequent and Emerging Attack Patterns',layout='wide')
 st.title('Frequent and Emerging Attack Patterns')
 support=st.selectbox('Minimum support',[.1,.05,.02,.01],index=1)
 base=ROOT/'reports/phase10_stageB'
 items=json.loads((base/f'items_{support}.json').read_text())
 rules=json.loads((base/f'rules_{support}.json').read_text())
 receipt=json.loads((base/'receipt.json').read_text())
 summary=next(r for r in receipt['summaries'] if r['support']==support)
 st.caption(f"16,232,943 flows · six mining features · {summary['itemsets']} total itemsets · {summary['rules']} total rules")
 st.caption('Tables contain at most 500 exported entries in the recorded selection order.')
 section=st.radio('Evidence',['Itemsets','Rules','Families','Temporal patterns','Detection'],horizontal=True)
 if section=='Itemsets':st.dataframe(pd.DataFrame(items),hide_index=True)
 elif section=='Rules':
  confidence=st.slider('Minimum confidence',0.,1.,.7)
  lift=st.slider('Minimum lift',0.,10.,1.2)
  st.dataframe(pd.DataFrame([r for r in rules if r['confidence']>=confidence and r['lift']>=lift]),hide_index=True)
 else:
  paths={'Families':'phase10_analysis/families.json','Temporal patterns':'phase10_analysis/temporal.json','Detection':'phase10_detection/metrics.json'}
  path=ROOT/'reports'/paths[section]
  if path.exists():
   data=json.loads(path.read_text())
   if section=='Families':
    family=st.selectbox('Attack family',[r['family'] for r in data]);data=next(r['export'] for r in data if r['family']==family)
   if isinstance(data,list):st.dataframe(pd.DataFrame(data),hide_index=True)
   else:st.json(data)
  else:st.info('Validated evidence for this analysis is pending.')
 st.caption('Retrospective capture data. Family and capture conditions are confounded. Pattern prevalence changes do not establish concept drift or a new attack.')

if __name__=='__main__':main()
