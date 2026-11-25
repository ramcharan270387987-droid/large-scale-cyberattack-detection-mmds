# Separate Streamlit Community Cloud deployment guide

No public deployment was performed. This is an administrative guide for a separately authorized advanced app service. Preserve the existing baseline app and its service configuration.

1. Connect the repository account with access to the desired checkout. Choose branch research-v2 and entry point dashboard/advanced_app.py.
2. In deployment settings choose Python 3.12 to match the accepted application runtime. Defaults can change; select the version explicitly.
3. Use dashboard/requirements.txt. Streamlit Community Cloud searches the entry-point directory before the repository root for dependencies. Avoid the root research requirements, which include unnecessary Spark research dependencies. Do not add competing dependency files to the deployment.
4. Ensure the full committed dashboard, src/interactive, compact parameters, model/evidence manifests, referenced reports and figures are present. The academic ZIP is not a full app checkout. No Kaggle secrets or private raw data are required for startup.
5. Apply the documented upload limit of 1 MiB and keep the application's 500-row limit. Disable usage statistics if required by the institution. Do not add a credential to make a missing compact artifact appear available; restore the exact committed artifact instead.
6. After hosting, repeat the focused overview/inference/replay/provenance checks, synthetic CSV validation, download inspection and invalid-row diagnostics. Check actual host memory and latency. Local tests establish neither cloud capacity nor prospective detector performance.
7. For a missing model or checksum mismatch, compare the registry and file hash. For an input error, restore exact ordered schema and finite nonnegative values or permitted blanks. Research-only hybrid, multiclass and direct tree SHAP availability must not be changed to satisfy a demonstration.

Official dependency-resolution guidance inspected for this package: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies (2026-11-25). Hosting provider policies and default versions may change. Deployment remains a separate action; no URL or public service success is claimed.
