# Phase 15 isolated deployment preparation

The advanced entry point is dashboard/advanced_app.py. Preserve dashboard/app.py and the existing public baseline service. Public deployment requires separate authorization and has not been performed.

Use Python3.12 and a separate service/environment. From a checkout containing the committed compact models,evidence manifests,referenced reports,dashboard/data and docs:

```bash
python -m venv .venv-advanced
. .venv-advanced/bin/activate
pip install -r dashboard/requirements.txt
python -m streamlit run dashboard/advanced_app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true --server.maxUploadSize 1 --browser.gatherUsageStats false
```

No Kaggle token,private artifact access,Java,PySpark or model download is required at application startup. Do not use the root research requirements for this lightweight service. The existing dashboard/requirements.txt pins Streamlit,pandas,Altair and its compatibility dependency. For a separately authorized Streamlit service,select dashboard/advanced_app.py and ensure that service uses dashboard/requirements.txt. Do not alter the baseline app's deployment configuration.

Memory planning:the three compact parameter artifacts total about224KiB;aggregate research tables/figures dominate application memory. Immutable evidence is cached;user uploads/results are not globally cached or persisted. The application enforces1MiB/500rows and a finite input domain. Use one process initially and measure the actual host before changing those documented limits. Local acceptance is mandatory;hosted capacity/latency are not claimed from local tests.

Missing artifact/checksum errors:restore the exact committed file and registry,never replace it with another fitted model. Missing evidence:restore its recorded version/path. CSV schema errors:use the downloadable synthetic CSV header and exact column order. Nonfinite/negative values:correct them or use a blank for training-median imputation. Wrong model score interpretation:review the source-domain and novelty limitations. If Git metadata is unavailable,the evidence page labels its archived checkpoint instead of inventing a deployment SHA.

Only offline re-export/parity verification uses scripts/export_phase15_models.py in the established Spark4.3.0 research environment. It must use original checksum-verified private artifacts;no fitting is allowed. The deployed app never runs that script.
