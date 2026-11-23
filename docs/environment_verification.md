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

In the running Codex Cloud environment settings, add `api.kaggle.com` to the restricted HTTP allowlist. Keep `www.kaggle.com` for public metadata. If GitHub REST authentication and repository permission checks are needed, add `api.github.com` and correct the existing `pi.github.com` entry.

Prefer `KAGGLE_API_TOKEN`. If it is missing from a new task, generate a token at [Kaggle API settings](https://www.kaggle.com/settings/api) and bind it through the Cloud environment's private credential configuration. For legacy authentication, supply both `KAGGLE_USERNAME` and `KAGGLE_KEY` through that configuration and remove the `KAGGLE_API_TOKEN` binding or unset it in the shell before testing the legacy pair. The CLI checks the modern token first. Keep values out of shell commands, source files, and logs.

Start a new shell after applying the environment changes, activate the project virtual environment, and run:

```bash
export KAGGLE_CONFIG_DIR="$(mktemp -d /tmp/mmds-kaggle.XXXXXX)"
kaggle --version
kaggle datasets files saisathwikregula/mmds-dataset-23013
kaggle datasets metadata saisathwikregula/mmds-dataset-23013 -p "$KAGGLE_CONFIG_DIR"
kaggle kernels list --mine
```

The writable config directory accommodates the CLI on Cloud images with a read-only home. A proxy CONNECT 403 means the destination was denied before reaching Kaggle. If Kaggle itself returns HTTP 401 once the host is reachable, replace the credential in Cloud settings and retry. A service HTTP 403 calls for checking the Kaggle account and its access. Inspect service availability and retry a transient HTTP 5xx.

### Private CPU notebook

The notebook manifest attaches the exact dataset by owner and slug. The notebook checks for a known file with a filesystem metadata operation, then runs a tiny synthetic Spark job. It prints Python and Java versions, checks both Spark versions and writes `phase0_status.txt`. Internet is enabled for the optional installation of the pinned PySpark package in Kaggle.

After the CLI account check succeeds, replace the username placeholder in a temporary copy. Before submitting, confirm the notebook slug is unused in your account and change the title and slug together if it is already in use.

```bash
phase0_dir="$(mktemp -d /tmp/mmds-kaggle-notebook.XXXXXX)"
cp notebooks/phase0_kaggle_environment.ipynb notebooks/kernel-metadata.json "$phase0_dir/"
read -r -p "Kaggle username: " phase0_owner
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
kaggle kernels push -p "$phase0_dir"
kaggle kernels status "$phase0_kernel"
kaggle kernels logs "$phase0_kernel"
kaggle kernels output "$phase0_kernel" -p "$phase0_dir" --file-pattern '^phase0_status\.txt$'
cat "$phase0_dir/phase0_status.txt"
```

Repeat the status command until the run reaches a terminal state and collect the log and output after completion. The same notebook can be imported from Kaggle's web UI. Select the exact dataset under **Add Input**, choose **Accelerator → None**, and use **Save Version → Save & Run All**.

## GitHub

The checkout uses the HTTPS remote `origin`. Phase 0 targets `origin/work`, the branch matching the Codex checkout. To compare the local and published commits:

```bash
git rev-parse HEAD
git ls-remote origin refs/heads/work
```
