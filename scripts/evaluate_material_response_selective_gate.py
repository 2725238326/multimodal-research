import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


BASELINE = "rgb_confidence_only"
PRIMARY = "response_router"
SHUFFLED = "shuffled_response_router"
RANDOM = "random_score"
CONDITIONS = (BASELINE, PRIMARY, SHUFFLED, RANDOM)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--predictions-output", type=Path)
    parser.add_argument("--bootstrap-draws", type=int)
    parser.add_argument("--seed-limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_features(path):
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key] for key in data.files}


def validate_features(data):
    required = {
        "sample_ids",
        "region_ids",
        "scenes",
        "labels",
        "light_dirs",
        "rgb_features",
    }
    missing = sorted(required - data.keys())
    if missing:
        raise ValueError(f"feature cache missing {missing}")
    count = len(data["labels"])
    if any(len(data[key]) != count for key in required if key != "rgb_features"):
        raise ValueError("feature arrays have inconsistent sample counts")
    if data["rgb_features"].ndim != 2 or len(data["rgb_features"]) != count:
        raise ValueError("rgb_features must be a sample-by-feature matrix")
    region_ids = data["region_ids"].astype(str)
    scenes = data["scenes"].astype(str)
    labels = data["labels"].astype(str)
    for region_id in np.unique(region_ids):
        mask = region_ids == region_id
        if len(np.unique(scenes[mask])) != 1:
            raise ValueError(f"region {region_id} crosses scenes")
        if len(np.unique(labels[mask])) != 1:
            raise ValueError(f"region {region_id} has inconsistent labels")
        if mask.sum() < 2:
            raise ValueError(f"region {region_id} has fewer than two light samples")


def normalized_entropy(probabilities):
    probabilities = np.asarray(probabilities, dtype=np.float64)
    clipped = np.clip(probabilities, 1e-12, 1.0)
    denominator = np.log(probabilities.shape[-1])
    if denominator == 0:
        return np.zeros(probabilities.shape[:-1], dtype=np.float64)
    return -(clipped * np.log(clipped)).sum(axis=-1) / denominator


def response_statistics(features):
    features = np.asarray(features, dtype=np.float64)
    centered = features - features.mean(axis=0, keepdims=True)
    variance_energy = float(np.sqrt(np.mean(centered**2)))
    residual_magnitude = float(np.linalg.norm(centered, axis=1).mean())
    norms = np.linalg.norm(features, axis=1, keepdims=True)
    normalized = features / np.clip(norms, 1e-12, None)
    cosine = normalized @ normalized.T
    upper = cosine[np.triu_indices(len(features), k=1)]
    dispersion = float(np.mean(1.0 - upper)) if len(upper) else 0.0
    return np.asarray(
        [variance_energy, residual_magnitude, dispersion], dtype=np.float64
    )


def region_table(indices, probabilities, data, classes):
    indices = np.asarray(indices, dtype=np.int64)
    probabilities = np.asarray(probabilities, dtype=np.float64)
    if len(indices) != len(probabilities):
        raise ValueError("indices and probabilities differ in length")
    region_ids = data["region_ids"].astype(str)
    scenes = data["scenes"].astype(str)
    labels = data["labels"].astype(str)
    rgb = data["rgb_features"].astype(np.float64)
    records = []
    for region_id in sorted(np.unique(region_ids[indices])):
        local = np.flatnonzero(region_ids[indices] == region_id)
        sample_indices = indices[local]
        mean_probability = probabilities[local].mean(axis=0)
        order = np.argsort(mean_probability)
        confidence = float(mean_probability[order[-1]])
        second = float(mean_probability[order[-2]]) if len(order) > 1 else 0.0
        prediction = str(classes[order[-1]])
        label = str(labels[sample_indices[0]])
        uncertainty = np.asarray(
            [
                1.0 - confidence,
                1.0 - (confidence - second),
                float(normalized_entropy(mean_probability)),
            ],
            dtype=np.float64,
        )
        records.append(
            {
                "region_id": region_id,
                "scene": str(scenes[sample_indices[0]]),
                "label": label,
                "prediction": prediction,
                "error": int(prediction != label),
                "uncertainty": uncertainty,
                "response": response_statistics(rgb[sample_indices]),
            }
        )
    return {
        "region_ids": np.asarray([record["region_id"] for record in records]),
        "scenes": np.asarray([record["scene"] for record in records]),
        "labels": np.asarray([record["label"] for record in records]),
        "predictions": np.asarray([record["prediction"] for record in records]),
        "errors": np.asarray([record["error"] for record in records], dtype=np.int8),
        "uncertainty": np.stack([record["uncertainty"] for record in records]),
        "response": np.stack([record["response"] for record in records]),
    }


