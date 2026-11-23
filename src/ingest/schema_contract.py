"""Versioned schema, record identity and strict Phase 1 source reconciliation."""

import csv
from dataclasses import dataclass
import json
from pathlib import Path

from pyspark.sql import functions as F

from src.ingest.dataset_audit import normalize_column, record_frame


EXTRA_FIELDS = ("flow_id", "src_ip", "src_port", "dst_ip")
TEXT_METADATA = ("flow_id", "src_ip", "dst_ip")
SOURCE_COUNTS = ("parsed", "headers", "blank", "bad_width_or_quotes", "spark_corrupt")
FEATURE_CONTEXT = ("record_fingerprint", "split_feature_key", "source_day", "temporal_eligibility")
TARGETS = ("original_label", "normalized_label", "binary_label", "attack_family")


@dataclass
class DataContract:
    policy: dict

    @classmethod
    def load(cls, path):
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    @property
    def common_values(self):
        return tuple(name for name in map(normalize_column, self.policy["headers"]["common_80"])
                     if name not in {"label", "timestamp"})

    @property
    def feature_names(self):
        return tuple(name for name in self.common_values if name not in self.policy["excluded_shared_features"])

    def source_variant(self, source_day):
        return "extended_84" if source_day == self.policy["extended_day"] else "common_80"

    def verified_header(self, path, source_day):
        variant = self.source_variant(source_day)
        with path.open("rb") as source:
            line = source.readline(65536)
        if not line.endswith(b"\n"):
            raise ValueError(f"Missing or oversized header in {path.name}")
        decoded = line.decode("utf-8-sig").rstrip("\r\n")
        header = next(csv.reader([decoded], strict=True))
        if header != self.policy["headers"][variant]:
            raise ValueError(f"Unexpected original header/order in {path.name} (expected {variant})")
        return variant, decoded, tuple(map(normalize_column, header))

    def label_lookup(self):
        # Match the exact audited originals. Normalization is for display only.
        pairs = []
        for original, values in self.policy["label_mapping"].items():
            pairs.extend((F.lit(original), F.struct(
                F.lit(values["normalized"]).alias("normalized"),
                F.lit(values["binary"]).cast("byte").alias("binary"),
                F.lit(values["family"]).alias("family"),
            )))
        return F.create_map(*pairs)


def source_records(spark, contract, path, source_day):
    variant, line, names = contract.verified_header(path, source_day)
    frame = record_frame(spark, path, line, len(names))
    return variant, frame.select("raw", "kind", *[F.col(f"c{i}").alias(name) for i, name in enumerate(names)])


def record_key(raw, variant):
    # Use exact UTF-8 source-line text (excluding line break), scoped by header variant.
    return F.unhex(F.sha2(F.concat(F.lit(variant + "\u0000"), raw), 256))


def reconcile_source(observed, expected):
    for name in SOURCE_COUNTS:
        if observed[name] != expected[name]:
            raise ValueError(f"Source count mismatch for {name}: {observed[name]} vs {expected[name]}")
    if observed["physical_lines"] != expected["physical_lines"]:
        raise ValueError("Source physical lines do not reconcile")
    return observed | {"repeated_headers": max(0, observed["headers"] - 1)}


def safe_union(frames):
    """Align only frames that already have matching canonical names and column types."""
    result = frames[0]
    expected = {field.name: field.dataType for field in result.schema}
    for frame in frames[1:]:
        actual = {field.name: field.dataType for field in frame.schema}
        if actual != expected:
            raise ValueError("Canonical frames have different columns or types")
        result = result.unionByName(frame)
    return result
