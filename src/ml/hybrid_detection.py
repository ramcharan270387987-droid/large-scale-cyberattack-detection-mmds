"""Fit and freeze study decisions before scoring each Phase 8 evaluation cohort."""

from collections import defaultdict
from hashlib import sha256
from time import monotonic

from pyspark import StorageLevel
from pyspark.ml import PipelineModel
from pyspark.ml.clustering import KMeans
from pyspark.ml.functions import vector_to_array
from pyspark.sql import functions as F

from src.ingest.dataset_audit import atomic_json
from src.ml.clustering_features import fit_transform
from src.ml.cost_sensitive_training import fit_candidate, preprocess, weights, with_preprocessor
from src.ml.model_registry import capture
from src.ml.novelty_normalization import calibrated_column, percentile_column, reference_grid
from src.ml.operational_metrics import burden
from src.ml.phase8_baselines import json_file, retain
from src.ml.phase8_evaluation import bucket, choose_method, eligible, histograms, supports
from src.ml.probability_calibration import isotonic, platt, reliability
from src.ml.risk_triage import summary as triage_summary
from src.ml.score_fusion import learned
from src.ml.split_protocols import crossing_groups, group_sample, group_summary, label_conflicts
from src.ml.threshold_calibration import at_threshold, curves, thresholds, threshold_value
from src.sql.traffic_analytics import compact, require, write_rows
from src.streaming.cluster_scoring import cluster_scores
from src.streaming.model_scoring import probe


def disk(frame):
    return frame.persist(StorageLevel.DISK_ONLY)


def chronology(plan):
    roles = ("train", "probability", "operating", "test")
    periods = [plan[name] for name in roles]
    return all(periods) and all(max(a) < min(b) for a, b in zip(periods, periods[1:]))


def overlap(frame, key):
    return group_summary(crossing_groups(frame, key))


def split_validation(frame, rolling, seed):
    salt = F.pmod(F.xxhash64("predictor_key", F.lit(seed), F.lit("phase8-validation-roles")), F.lit(10000))
    rank = F.col("split_rank")
    middle = (F.when(salt < 6500, "probability").otherwise("meta") if rolling else
              F.when(salt < 3500, "probability").when(salt < 5500, "meta").otherwise("operating"))
    return frame.withColumn("role", F.when(rank == 0, "train").when(rank == 1, middle)
                            .when(rank == 2, "operating" if rolling else "test").otherwise("test"))


def rolling(project, output, spark, prepared, population, names, config, summary):
    plan = config["rolling"][population]
    require(chronology(plan), "Rolling origin is out of order")
    pairs = [value for rank, role in enumerate(("train", "probability", "operating", "test"))
             for day in plan[role] for value in (F.lit(day), F.lit(rank))]
    lookup = F.create_map(*pairs)
    assigned = prepared.withColumn("split_rank", lookup[F.col("source_day")]).where("split_rank IS NOT NULL")
    active, crossing = retain(assigned)
    summary["split"] = {"dates": plan, "prepurge_predictor_groups": crossing, "purged_rows": assigned.count()-active.count()}
    frame = disk(split_validation(active, True, config["seed"]))
    try:
        study(output, spark, frame, {}, None, population, names, config, summary)
    finally:
        active.unpersist()
        frame.unpersist()


def benchmark(project, output, spark, active, saved, km, population, names, config, summary):
    frame = disk(split_validation(active, False, config["seed"]))
    try:
        study(output, spark, frame, saved, km, population, names, config, summary)
    finally:
        active.unpersist()
        frame.unpersist()


def model_score(frame, model, name):
    return model.transform(frame).select(*frame.columns, vector_to_array("probability")[1].alias(name))


def sample_reference(train, config):
    code = F.pmod(F.xxhash64("predictor_key", F.lit(config["seed"]), F.lit("phase8-novelty-reference")), F.lit(10000))
    return train.where(code < config["reference_sample_permyriad"])


def fit_cluster(sample, names, config):
    started = monotonic()
    prep, details = fit_transform(sample.select(*names), names)
    model = KMeans(k=12, maxIter=12, seed=config["seed"], featuresCol="features", predictionCol="cluster").fit(
        prep.transform(sample.select(*names)).select("features"))
    return prep, model, details, monotonic()-started