def exact_acceptance(scores, region_ids, coverage):
    scores = np.asarray(scores, dtype=np.float64)
    region_ids = np.asarray(region_ids).astype(str)
    accepted_count = min(len(scores), max(1, int(round(float(coverage) * len(scores)))))
    order = np.lexsort((region_ids, scores))
    accepted = np.zeros(len(scores), dtype=bool)
    accepted[order[:accepted_count]] = True
    return accepted


def selective_metrics(labels, predictions, accepted):
    labels = np.asarray(labels).astype(str)
    predictions = np.asarray(predictions).astype(str)
    accepted = np.asarray(accepted, dtype=bool)
    if not accepted.any():
        return {
            "coverage": 0.0,
            "accepted_regions": 0,
            "selective_accuracy": None,
            "macro_selective_accuracy": None,
        }
    per_class = []
    for label in np.unique(labels[accepted]):
        mask = accepted & (labels == label)
        per_class.append(np.mean(predictions[mask] == labels[mask]))
    return {
        "coverage": float(accepted.mean()),
        "accepted_regions": int(accepted.sum()),
        "selective_accuracy": float(np.mean(predictions[accepted] == labels[accepted])),
        "macro_selective_accuracy": float(np.mean(per_class)),
    }


def risk_coverage_auc(labels, predictions, scores, region_ids, minimum, step):
    coverages = np.arange(float(minimum), 1.0 + float(step) / 2.0, float(step))
    coverages = np.clip(coverages, 0.0, 1.0)
    achieved = []
    risks = []
    for coverage in coverages:
        accepted = exact_acceptance(scores, region_ids, coverage)
        metric = selective_metrics(labels, predictions, accepted)
        achieved.append(metric["coverage"])
        risks.append(1.0 - metric["selective_accuracy"])
    span = achieved[-1] - achieved[0]
    auc = float(np.trapz(risks, achieved) / span) if span > 0 else float(risks[0])
    return {
        "minimum_coverage": float(minimum),
        "auc": auc,
        "coverages": [float(value) for value in achieved],
        "risks": [float(value) for value in risks],
    }


def paired_scene_bootstrap(
    labels,
    predictions,
    candidate_accept,
    baseline_accept,
    scenes,
    draws,
    seed,
    ci_level,
):
    labels = np.asarray(labels).astype(str)
    predictions = np.asarray(predictions).astype(str)
    candidate_accept = np.asarray(candidate_accept, dtype=bool)
    baseline_accept = np.asarray(baseline_accept, dtype=bool)
    scenes = np.asarray(scenes).astype(str)
    correct = predictions == labels
    unique_scenes = np.unique(scenes)
    candidate_counts = []
    candidate_correct = []
    baseline_counts = []
    baseline_correct = []
    for scene in unique_scenes:
        mask = scenes == scene
        candidate_counts.append(np.sum(mask & candidate_accept))
        candidate_correct.append(np.sum(mask & candidate_accept & correct))
        baseline_counts.append(np.sum(mask & baseline_accept))
        baseline_correct.append(np.sum(mask & baseline_accept & correct))
    candidate_counts = np.asarray(candidate_counts)
    candidate_correct = np.asarray(candidate_correct)
    baseline_counts = np.asarray(baseline_counts)
    baseline_correct = np.asarray(baseline_correct)
    rng = np.random.default_rng(seed)
    sampled = rng.integers(0, len(unique_scenes), size=(draws, len(unique_scenes)))
    candidate_denominator = candidate_counts[sampled].sum(axis=1)
    baseline_denominator = baseline_counts[sampled].sum(axis=1)
    valid = (candidate_denominator > 0) & (baseline_denominator > 0)
    differences = (
        candidate_correct[sampled].sum(axis=1)[valid] / candidate_denominator[valid]
        - baseline_correct[sampled].sum(axis=1)[valid] / baseline_denominator[valid]
    )
    observed = (
        correct[candidate_accept].mean() - correct[baseline_accept].mean()
    )
    alpha = (1.0 - float(ci_level)) / 2.0
    return {
        "mean_delta": float(observed),
        "ci_low": float(np.quantile(differences, alpha)),
        "ci_high": float(np.quantile(differences, 1.0 - alpha)),
        "scene_count": len(unique_scenes),
        "draws": int(draws),
        "valid_draws": int(len(differences)),
    }


