"""Forest-green and ivory presentation for the evaluator dashboard."""
import streamlit as st
from html import escape


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
/* Native buttons provide keyboard navigation without radio circles. */
.mmds-nav-heading { color: #a8beb0; letter-spacing: .18em; font-size: .7rem; font-weight: 650; margin: .4rem .75rem .8rem; }
[data-testid="stSidebar"] .st-key-workspace-menu [data-testid="stButton"] button {
    display: flex; justify-content: flex-start; text-align: left;
    min-height: 3.1rem; padding: .75rem .95rem; border-radius: 11px;
    background: transparent; border: 1px solid transparent; color: #dbe6db;
    box-shadow: none; transition: background .15s, border-color .15s;
}
[data-testid="stSidebar"] .st-key-workspace-menu [data-testid="stButton"] button p {
    color: inherit; font-size: .92rem; font-weight: 500; line-height: 1.4;
}
[data-testid="stSidebar"] .st-key-workspace-menu [data-testid="stButton"] button:hover {
    background: #24483a; border-color: #385b48; color: #f4f7ec;
}
[data-testid="stSidebar"] .st-key-workspace-menu [data-testid="stButton"] button[kind="primary"] {
    background: #345943; border-color: #527154; color: #f4f7ec;
    box-shadow: inset 3px 0 0 #bfd4a6;
}
[data-testid="stSidebar"] .st-key-workspace-menu [data-testid="stButton"] button:focus-visible {
    outline: 2px solid #bdd2ac; outline-offset: 3px;
}
@media (prefers-reduced-motion: reduce) {
 [data-testid="stSidebar"] .st-key-workspace-menu button { transition: none !important; }
}
[data-testid="stMetric"] { background: #ffffff; border: 1px solid #dce4db; border-radius: 16px; padding: 1.2rem 1.35rem; }
[data-testid="stMetricLabel"] { color: #64776b; }
[data-testid="stMetricValue"] { color: #18372f; font-size: clamp(1.7rem, 2.6vw, 2.7rem); font-variant-numeric: tabular-nums; letter-spacing: -.04em; }
[data-testid="stDataFrame"], [data-testid="stForm"], [data-testid="stExpander"] { border: 1px solid #dce4db; border-radius: 14px; overflow: hidden; }
[data-testid="stForm"] { background: white; padding: 1.4rem; }
[data-testid="stFileUploaderDropzone"] { background: #ffffff; border: 1px dashed #98af91; border-radius: 14px; }
[data-testid="stButton"] button, [data-testid="stDownloadButton"] button, [data-testid="stFormSubmitButton"] button { border-radius: 10px; min-height: 2.8rem; font-weight: 600; }
[data-testid="stAlert"] { border-radius: 12px; }
.mmds-hero { background: linear-gradient(120deg, #173c30, #2e5140); color: #f4f7ec; border-radius: 22px; padding: 2rem 2.2rem; margin: .5rem 0 1.6rem; box-shadow: 0 12px 32px #173c3010; }
.mmds-hero h2 { color: #f4f7ec; font-size: clamp(1.7rem, 3vw, 2.7rem); line-height: 1.15; margin: .5rem 0 .8rem; max-width: 850px; }
.mmds-hero p { color: #d2dfcc; max-width: 720px; margin: 0; }
.mmds-kicker { font-size: .68rem; letter-spacing: .18em; text-transform: uppercase; color: #c3d6aa; }
.mmds-guide { border-left: 3px solid #7d9868; padding: .7rem 1rem; margin: 0 0 1.3rem; background: #edf1e7; border-radius: 0 10px 10px 0; color: #435a48; font-size: .9rem; }
.mmds-tile { background: white; padding: 1.2rem 1.3rem; border: 1px solid #dce4db; border-radius: 14px; min-height: 165px; margin-bottom: .6rem; }
.mmds-tile h3 { font-size: 1.1rem; margin: .55rem 0 .5rem; letter-spacing: -.02em; }
.mmds-tile p { color: #63766d; font-size: .9rem; margin: 0; }
.mmds-tile-number { color: #71865c; letter-spacing: .14em; font-size: .7rem; font-weight: 700; }
[data-testid="stMetric"] { box-shadow: 0 4px 16px #173c3005; }
[data-testid="stFormSubmitButton"] button { background: #254e39; color: white; border-color: #254e39; padding: .6rem 1.5rem; }
[data-testid="stFormSubmitButton"] button:hover { background: #183c2b; color: white; border-color: #183c2b; }
button:focus-visible, input:focus-visible { outline: 3px solid #7d9868; outline-offset: 3px; }
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
 .mmds-hero { padding: 1.4rem; border-radius: 16px; }
 .mmds-tile { min-height: auto; }
}
</style>
''', unsafe_allow_html=True)


def sidebar_brand():
    st.sidebar.markdown('''<div class="mmds-brand"><div class="mmds-emblem">M</div><div><div class="mmds-brand-name">MMDS</div><div class="mmds-brand-subtitle">CYBERSECURITY RESEARCH</div></div></div>''', unsafe_allow_html=True)


def page_context():
    st.markdown('''<div class="mmds-topline"><span>Cyberattack intelligence / Research workspace</span><span class="mmds-status">● Research demonstration</span></div><div class="mmds-eyebrow">MMDS / ANALYSIS</div>''', unsafe_allow_html=True)


def hero():
    st.markdown('''<div class="mmds-hero"><div class="mmds-kicker">Large-scale cybersecurity research</div><h2>Explore the evidence.<br>Understand the prediction.</h2><p>Investigate cyberattack detection and evolving traffic patterns through archived experiments and interactive model inference.</p></div>''', unsafe_allow_html=True)


def guide(text):
    st.markdown('<div class="mmds-guide">'+escape(text)+'</div>', unsafe_allow_html=True)


def tile(number, title, description):
    st.markdown('<div class="mmds-tile"><div class="mmds-tile-number">'+escape(number)+'</div><h3>'+escape(title)+'</h3><p>'+escape(description)+'</p></div>', unsafe_allow_html=True)
