"""Execute one predeclared Phase 4 protocol over the verified Kaggle input."""

from collections import Counter
import json
from hashlib import sha256
from pathlib import Path
import time

from pyspark import StorageLevel
from pyspark.ml import PipelineModel
from pyspark.ml.classification import GBTClassifier, LogisticRegression, RandomForestClassifier
from pyspark.ml.functions import vector_to_array
from pyspark.sql import functions as F

from src.ingest.dataset_audit import atomic_json, spark_session
from src.ingest.parquet_pipeline import driver_peak_bytes, parquet_footers, resource_limits
from src.ml.baselines import baseline_score, fit_baselines
from src.ml.evaluate_supervised import estimator_score, evaluate, family_recall
from src.ml.feature_registry import predictor_input, registry
from src.ml.model_explanations import explain
from src.ml.preprocessing import fit_preprocessing, verify_vectors
from src.ml.split_protocols import (
    SPLITS, assign_population, crossing_groups, group_sample, group_summary, label_conflicts, mark_retention,
)
from src.sql.traffic_analytics import compact, label_grouping, locate_producer, require, write_rows


AUDIT_KEYS = ("predictor_key", "record_fingerprint", "split_feature_key")


def read_json(path):
    return json.loads(path.read_text())


def verified_input(spark, receipt, manifest, clean_policy):
    root = receipt.parent.parent
    evidence = read_json(receipt)
    require(evidence["status"] == "validated" and evidence["dataset"] == manifest["dataset"], "Producer dataset differs")
    require(evidence["policy_version"] == clean_policy["version"] == manifest["policy_version"], "Cleaning policy differs")
    path = root / manifest["policy_version"] / "feature_ready"
    footer = parquet_footers(path)
    expected = manifest["layers"]["feature_ready"]
    require(all(footer[key] == expected[key] for key in footer), "Saved feature-ready Parquet differs")
    days = sorted(x.name.split("=", 1)[1] for x in path.glob("source_day=*") if x.is_dir())
    require(len(days) == expected["partitions"] == 10, "Verified input must contain ten days")
    frame = spark.read.parquet(str(path))
    extras = {"source_day", "binary_label", "original_label", "normalized_label", "attack_family",
              "temporal_eligibility", "record_fingerprint", "split_feature_key"}
    require(set(frame.columns) == set(manifest["feature_columns"]) | extras, "Input schema differs")
    types = dict(frame.dtypes)
    require(all(types.get(name) == "double" for name in manifest["feature_columns"]), "Input feature types differ")
    require(types["binary_label"] == "tinyint" and types["source_day"] == "string", "Label or day type differs")
    label_totals, day_totals = Counter(), Counter()
    ineligible = 0
    for row in compact(label_grouping(frame), 500):
        mapping = clean_policy["label_mapping"].get(row["original_label"])
        require(mapping and (mapping["binary"], mapping["family"], mapping["normalized"]) ==
                (row["binary_label"], row["attack_family"], row["normalized_label"]), "Label integrity check failed")
        require(row["temporal_eligibility"] in (True, False), "Temporal flag is unavailable")
        label_totals[row["binary_label"]] += row["count"]
        day_totals[row["source_day"]] += row["count"]
        ineligible += 0 if row["temporal_eligibility"] else row["count"]
    require(dict(label_totals) == {0: 13484708, 1: 2748235} and sum(label_totals.values()) == 16232943,
            "Input row or label totals differ")
    require(ineligible == 14, "Timestamp eligibility count differs")
    require(dict(day_totals) == {row["source_day"]: row["counts"]["canonical_rows"] for row in evidence["completed_files"]},
            "Capture-day totals differ")
    return frame, {"path": str(path), "days": days, "totals": dict(label_totals), "rows": footer["records"],
                   "temporally_flagged": ineligible, "policy_version": manifest["policy_version"],
                   "receipt_sha256": sha256(receipt.read_bytes()).hexdigest(), "producer": manifest["producer"]}


def split_rows(frame, config):
    return compact(frame.groupBy("split_rank", "retained", "sampled", "source_day", "binary_label",
                                 "attack_family", "original_label").count()
                   .orderBy("split_rank", "retained", "sampled", "source_day", "original_label"), 1500)


