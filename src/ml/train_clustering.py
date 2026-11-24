"""Run a preregistered clustering version against the verified mounted Phase 2 data."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import time

from pyspark import StorageLevel
from pyspark.ml import PipelineModel
from pyspark.ml.functions import vector_to_array
from pyspark.sql import functions as F

from src.ingest.dataset_audit import atomic_json, spark_session
from src.ingest.parquet_pipeline import driver_peak_bytes, parquet_footers, resource_limits
from src.ml.cluster_diagnostics import centroid_dominance, choose_k, compare_assignments, fit_kmeans, silhouette
from src.ml.cluster_evolution import occupancy
from src.ml.clustering_features import clustering_registry, fit_transform, verify_finite_vectors
from src.ml.feature_registry import META, finite
from src.ml.novelty_scoring import calibrate, novelty_metrics, squared_distance
from src.ml.split_protocols import assign_population, crossing_groups, group_summary, mark_retention
from src.ml.train_supervised import verified_input
from src.sql.traffic_analytics import compact, locate_producer, require, write_rows
from src.visualization.clustering_charts import draw_phase5


def read(path):
    return json.loads(path.read_text())


def cohorts(clean, names, phase4, experiment, days):
    # Exactly the Phase 4 predictor digest, with clean timestamps carried only as metadata.
    projected = clean.select(*META, "parsed_event_time", "record_fingerprint", *[finite(x).alias(x) for x in names])
    projected = projected.withColumn("predictor_key", F.unhex(F.sha2(
        F.concat(F.lit(phase4["version"] + "\u0000"), F.to_json(F.array(*names))), 256)))
    if experiment == "G":
        return projected.withColumn("split_rank", F.lit(0))
    return assign_population(projected, experiment, phase4, days)


def pick_reference(frame, config):
    value = F.pmod(F.xxhash64("predictor_key", F.lit(config["seed"]), F.lit("phase5-reference")), F.lit(10000))
    ranked = frame.where(F.col("split_rank") == 0).withColumn("sample_bucket", value)
    boundary = config["training_permyriad"]
    training = ranked.where(F.col("sample_bucket") < boundary)
    probe = ranked.where((F.col("sample_bucket") >= boundary) & (F.col("sample_bucket") < boundary + config["internal_permyriad"]))
    return training, probe


def split_counts(data):
    return compact(data.groupBy("split_rank", "source_day", "binary_label", "attack_family")
                   .count().orderBy("split_rank", "source_day", "binary_label", "attack_family"), 1000)


def verify_phase4_match(rows, experiment, phase4_receipt):
    if experiment == "G":
        return None
    expected = phase4_receipt["protocols"][experiment]
    ranks = ("train", "validation", "test")
    for i, split in enumerate(ranks):
        families, labels = Counter(), Counter()
        for row in rows:
            if row["split_rank"] == i:
                families[row["attack_family"]] += row["count"]
                labels[str(row["binary_label"])] += row["count"]
        support = expected["split_support"][split]
        require(dict(families) == support["families"] and dict(labels) == support["labels"], "Phase 4 retained cohort differs")
    return {"protocol": experiment, "kaggle_version": expected["version"], "checked": "matched split rules and family/binary totals",
            "purged_rows": expected["overlap"]["purged_rows"]}


def profiles(scores, centers, config):
    return compact(scores.groupBy("cluster").agg(
        F.count("*").alias("records"), F.count(F.when(F.col("binary_label") == 1, 1)).alias("attacks"),
        F.avg("score").alias("mean_score"),
        F.percentile_approx("score", 0.95, config["quantile_accuracy"]).alias("score_p95"),
        F.avg("flow_duration").alias("mean_duration_us"), F.avg("tot_fwd_pkts").alias("mean_forward_packets"),
        F.avg("tot_bwd_pkts").alias("mean_backward_packets"), F.avg("totlen_fwd_pkts").alias("mean_forward_bytes"),
        F.avg("totlen_bwd_pkts").alias("mean_backward_bytes"), F.avg("flow_pkts_s").alias("mean_rate")
    ).orderBy("cluster"), centers)


def saved_pipeline(preprocessing, model, probe, target):
    pipeline = PipelineModel(stages=[*preprocessing.stages, model])
    pipeline.write().save(str(target))
    recovered = PipelineModel.load(str(target))
    small = probe.limit(32).cache()
    try:
        expected = sorted(row[0] for row in pipeline.transform(small).select("cluster").collect())
        actual = sorted(row[0] for row in recovered.transform(small).select("cluster").collect())
        require(expected and actual == expected, "Saved pipeline reload did not reproduce assignments")
    finally:
        small.unpersist()
    files = [p for p in target.rglob("*") if p.is_file() and not p.name.endswith(".crc")]
    return {"path": str(target), "reload_rows": len(actual),
            "sha256": {p.relative_to(target).as_posix(): sha256(p.read_bytes()).hexdigest() for p in sorted(files)},
            "bytes": sum(p.stat().st_size for p in files)}


def run(project, input_root, output, scratch, experiment):
    config = read(project / "configs/clustering_experiments.yaml")
    phase4 = read(project / "configs/ml_experiments.yaml")
    phase4_receipt = read(project / "manifests/phase4_models.json")
    manifest = read(project / "manifests/parquet_layers.json")
    policy = read(project / "configs/cleaning.yaml")
    names = clustering_registry(phase4, manifest["feature_columns"])
    output.mkdir(parents=True, exist_ok=True)
    scratch.mkdir(parents=True, exist_ok=True)
    spark = spark_session(config, scratch)
    spark.conf.set("spark.sql.sources.partitionColumnTypeInference.enabled", "false")
    spark.sparkContext.setLogLevel("WARN")
    started = time.monotonic()
    cached = []

    def disk(data):
        result = data.persist(StorageLevel.DISK_ONLY)
        cached.append(result)
        return result

    summary = {"experiment": experiment, "config": config, "status": "running",
               "resources": resource_limits(spark, config, output), "features": names}
    path = output / "phase5_summary.json"
    atomic_json(path, summary)

    def emit(name, rows):
        write_rows(output / f"phase5_{name}.csv", rows)
        print(f"PHASE5 {experiment} {name}: {len(rows)} rows", flush=True)

    try:
        receipt = locate_producer(input_root, manifest["independent_mount"]["summary_sha256"])
        _, summary["input"] = verified_input(spark, receipt, manifest, policy)
        clean_path = receipt.parent.parent / manifest["policy_version"] / "clean"
        require(all(manifest["layers"]["clean"][key] == value for key, value in parquet_footers(clean_path).items()),
                "Clean Parquet metadata differs")
        clean = spark.read.parquet(str(clean_path))
        require(dict(clean.dtypes).get("parsed_event_time") == "timestamp_ntz" and set(names) <= set(clean.columns), "Clean schema changed")
        base = disk(cohorts(clean, names, phase4, experiment, summary["input"]["days"]))
        require(base.count() == summary["input"]["rows"], "Input split lost records")
        observed = split_counts(base)
        label_total = Counter()
        for row in observed:
            label_total[row["binary_label"]] += row["count"]
        require(dict(label_total) == {0: 13484708, 1: 2748235}, "Clean layer binary counts changed")
        expected_families = read(receipt)["completed_files"]
        # The feature-ready layer verifies exact original-label mappings before this check.
        require(len(expected_families) == len({r["source_day"] for r in observed}), "Clean capture-day inventory changed")
        require(base.where("record_fingerprint IS NULL OR temporal_eligibility IS NULL").limit(1).count() == 0,
                "Required record provenance is missing")
        if experiment == "G":
            retained = base
            summary["purge"] = {"groups_before": 0, "groups_after": 0, "rows": 0}
        else:
            crossings = disk(crossing_groups(base, "predictor_key"))
            counts = group_summary(crossings)
            retained = disk(mark_retention(base, crossings, counts["groups"]).where("retained").drop("retained"))
            retained_count = retained.count()
            remaining = group_summary(crossing_groups(retained, "predictor_key"))
            require(remaining["groups"] == 0, "Overlap remains between reference and later cohorts")
            summary["purge"] = {"groups_before": counts["groups"], "groups_after": remaining["groups"],
                                "rows": summary["input"]["rows"] - retained_count}
            base.unpersist(blocking=True)
            crossings.unpersist(blocking=True)
        split = split_counts(retained)
        summary["matched_phase4"] = verify_phase4_match(split, experiment, phase4_receipt)
        if summary["matched_phase4"]:
            require(summary["matched_phase4"]["purged_rows"] == summary["purge"]["rows"], "Phase 4 purge size changed")
        else:
            classified = Counter()
            for row in split:
                classified[row["attack_family"]] += row["count"]
            canonical = phase4_receipt["protocols"]["A"]["split_support"]
            aggregate = Counter()
            for entry in canonical.values():
                aggregate.update(entry["families"])
            require(classified == aggregate, "Clean family frequencies differ")
        emit("cohorts", split)
        reference_rows = sum(row["count"] for row in split if row["split_rank"] == 0)
        train, probe = pick_reference(retained, config)
        train_features, probe_features = disk(train.select(*names)), disk(probe.select(*names))
        train_rows, probe_rows = train_features.count(), probe_features.count()
        require(1 < probe_rows <= config["max_internal_rows"] and train_rows > probe_rows, "Bounded reference cohort differs")
        prep, diagnostics = fit_transform(train_features, names)
        summary["preprocessing"] = diagnostics
        summary["training"] = {"fit_rows": train_rows, "internal_rows": probe_rows, "reference_rows": reference_rows,
                               "share_of_reference": train_rows / reference_rows}
        fit = disk(prep.transform(train_features).select("features"))
        internal = disk(prep.transform(probe_features).select("features"))
        verify_finite_vectors(fit, len(diagnostics["active"]))
        verify_finite_vectors(internal, len(diagnostics["active"]))
        trials, models = [], {}
        for k in config["candidate_k"]:
            model, info = fit_kmeans(fit, k, config, config["seed"])
            require(info["training_rows"] == train_rows, "K-Means training sizes do not reconcile")
            info["silhouette"] = silhouette(model, internal)
            info["silhouette_rows"] = probe_rows
            trials.append(info)
            models[k] = model
            atomic_json(path, summary | {"trials": trials})
            print(f"PHASE5 {experiment} k={k} trained {train_rows} rows, silhouette {info['silhouette']}", flush=True)
        selected = choose_k(trials)
        best = models[selected["k"]]
        summary["selected_k"] = selected["k"]
        summary["trials"] = trials
        emit("model_selection", [row | {"selected": row["k"] == selected["k"]} for row in trials])

        # Evolve both sensitivity models exclusively on the same fit and internal reference rows.
        alternate, alt_seed_info = fit_kmeans(fit, selected["k"], config, config["seed"] + 1)
        seed_ari, _ = compare_assignments(best, alternate, internal.withColumn("alternate_features", F.col("features")))
        linear, linear_prep = fit_transform(train_features, names, transform="linear")
        linear_fit = disk(linear.transform(train_features).select("features"))
        verify_finite_vectors(linear_fit, len(linear_prep["active"]))
        linear_model, linear_info = fit_kmeans(linear_fit, selected["k"], config, config["seed"])
        paired = linear.transform(prep.transform(probe_features).withColumnRenamed("features", "primary_features")
                                  .select(*names, "primary_features"))             .select(F.col("primary_features").alias("features"), F.col("features").alias("alternate_features"))
        paired = disk(paired)
        scale_ari, count = compare_assignments(best, linear_model, paired)
        summary["robustness"] = {"paired_rows": count, "seed_ari": seed_ari, "scale_ari": scale_ari,
                                 "alternate_seed": alt_seed_info, "linear": linear_info,
                                 "linear_silhouette": silhouette(linear_model, paired.select(F.col("alternate_features").alias("features"))),
                                 "dominance": centroid_dominance(best.clusterCenters(), selected["cluster_sizes"], diagnostics["active"])}
        # Distances for threshold calibration come from the disjoint internal training-day sample.
        calibration = calibrate(squared_distance(best, internal).select(F.lit(0).alias("split_rank"), "score"),
                                config["reference_percentiles"], config["quantile_accuracy"])
        summary["calibration"] = calibration
        require(calibration["rows"] == probe_rows, "Thresholds were calibrated on an unexpected cohort")
        for frame in (fit, internal, linear_fit, paired, train_features):
            frame.unpersist(blocking=True)
        assembled = disk(prep.transform(retained).select(
            "source_day", "split_rank", "temporal_eligibility", "parsed_event_time", "binary_label", "attack_family",
            "original_label", "record_fingerprint", "features", "flow_duration", "tot_fwd_pkts", "tot_bwd_pkts",
            "totlen_fwd_pkts", "totlen_bwd_pkts", "flow_pkts_s",
        ))
        verify_finite_vectors(assembled, len(diagnostics["active"]))
        total = sum(row["count"] for row in split)
        scored = disk(squared_distance(best, assembled).drop("features"))
        require(scored.count() == total, "Scoring changed retained count")
        assembled.unpersist(blocking=True)
        require(scored.where("score IS NULL OR isnan(score) OR score < 0 OR abs(score) = double('Infinity')").limit(1).count() == 0,
                "Centroid distance is invalid")
        # Diagnose invalid and missing inputs in the retained train/evaluation populations.
        null_counts = compact(retained.groupBy("split_rank").agg(F.count("*").alias("rows"), *[
            F.count(F.when(F.col(name).isNull(), 1)).alias(name) for name in names
        ]).orderBy("split_rank"), 3)
        emit("transform_diagnostics", [{"split_rank": row["split_rank"], "rows": row["rows"], "feature": name,
                                         "nullified_or_missing": row[name]} for row in null_counts for name in names])
        selected_profiles = profiles(scored, selected["k"], config)
        require(sum(row["records"] for row in selected_profiles) == total, "Cluster profiles lost rows")
        emit("cluster_profiles", [row | {"attack_share": row["attacks"] / row["records"],
                                        "binary_purity": max(row["attacks"], row["records"] - row["attacks"]) / row["records"]}
                                 for row in selected_profiles])
        emit("centroids", [{"cluster": i, "feature": name, "center": float(center[j])}
                          for i, center in enumerate(best.clusterCenters()) for j, name in enumerate(diagnostics["active"])])
        composition = compact(scored.groupBy("source_day", "split_rank", "cluster", "binary_label", "attack_family", "original_label")
                              .count().orderBy("source_day", "cluster", "original_label"), 3500)
        emit("composition", composition)
        require(sum(row["count"] for row in composition) == total, "Composition changed retained count")
        windows = compact(scored.where("temporal_eligibility").withColumn(
            "window_hour", (F.floor(F.hour("parsed_event_time") / config["window_hours"]) * config["window_hours"]).cast("int"))
            .groupBy("source_day", "split_rank", "window_hour", "cluster", "attack_family").count()
            .orderBy("source_day", "window_hour", "cluster", "attack_family"), 6500)
        emit("window_family", windows)
        primary = calibration["cutoffs"][str(config["primary_percentile"])]
        populated, shifts, reference = occupancy(scored, selected["k"], config, primary)
        require(sum(row["records"] for row in populated if row["window_hour"] == -1) == total, "Daily occupancy changed retained count")
        require(sum(row["records"] for row in populated if row["window_hour"] >= 0) == sum(row["count"] for row in windows),
                "Eligible event-time tables differ")
        emit("cluster_occupancy", populated)
        emit("temporal_shift", shifts)
        summary["reference_occupancy"] = reference
        catalog = sorted({entry["family"] for entry in policy["label_mapping"].values() if entry["binary"]})
        emit("novelty_metrics", novelty_metrics(scored, calibration["cutoffs"], catalog, config["rare_support"]))
        histogram = compact(scored.withColumn("score_bin", F.floor(F.log1p("score") * 4).cast("int"))
                            .groupBy("split_rank", "binary_label", "score_bin").count()
                            .orderBy("split_rank", "binary_label", "score_bin"), 1000)
        emit("score_histogram", histogram)
        require(sum(row["count"] for row in histogram) == total, "Distance histogram changed retained count")
        if experiment == "G":
            duplicates = compact(scored.groupBy("record_fingerprint", "cluster").count().groupBy("cluster").agg(
                F.sum("count").alias("records"), F.count("*").alias("exact_digest_representatives"),
                F.sum(F.col("count") - 1).alias("excess")
            ).orderBy("cluster"), selected["k"])
            require(sum(row["excess"] for row in duplicates) == 410707, "Exact duplicate sensitivity differs from Phase 2")
            emit("duplicate_sensitivity", duplicates)
        summary["retained_rows"] = total
        summary["model"] = saved_pipeline(prep, best, probe_features, output / "model")
        summary.update(status="validated", elapsed_seconds=round(time.monotonic() - started, 3))
        summary["resources"]["driver_peak_rss_bytes"] = driver_peak_bytes(spark)
        atomic_json(path, summary)
        summary["figures"] = draw_phase5(output, experiment, project / "reports/phase4_metrics.csv")
        atomic_json(path, summary)
        print(f"PHASE5 {experiment} complete k={selected['k']} trained {train_rows}, scored {total} in {summary['elapsed_seconds']}s", flush=True)
    except Exception as exc:
        summary.update(status="partial", error=f"{type(exc).__name__}: {str(exc)[:500]}")
        atomic_json(path, summary)
        raise
    finally:
        for frame in reversed(cached):
            frame.unpersist()
        spark.stop()
