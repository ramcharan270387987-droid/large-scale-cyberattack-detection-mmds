"""Isolated, aggregate-only preview for the research branch."""

from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
TABLES = {
    "Operating points": ("model_comparison", ["method", "threshold", "precision", "recall", "f1", "fpr", "pr_auc", "rows"]),
    "False-positive budgets": ("false_positive_budgets", ["method", "policy", "threshold", "validation_fpr", "fpr", "precision", "recall"]),
    "Probability calibration": ("calibration_metrics", ["partition", "method", "rows", "brier", "log_loss", "ece"]),
    "Attack families": ("family_recall", ["method", "family", "support", "seen_in_training", "recall", "hybrid_referred"]),
    "Triage": ("triage_metrics", ["policy", "automatic_coverage", "review_rate", "abstain_rate", "automatic_error_rate", "benign_review_burden"]),
}


def evidence(path, expected):
    content = path.read_bytes()
    if sha256(content).hexdigest() != expected:
        raise ValueError(f"Evidence checksum mismatch for {path.name}")
    return content


def main():
    st.set_page_config(page_title="Hybrid Detection and Threshold Analysis", layout="wide")
    st.title("Hybrid Detection and Threshold Analysis")
    try:
        manifest = json.loads((ROOT / "manifests/phase8_experiments.json").read_text())
        supported = {run["population"]: run for run in manifest["runs"].values()
                     if run["stage"] == "hybrid" and run["status"] == "validated"}
        names = {"B": "B · Retrospective chronological", "C": "C · Retrospective Web holdout",
                 "R1": "R1 · Rolling origin", "R2": "R2 · Rolling origin"}
        population = st.selectbox("Evaluation population", supported, format_func=names.__getitem__)
        run = supported[population]
        st.caption(f"{run['scored_rows']:,} held-out flows · Frozen fusion {run['selected']} · Kaggle version {run['kernel_version']}")
        st.caption("Policy selection used a 1% validation benign false-positive ceiling. The held-out false-positive rate measures transfer to later traffic.")
        section = st.radio("Evidence", TABLES, horizontal=True)
        stem, columns = TABLES[section]
        filename = f"phase8_{stem}.csv"
        data = pd.read_csv(BytesIO(evidence(REPORTS / filename, manifest["tables_sha256"][filename])))
        data = data.loc[data["population"].eq(population), columns]
        st.dataframe(data, hide_index=True, width="stretch")
        st.download_button("Download selected table", data.to_csv(index=False), filename, "text/csv")
        with st.expander("Study figures"):
            files = manifest["figures_sha256"]
            figure = st.selectbox("Study figure", files, format_func=lambda name: Path(name).stem.removeprefix("phase8_").replace("_", " "))
            st.image(evidence(REPORTS / figure, files[figure]))
    except (OSError, KeyError, ValueError) as exc:
        st.error(f"Phase 8 evidence is unavailable. {exc}")


if __name__ == "__main__":
    main()
