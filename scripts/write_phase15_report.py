"""Generate the integrated application technical report from acceptance evidence."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    registry=json.loads((ROOT/'manifests/phase15_models.json').read_text());parity=json.loads((ROOT/'reports/phase15_validation/parity.json').read_text());catalog=json.loads((ROOT/'manifests/phase15_evidence.json').read_text());browser=json.loads((ROOT/'reports/phase15_validation/browser.json').read_text());tests=json.loads((ROOT/'reports/phase15_validation/regression.json').read_text())
    rows='\n'.join('| '+m['id']+' | '+m['source_version']+' | '+str(m['parity']['probes'])+' | '+str(m['parity']['max_absolute_residual'])+' | '+m['sha256']+' |' for m in registry['models'])
    text=f'''# Phase 15 — Integrated dashboard and validated interactive inference

## A. Checkpoint and preserved research

Start51392548c562d098e3d74b9a0bda4c402bd421d7. The Phase15protocol was committed before inference implementation. The research-v2branch contains only the new advanced application,compact owner-authorized parameter artifacts,tests and documentation. All Phase1–14research and the public dashboard/app.py remain unchanged. Final remote identity is checked after the final push to avoid a self-referential commit hash. No public deployment or Phase16work was performed.

## B. Architecture and reusable integration

The separate entry point is dashboard/advanced_app.py. Thirteen application modules comprise executive overview,nine research areas,actual inference,historical replay and evidence/reproducibility. The catalog references{sum(map(len,catalog['groups'].values()))}existing CSV/JSONtables,plus original figures with path/hash lineage. Source phases and protocols remain visible. Dataset/SQL and engineering,supervised/hybrid,clustering/novelty,multiclass/open-set/pipeline gates,patterns,streaming/drift,adaptive learning,explainability and external validation/scalability all retain their actual evidence.

The runtime uses only Streamlit,pandas,Altair and standard Python. It does not require Java,Spark,Kaggle credentials or private model access. Only immutable research evidence is globally cached. Uploaded records and predictions are not cached across sessions,persisted or sent to third-party services. CSV downloads are bound to the displayed evidence identity. The baseline entry point and deployment remain separate.

## C. Executable models and identity

The minimum prespecified set contains exact archived Phase4B Logistic Regression and Random Forest,and Phase5B K-Means. Hybrid,multiclass/open-set and direct tree SHAP are research-only. No replacement model was trained. The compact JSON artifacts preserve active feature order,training medians,scaler flags/std/mean,LRcoefficients/intercept,RFcontinuous splits/leaf probabilities/tree weights,and K-Means signed-log1p/centroids. Original component hashes and source versions are in manifests/phase15_models.json.

| Model | Original source/version | Spark parity probes | Maximum score residual | Portable SHA256 |
|---|---|---:|---:|---|
{rows}

All{sum(r['probes'] for r in parity['models'])}deterministic missing,zero,unit,extreme finite,random and forest split-boundary probes match original Spark4.3.0pipelines. LR/RFprobability tolerance is1e-10;K-Means squared-distance tolerance is1e-8relative/absolute. Every threshold decision and assigned cluster agrees. Derived artifacts total about224KiB,contain parameters rather than private training records,and are distributed under the owner's requested application integration;the original source mirror declaresApache2.0. Uncertain upstream provenance remains documented.

## D. Manual inference and explanations

All three models execute from an18feature form. Blank fields use stored training medians. Names,available units and extraction caveats accompany inputs. Finite nonnegative inputs are capped at1e12;invalid inputs produce errors rather than predictions. Source-training min/max warnings are descriptive,not a guarantee of model validity on another extractor. Synthetic presets are explicitly numeric fixtures,not captured or necessarily physically consistent flows.

Results show the actual score,decision threshold,model identity,imputation count and limitations. LR signed contributions plus intercept reconstruct the new record's logit. K-Means feature deviations reconstruct squared distance to the actual assigned centroid after signed-log1p,imputation and scaling. RF predictions are genuine,but local tree SHAP is unsupported;archived native importance is global research evidence. No archived local explanation is substituted for an uploaded record. No score is labeled calibrated confidence or causal evidence.

## E. CSV ingestion,alignment and export

The exact ordered18feature schema is required. UTF8/BOMCSV is limited to1MiB/500logical rows. Missing/extra/reordered/duplicate headers fail explicitly. Per-row numeric/nonfinite/domain/column-count errors retain row numbers and invalid status;valid observations are scored without fitting preprocessing. The demonstration CSV has three synthetic rows. Browser acceptance verifies a valid three-row batch and a four-row mixed batch with its invalid row retained,plus incompatible-header rejection. Prediction downloads match independently computed output bytes. A valid uploaded row can be selected for a newly computed model explanation. Bounded results remain only in session memory and are cleared when the upload identity or model changes. Formula-leading text is escaped for spreadsheet export;numeric negative result values retain numerical representation.

## F. Historical replay and research interpretation

Capture,replay-position and microbatch controls select original Phase6records. The app joins actual archived detection,novelty,distance and alert evidence for the chosen window and displays its volume/latency. Phase12adaptive model versions are labeled as a separate retrospective experiment rather than retroactively assigned to the Phase6replay. No packet capture,new attack events,live monitoring or autonomous retraining was introduced.

All negative findings remain visible:weak chronological generalization,source LR's zero primary external detections,source RF's exceeded validation FPR ceiling,conditional common3rather than original18feature transfer,and non-monotonic local worker speedups. At1Mmatched rows Phase14Pandas end-to-end median0.242s versusSpark0.616s remains in its original table. No universalSpark,multi-node,production or causal claim is made.

## G. Model registry,security and resource controls

Artifacts are checked against recorded SHA256before use;missing/corrupt/unsupported representations disable inference with no fallback. CSV/manual paths share the same schema/domain parser. Uploads stay inside the app process and are not used for training. Tree traversal is bounded;small artifacts and500row budgets keep runtime practical. Shared caches contain immutable research evidence only. Deployment/server logs and host policies still apply;this is not a production authentication/tenant service. Source-domain and finite-probe parity limitations remain explicit.

## H. Browser and integration acceptance

AppTest passes all13modules,all3manual models,missing-model/empty/undefined states. Chromium verifies nine research areas and supported filters with exact downloaded CSV identities,all3manual predictions,invalid manual input,valid/mixed/invalid CSV,actual prediction downloads,explanation rendering,historical replay,provenance and a real temporarily unavailable-model state restored afterward. Desktop/mobile screenshots are genuine. Final browser scope passes with no page errors,unexpected HTTP errors or mobile main-content horizontal overflow. Research-area assertions may be retained from a preceding browser scope while affected inference/mobile controls are retried;the receipt marks that scope explicitly.

Screenshots: {', '.join(browser['screenshots'])}. Synthetic CSV:dashboard/data/phase15_demo.csv. Demonstration steps are in docs/phase15_demo_guide.md. No private historical input row appears in screenshots or committed prediction fixtures.

## I. Regression and completion

All{tests['total']}tests pass with zero failures,errors or skips,preserving164baseline tests plus16new input/model/evidence/parity/security contract tests. Full-suite runtime is{tests['seconds']:.3f}seconds. Existing Spark4.3.0compatibility is preserved. The independent completion validator checks original model identity,portable hash/parity binding,numerical explanations,batch alignment,all catalog/figure hashes,UI/download evidence,documentation,regression and protected references. The final receipt is reports/phase15_validation/acceptance.json.

## J. Deployment preparation and limitations

Use a separate service with Python3.12 and dashboard/requirements.txt:

```bash
pip install -r dashboard/requirements.txt
python -m streamlit run dashboard/advanced_app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true --server.maxUploadSize 1 --browser.gatherUsageStats false
```

No public deployment is claimed or authorized. Preserve the existing public baseline service. Exact deployment,artifact requirements,troubleshooting,inference and limitation documentation are in docs/phase15_*.md. Interactive source models are not validated production detectors. Their bounded Spark parity is numerical compatibility evidence,not a generalization guarantee. K-Means novelty is not attack probability,and LR attributions are not causal. Historical replay and simulated label availability are not real-world live monitoring. Phase16has not begun.
'''
    import re
    text=re.sub(r'\b(Phase)(1[0-6]|[1-9])\b',r'\1 \2',text);text=re.sub(r',(?=[A-Za-z])',', ',text);text=re.sub(r'\b(All|all|Start|references|contains|with|plus|preserving|at|total|is)(?=\d)',r'\1 ',text)
    text=re.sub(r'\bPhase(?=\d)','Phase ',text)
    text=re.sub(r'(?<=\d)(?=(?:protocol|work|research|existing|saved|models|model|rows|probes|tests|baseline|new|pipelines|feature|features|KiB|MiB|GiB|logical)\b)',' ',text)
    text=text.replace('CSV/JSONtables','CSV/JSON tables').replace('research-v2branch','research-v2 branch').replace('LRcoefficients','LR coefficients').replace('RFcontinuous','RF continuous').replace('RFprobability','RF probability')
    (ROOT/'reports/phase15_results.md').write_text(text);print('Wrote Phase15technical report')
if __name__=='__main__':main()
