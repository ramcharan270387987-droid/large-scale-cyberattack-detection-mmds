"""Read the verified evidence as defensive copies for Streamlit views."""

import pandas as pd
import streamlit as st

from dashboard.validation import ROOT, verify_package


@st.cache_data(show_spinner=False)
def evidence():
    return verify_package()


@st.cache_data(show_spinner=False)
def table(name):
    manifest, _ = evidence()
    if name not in manifest["tables"]:
        raise KeyError(f"Unknown evidence table {name}")
    return pd.read_csv(ROOT / "dashboard/data" / f"{name}.csv", keep_default_na=False, na_values=[""])


def lineage(*names):
    manifest, _ = evidence()
    return [manifest["tables"][name]["source"] for name in names]
