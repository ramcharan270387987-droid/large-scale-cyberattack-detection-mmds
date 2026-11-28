"""Forest-green and ivory presentation for the evaluator dashboard."""
import streamlit as st


def apply():
    st.markdown('''
<style>
.stApp { background: #f6f7f3; color: #18372f; }
[data-testid="stHeader"] { background: #f6f7f3; }
[data-testid="stMainBlockContainer"] { max-width: 1440px; padding: 2.5rem 3.5rem 4rem; }
h1, h2, h3 { color: #18372f; letter-spacing: -.035em; font-weight: 650; }
h2 { font-size: clamp(1.8rem, 3vw, 2.8rem); margin-top: .5rem; }
p, label { line-height: 1.65; }
[data-testid="stCaptionContainer"] { color: #63766d; }
[data-testid="stSidebar"] { background: #152f28; border-right: 1px solid #29473c; }
[data-testid="stSidebar"] [data-testid="stSidebarContent"] { padding: 2rem 1.1rem; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] { color: #dbe6db; }
[data-testid="stSidebar"] [data-testid="stRadio"] > label { color: #a8beb0; letter-spacing: .16em; text-transform: uppercase; font-size: .72rem; }
[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] { gap: .35rem; }
[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] > label {
    border: 1px solid transparent; border-radius: 10px; padding: .65rem .8rem;
    width: 100%; margin: 0; transition: background .15s; color: #dbe6db;
}
[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] > label:hover { background: #25463a; }
[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) { background: #305344; border-color: #416552; }
[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] > label p { font-size: .95rem; line-height: 1.4; }
[data-testid="stMetric"] { background: #ffffff; border: 1px solid #dce4db; border-radius: 16px; padding: 1.2rem 1.35rem; }
[data-testid="stMetricLabel"] { color: #64776b; }
[data-testid="stMetricValue"] { color: #18372f; font-size: clamp(1.7rem, 2.6vw, 2.7rem); font-variant-numeric: tabular-nums; letter-spacing: -.04em; }
[data-testid="stDataFrame"], [data-testid="stForm"], [data-testid="stExpander"] { border: 1px solid #dce4db; border-radius: 14px; overflow: hidden; }
[data-testid="stForm"] { background: white; padding: 1.4rem; }
[data-testid="stFileUploaderDropzone"] { background: #ffffff; border: 1px dashed #98af91; border-radius: 14px; }
[data-testid="stButton"] button, [data-testid="stDownloadButton"] button, [data-testid="stFormSubmitButton"] button { border-radius: 10px; min-height: 2.8rem; font-weight: 600; }
[data-testid="stAlert"] { border-radius: 12px; }
.mmds-brand { display: flex; gap: .85rem; align-items: center; margin: .5rem 0 2.6rem; }
.mmds-emblem { display: grid; place-items: center; width: 48px; height: 48px; border-radius: 14px; background: #305344; border: 1px solid #4f6a54; color: #d5e3c9; font-size: 1.6rem; }
.mmds-brand-name { font-size: 1.5rem; color: #edf2e8; font-weight: 650; letter-spacing: -.04em; }
.mmds-brand-subtitle { font-size: .66rem; letter-spacing: .15em; color: #a8beb0; margin-top: .15rem; }
.mmds-topline { display: flex; justify-content: space-between; gap: 1rem; padding-bottom: 1.1rem; margin-bottom: 1.8rem; border-bottom: 1px solid #dce4db; color: #64776b; font-size: .88rem; }
.mmds-status { color: #42674d; white-space: nowrap; }
.mmds-eyebrow { font-size: .7rem; color: #64776b; letter-spacing: .16em; font-weight: 600; margin: 0 0 .6rem; }
.mmds-sidebar-note { border-top: 1px solid #385448; padding-top: 1.2rem; margin-top: 2.5rem; color: #a8beb0; font-size: .8rem; line-height: 1.6; }
@media (max-width: 768px) {
 [data-testid="stMainBlockContainer"] { padding: 1.7rem 1rem 3rem; }
 .mmds-topline { flex-wrap: wrap; margin-bottom: 1.2rem; }
 [data-testid="stForm"] { padding: .8rem; }
}
</style>
''', unsafe_allow_html=True)


def sidebar_brand():
    st.sidebar.markdown('''<div class="mmds-brand"><div class="mmds-emblem">M</div><div><div class="mmds-brand-name">MMDS</div><div class="mmds-brand-subtitle">CYBERSECURITY RESEARCH</div></div></div>''', unsafe_allow_html=True)


def page_context():
    st.markdown('''<div class="mmds-topline"><span>Cyberattack intelligence / Research workspace</span><span class="mmds-status">● Research demonstration</span></div><div class="mmds-eyebrow">MMDS / ANALYSIS</div>''', unsafe_allow_html=True)
