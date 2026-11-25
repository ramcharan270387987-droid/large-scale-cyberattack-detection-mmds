# Adaptive research methodology

The committed protocol is authoritative. One backend-independent runner scores before label release, selects training windows, applies trigger eligibility and schedules future-only model activation. The Spark backend independently verifies the pinned Phase2 producer receipt and all source counts. It retains the14 timestamp-anomaly rows in capture-day blocks under the inherited policy and assigns permanent predictor-group roles. The amendment ledger documents the earlier stricter sensitivity cohort. Exact, canonical and predictor crossing-group audits run over the full retained corpus. Candidate-specific imputed-vector collisions are diagnostic, since preprocessing can merge distinct raw groups.

Training fits median imputation, variance filtering and scaling only on eligible sampled training rows. The initial model uses February14–15 and February16 calibration. Frozen evaluation groups from seven later captures are identical across policies. Initial-calibration retention is separate from forward generalization. Each candidate is saved as a full Spark pipeline, reopened and checked on deterministic probes. Retrieved component hashes are independently verified against the Kaggle outputs.

Raw issued row predictions are materialized in private Kaggle scratch before labels release. Compact archived family/score-bin counts retain active version, capture and role and exactly reconstruct every configured bin-threshold confusion matrix. Row-level scratch does not persist after the runtime expires. Full fitted models persist in private notebook outputs. Git contains compact counts, lifecycle metadata and hashes.

All thresholds use2048 score bins. PR-AUC is the step sum of recall increments times precision after each descending bin, with ties grouped. ROC-AUC uses trapezoids. AUC values are descriptive, particularly across model versions with no guarantee of common calibration. Pooled confusion metrics sum original integer counts, with undefined denominators represented as null. Per-window metrics must not be averaged to claim pooled flow performance.

Physical fits are shared only for identical backend/model/seed/training-day keys. Charged counterfactual fit costs include the original measured fit cost for each policy request. Request count limits match, but realized training rows and total cost may differ and are reported. Neither wall time nor local4 worker count establishes distributed multi-node scaling. Synthetic logistic pipelines use sklearn and are identified separately from Spark LR.


## Stage 12F reproduction

The finalization resumed from ccb6de944ae41b3c1210e1b2b1808db6e4e111c3. The completed 12C, 12D and 12E archives were retrieved and checksum-verified, including the partial failed worker used by the immutable resume. The independent metric audit reconstructs issued-window confusion counts, pooled AUC and calibration threshold optima from 159 archived prediction histograms. It covers 35 historical policy scopes and 85 independent metric checks. No new model fitting or Kaggle submission was needed for finalization.

Use the pinned Spark 4.3.0 environment and requirements-phase12-synthetic.txt. Retrieve the completed archives into the paths declared by scripts/audit_phase12_metrics.py, preserving their private prediction_histograms directories. The committed retrieval receipts identify every notebook version and summary checksum. Regenerate and verify the compact evidence with the existing commands.

```bash
python scripts/finalize_phase12.py
python scripts/audit_phase12_metrics.py
python scripts/render_phase12_figures.py
python scripts/validate_phase12_preview.py
python scripts/build_phase12_manifests.py
python -m unittest discover -s tests -v
python scripts/verify_phase12_completion.py
```

The browser audit additionally uses the isolated local Streamlit server on port 8512 and scripts/browser_phase12_preview.py. Its screenshots, downloads and error checks are recorded separately from AppTest. The finalizer derives positive prediction rate and missed attacks directly from pooled TP, TN, FP and FN, preserving all archived model decisions. CSV export uses deterministic LF line endings.
