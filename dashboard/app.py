"""Start the MMDS Streamlit dashboard from the repository checkout."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from dashboard import styles
from dashboard.data_loader import evidence
from dashboard.validation import EvidenceError



def run():
    st.set_page_config(page_title="MMDS · Traffic Research", layout="wide")
    styles.apply()
    try:
        evidence()
    except EvidenceError as exc:
        st.error(str(exc))
        st.caption("Restore the committed aggregate package or rebuild it from the verified evidence checkout.")
        st.stop()

    with st.sidebar:
        st.markdown('<div class="mmds-brand"><b><span class="mmds-symbol">M</span>MMDS</b>'
                    '<p>Traffic research workspace</p></div>', unsafe_allow_html=True)
    sections = {
        "Project": [("Overview", "overview")],
        "Research": [("Dataset explorer", "dataset"), ("Spark SQL analytics", "analytics"),
                     ("Machine learning", "models"), ("Clustering", "clustering"),
                     ("Novelty detection", "novelty")],
        "Monitoring": [("Historical replay", "replay"), ("Alerts explorer", "alerts")],
        "Methods": [("Architecture", "architecture")],
    }

    pages = {section: [st.Page(f"pages/{path}.py", title=title, url_path=path, default=path == "overview")
                       for title, path in entries] for section, entries in sections.items()}
    st.navigation(pages).run()


run()
