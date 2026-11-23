# Phase 2 data contract

Contract `phase2-v1` applies to `saisathwikregula/mmds-dataset-23013` release 1. The pipeline checks paths, byte sizes, exact original headers and per-file row counts against the committed Phase 1 evidence. Header strings and order are frozen in the contract configuration. Normalization uses the Phase 1 NFKC, trim, case-fold and punctuation-to-underscore rule. [Cleaning configuration](../configs/cleaning.yaml) · [Phase 1 schema](dataset_schema.md)

| Fields | Spark type | Meaning |
| --- | --- | --- |
| 78 shared measurement and transport fields | DOUBLE | Explicit numeric casts. `protocol` is a categorical code and `dst_port` is retained as transport context. |
| `flow_id`, `src_ip`, `dst_ip` | STRING | Original February 20 metadata. All other captures record structural nulls. |
| `src_port` | DOUBLE | February 20 source port. All other captures record a structural null. |
| `original_label`, `normalized_label`, `attack_family` | STRING | Source spelling, audited display normalization and explicit Phase 1 family mapping. |
| `binary_label` | BYTE | 0 for Benign and 1 for an audited attack label. |
| `original_timestamp`, `source_file`, `source_day`, `schema_variant` | STRING | Raw timestamp text, exact source basename, ISO capture day and either `common_80` or `extended_84`. |
| `parsed_event_time` | TIMESTAMP_NTZ | Day-first parsed wall time with seconds retained. |
| `timestamp_parse_status` | STRING | `matched`, `outside_capture_day`, `unparseable` or `missing`. |
| `timestamp_capture_day_match`, `temporal_eligibility` | BOOLEAN | A missing or unparseable timestamp gives a null match and ineligible row. |
| `record_fingerprint` | BINARY | SHA-256 over ordered schema variant, a NUL separator and original line text without its record delimiter. |
| `dataset_version`, `cleaning_policy_version` | INT, STRING | Source release and the exact policy version. |
| `structural_missing_fields` | ARRAY of STRING | Capture-variant fields with structural nulls. |
| `quality_issues` | ARRAY of STRUCT | Field name, original cell text, reason and action for each recorded issue. |

The pipeline resolves columns using the audited header for each file, then materializes canonical fields by name. Spark readers should project fields by name across days. The logical Parquet partition key `source_day` is an ISO string encoded in directory names. With Spark readers, use `spark.sql.sources.partitionColumnTypeInference.enabled=false` to preserve that type.

`record_fingerprint` identifies content within this schema contract. Identical source-line text can share a fingerprint and can occur multiple times. `source_file` and the digest allow a source lookup against the pinned immutable input, and `quality_issues` retains affected original values directly. No physical occurrence offset is available. All primary layers preserve multiplicity. The diagnostic output records exact group sizes.

The feature-ready projection exposes 77 shared model candidates from the explicit allowlist in the Parquet manifest. It excludes destination port, identifiers, February 20 extra fields and their presence, raw or parsed timestamps, schema variant, source filename and quality flags. It carries targets, the capture-day partition key, temporal eligibility and two fingerprints as non-feature metadata. `split_feature_key` hashes the cleaned numeric candidate vector in the contract's order with a policy-version prefix. Use both keys as constraints for split grouping. Conflicting labels remain explicit even when their feature keys agree. [Parquet manifest](../manifests/parquet_layers.json)
