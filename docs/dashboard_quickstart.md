# Dashboard quick start

From the repository root on branch `work`, use Python 3.12.

```sh
python -m venv .dashboard-venv
source .dashboard-venv/bin/activate
python -m pip install -r dashboard/requirements.txt
python scripts/validate_dashboard_package.py
python -m streamlit run dashboard/app.py
```

Open the local URL printed by Streamlit. The application bundles the validated aggregates. It starts without Spark, Java, Kaggle mounts, fitted model archives, or credentials. The prediction explorer shows historical outputs in aggregate.

Start on Overview, then select protocol B on Machine learning, experiment C and P99 on Novelty detection, a March day on Historical replay, and finally a severity in Alerts explorer. The CSV download follows all selected alert filters.

## Technical workflow

- Regenerate the package with `python scripts/build_dashboard_package.py`, then run the validator again. Byte-for-byte table copies keep upstream row ordering and numeric precision. The manifest records original paths, checksums, lengths, aggregate row counts and the verified upstream revision.
- Run `python -m unittest discover -s tests -p test_dashboard.py -v` in the dashboard environment. Use the research environment for the existing Spark tests.
- Choose a different local port with `--server.port 8502` if 8501 is occupied.
- If the app reports an evidence error, restore the committed data and manifest together. Use the upstream files pinned in the contract when rebuilding.
- On deployment, select the real Streamlit entry point and Python 3.12. [Deployment settings](dashboard_deployment.md)
