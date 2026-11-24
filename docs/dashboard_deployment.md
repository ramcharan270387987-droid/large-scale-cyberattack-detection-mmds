# Dashboard deployment

**Status: ready for manual deployment.** The Codex Cloud browser returned a tunnel connection failure and the Cloud proxy returned HTTP 403 for the Streamlit Community Cloud dashboard. An authorized Streamlit account and a reachable Community Cloud UI are needed to create the app. A public deployment URL has yet to be verified.

1. Sign in to [Streamlit Community Cloud](https://share.streamlit.io/) using a GitHub account authorized for the repository.
2. Choose **Create app** and select repository `ramcharan270387987-droid/large-scale-cyberattack-detection-mmds`, branch `work`, and main file path `dashboard/app.py`.
3. In advanced settings select **Python 3.12**. The supported Community Cloud dependency file beside the entry point is `dashboard/requirements.txt`. Leave secrets empty.
4. Deploy, wait for startup, open the resulting `.streamlit.app` URL and verify Overview, Machine learning with protocol B, Novelty detection with experiment C at P99, Historical replay, and a filtered alert download. Confirm the flow, batch and alert totals match the verified report.
5. Record the successful URL in the README after inspection.

Local validation is independent of the hosting account. The app needs the repository’s `dashboard/data`, `configs/dashboard.yaml`, and `manifests/dashboard_package.json` paths. It renders read-only aggregates and exports filtered historical alert rows. [Local launch](dashboard_quickstart.md)
