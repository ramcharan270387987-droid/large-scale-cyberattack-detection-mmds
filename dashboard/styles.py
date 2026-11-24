"""Visual system for the research dashboard."""

import streamlit as st


def apply():
    st.markdown("""
<style>
[data-testid="stMainBlockContainer"] {max-width: 1320px; padding: 3.1rem 3.4rem 4rem;}
[data-testid="stSidebar"] {background: #121e21; border-right: 1px solid #2e4143;}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {padding-top: 1.25rem;}
[data-testid="stMetric"] {border: 1px solid #2f4547; background: #152123; border-radius: 12px;
    padding: 1rem; min-width: 0;}
[data-testid="stMetricValue"] {font-variant-numeric: tabular-nums; font-size: clamp(1.25rem, 2.2vw, 2rem);}
[data-testid="stMetricLabel"] {color: #b3c8c4;}
[data-testid="stCaptionContainer"] {color: #a8bfbb;}
.mmds-brand {border-bottom: 1px solid #314749; padding: .4rem 0 1rem; margin-bottom: .8rem;}
.mmds-brand b {font-size: 1.2rem; letter-spacing: -.04em;}
.mmds-brand p {color: #a8bfbb; font-size: .88rem; margin: .15rem 0 0;}
.mmds-symbol {display: inline-grid; place-items: center; width: 32px; height: 32px; color: #102323;
    background: #58e0c1; border-radius: 8px; font-weight: 900; margin-right: .5rem;}
.mmds-hero {position: relative; overflow: hidden; border-radius: 18px; border: 1px solid #345354;
    background: radial-gradient(ellipse at 100% 0%, #224641, transparent 63%), #172629; padding: 1.85rem 2.5rem;}
.mmds-hero::after {content: ""; position: absolute; right: -2rem; top: -4rem; width: 37%; height: 155%;
    background: repeating-linear-gradient(90deg, transparent 0 26px, #71e7c631 27px 28px),
                repeating-linear-gradient(0deg, transparent 0 26px, #71e7c631 27px 28px);
    transform: rotate(-16deg); mask-image: linear-gradient(90deg, transparent, #000); pointer-events: none;}
.mmds-hero h1 {position: relative; z-index: 1; color: #f2faf7; letter-spacing: -.05em;
    font-size: clamp(2.15rem, 3.65vw, 3.4rem); line-height: 1.05; margin: .35rem 0 .8rem; padding: 0; max-width: 22ch;}
.mmds-hero p {position: relative; z-index: 1; color: #bcceca; max-width: 55ch; margin: 0; font-size: 1rem;}
.mmds-context {font: 600 .79rem ui-monospace, monospace; color: #75ddc4; letter-spacing: .1em;}
.mmds-finding {border: 1px solid #4b4739; border-left: 4px solid #ffbb85; border-radius: 9px;
    background: #222322; color: #eeddd0; padding: 1rem 1.2rem;}
[data-testid="stHeadingWithActionElements"] h2 {letter-spacing: -.035em;}
@media(max-width: 700px) {
    [data-testid="stMainBlockContainer"] {padding: 3.2rem 1rem 2rem;}
    .mmds-hero {padding: 1.25rem;}
}
</style>
""", unsafe_allow_html=True)
