# large-scale-cyberattack-detection-mmds
Large-Scale Cyberattack Detection and Evolving Attack Pattern Mining using Apache Spark, PySpark, Spark MLlib and Kaggle.

## Phase 0 environment verification

Run the synthetic Spark smoke test from the repository root in Codex Cloud:

```bash
source .venv/bin/activate
SPARK_LOCAL_IP=127.0.0.1 python -m unittest discover -s tests -v
```

See the [verification guide](docs/environment_verification.md) for dependency setup and the private Kaggle CPU notebook procedure. The [status report](reports/environment_status.md) records the observed results and remaining integration blockers.
