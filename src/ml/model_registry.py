"""Save selected Spark pipelines and verify same-probe scoring and file hashes."""

from hashlib import sha256
from pathlib import Path
from time import monotonic

from pyspark.ml import PipelineModel
from pyspark.ml.functions import vector_to_array


def capture(model, name, output, probes, kmeans=False, timings=None):
    target = output / "models" / name
    start = monotonic()
    model.write().save(str(target))
    saved = monotonic() - start
    start = monotonic()
    opened = PipelineModel.load(str(target))
    reloaded = monotonic() - start
    if timings is not None:
        timings.update(serialization_seconds=saved, reload_seconds=reloaded)

    def score(pipeline):
        scored = pipeline.transform(probes)
        if kmeans:
            return [(r[0], tuple(r[1])) for r in scored.select("cluster", "features").collect()]
        return [tuple(r[0]) for r in scored.select(vector_to_array("probability")).collect()]

    before, after = score(model), score(opened)
    if not before or before != after:
        raise ValueError(f"Reloaded model {name} scored differently")
    payloads = [p for p in Path(target).rglob("*") if p.is_file() and not p.name.endswith(".crc")]
    return {"artifact": target.relative_to(output).as_posix(), "reload_probe_rows": len(after),
            "preprocessing_stages": [type(stage).__name__ for stage in model.stages[:-1]],
            "bytes": sum(p.stat().st_size for p in payloads),
            "sha256": {p.relative_to(target).as_posix(): sha256(p.read_bytes()).hexdigest() for p in sorted(payloads)}}
