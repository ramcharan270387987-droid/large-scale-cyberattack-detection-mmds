# large-scale-cyberattack-detection-mmds
Large-Scale Cyberattack Detection and Evolving Attack Pattern Mining using Apache Spark, PySpark, Spark MLlib and Kaggle.

## Phase 0 environment verification

Run the synthetic Spark smoke test from the repository root in Codex Cloud:

```bash
source .venv/bin/activate
SPARK_LOCAL_IP=127.0.0.1 python -m unittest discover -s tests -v
```

See the [verification guide](docs/environment_verification.md) for dependency setup and the private Kaggle CPU notebook procedure. The [status report](reports/environment_status.md) records the observed results and remaining integration blockers.

## Phase 1 dataset audit

The audit measures the ten version 1 captures on Kaggle CPU. It separates data records from headers, blank lines and malformed lines, and retains original labels and headers. The [audit report](reports/dataset_audit.md), [schema reference](docs/dataset_schema.md), and [research feasibility assessment](docs/dataset_feasibility.md) contain the results.

To regenerate the self-contained notebook and exercise its audit code against synthetic fixtures:

```bash
python scripts/build_phase1_notebook.py
SPARK_LOCAL_IP=127.0.0.1 python -m unittest discover -s tests -v
```

The Phase 1 submission uses a temporary copy of the private CPU manifest from Phase 0B with the authenticated owner, title `MMDS Phase 1 Dataset Audit`, ID `owner/mmds-phase-1-dataset-audit`, and code file `phase1_dataset_audit.ipynb`. Confirm that the Kaggle dataset is version 1 and that its mounted inventory matches `configs/dataset.yaml`. The notebook writes compact JSON markers under `/kaggle/working/mmds_phase1`. Parsed disk caches and fingerprint intermediates stay in `/kaggle/temp`.

Use the Kaggle CLI setup in the [integration guide](docs/environment_verification.md) to submit and monitor a version. After the run finishes, the same web API retrieves the archive and extracts the audit markers:

```bash
python scripts/kaggle_web_api.py kernels logs "$kernel/$version" > "$run_dir/audit.log"
python scripts/kaggle_web_api.py phase1-output "$kernel/$version" "$run_dir/audit"
python scripts/render_phase1_audit.py "$run_dir/audit" \
  --kernel-url "https://www.kaggle.com/code/$kernel" --version "$version" --status COMPLETE
```

For a bounded retry, set `ONLY_DAYS` in a temporary notebook to the unfinished ISO capture dates. Retrieve completed versions' JSON separately and retain the source version for each recovered file. A caught per-file error leaves earlier stage markers available in the finished archive. An interrupted worker may lose unpublished markers. Global fingerprint metrics require one run with all captures present. Use `scripts/build_phase1_notebook.py --exact-duplicates --output PATH` for the independent full-value duplicate pass. Pass its extracted directory and verified version to the renderer with `--exact-source` and `--exact-version`.

## Phase 2 typed Parquet

Phase 2 builds and validates a raw-aligned layer, a clean layer, and a feature-ready base layer in private Kaggle CPU. See the [data contract](docs/data_contract.md), [cleaning policy](docs/cleaning_policy.md), [saved output reuse](docs/parquet_storage.md), and [execution report](reports/phase2_data_engineering.md).

For local verification, activate the project virtual environment and install PyArrow in addition to the Phase 0 dependencies. Build the self-contained notebook and run the tests with the same Spark version as Kaggle.

```bash
python -m pip install pyarrow
python scripts/build_phase2_notebook.py
SPARK_LOCAL_IP=127.0.0.1 python -m unittest discover -s tests -v
```

## Phase 3 Spark SQL analytics

Phase 3 queries the verified Phase 2 Notebook Output in private Kaggle CPU. See the [analytics results](reports/phase3_analytics.md), [methodology](docs/phase3_methodology.md), [pattern findings](docs/attack_pattern_findings.md), and [research readiness](reports/phase3_research_readiness.md). Local tests use Spark, PyArrow, and Matplotlib. Rebuild the bundled notebook with `python scripts/build_phase3_notebook.py`.