def supports(rows, rank, sample_only=False):
    labels, families, originals = Counter(), Counter(), Counter()
    for row in rows:
        if row["split_rank"] == rank and row["retained"] and (not sample_only or row["sampled"]):
            labels[row["binary_label"]] += row["count"]
            families[row["attack_family"]] += row["count"]
            originals[row["original_label"]] += row["count"]
    return {"labels": dict(labels), "families": dict(families), "original_labels": dict(originals), "rows": sum(labels.values())}


def create_estimator(name, params, config):
    common = {"labelCol": "binary_label"}
    if name == "logistic_regression":
        return LogisticRegression(**common, **params, featuresCol="scaled_features", standardization=False, tol=1e-5)
    trees = {"featuresCol": "features", "seed": config["seed"], "maxBins": 24, "maxMemoryInMB": 192, **common}
    if name == "random_forest":
        return RandomForestClassifier(**trees, **params, featureSubsetStrategy="sqrt", subsamplingRate=1.0)
    if name == "gradient_boosted_trees":
        return GBTClassifier(**trees, **params, subsamplingRate=1.0, minInstancesPerNode=30)
    raise ValueError(f"Unknown estimator {name}")


def select_trial(trials):
    candidates = [row for row in trials if row["pr_auc"] is not None]
    if not candidates:
        raise ValueError("No trial has a defined validation PR-AUC")
    return max(candidates, key=lambda row: (row["pr_auc"], -row["trial"]))


def save_and_reload(estimator, preprocessor, model_name, dataset, directory):
    pipeline = PipelineModel(stages=[*preprocessor.stages, estimator])
    directory.parent.mkdir(parents=True, exist_ok=True)
    pipeline.write().save(str(directory))
    reopened = PipelineModel.load(str(directory))
    require(len(reopened.stages) == len(pipeline.stages), "Reloaded pipeline has a different stage count")
    def scores(model):
        return sorted(row[0] for row in model.transform(dataset).select(vector_to_array("probability")[1]).collect())

    probe = dataset.orderBy("predictor_key", "binary_label").limit(24).persist()
    try:
        before, after = scores(pipeline), scores(reopened)
        require(bool(before) and before == after, "Reloaded probabilities differ")
    finally:
        probe.unpersist()
    files = sorted(x for x in directory.rglob("*") if x.is_file() and not x.name.endswith(".crc"))
    return {"path": str(directory), "model": model_name, "reload_probe_rows": len(after),
            "model_bytes": sum(x.stat().st_size for x in files), "model_files": len(files),
            "sha256": {x.relative_to(directory).as_posix(): sha256(x.read_bytes()).hexdigest() for x in files}}


