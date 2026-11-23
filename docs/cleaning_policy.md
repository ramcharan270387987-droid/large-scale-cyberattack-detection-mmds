# Phase 2 cleaning policy

The canonical raw-aligned layer preserves all audited data records and the numeric representation before policy changes. Numeric lexemes are trimmed for conversion to DOUBLE. Affected original cell text travels in `quality_issues`, and the source filename and line fingerprint provide traceability for every row.

| Condition | Raw-aligned value | Clean value | Diagnostic action |
| --- | --- | --- | --- |
| NaN | NaN | null | `nullify` |
| Positive or negative infinity | Signed infinity where the Spark cast represents it | null | `nullify` with separate reason by sign |
| Audited impossible negative | Original typed negative | null | `nullify` |
| Initial TCP window `-1` | -1 | null | `nullify` with reason `sentinel` |
| Numeric cast failure | null with source lexeme | null | `typed_null` |
| Source null or whitespace-only numeric cell | null | null | `retain_null` |
| Metadata unavailable for this schema | Structural null | Structural null | Separate structural field array and counts |

The negative-value rule is inherited from the Phase 1 measurement and excludes initial window fields. The configuration governs actions and sentinel values. Per-file counters distinguish affected rows, affected cells, and the source-variant structural cells. A row may contribute to several reason-specific counts. A union of affected rows is reported separately. [Policy settings](../configs/cleaning.yaml) · [Measured quality actions](../reports/phase2_quality_actions.csv)

Timestamps use the Phase 1 day-first policy and preserve original timestamp text. The parsed field stores wall time with no source timezone. A parsed date outside its filename-derived day remains in the dataset with `outside_capture_day` and `temporal_eligibility=false`.

The label lookup matches each original label exactly. The normalized label is descriptive. An unrecognized spelling fails the capture validation before a verified layer is published for that capture. The underlying source and conflicting labels remain traceable.

The default `diagnostic` duplicate policy keeps all rows and writes exact-group multiplicity and cleaned-feature conflict groups. `preserve_all` skips the group artifacts. `exact_representative` also writes a separate representative layer while retaining all primary records. It groups by schema-scoped original-line digest, choosing the lexicographically earliest source filename. Ties are duplicate occurrences of the same source line within that file. The default full-run group excess is reconciled against the Phase 1 full parsed-field comparison. Feature similarity or differing labels never triggers consolidation. [Phase 1 duplicate evidence](../reports/dataset_audit.md)