def _aligned_probabilities(model, features, classes):
    raw = model.predict_proba(features)
    output = np.zeros((len(features), len(classes)), dtype=np.float64)
    mapping = {str(label): index for index, label in enumerate(classes)}
    for source, label in enumerate(model.classes_.astype(str)):
        output[:, mapping[label]] = raw[:, source]
    return output


def _build_rgb_head(sample_count, feature_count, config, seed):
    from sklearn.decomposition import PCA
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    components = min(
        int(config["pca_components_max"]), sample_count - 1, feature_count
    )
    return make_pipeline(
        StandardScaler(),
        PCA(n_components=components, whiten=True, random_state=seed),
        LogisticRegression(
            C=float(config["C"]),
            class_weight=config["class_weight"],
            max_iter=int(config["max_iter"]),
            random_state=seed,
        ),
    )


class ConstantScoreModel:
    def __init__(self, score):
        self.score = float(score)

    def predict_score(self, features):
        return np.full(len(features), self.score, dtype=np.float64)


class LogisticScoreModel:
    def __init__(self, model):
        self.model = model

    def predict_score(self, features):
        probabilities = self.model.predict_proba(features)
        error_column = int(np.flatnonzero(self.model.classes_ == 1)[0])
        return probabilities[:, error_column]


def fit_error_router(features, errors, config, seed):
    errors = np.asarray(errors, dtype=np.int8)
    if len(np.unique(errors)) < 2:
        return ConstantScoreModel(errors.mean())
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(
            C=float(config["C"]),
            class_weight=config["class_weight"],
            max_iter=int(config["max_iter"]),
            random_state=seed,
        ),
    )
    model.fit(features, errors)
    return LogisticScoreModel(model)


def _inner_oof_probabilities(train_indices, data, classes, config, folds, seed):
    from sklearn.model_selection import GroupKFold

    train_indices = np.asarray(train_indices, dtype=np.int64)
    rgb = data["rgb_features"].astype(np.float32)
    labels = data["labels"].astype(str)
    scenes = data["scenes"].astype(str)
    group_count = len(np.unique(scenes[train_indices]))
    splitter = GroupKFold(n_splits=min(int(folds), group_count))
    output = np.zeros((len(train_indices), len(classes)), dtype=np.float64)
    for fold, (inner_train, inner_validation) in enumerate(
        splitter.split(
            rgb[train_indices], labels[train_indices], scenes[train_indices]
        )
    ):
        fit_indices = train_indices[inner_train]
        validation_indices = train_indices[inner_validation]
        model = _build_rgb_head(len(fit_indices), rgb.shape[1], config, seed + fold)
        model.fit(rgb[fit_indices], labels[fit_indices])
        output[inner_validation] = _aligned_probabilities(
            model, rgb[validation_indices], classes
        )
    if not np.allclose(output.sum(axis=1), 1.0, atol=1e-6):
        raise ValueError("inner OOF probabilities are not normalized")
    return output


def _concatenate_tables(tables):
    keys = tables[0].keys()
    return {key: np.concatenate([table[key] for table in tables]) for key in keys}


def error_detection_metrics(errors, scores):
    from sklearn.metrics import average_precision_score, roc_auc_score

    if len(np.unique(errors)) < 2:
        return {"auroc": None, "average_precision": None}
    return {
        "auroc": float(roc_auc_score(errors, scores)),
        "average_precision": float(average_precision_score(errors, scores)),
    }


