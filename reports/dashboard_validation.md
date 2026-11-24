# Dashboard validation

**Local application complete.** Streamlit 1.58.0, pandas 2.3.3 and Altair 6.0.0 were installed in a separate Python 3.12 environment. The dashboard used its compact committed data. The Streamlit health endpoint returned `ok`.

| Check | Evidence |
|---|---|
| Source package | `dashboard-v1` includes 30 aggregate tables and a derived metadata summary, totaling 682,936 bytes. Verification checks SHA-256, schema, row counts and upstream reconciliation. |
| Reproducibility | Regeneration from the authoritative reports produced the same manifest and table hashes. |
| Existing research suite | 42 tests passed in the Spark research environment. |
| Dashboard suite | 7 tests passed, covering input tampering and missing files, CSV validation, all route scripts, chart elements, traceability, confusion counts, model and novelty filters, family support, alert counts and export. |
| Chrome | Rendered all nine routes and inspected Overview and Machine learning. Chronological selection showed 980,109 evaluation flows. The Overview’s full flow counts were visible at the inspected viewport. |
| Actual export | Chrome downloaded a CSV after selecting high severity. Parsing the browser download returned 62 rows, all high severity. |
| Deployment | Cloud browser tunnel failed and HTTP CONNECT to Streamlit Community Cloud returned 403. Public deployment remains ready for manual setup. |

[Overview screenshot](../docs/screenshots/overview.jpg) · [Chronological screenshot](../docs/screenshots/chronological.jpg) · [Package manifest](../manifests/dashboard_package.json) · [Deployment settings](../docs/dashboard_deployment.md)
