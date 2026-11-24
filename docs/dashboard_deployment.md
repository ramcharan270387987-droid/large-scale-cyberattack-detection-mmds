# Dashboard deployment

**QA status: public verification pending.** The maintainer supplied the [public Streamlit URL](https://large-scale-cyberattack-detection-mmds-jbsvxctpmtssjjcbeaky6d.streamlit.app/). During final QA the Cloud proxy returned HTTP 403 and Chromium could not establish the tunnel. The post-audit UI was tested locally. The published host’s active revision could not be observed from this environment.

The existing app should track repository `ramcharan270387987-droid/large-scale-cyberattack-detection-mmds`, branch `work`, and entry point `dashboard/app.py`. In Streamlit Community Cloud, confirm the app is following that branch and that the latest revision rebuilt successfully. Follow the steps below only when setting up a new deployment.

1. Sign in to [Streamlit Community Cloud](https://share.streamlit.io/) using a GitHub account authorized for the repository.
2. Choose **Create app** and select repository `ramcharan270387987-droid/large-scale-cyberattack-detection-mmds`, branch `work`, and main file path `dashboard/app.py`.
3. In advanced settings select **Python 3.12**. The supported Community Cloud dependency file beside the entry point is `dashboard/requirements.txt`. Leave secrets empty.
4. Deploy, wait for startup, open the resulting `.streamlit.app` URL and verify Overview, Machine learning with protocol B, Novelty detection with experiment C at P99, Historical replay, and a filtered alert download. Confirm the flow, batch and alert totals match the verified report.
5. Record the successful URL in the README after inspection.

Local validation is independent of the hosting account. The app needs the repository’s `dashboard/data`, `configs/dashboard.yaml`, and `manifests/dashboard_package.json` paths. It renders read-only aggregates and exports filtered historical alert rows. [Local launch](dashboard_quickstart.md)
