# Phase 0 environment status

Verified on 23 November 2026 in Codex Cloud. **PARTIALLY READY**. Spark passed two local runs, and the Phase 0 setup was published to GitHub. Kaggle public metadata is reachable, while the Cloud proxy blocks authenticated Kaggle CLI calls and the Kaggle notebook has yet to run.

| Component | Observed version or evidence | Status |
| --- | --- | --- |
| Python | 3.12.14 | Pass |
| Java | OpenJDK runtime 21.0.13; `javac` absent and unused by these workloads | Pass for Spark |
| Apache Spark | 4.3.0; confirmed by `spark-submit` and the live session | Pass |
| PySpark | 4.3.0 with Py4J 0.10.9.9 and NumPy 2.5.5 | Pass |
| Spark SQL | Group totals blue = 6.0 and green = 12.0 | Pass |
| Spark MLlib | Binarizer and VectorAssembler pipeline produced the four expected vectors | Pass |
| Git | 2.56.1; HTTPS remote and commit identity available | Pass |
| Kaggle CLI | 2.2.5 with Kaggle SDK 0.1.38; writable config directory needed | Pass locally |
| Kaggle API authentication | Modern token present at runtime; proxy CONNECT 403 for `api.kaggle.com` | Blocked by policy |
| Kaggle notebook execution | Notebook and CPU manifest validated locally with a mock mount | Cloud run unverified |
| GitHub push | `git push` and independent remote ref lookup confirmed the Phase 0 setup commit on `origin/work` | Pass |
| Internet access | GitHub Git, raw GitHub, Kaggle web and PyPI reachable through the proxy | Restricted |

## System and Spark

Debian GNU/Linux 13.7 (trixie), 3 CPUs in process affinity with a cgroup quota equivalent to 2 CPUs, 9.7 GiB visible RAM with an 8 GiB cgroup limit, and about 60 GiB free on the workspace filesystem. PySpark, Kaggle and their dependencies were already installed in the checkout's `.venv`. `python -m pip list --format=freeze` was inspected, and `.venv/bin/python -m pip check` found no broken requirements. PySpark and Kaggle are isolated from the base interpreter. The PyPI package index was reachable for setup in a fresh virtual environment.

The synthetic test passed in 8.58 s and 9.18 s. The DataFrame filter and derived column returned `[4.0, 6.0, 8.0]`, the SQL aggregation returned the totals in the table, and the RDD map and sum returned 14. The pipeline produced `[[1.0, 0.0], [2.0, 0.0], [3.0, 1.0], [4.0, 1.0]]`. Spark stopped on both runs. Startup reported Java's incubator vector module and Spark's fallback to built-in Java classes for Hadoop. Both warnings were nonfatal. These results establish repeatability for local smoke jobs.

## Kaggle dataset

Kaggle's public view, file-list and metadata endpoints returned HTTP 200 and JSON for [MMDS_DATASET_23013](https://www.kaggle.com/datasets/saisathwikregula/mmds-dataset-23013). The exact reference is `saisathwikregula/mmds-dataset-23013`, numeric ID `13610604`. Kaggle reports version 1 as Ready with notes “Initial release,” owner Sai Sathwik Regula, Apache 2.0 license, and 6,886,649,507 total bytes. The description and subtitle are empty and the update frequency is unspecified. Only metadata was retrieved.

The file list contained ten entries with no next page. All names have the directory prefix `Cyberattack-MMDS/dataset/raw/`.

| File name | Bytes |
| --- | ---: |
| Friday-02-03-2018_TrafficForML_CICFlowMeter.csv | 352,368,373 |
| Friday-16-02-2018_TrafficForML_CICFlowMeter.csv | 333,723,605 |
| Friday-23-02-2018_TrafficForML_CICFlowMeter.csv | 382,840,456 |
| Thuesday-20-02-2018_TrafficForML_CICFlowMeter.csv | 4,054,925,350 |
| Thursday-01-03-2018_TrafficForML_CICFlowMeter.csv | 107,842,858 |
| Thursday-15-02-2018_TrafficForML_CICFlowMeter.csv | 375,945,899 |
| Thursday-22-02-2018_TrafficForML_CICFlowMeter.csv | 382,636,202 |
| Wednesday-14-02-2018_TrafficForML_CICFlowMeter.csv | 358,223,333 |
| Wednesday-21-02-2018_TrafficForML_CICFlowMeter.csv | 328,893,673 |
| Wednesday-28-02-2018_TrafficForML_CICFlowMeter.csv | 209,249,758 |

`KAGGLE_API_TOKEN` was present at runtime. The CLI stopped during token introspection at the Cloud proxy, before Kaggle could validate the token. The legacy environment-variable pair was absent. The notebook creation or update, dataset attachment, submission, execution status, and retrieval of logs and outputs remain unverified on Kaggle. Local validation checked the notebook schema and CPU manifest, ran its code against an empty stand-in for one mounted file, and produced the expected status file. See the [reproduction and credential instructions](../docs/environment_verification.md).

## GitHub and network policy

The clean checkout started on `work` with one commit, `e6215d6834ce06ba60fe9c7e65ce4a97b611343d`. HTTPS fetch and push both use [the project repository](https://github.com/ramcharan270387987-droid/large-scale-cyberattack-detection-mmds). Remote HEAD pointed to `main` at that same commit. The authenticated Git-over-HTTPS push published setup commit `878bb79e02adca867f5c20d72dc755fd97bbac3a` to `origin/work`, and `git ls-remote` returned the matching hash. The local fetch configuration originally tracked only `main`; it now also tracks `work`. The proxy blocked the separate GitHub REST identity check.

| Host | Observed result |
| --- | --- |
| `github.com` | HTTP 200; `git ls-remote` returned remote HEAD |
| `api.github.com` | Proxy CONNECT 403; correct the `pi.github.com` allowlist entry |
| `raw.githubusercontent.com` | HTTP 200 for the remote README |
| `www.kaggle.com` | HTTP 200 for the dataset page and metadata endpoints |
| `api.kaggle.com` | Proxy CONNECT 403; allowlist for CLI authentication and notebook operations |
| `pypi.org` | HTTP 200 for the PySpark index |
| `files.pythonhosted.org` | HTTP 404 at the root, establishing connectivity to the already-allowed package file host |

Direct local DNS lookups returned no addresses for the tested service names. Successful HTTPS requests used the managed proxy, which resolves approved destinations. The failed CONNECT requests align with the enforced allowlist.