def run(project, input_root, output, scratch, protocol):
    output.mkdir(parents=True, exist_ok=True)
    scratch.mkdir(parents=True, exist_ok=True)
    config = read_json(project / "configs/ml_experiments.yaml")
    manifest = read_json(project / "manifests/parquet_layers.json")
    policy = read_json(project / "configs/cleaning.yaml")
    atomic_json(output / "phase4_config.json", config)
    spark = spark_session(config, scratch)
    spark.conf.set("spark.sql.sources.partitionColumnTypeInference.enabled", "false")
    spark.sparkContext.setLogLevel("WARN")
    start = time.monotonic()
    cached = []

    def disk(frame):
        result = frame.persist(StorageLevel.DISK_ONLY)
        cached.append(result)
        return result

    metrics, family_rows, performance = [], [], []
    summary = {"protocol": protocol, "version": config["version"], "status": "running",
               "design": config["protocols"][protocol], "resources": resource_limits(spark, config, output),
               "models": [], "trial_selections": {}}
    atomic_json(output / "phase4_summary.json", summary)

    def checkpoint():
        for name, rows in (("metrics", metrics), ("family_recall", family_rows), ("training_performance", performance)):
            if rows:
                write_rows(output / f"phase4_{name}.csv", rows)
        atomic_json(output / "phase4_summary.json", summary)

    try:
        receipt = locate_producer(input_root, manifest["independent_mount"]["summary_sha256"])
        frame, summary["input"] = verified_input(spark, receipt, manifest, policy)
        names = registry(config, manifest["feature_columns"])
        summary["registered_predictors"] = names
        print(f"PHASE4 {protocol} verified {summary['input']['rows']} input rows", flush=True)
        assigned = disk(assign_population(predictor_input(frame, names, config["version"]), protocol, config, summary["input"]["days"]))
        require(assigned.count() == summary["input"]["rows"], "Assignment lost input rows")
        groups = disk(crossing_groups(assigned, "predictor_key"))
        before = group_summary(groups)
        if protocol == "A":
            require(before["groups"] == 0, "Grouped random assignment crossed an equivalence boundary")
        retained = disk(group_sample(mark_retention(assigned, groups, before["groups"]), config))
        counts = split_rows(retained, config)
        require(sum(row["count"] for row in counts) == summary["input"]["rows"], "Split partition rows do not reconcile")
        write_rows(output / "phase4_split_diagnostics.csv", counts)
        active_source = retained.where("retained")
        after = {key: group_summary(crossing_groups(active_source, key)) for key in AUDIT_KEYS}
        require(all(count["groups"] == 0 for count in after.values()), "Retained partition keys overlap")
        summary["overlap"] = {"predictor_before": before, "after": after,
                              "purged_rows": sum(row["count"] for row in counts if not row["retained"])}
        summary["retained_predictor_conflicts"] = group_summary(label_conflicts(active_source))
        summary["split_support"] = {name: supports(counts, rank) for rank, name in enumerate(SPLITS)}
        sample_support = supports(counts, 0, True)
        summary["train_sample_support"] = sample_support
        require(all(summary["split_support"][name]["rows"] > 0 for name in SPLITS), "A required partition is empty")
        require(set(sample_support["labels"]) == {0, 1}, "Training sample lacks a binary class")
        print(f"PHASE4 {protocol} retained split sizes {[(n, summary['split_support'][n]['rows']) for n in SPLITS]}", flush=True)
        assigned.unpersist(blocking=True)
        groups.unpersist(blocking=True)
        training = active_source.where("split_rank = 0")
        sample = disk(training.where("sampled"))
        calibration = fit_baselines(training, summary["split_support"]["train"]["labels"].get(0, 0),
                                    summary["split_support"]["train"]["labels"].get(1, 0))
        summary["baselines"] = calibration
        eval_sources = {name: active_source.where(F.col("split_rank") == rank) for rank, name in enumerate(SPLITS) if rank}
        catalogs = {name: values["binary"] for name, values in policy["label_mapping"].items()}
        families = {values["family"]: values["binary"] for values in policy["label_mapping"].values()}

        def record(scored, model, cohort, split, training_seconds):
            result, groups = evaluate(scored, config)
            require(result["rows"] == summary["split_support"][split]["rows"], f"{model} prediction population differs")
            support = summary["train_sample_support"] if cohort == "group_sample" else summary["split_support"]["train"]
            stamp = {"protocol": protocol, "model": model, "training_cohort": cohort, "split": split}
            metrics.append(stamp | {"training_rows": support["rows"], "training_seconds": training_seconds} | result)
            family_rows.extend(stamp | row for row in family_recall(
                groups, support["families"], support["original_labels"], families, catalogs, config["rare_family_minimum"]))
            checkpoint()
            print(f"PHASE4 {protocol} {model} {cohort} {split}: {result['rows']} scored", flush=True)
            return result

        # Baseline validation scores are established before fitting complex estimators.
        for model, params in calibration.items():
            record(baseline_score(eval_sources["validation"], model, params), model, "full_train_baseline", "validation", 0.0)

        prep_started = time.monotonic()
        common, scaled, summary["preprocessing"] = fit_preprocessing(sample, names)
        summary["preprocess_seconds"] = round(time.monotonic() - prep_started, 3)
        columns = ["split_rank", "sampled", "binary_label", "attack_family", "original_label", "features", "scaled_features"]
        design = disk(scaled.transform(active_source).select(*columns))
        require(design.count() == sum(v["rows"] for v in summary["split_support"].values()), "Transform lost retained rows")
        verify_vectors(design, len(summary["preprocessing"]["active"]))
        vector_keys = design.select("split_rank", F.unhex(F.sha2(F.to_json(vector_to_array("features")), 256)).alias("vector_key"))
        summary["post_imputation_overlap"] = group_summary(crossing_groups(vector_keys, "vector_key"))
        checkpoint()
        sampled_vector = disk(design.where("split_rank = 0 AND sampled"))
        sampled_vector.count()
        vectors = {name: design.where(F.col("split_rank") == rank) for rank, name in enumerate(SPLITS)}
        winners = []
        for name, choices in config["trials"].items():
            runs, fitted = [], {}
            for i, params in enumerate(choices, 1):
                fit_start = time.monotonic()
                model = create_estimator(name, params, config).fit(sampled_vector)
                fit_s = round(time.monotonic() - fit_start, 3)
                measured, _ = evaluate(estimator_score(model, vectors["validation"]), config)
                require(measured["rows"] == summary["split_support"]["validation"]["rows"], "Trial validation rows differ")
                row = {"protocol": protocol, "model": name, "training_cohort": "group_sample", "trial": i,
                       "parameters": params, "training_rows": sample_support["rows"], "training_seconds": fit_s,
                       "validation_inference_seconds": measured["prediction_seconds"], "pr_auc": measured["pr_auc"],
                       "roc_auc": measured["roc_auc"], "validation_f1": measured["f1"], "selected": False}
                runs.append(row)
                performance.append(row)
                fitted[i] = model
                checkpoint()
                print(f"PHASE4 {protocol} {name} trial {i}: fit {fit_s:.3f}s, validation PR-AUC {measured['pr_auc']}", flush=True)
            selected = select_trial(runs)
            selected["selected"] = True
            summary["trial_selections"][name] = {"trial": selected["trial"], "parameters": selected["parameters"]}
            winners.append((name, "group_sample", fitted[selected["trial"]], selected["training_seconds"]))

        # Additional full-training LR uses fixed sample-selected settings and the same train-only transform.
        name = "logistic_regression"
        params = summary["trial_selections"][name]["parameters"]
        fit_start = time.monotonic()
        full_model = create_estimator(name, params, config).fit(vectors["train"])
        full_time = round(time.monotonic() - fit_start, 3)
        full_result, _ = evaluate(estimator_score(full_model, vectors["validation"]), config)
        performance.append({"protocol": protocol, "model": name, "training_cohort": "full_train_refit", "trial": 1,
                            "parameters": params, "training_rows": summary["split_support"]["train"]["rows"],
                            "training_seconds": full_time, "validation_inference_seconds": full_result["prediction_seconds"],
                            "pr_auc": full_result["pr_auc"], "roc_auc": full_result["roc_auc"],
                            "validation_f1": full_result["f1"], "selected": True})
        winners.append((name, "full_train_refit", full_model, full_time))
        summary["selection_frozen"] = True
        checkpoint()
        print(f"PHASE4 {protocol} selections frozen before testing", flush=True)

        for baseline, params in calibration.items():
            record(baseline_score(eval_sources["test"], baseline, params), baseline, "full_train_baseline", "test", 0.0)
        for name, cohort, model, fit_s in winners:
            for split in ("validation", "test"):
                record(estimator_score(model, vectors[split]), name, cohort, split, fit_s)
            stored = save_and_reload(model, scaled if name == "logistic_regression" else common, name,
                                     sample, output / "models" / f"{name}_{cohort}")
            stored.update(training_cohort=cohort, training_seconds=fit_s,
                          parameters=summary["trial_selections"][name]["parameters"],
                          explanation=explain(model, name, summary["preprocessing"]["active"]))
            summary["models"].append(stored)
            checkpoint()
        summary.update(status="validated", elapsed_seconds=round(time.monotonic() - start, 3))
        summary["resources"]["driver_peak_rss_bytes"] = driver_peak_bytes(spark)
        checkpoint()
        print(f"PHASE4 {protocol} complete: {len(metrics)} evaluation rows, {len(summary['models'])} reloaded pipelines "
              f"in {summary['elapsed_seconds']}s", flush=True)
    except Exception as exc:
        summary.update(status="partial", error=f"{type(exc).__name__}: {str(exc)[:500]}",
                       elapsed_seconds=round(time.monotonic() - start, 3))
        checkpoint()
        raise
    finally:
        for item in reversed(cached):
            item.unpersist()
        spark.stop()
