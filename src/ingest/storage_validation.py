"""Validate a mounted Phase 2 notebook output with bounded Arrow batches."""

from collections import Counter
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq


def count_matches(values, value):
    return pc.sum(pc.cast(pc.equal(values, value), "int64")).as_py() or 0


def validate_clean_file(parquet):
    reasons, actions = Counter(), Counter()
    affected_rows = outliers = 0
    nullified_fields = set()
    for batch in parquet.iter_batches(columns=["quality_issues", "timestamp_parse_status", "temporal_eligibility"]):
        issues = batch.column("quality_issues")
        flat = pc.list_flatten(issues)
        affected_rows += pc.sum(pc.cast(pc.greater(pc.list_value_length(issues), 0), "int64")).as_py() or 0
        reasons.update({item["values"]: item["counts"] for item in pc.value_counts(flat.field("reason")).to_pylist()})
        nullification = pc.equal(flat.field("action"), "nullify")
        for item in pc.unique(pc.filter(flat.field("field"), nullification)).to_pylist():
            nullified_fields.add(item)
        actions["nullify"] += count_matches(flat.field("action"), "nullify")
        status = batch.column("timestamp_parse_status")
        outliers += count_matches(status, "outside_capture_day")
        eligibility = batch.column("temporal_eligibility")
        if pc.any(pc.not_equal(eligibility, pc.equal(status, "matched"))).as_py():
            raise ValueError("Stored temporal eligibility disagrees with timestamp status")
    checked_cells = 0
    if nullified_fields:
        for batch in parquet.iter_batches(columns=["quality_issues", *sorted(nullified_fields)]):
            issues = batch.column("quality_issues")
            flat = pc.list_flatten(issues)
            parents = pc.list_parent_indices(issues)
            nullification = pc.equal(flat.field("action"), "nullify")
            for field in nullified_fields:
                rows = pc.filter(parents, pc.and_(nullification, pc.equal(flat.field("field"), field)))
                values = pc.take(batch.column(field), rows)
                if values.null_count != len(values):
                    raise ValueError(f"Nullification policy did not persist for {field}")
                checked_cells += len(values)
    if checked_cells != actions["nullify"]:
        raise ValueError("Stored nullification counts fail reconciliation")
    return reasons, affected_rows, checked_cells, outliers


def verify_published_layers(summary, producer):
    result = {}
    verified_quality = Counter()
    verified_affected_rows = verified_nullified = verified_outliers = 0
    for name, layer in summary["layers"].items():
        directory = Path(producer) / summary["policy_version"] / name
        files = sorted(directory.rglob("part-*.parquet"))
        counts = Counter()
        partitions = {file.parent.name for file in files}
        for path in files:
            parquet = pq.ParquetFile(path)
            counts.update(records=parquet.metadata.num_rows, bytes=path.stat().st_size)
            if name in {"raw_aligned", "clean"}:
                timestamp = parquet.schema_arrow.field("parsed_event_time").type
                if not pa.types.is_timestamp(timestamp) or timestamp.tz is not None:
                    raise ValueError(f"Wall-clock timestamp type was lost in {name}")
            for batch in parquet.iter_batches(columns=["binary_label"]):
                target = batch.column("binary_label")
                benign = count_matches(target, 0)
                attack = count_matches(target, 1)
                if benign + attack != len(target):
                    raise ValueError(f"Unexpected stored binary target in {name}")
                counts.update(benign=benign, attack=attack)
            if name == "clean":
                reasons, affected, nullified, outliers = validate_clean_file(parquet)
                verified_quality.update(reasons)
                verified_affected_rows += affected
                verified_nullified += nullified
                verified_outliers += outliers
        observed = dict(counts, files=len(files), partitions=len(partitions))
        if any(layer[key] != observed[key] for key in ("files", "records", "bytes", "partitions")):
            raise ValueError(f"Published {name} Parquet differs from producer metadata")
        if any(summary["totals"][key] != observed[key] for key in ("benign", "attack")):
            raise ValueError(f"Published {name} label counts differ from producer evidence")
        result[name] = observed
    for reason in ("nan", "positive_infinity", "negative_infinity", "invalid_negative",
                   "sentinel", "cast_failure", "source_null"):
        if verified_quality[reason] != summary["totals"][f"{reason}_cells"]:
            raise ValueError(f"Stored quality evidence differs for {reason}")
    if verified_affected_rows != summary["totals"]["quality_affected_rows"] or verified_outliers != summary["totals"]["timestamp_outlier"]:
        raise ValueError("Stored quality rows or timestamp outliers differ from producer evidence")
    return {
        "layers": result,
        "clean_cells_verified_null": verified_nullified,
        "clean_quality_affected_rows": verified_affected_rows,
        "clean_quality_reasons": dict(verified_quality),
        "clean_timestamp_outliers": verified_outliers,
    }