def evaluate_seed(data, config, seed, bootstrap_draws):
    from sklearn.model_selection import GroupKFold

    rgb = data["rgb_features"].astype(np.float32)
    labels = data["labels"].astype(str)
    scenes = data["scenes"].astype(str)
    classes = np.unique(labels)
    split = config["split"]
    outer = GroupKFold(
        n_splits=min(int(split["outer_folds"]), len(np.unique(scenes)))
    )
    tables = []
    score_parts = {condition: [] for condition in CONDITIONS}
    nested_parts = {
        condition: {str(coverage): [] for coverage in config["metrics"]["fixed_coverages"]}
        for condition in CONDITIONS
    }
    fold_records = []
    for fold, (train, test) in enumerate(outer.split(rgb, labels, scenes)):
        if set(scenes[train]) & set(scenes[test]):
            raise ValueError("outer scene overlap detected")
        inner_probabilities = _inner_oof_probabilities(
            train,
            data,
            classes,
            config["rgb_head"],
            split["inner_folds"],
            seed + fold * 100,
        )
        train_table = region_table(train, inner_probabilities, data, classes)
        head = _build_rgb_head(len(train), rgb.shape[1], config["rgb_head"], seed + fold)
        head.fit(rgb[train], labels[train])
        test_probabilities = _aligned_probabilities(head, rgb[test], classes)
        test_table = region_table(test, test_probabilities, data, classes)

        train_baseline = train_table["uncertainty"]
        test_baseline = test_table["uncertainty"]
        train_primary = np.concatenate(
            [train_table["uncertainty"], train_table["response"]], axis=1
        )
        test_primary = np.concatenate(
            [test_table["uncertainty"], test_table["response"]], axis=1
        )
        rng = np.random.default_rng(seed + fold * 1000)
        shuffled_train = train_table["response"][rng.permutation(len(train_table["response"]))]
        shuffled_test = test_table["response"][rng.permutation(len(test_table["response"]))]
        train_shuffled = np.concatenate(
            [train_table["uncertainty"], shuffled_train], axis=1
        )
        test_shuffled = np.concatenate(
            [test_table["uncertainty"], shuffled_test], axis=1
        )
        routers = {
            BASELINE: fit_error_router(
                train_baseline, train_table["errors"], config["router"], seed + fold
            ),
            PRIMARY: fit_error_router(
                train_primary, train_table["errors"], config["router"], seed + fold
            ),
            SHUFFLED: fit_error_router(
                train_shuffled, train_table["errors"], config["router"], seed + fold
            ),
        }
        train_inputs = {
            BASELINE: train_baseline,
            PRIMARY: train_primary,
            SHUFFLED: train_shuffled,
        }
        test_inputs = {
            BASELINE: test_baseline,
            PRIMARY: test_primary,
            SHUFFLED: test_shuffled,
        }
        train_scores = {
            condition: routers[condition].predict_score(train_inputs[condition])
            for condition in routers
        }
        test_scores = {
            condition: routers[condition].predict_score(test_inputs[condition])
            for condition in routers
        }
        train_scores[RANDOM] = rng.random(len(train_table["labels"]))
        test_scores[RANDOM] = rng.random(len(test_table["labels"]))
        for condition in CONDITIONS:
            score_parts[condition].append(test_scores[condition])
            for coverage in config["metrics"]["fixed_coverages"]:
                threshold = float(np.quantile(train_scores[condition], coverage))
                nested_parts[condition][str(coverage)].append(
                    test_scores[condition] <= threshold
                )
        tables.append(test_table)
        fold_records.append(
            {
                "fold": fold,
                "train_scenes": int(len(np.unique(scenes[train]))),
                "test_scenes": int(len(np.unique(scenes[test]))),
                "train_regions": int(len(train_table["labels"])),
                "test_regions": int(len(test_table["labels"])),
            }
        )

    table = _concatenate_tables(tables)
    scores = {key: np.concatenate(value) for key, value in score_parts.items()}
    nested = {
        condition: {
            coverage: np.concatenate(parts)
            for coverage, parts in coverage_parts.items()
        }
        for condition, coverage_parts in nested_parts.items()
    }
    metrics_config = config["metrics"]
    condition_results = {}
    fixed_masks = {condition: {} for condition in CONDITIONS}
    for condition in CONDITIONS:
        fixed = {}
        for coverage in metrics_config["fixed_coverages"]:
            key = str(coverage)
            accepted = exact_acceptance(scores[condition], table["region_ids"], coverage)
            fixed_masks[condition][key] = accepted
            fixed[key] = selective_metrics(
                table["labels"], table["predictions"], accepted
            )
        threshold_metrics = {
            key: selective_metrics(table["labels"], table["predictions"], accepted)
            for key, accepted in nested[condition].items()
        }
        condition_results[condition] = {
            "error_detection": error_detection_metrics(table["errors"], scores[condition]),
            "risk_coverage": risk_coverage_auc(
                table["labels"],
                table["predictions"],
                scores[condition],
                table["region_ids"],
                metrics_config["risk_coverage_min"],
                metrics_config["risk_coverage_step"],
            ),
            "fixed_coverage": fixed,
            "inner_threshold": threshold_metrics,
        }

    comparisons = {"response_vs_rgb_confidence": {}, "response_vs_shuffled": {}}
    for coverage in metrics_config["fixed_coverages"]:
        key = str(coverage)
        comparisons["response_vs_rgb_confidence"][key] = paired_scene_bootstrap(
            table["labels"],
            table["predictions"],
            fixed_masks[PRIMARY][key],
            fixed_masks[BASELINE][key],
            table["scenes"],
            bootstrap_draws,
            seed + int(coverage * 1000),
            metrics_config["ci_level"],
        )
        comparisons["response_vs_shuffled"][key] = paired_scene_bootstrap(
            table["labels"],
            table["predictions"],
            fixed_masks[PRIMARY][key],
            fixed_masks[SHUFFLED][key],
            table["scenes"],
            bootstrap_draws,
            seed + 10000 + int(coverage * 1000),
            metrics_config["ci_level"],
        )
    return {
        "seed": seed,
        "region_count": len(table["labels"]),
        "scene_count": len(np.unique(table["scenes"])),
        "rgb_region_accuracy": float(np.mean(table["predictions"] == table["labels"])),
        "rgb_region_error_count": int(table["errors"].sum()),
        "folds": fold_records,
        "conditions": condition_results,
        "comparisons": comparisons,
    }, table, scores


