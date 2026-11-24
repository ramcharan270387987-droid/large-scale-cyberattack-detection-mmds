"""Read the verified evidence as defensive copies for Streamlit views."""

import pandas as pd
import streamlit as st

from dashboard.validation import ROOT, verify_package


@st.cache_data(show_spinner=False)
def evidence():
    return verify_package()


@st.cache_data(show_spinner=False)
def table(name, *, text=False):
    manifest, _ = evidence()
    if name not in manifest["tables"]:
        raise KeyError(f"Unknown evidence table {name}")
    path = ROOT / "dashboard/data" / f"{name}.csv"
    if text:
        return pd.read_csv(path, keep_default_na=False, dtype=str)
    return pd.read_csv(path, keep_default_na=False, na_values=[""], float_precision="round_trip")


def lineage(*names):
    manifest, _ = evidence()
    return [manifest["tables"][name]["source"] for name in names]