def train_candidates(sample, operating, prep, train_support, config, population, output):
    bins = config["score_bins"]
    prepared = disk(prep.transform(sample).select("binary_label", "scaled_features", "features"))
    scoring = disk(prep.transform(operating).select("binary_label", "scaled_features", "features"))
    fit_rows = prepared.count()
    all_results, selected = [], {}
    grid = weights(train_support, config["positive_weights"])
    try:
        for algorithm in ("lr", "rf", "gbt"):
            candidates, key_metrics = {}, {}
            candidates_for_algorithm = grid if algorithm != "gbt" else {k: grid[k] for k in ("1", "5")}
            for key, weight in candidates_for_algorithm.items():
                name = f"{algorithm}_w{key}"
                estimator, timing = fit_candidate(prepared, algorithm, weight, config["seed"])
                model = with_preprocessor(prep, estimator)
                scoring_started = monotonic()
                hs, _, _ = histograms(model_score(scoring, estimator, name), [name], bins)
                index, _ = thresholds(hs[name], config)[f"budget_{config['primary_budget']:g}"]
                result = at_threshold(hs[name], index, bins)
                item = {"population": population, "model": name, "weight": weight, "train_rows": fit_rows,
                        "threshold": threshold_value(index, bins), "scoring_seconds": monotonic()-scoring_started,
                        **timing, **result}
                all_results.append(item)
                candidates[name] = model
                key_metrics[name] = (result, timing["fit_seconds"], 1 if key == "1" else 2)
                write_rows(output / "phase8_cost_sensitive_results.csv", all_results)
                print(f"PHASE8 {population} fitted {name} on {fit_rows}", flush=True)
            chosen = choose_method(key_metrics)
            unweighted = f"{algorithm}_w1"
            weighted_best = choose_method({key: row for key, row in key_metrics.items() if key != unweighted})
            for name in {chosen, unweighted, weighted_best}:
                selected[name] = candidates[name]
    finally:
        prepared.unpersist()
        scoring.unpersist()
    return selected, all_results


def encode_columns(frame, models, km, grid, base, calibration, bins):
    for key, model in models.items():
        frame = model_score(frame, model, key)
    frame = cluster_scores(frame, *km).withColumn("novelty", percentile_column(F.col("distance"), grid))
    frame = frame.withColumn("supervised", calibrated_column(F.col(base), calibration["platt"], bins) if calibration else F.col(base))
    if calibration:
        frame = frame.withColumn("platt", F.col("supervised"))
        if "isotonic" in calibration:
            frame = frame.withColumn("isotonic", calibrated_column(F.col(base), calibration["isotonic"], bins))
    return frame


def blend_name(alpha):
    return f"blend_{alpha:g}".replace(".", "_")


def fusion_columns(frame, config, gates, meta):
    s, n = F.col("supervised"), F.col("novelty")
    first = F.col("supervised") >= gates["supervised"]
    second = F.col("novelty") >= gates["novelty"]
    frame = frame.withColumn("or", (first | second).cast("double")).withColumn("and", (first & second).cast("double"))
    for alpha in config["fusion_alphas"]:
        frame = frame.withColumn(blend_name(alpha), alpha * s + (1-alpha) * n)
    if meta:
        a, b = meta["coefficients"]
        z = meta["intercept"] + a*s + b*n
        frame = frame.withColumn("learned", 1 / (1 + F.exp(-F.greatest(F.lit(-35.0), F.least(F.lit(35.0), z)))))
    return frame


def inference(frame, model, km, config, frozen):
    """Return Phase 8 risk evidence from fitted artifacts and a frozen receipt."""
    base = frozen["base"]
    winner = frozen["selected_hybrid"]
    bins = frozen["bins"]
    scored = fusion_columns(encode_columns(frame, {base: model}, km, frozen["reference_grid"], base,
                                           frozen["calibration"], bins), config, frozen["gates"], frozen["learned"])
    high = frozen["operating_bins"][winner]
    lower = frozen["lower_bins"][winner]
    vote = bucket(F.col(winner), bins)
    present = F.greatest(*[F.col(name).isNotNull().cast("int") for name in frozen["feature_order"]])
    decision = F.when((present == 0) | (vote < 0), "ABSTAIN").when(vote >= high, "HIGH_RISK") \
        .when(vote >= lower, "REVIEW_REQUIRED").otherwise("LOW_RISK")
    return scored.withColumn("risk_category", decision).select(
        F.lit(frozen["protocol"] + "-" + frozen["population"]).alias("model_version"),
        F.col(base).alias("supervised_score"), F.col("supervised").alias("calibrated_probability"),
        F.col("cluster").alias("cluster_id"), F.col("distance").alias("centroid_distance_squared"),
        F.col("novelty").alias("novelty_percentile"), F.col(winner).alias("hybrid_score"),
        F.lit(threshold_value(high, bins)).alias("decision_threshold"), "risk_category",
        (F.col("risk_category") == "REVIEW_REQUIRED").alias("review_required"),
        F.when(F.col("risk_category") == "ABSTAIN", "unsupported_input").alias("abstention_reason"))


