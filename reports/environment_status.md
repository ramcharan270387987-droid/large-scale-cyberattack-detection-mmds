# Phase 0 and Phase 0B environment status

## Phase 0B integration

Checked on 23 November 2026 IST from Codex Cloud, starting from Phase 0 commit `b4d316db5046df081de9dab672f33e71429b42a8`.

| Check | Observed result |
| --- | --- |
| `api.kaggle.com` | Cloud proxy CONNECT 403 before HTTPS reached Kaggle. The standard CLI stopped at its token introspection request. |
| `www.kaggle.com` | Proxy CONNECT 200 and HTTPS 200. Kaggle's API routes under `/api/v1` served the authenticated notebook operations. |
| `api.github.com` | Cloud proxy CONNECT 403 before HTTPS reached GitHub REST. |
| `github.com` | Git over HTTPS fetched `origin/work` at the expected Phase 0 commit. |
| Kaggle authentication | Token introspection returned HTTP 200 with `active: true` and an account. The authenticated notebook list returned HTTP 200. |
| Dataset metadata | The authenticated CLI retrieved metadata for `saisathwikregula/mmds-dataset-23013`, ID `13610604`. |
| Notebook submission | Kaggle accepted version 1. A versioned API pull confirmed private visibility, GPU and TPU disabled, and the exact dataset attachment. |
| CPU execution | The versioned API reported `RUNNING`, then `COMPLETE`. The first `COMPLETE` poll was at 22:25:59 IST. |
| Runtime and Spark | Python 3.13.18 and OpenJDK 21.0.12.1. Spark and PySpark 4.3.0 initialized on `local[2]` and the synthetic four-row count passed. The log recorded the Spark result at +75.58 s and its last event at +85.67 s. |
| Dataset mount | The log confirmed the known file under `/kaggle/input/datasets/saisathwikregula/mmds-dataset-23013/Cyberattack-MMDS/dataset/raw/`. The notebook checked the path with `Path.is_file()` and ran Spark on synthetic rows. |
| Logs and output | The versioned API returned the completed execution log with 124 records. The archive API returned the [74-byte smoke test status file](phase0b_kaggle_status.txt), which matched the log. |

The enforced settings for the running task included `www.kaggle.com` and the misspelled `pi.github.com`. The two requested API hostnames were absent. The [private Phase 0B notebook](https://www.kaggle.com/code/ramcharan2345/mmds-phase-0b-cloud-integration-check) used the existing notebook and CPU manifest. A temporary manifest supplied the authenticated owner and a new title and slug so the check could use its own version history.

The CLI's individual output file download hit a proxy CONNECT 403 for `www.kaggleusercontent.com`. The authenticated archive endpoint on `www.kaggle.com` returned HTTP 200 and contained `phase0_status.txt`. The archive contained notebook outputs only. Kaggle logged a dependency conflict with its preinstalled `dataproc-spark-connect` package after upgrading PySpark and a Spark temporary-directory cleanup warning. The synthetic local-mode job and the Kaggle run completed successfully.

Codex Cloud prepared the submission, resolved the Kaggle account from the existing token, submitted the notebook, monitored version 1, retrieved the completed log and status file, and verified the results without manual intervention. The integration guide records the working API and Git commands. [Verification guide](../docs/environment_verification.md)

## Phase 0 baseline

Spark passed two local runs on 23 November 2026 IST, and the Phase 0 setup was published to GitHub. The table and sections below record the Phase 0 observations.

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