def decide(seed_results, config):
    thresholds = config["thresholds"]
    reasons = []
    for result in seed_results:
        seed = result["seed"]
        primary_auc = result["conditions"][PRIMARY]["risk_coverage"]["auc"]
        baseline_auc = result["conditions"][BASELINE]["risk_coverage"]["auc"]
        if thresholds["require_lower_risk_coverage_auc"] and primary_auc >= baseline_auc:
            reasons.append(f"seed {seed}: response risk-coverage AUC is not lower")
        for coverage in config["metrics"]["fixed_coverages"]:
            key = str(coverage)
            comparison = result["comparisons"]["response_vs_rgb_confidence"][key]
            if comparison["ci_low"] <= thresholds["require_accuracy_ci_low_above"]:
                reasons.append(f"seed {seed}, coverage {key}: primary CI crosses threshold")
            if thresholds["require_candidate_above_shuffled_ci"]:
                control = result["comparisons"]["response_vs_shuffled"][key]
                if control["ci_low"] <= 0:
                    reasons.append(f"seed {seed}, coverage {key}: shuffled control not excluded")
            primary_macro = result["conditions"][PRIMARY]["fixed_coverage"][key][
                "macro_selective_accuracy"
            ]
            baseline_macro = result["conditions"][BASELINE]["fixed_coverage"][key][
                "macro_selective_accuracy"
            ]
            if baseline_macro - primary_macro > thresholds[
                "macro_selective_accuracy_drop_no_more_than"
            ]:
                reasons.append(f"seed {seed}, coverage {key}: macro guardrail failed")
    return {"status": "Go" if not reasons else "No-Go", "go": not reasons, "reasons": reasons}


def main():
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    data = load_features(args.features)
    validate_features(data)
    dry_summary = {
        "experiment_id": config["experiment_id"],
        "status": "Smoke test",
        "dry_run": True,
        "feature_cache_sha256": sha256(args.features),
        "sample_count": len(data["labels"]),
        "region_count": len(np.unique(data["region_ids"].astype(str))),
        "scene_count": len(np.unique(data["scenes"].astype(str))),
        "feature_dimension": int(data["rgb_features"].shape[1]),
        "conditions": list(CONDITIONS),
    }
    if args.dry_run:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(dry_summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(dry_summary, indent=2))
        return

    seeds = list(config["seeds"])
    if args.seed_limit:
        seeds = seeds[: args.seed_limit]
    bootstrap_draws = args.bootstrap_draws or int(config["metrics"]["bootstrap_draws"])
    seed_results = []
    prediction_records = []
    for seed in seeds:
        result, table, scores = evaluate_seed(data, config, seed, bootstrap_draws)
        seed_results.append(result)
        if args.predictions_output:
            for index, region_id in enumerate(table["region_ids"]):
                prediction_records.append(
                    {
                        "seed": seed,
                        "region_id": str(region_id),
                        "scene": str(table["scenes"][index]),
                        "label": str(table["labels"][index]),
                        "rgb_prediction": str(table["predictions"][index]),
                        "error_scores": {
                            condition: float(scores[condition][index])
                            for condition in CONDITIONS
                        },
                    }
                )
    output = {
        **{key: value for key, value in dry_summary.items() if key != "dry_run"},
        "status": "Completed",
        "track": "exploratory_gate",
        "same_data_hypothesis_warning": True,
        "seeds": seeds,
        "outer_folds": int(config["split"]["outer_folds"]),
        "inner_folds": int(config["split"]["inner_folds"]),
        "bootstrap_draws": bootstrap_draws,
        "seed_results": seed_results,
        "decision": decide(seed_results, config),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    if args.predictions_output:
        args.predictions_output.parent.mkdir(parents=True, exist_ok=True)
        with args.predictions_output.open("w", encoding="utf-8") as handle:
            for record in prediction_records:
                handle.write(json.dumps(record) + "\n")
    print(json.dumps(output["decision"], indent=2))


if __name__ == "__main__":
    main()
