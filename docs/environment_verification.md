# Phase 0 environment verification

## Spark in Codex Cloud

The checked configuration uses Python 3.12, OpenJDK 21 and Spark 4.3.0 from the PySpark package. Use the checkout's configured virtual environment if present. For a fresh checkout with Python and Java already available:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
SPARK_LOCAL_IP=127.0.0.1 spark-submit --version
SPARK_LOCAL_IP=127.0.0.1 python -m unittest discover -s tests -v
```

Activating the virtual environment lets `spark-submit` find the installed PySpark distribution. The unit test uses two local Spark workers and checks a DataFrame filter and derived column, SQL aggregation, RDD map and sum, and an MLlib pipeline made of feature transformers. Spark stops in a `finally` block.

## Kaggle connection

The standard Kaggle CLI uses `api.kaggle.com`. Phase 0B used Kaggle's API routes on `www.kaggle.com` through `scripts/kaggle_web_api.py` because the running Cloud proxy allowed that host. For the standard route, allow `api.kaggle.com` in the running environment. GitHub REST uses `api.github.com`, and Git over HTTPS uses `github.com`.

Prefer `KAGGLE_API_TOKEN`. If it is missing from a new task, generate a token at [Kaggle API settings](https://www.kaggle.com/settings/api) and bind it through the Cloud environment's private credential configuration. For legacy authentication, supply both `KAGGLE_USERNAME` and `KAGGLE_KEY` through that configuration and remove the `KAGGLE_API_TOKEN` binding or unset it in the shell before testing the legacy pair. The CLI checks the modern token first. Keep values out of shell commands, source files, and logs.

Activate the project virtual environment. For a CLI-only setup, install `kaggle==2.2.5`, `kagglesdk==0.1.38`, and `six`. Run the following from the repository root:

```bash
export KAGGLE_CONFIG_DIR="$(mktemp -d /tmp/mmds-kaggle.XXXXXX)"
phase0_cli=(python scripts/kaggle_web_api.py)
"${phase0_cli[@]}" --version
phase0_owner=$("${phase0_cli[@]}" account)
"${phase0_cli[@]}" datasets metadata saisathwikregula/mmds-dataset-23013 -p "$KAGGLE_CONFIG_DIR"
"${phase0_cli[@]}" kernels list --mine --csv
```

The writable config directory accommodates the CLI on Cloud images with a read-only home. The `account` command prints the account returned by Kaggle token introspection. A proxy CONNECT 403 means the destination was denied before reaching Kaggle. If Kaggle rejects the credential or reports that it is inactive, update the binding in Cloud settings and retry. A service HTTP 403 calls for checking the Kaggle account and resource access.

### Private CPU notebook

The notebook manifest attaches the exact dataset by owner and slug. The notebook checks for a known file with a filesystem metadata operation, then runs a tiny synthetic Spark job. It prints Python and Java versions, checks both Spark versions and writes `phase0_status.txt`. Internet is enabled for the optional installation of the pinned PySpark package in Kaggle.

After the account check succeeds, replace the username placeholder in a temporary copy. Before submitting, confirm the notebook slug is unused in your account and change the title and slug together if it is already in use.

```bash
phase0_dir="$(mktemp -d /tmp/mmds-kaggle-notebook.XXXXXX)"
cp notebooks/phase0_kaggle_environment.ipynb notebooks/kernel-metadata.json "$phase0_dir/"
python - "$phase0_dir/kernel-metadata.json" "$phase0_owner" <<'PY'
import json
from pathlib import Path
import sys

manifest_path = Path(sys.argv[1])
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["id"] = manifest["id"].replace("YOUR_KAGGLE_USERNAME", sys.argv[2])
manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
PY
phase0_kernel="$phase0_owner/mmds-phase-0-environment-check"
"${phase0_cli[@]}" kernels push -p "$phase0_dir"
```

Use the version number returned by the push. The following uses version 1, as returned in Phase 0B. Pull the saved metadata and check private visibility, CPU settings and the exact dataset reference before monitoring the version.

```bash
phase0_version="$phase0_kernel/1"
"${phase0_cli[@]}" kernels pull "$phase0_version" -p "$phase0_dir/saved" -m
"${phase0_cli[@]}" kernels status "$phase0_version"
```

Poll until the status is `KernelWorkerStatus.COMPLETE`, then retrieve the execution log and status file.

```bash
"${phase0_cli[@]}" kernels logs "$phase0_version" > "$phase0_dir/run.log"
"${phase0_cli[@]}" phase0-output "$phase0_version" "$phase0_dir/phase0_status.txt"
cat "$phase0_dir/phase0_status.txt"
```

The `phase0-output` command downloads the compact archive from Kaggle's web API and extracts only `phase0_status.txt`. The regular `kernels output` command uses `www.kaggleusercontent.com` for individual files and requires that host to be allowed. Confirm the log includes the Python version, dataset path and Spark result, and the status file contains `PASS`. The same notebook can be imported from Kaggle's web UI. Select the exact dataset under **Add Input**, choose **Accelerator → None**, and use **Save Version → Save & Run All**.

## GitHub

The checkout uses the HTTPS remote `origin`. Phase 0 targets `origin/work`, the branch matching the Codex checkout. To compare the local and published commits:

```bash
git rev-parse HEAD
git ls-remote origin refs/heads/work
```
