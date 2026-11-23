# Phase 2 Parquet storage and reuse

The versioned producer root is `/kaggle/working/mmds_phase2/phase2-v1`. The layer directories are `raw_aligned`, `clean`, and `feature_ready`. Each uses Snappy Parquet with Hive-style `source_day=YYYY-MM-DD` directories. Small captures coalesce according to a target of 128 MiB of source CSV per output task. This target controls task counts. Compressed file sizes are measured separately.

The same version contains `diagnostics/exact_groups` and `diagnostics/label_conflicts`, which use the fingerprints described in the data contract. The producer writes per-capture checkpoints and compact evidence in `mmds_phase2/evidence`. Its validator opens Parquet footers and checks the written record count and compression for every primary partition. [Data contract](data_contract.md) · [Measured paths and file counts](../manifests/parquet_layers.json)

## Open saved Kaggle outputs

Add the private Phase 2 producer as a **Notebook Output** input using the same authorized account. The CLI uses the producer ref in `kernel_sources`. Resolve the mounted `mmds_phase2/evidence/validation_summary.json` and verify its SHA-256 against the manifest for the intended producer execution. Its grandparent is the mounted `mmds_phase2` directory. Read each layer under the recorded policy version. Use consistent Spark partition-column type inference when decoding `source_day`.

A Kaggle worker starts with its own working directory. Subsequent workers obtain the producer data from the saved notebook output mount. The separate verification notebook reopens the Parquet footers, independently re-counts stored labels, and checks every stored nullification recorded by the policy. Its compact archive contains only the evidence it verified. [Published mount evidence](../manifests/parquet_layers.json)

## Rebuild a layer

`scripts/build_phase2_notebook.py` embeds the pipeline, schema contract, and Phase 1 inventory into the producer notebook. The matched private CPU Kaggle configuration attaches the exact dataset release and uses the recorded memory and partition settings. Each capture writes its three complete partitions before publishing its checkpoint. Within an output directory, the pipeline can reuse a checkpoint after rechecking existing footers. For an independent worker or partial resume, generate a fresh notebook with `--day YYYY-MM-DD` for each requested capture day, retain the published evidence for every successful partition, and reconcile all day partitions before using a combined dataset. A complete rebuild runs the default notebook without any day filter.

Use the Phase 0B Kaggle wrapper for submission, status, and persisted logs. The Phase 2 evidence helper extracts the producer summary and its signature from the log. Generate a small storage probe with `--storage-probe-sha SHA`, attach the saved producer as its notebook input, then retrieve the probe with `scripts/retrieve_phase2_evidence.py probe OWNER/SLUG/VERSION OUTPUT_DIR`. The Parquet layers stay in Kaggle. GitHub tracks source, documentation and aggregate receipts.