def record(output, name, rows):
    if rows:
        keys = dict.fromkeys(key for row in rows for key in row)
        write_rows(output / f"phase8_{name}.csv", [{key: row.get(key) for key in keys} for row in rows])


def study(output, spark, frame, previous, km, population, names, config, summary):
    start = monotonic()
    bins = config["score_bins"]
    support = supports(frame)
    total = sum(sum(group.values()) for group in support.values())
    summary["roles"] = support
    counts = compact(frame.groupBy("source_day", "role", "binary_label", "attack_family").count()
                     .orderBy("source_day", "role", "binary_label", "attack_family"), 2000)
    record(output, "split_diagnostics", [{"population": population, **row} for row in counts])
    minimum = config["minimum_per_class"]
    unsupported = [role for role in ("train", "probability", "operating", "test") if not eligible(support.get(role, {}), minimum)]
    if unsupported:
        summary.update(outcome="unsupported", unsupported_roles=unsupported)
        return
    # Predictor keys are deterministically derived from cleaned canonical inputs.
    roles = {"train": 0, "probability": 1, "meta": 2, "operating": 3, "test": 4}
    lookup = F.create_map(*[x for k, i in roles.items() for x in (F.lit(k), F.lit(i))])
    keys = frame.select(lookup[F.col("role")].alias("split_rank"), "predictor_key", "record_fingerprint", "split_feature_key")
    summary["postpurge_overlap"] = {k: overlap(keys, k) for k in ("predictor_key", "record_fingerprint", "split_feature_key")}
    require(not any(v["groups"] for v in summary["postpurge_overlap"].values()), "Retained roles overlap on source keys")
    summary["conflicting_predictor_groups"] = group_summary(label_conflicts(frame))
    train = frame.where("role = 'train'")
    sample = disk(group_sample(train, config).where("sampled"))
    operating = frame.where("role = 'operating'")
    prep, prep_details = preprocess(sample, names)
    summary["preprocessing"] = prep_details
    chosen, cost = train_candidates(sample, operating, prep, support["train"], config, population, output)
    variants = previous | chosen
    train_sample_rows = sample.count()
    # Diagnostic only: hold the benchmark populations fixed after imputation.
    transformed = prep.transform(frame).select(lookup[F.col("role")].alias("split_rank"),
            F.sha2(F.to_json(vector_to_array("features")), 256).alias("imputed_key"))
    summary["imputed_overlap"] = overlap(transformed, "imputed_key")
    reference = disk(sample_reference(train, config))
    new_cluster = None
    if km is None:
        transform, centers, details, fit_time = fit_cluster(sample, names, config)
        new_cluster = PipelineModel(stages=[*transform.stages, centers])
        km = (transform, centers, 0.0)
        summary["rolling_cluster"] = {"fit_seconds": fit_time, "preprocessing": details}
    ref_scores = disk(cluster_scores(reference, *km).select("distance"))
    grid = reference_grid(ref_scores)
    bounds = dict(zip(("0.95", "0.99", "0.999"), ref_scores.approxQuantile("distance", [.95, .99, .999], .0001)))
    summary["reference"] = {"rows": ref_scores.count(), "grid": grid, "thresholds": bounds, "original_p99": km[2] if previous else None}
    ref_scores.unpersist()
    reference.unpersist()
    sample.unpersist()
    primary = f"budget_{config['primary_budget']:g}"
    review = f"budget_{config['review_budget']:g}"
    # Pick the base classifier by operating data prior to probability calibration.
    op_raw = disk(encode_columns(operating, variants, km, grid, next(iter(variants)), {}, bins))
    op_base, _, _ = histograms(op_raw, list(variants), bins)
    fit_cost = {r["model"]: r["fit_seconds"] for r in cost}
    base = choose_method({name: (thresholds(hist, config)[primary][1], fit_cost.get(name, 0), 1)
                          for name, hist in op_base.items()})
    calibration_started = monotonic()
    prob_frame = frame.where("role = 'probability'")
    prob_hist, _, _ = histograms(model_score(prob_frame, variants[base], base), [base], bins)
    calibration = {"platt": platt(prob_hist[base], bins)}
    if len(prob_hist[base]) >= 3:
        calibration["isotonic"] = isotonic(prob_hist[base])
    op = op_raw.withColumn("supervised", calibrated_column(F.col(base), calibration["platt"], bins))
    for name, spec in calibration.items():
        op = op.withColumn(name, calibrated_column(F.col(base), spec, bins))
    gate_hist, _, _ = histograms(op, ["supervised", "novelty"], bins)
    gates = {name: threshold_value(thresholds(hist, config)[primary][0], bins) for name, hist in gate_hist.items()}
    calibrated_seconds = monotonic()-calibration_started
    meta_started = monotonic()
    meta = None
    if eligible(support.get("meta", {}), minimum):
        fitted_meta = encode_columns(frame.where("role = 'meta'"), {base: variants[base]}, km, grid, base, calibration, bins)
        meta = learned(fitted_meta.select("role", "supervised", "novelty", "binary_label"))
    fusion_seconds = monotonic()-meta_started
    op = fusion_columns(op, config, gates, meta)
    methods = [*variants, *calibration, "supervised", "novelty", "or", "and",
               *[blend_name(alpha) for alpha in config["fusion_alphas"]], *(["learned"] if meta else [])]
    op_hist, _, _ = histograms(op, methods, bins)
    selection = {method: thresholds(hist, config) for method, hist in op_hist.items()}
    for name in ("and", "or"):
        literal = at_threshold(op_hist[name], bins // 2, bins)
        selection[name]["literal"] = (bins // 2, literal)
    valid_hybrid = {name: (selection[name]["literal" if name in ("and", "or") else primary][1],
                           int(name == "learned"), 2)
                    for name in methods if (name in ("and", "or", "learned") or name.startswith("blend_"))
                    and selection[name]["literal" if name in ("and", "or") else primary][1]["fpr"] <= config["primary_budget"]}
    winner = choose_method(valid_hybrid)
    selected_threshold = lambda name: selection[name]["literal" if name in ("and", "or") else primary][0]
    threshold_records = [{"population": population, "method": name, "policy": rule, "bin": value,
                          "threshold": threshold_value(value, bins), **row}
                         for name, rules in selection.items() for rule, (value, row) in rules.items()]
    record(output, "threshold_selection", threshold_records)
    record(output, "fusion_selection", [{"population": population, "method": name, "validation_eligible": name in valid_hybrid,
                                        "selected": name == winner, "validation_recall": selection[name]["literal" if name in ("and", "or") else primary][1]["recall"],
                                        "validation_fpr": selection[name]["literal" if name in ("and", "or") else primary][1]["fpr"]}
                                      for name in methods if name in ("supervised", "novelty", "and", "or", "learned") or name.startswith("blend_")])
    freeze = {"population": population, "protocol": config["version"], "base": base, "selected_hybrid": winner,
              "calibration": calibration, "gates": gates, "learned": meta, "feature_order": names,
              "bins": bins, "reference_grid": grid,
              "operating_bins": {name: selected_threshold(name) for name in methods},
              "lower_bins": {name: min(selected_threshold(name), selection[name][review][0]) for name in methods}}
    atomic_json(output / "phase8_frozen.json", freeze)
    summary["frozen_sha256"] = sha256((output / "phase8_frozen.json").read_bytes()).hexdigest()
    print(f"PHASE8 {population} frozen {base} and {winner} before evaluation", flush=True)
    op_raw.unpersist()
    test = frame.where("role = 'test'")
    scoring_started = monotonic()
    scored = disk(fusion_columns(encode_columns(test, variants, km, grid, base, calibration, bins), config, gates, meta)
                  .select(*methods, "source_day", "attack_family", "binary_label", "distance", "cluster",
                          F.greatest(*[F.col(name).isNotNull().cast("int") for name in names]).alias("observed_predictors")))
    hist, slices, inference_seconds = histograms(scored, methods, bins, sliced=True)
    require(all(sum(sum(x) for x in h.values()) == sum(support["test"].values()) for h in hist.values()), "Test accounting differs")
    comparison, budget_rows, families, robustness, curve_rows = [], [], [], [], []
    family_catalog = ("DDoS", "DoS", "Credential brute force", "Bot", "Infiltration", "Web attack")
    for name in methods:
        outcome = at_threshold(hist[name], selected_threshold(name), bins)
        comparison.append({"population": population, "method": name, "selection": "literal" if name in ("or", "and") else primary,
                           "selected_hybrid": name == winner, "threshold": threshold_value(selected_threshold(name), bins),
                           "evaluation_coverage": outcome["rows"] / total, **outcome, **burden(outcome, config["hypothetical_prevalences"])})
        for rule, (index, val) in selection[name].items():
            result = at_threshold(hist[name], index, bins)
            budget_rows.append({"population": population, "method": name, "policy": rule, "threshold": threshold_value(index, bins),
                                "validation_fpr": val["fpr"], "validation_recall": val["recall"], **result})
        for partition, distributions in (("operating", op_hist), ("test", hist)):
            points = curves(distributions[name], bins)
            for i in range(0, bins+1, max(1, bins//128)):
                row = points[i]
                curve_rows.append({"population": population, "partition": partition, "method": name,
                                   "threshold": threshold_value(i, bins),
                                   **{key: row[key] for key in ("fpr", "recall", "precision")}})
        for (method, kind, category), histogram in slices.items():
            if method != name:
                continue
            row = at_threshold(histogram, selected_threshold(name), bins)
            if kind == "source_day":
                robustness.append({"population": population, "method": name, "capture_day": category, **row})
            elif category != "Benign":
                families.append({"population": population, "method": name, "family": category, "support": row["tp"] + row["fn"],
                                 "seen_in_training": any(c["role"] == "train" and c["attack_family"] == category for c in counts),
                                 "recall": row["recall"], "detected": row["tp"]})
        present_families = {row["family"] for row in families if row["method"] == name}
        for family in family_catalog:
            if family not in present_families:
                families.append({"population": population, "method": name, "family": family, "support": 0,
                                 "seen_in_training": any(c["role"] == "train" and c["attack_family"] == family for c in counts),
                                 "recall": None, "detected": 0})
    record(output, "model_comparison", comparison)
    record(output, "false_positive_budgets", budget_rows)
    record(output, "robustness", robustness)
    record(output, "score_curves", curve_rows)
    distances = []
    for label, cutoff in bounds.items():
        value = F.col("distance") > cutoff
        for row in compact(scored.groupBy("binary_label").agg(F.count("*").alias("rows"),
                                               F.count(F.when(value, 1)).alias("flags")), 2):
            distances.append({"population": population, "percentile": label, "cutoff": cutoff, **row})
    record(output, "reference_novelty_flags", distances)
    paired = compact(scored.select("source_day", "attack_family", "binary_label",
                                  (bucket(F.col("supervised"), bins) >= selected_threshold("supervised")).alias("supervised_positive"),
                                  (bucket(F.col(winner), bins) >= selected_threshold(winner)).alias("hybrid_positive"))
                     .groupBy("source_day", "attack_family", "binary_label", "supervised_positive", "hybrid_positive").count(), 400)
    record(output, "paired_disagreement", [{"population": population, **row} for row in paired])
    specs = {"raw": base, **{name: name for name in calibration}}
    cal_rows, cal_bins = [], []
    for method, col in specs.items():
        for partition, distributions in (("operating", op_hist), ("test", hist)):
            stats, rel = reliability(distributions[col], bins, config["reliability_bins"], config["probability_epsilon"])
            cal_rows.append({"population": population, "partition": partition, "method": method, **stats})
            for i, (n, y, q) in enumerate(rel):
                cal_bins.append({"population": population, "partition": partition, "method": method, "bin": i,
                                 "rows": n, "attack_rate": y/n if n else None, "mean_probability": q/n if n else None})
    record(output, "calibration_metrics", cal_rows)
    record(output, "reliability", cal_bins)
    triage = []
    vote = bucket(F.col(winner), bins)
    for rule in ("primary", *[f"budget_{p:g}" for p in config["budgets"]]):
        high = selected_threshold(winner)
        lower = freeze["lower_bins"][winner] if rule == "primary" else min(high, selection[winner][rule][0])
        category = F.when(F.col("observed_predictors") == 0, "ABSTAIN").when(vote >= high, "HIGH_RISK") \
            .when(vote >= lower, "REVIEW_REQUIRED").otherwise("LOW_RISK")
        result = defaultdict(lambda: [0, 0])
        for row in compact(scored.select("binary_label", category.alias("risk")).groupBy("binary_label", "risk").count(), 12):
            result[row["risk"]][row["binary_label"]] = row["count"]
        triage.append({"population": population, "method": winner, "policy": rule,
                       "high": threshold_value(high, bins), "lower": threshold_value(lower, bins), **triage_summary(result)})
        if rule == "primary":
            review_counts = {row["attack_family"]: row["count"] for row in compact(scored.where("binary_label = 1")
                             .withColumn("risk", category).where("risk IN ('REVIEW_REQUIRED','ABSTAIN')")
                             .groupBy("attack_family").count(), 20)}
    for row in families:
        row["hybrid_referred"] = review_counts.get(row["family"], 0) if row["method"] == winner else None
    record(output, "family_recall", families)
    record(output, "triage_metrics", triage)
    best_lr = choose_method({name: (selection[name][primary][1], 0, 1) for name in variants
                             if name.startswith("lr_") or name == "logistic_regression"})
    weighted_names = {name: (selection[name][primary][1], fit_cost.get(name, 0), 1) for name in chosen
                      if not name.endswith("_w1")}
    best_weight = choose_method(weighted_names)
    original = "random_forest" if previous else "rf_w1"
    ablation = [("A", original, bins // 2), ("B", original, selected_threshold(original)), ("C", "platt", selected_threshold("platt")),
                ("D", best_weight, selected_threshold(best_weight)), ("E", "novelty", selected_threshold("novelty")),
                ("F", winner, selected_threshold(winner)), ("G", winner, selected_threshold(winner))]
    record(output, "ablation_results", [{"population": population, "component": ab, "method": name, "threshold": threshold_value(idx, bins),
                                       **at_threshold(hist[name], idx, bins),
                                       "review_rate": triage[0]["review_rate"] if ab == "G" else None,
                                       "automatic_coverage": triage[0]["automatic_coverage"] if ab == "G" else None}
                                      for ab, name, idx in ablation])
    # Independently time the same retained workload under base and selected hybrid scoring.
    def measured(combined):
        tick = monotonic()
        if combined:
            result = fusion_columns(encode_columns(test, {base: variants[base]}, km, grid, base, calibration, bins),
                                    config, gates, meta)
            column = winner
        else:
            result, column = model_score(test, variants[base], "base_runtime"), "base_runtime"
        rows = result.agg(F.count(column).alias("rows"), F.sum(column).alias("check")).first()
        require(rows["rows"] == sum(support["test"].values()), "Runtime scoring lost rows")
        elapsed = monotonic() - tick
        return elapsed, rows["rows"]
    base_time, runtime_rows = measured(False)
    hybrid_time, _ = measured(True)
    saved_meta = {}
    for name in sorted({base, best_weight, best_lr} & set(chosen)):
        saved_meta[name] = capture(chosen[name], name, output, probe(spark, names))
    if new_cluster:
        saved_meta["kmeans"] = capture(new_cluster, "kmeans", output, probe(spark, names), kmeans=True)
    reopened = PipelineModel.load(str(output / saved_meta[base]["artifact"])) if base in saved_meta else variants[base]
    reopened_km = km
    if new_cluster:
        reopened_cluster = PipelineModel.load(str(output / saved_meta["kmeans"]["artifact"]))
        reopened_km = (PipelineModel(stages=reopened_cluster.stages[:-1]), reopened_cluster.stages[-1], km[2])
    probes = probe(spark, names)
    old = inference(probes, variants[base], km, config, freeze).collect()
    new = inference(probes, reopened, reopened_km, config, json_file(output, "phase8_frozen.json")).collect()
    require(old == new and len(new) == 3, "Unified inference reload differs")
    summary.update(registry=saved_meta, best_lr=best_lr, best_weighted=best_weight, selected=winner, supervised_base=base,
                   training_sample_rows=train_sample_rows, scored_rows=sum(support["test"].values()), inference_reload_probes=len(new),
                   preparation_seconds=monotonic()-start)
    record(output, "performance", [{"population": population, "stage": name, "rows": n, "seconds": elapsed,
                                    "rows_per_second": n/elapsed if n else None}
                                   for name, n, elapsed in (("supervised_matched", runtime_rows, base_time),
                                               ("hybrid_matched", runtime_rows, hybrid_time), ("calibration", 0, calibrated_seconds),
                                               ("learned_fusion", 0, fusion_seconds),
                                               ("all_candidate_scoring_and_aggregation", runtime_rows, monotonic()-scoring_started))])
    scored.unpersist()
    print(f"PHASE8 {population} evaluated {summary['scored_rows']} and verified {len(saved_meta)} saved models", flush=True)
