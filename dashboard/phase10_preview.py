"""Isolated explorer of verified Phase 10 aggregate evidence."""
import json
from pathlib import Path
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]


def read(relative):
    return json.loads((ROOT / 'reports' / relative).read_text())


def main():
    st.set_page_config(page_title='Emerging Attack Pattern Explorer', layout='wide')
    st.title('Emerging Attack Pattern Explorer')
    support = st.selectbox('Minimum support', [.1, .05, .02, .01], index=1)
    summary = next(r for r in read('phase10_stageB/receipt.json')['summaries'] if r['support'] == support)
    st.caption(f"16,232,943 flows · six mining features · {summary['itemsets']} itemsets · {summary['rules']} rules")
    section = st.radio('Evidence', ['Itemsets', 'Rules', 'Family contrast', 'Temporal evolution', 'Persistence', 'Detection', 'Sensitivity', 'Performance'], horizontal=True)
    if section == 'Itemsets':
        data = read(f'phase10_stageB/items_{support}.json')
    elif section == 'Rules':
        confidence = st.slider('Minimum confidence', 0., 1., .7)
        lift = st.slider('Minimum lift', 0., 10., 1.2)
        data = [r for r in read(f'phase10_stageB/rules_{support}.json') if r['confidence'] >= confidence and r['lift'] >= lift]
        st.caption('Rule exports contain at most 500 entries. Thresholds filter this recorded export.')
    elif section == 'Family contrast':
        families = read('phase10_analysis/families.json')
        family = st.selectbox('Attack family', [r['family'] for r in families])
        data = next(r['export'] for r in families if r['family'] == family)
    elif section == 'Temporal evolution':
        data = read('phase10_analysis/temporal.json')
        category = st.selectbox('Change category', ['All'] + sorted({r['category'] for r in data}))
        data = [r for r in data if category == 'All' or r['category'] == category]
    elif section == 'Persistence':
        data = read('phase10_analysis/persistence.json')
    elif section == 'Detection':
        data = [{'configuration': 'primary three bins', **read('phase10_detection/metrics.json')},
                {'configuration': 'five-bin sensitivity', **read('phase10_detection_B5/metrics.json')}]
    elif section == 'Sensitivity':
        data = read('phase10_analysis/discretization_duplicate_sensitivity.json')
    else:
        data = read('phase10_stageB/receipt.json')['summaries']
    if data:
        frame = pd.json_normalize(data)
        st.dataframe(frame, hide_index=True)
        st.download_button('Download displayed evidence', frame.to_csv(index=False), 'phase10_evidence.csv', 'text/csv')
        numeric = [c for c in frame.select_dtypes(include='number').columns if frame[c].notna().any()]
        if numeric:
            metric = st.selectbox('Chart metric', numeric)
            st.bar_chart(frame[metric].head(50))
            st.caption('Chart displays the first 50 rows of the current table.')
    else:
        st.info('No exported observations match these filters.')
    st.caption('Retrospective captures. Family and capture conditions are confounded. Frequency changes do not establish concept drift or discovery of an attack.')


if __name__ == '__main__':
    main()
