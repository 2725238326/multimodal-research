import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


BASELINE = "siglip_region_mean"
PRIMARY = "siglip_plus_censored"
SHUFFLED = "siglip_plus_shuffled"
EXPOSURE = "siglip_plus_exposure_only"
CONDITIONS = (
    BASELINE,
    "photometric_censored_only",
    PRIMARY,
    "siglip_plus_uncensored",
    EXPOSURE,
    SHUFFLED,
)


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
        "region_ids",
        "scenes",
        "labels",
        "siglip_region_features",
        "censored_photometric_features",
        "uncensored_photometric_features",
        "exposure_only_features",
        "reliable_light_counts",
    }
    missing = sorted(required - data.keys())
    if missing:
        raise ValueError(f"descriptor cache missing {missing}")
    count = len(data["labels"])
    if len(np.unique(data["region_ids"].astype(str))) != count:
        raise ValueError("descriptor cache must contain one row per unique region")
    for key in required - {"region_ids", "scenes", "labels", "reliable_light_counts"}:
        if data[key].ndim != 2 or len(data[key]) != count:
            raise ValueError(f"{key} must be a region-by-feature matrix")
        if not np.isfinite(data[key]).all():
            raise ValueError(f"{key} contains non-finite values")
    if len(data["scenes"]) != count or len(data["reliable_light_counts"]) != count:
        raise ValueError("descriptor arrays have inconsistent region counts")


def deranged_indices(count, rng):
    if count < 2:
        raise ValueError("derangement requires at least two rows")
    original = np.arange(count)
    for _ in range(100):
        candidate = rng.permutation(count)
        if np.all(candidate != original):
            return candidate
    return np.roll(original, 1)


def build_condition_features(condition, data, indices, rng=None, shuffled_source=None):
    indices = np.asarray(indices, dtype=np.int64)
    siglip = data["siglip_region_features"][indices].astype(np.float32)
    censored = data["censored_photometric_features"][indices].astype(np.float32)
    if condition == BASELINE:
        return siglip
    if condition == "photometric_censored_only":
        return censored
    if condition == PRIMARY:
        return np.concatenate([siglip, censored], axis=1)
    if condition == "siglip_plus_uncensored":
        return np.concatenate(
            [siglip, data["uncensored_photometric_features"][indices]], axis=1
        )
    if condition == EXPOSURE:
        return np.concatenate([siglip, data["exposure_only_features"][indices]], axis=1)
    if condition == SHUFFLED:
        if shuffled_source is None:
            if rng is None:
                raise ValueError("shuffled condition requires rng")
            shuffled = censored[deranged_indices(len(indices), rng)]
        else:
            shuffled = np.asarray(shuffled_source, dtype=np.float32)
        return np.concatenate([siglip, shuffled], axis=1)
    raise ValueError(condition)


def classification_metrics(labels, predictions):
    labels = np.asarray(labels).astype(str)
    predictions = np.asarray(predictions).astype(str)
    per_class = []
    for label in np.unique(labels):
        mask = labels == label
        per_class.append(np.mean(predictions[mask] == labels[mask]))
    return {
        "region_accuracy": float(np.mean(predictions == labels)),
        "macro_class_accuracy": float(np.mean(per_class)),
    }


def paired_scene_bootstrap(
    labels, baseline_predictions, candidate_predictions, scenes, draws, seed, ci_level
):
    labels = np.asarray(labels).astype(str)
    baseline_predictions = np.asarray(baseline_predictions).astype(str)
    candidate_predictions = np.asarray(candidate_predictions).astype(str)
    scenes = np.asarray(scenes).astype(str)
    unique_scenes = np.unique(scenes)
    differences = []
    for scene in unique_scenes:
        mask = scenes == scene
        differences.append(
            np.mean(candidate_predictions[mask] == labels[mask])
            - np.mean(baseline_predictions[mask] == labels[mask])
        )
    differences = np.asarray(differences, dtype=np.float64)
    rng = np.random.default_rng(seed)
    sampled = differences[
        rng.integers(0, len(differences), size=(draws, len(differences)))
    ].mean(axis=1)
    alpha = (1.0 - float(ci_level)) / 2.0
    return {
        "mean_scene_delta": float(differences.mean()),
        "pooled_region_accuracy_delta": float(
            np.mean(candidate_predictions == labels)
            - np.mean(baseline_predictions == labels)
        ),
        "ci_low": float(np.quantile(sampled, alpha)),
        "ci_high": float(np.quantile(sampled, 1.0 - alpha)),
        "scene_count": len(unique_scenes),
        "draws": int(draws),
    }


def build_model(train_count, feature_count, config, seed):
    from sklearn.decomposition import PCA
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    components = min(
        int(config["pca_components_max"]), train_count - 1, feature_count
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


def evaluate_seed(data, config, seed, bootstrap_draws):
    from sklearn.model_selection import GroupKFold

    labels = data["labels"].astype(str)
    scenes = data["scenes"].astype(str)
    folds = min(int(config["split"]["folds"]), len(np.unique(scenes)))
    splitter = GroupKFold(n_splits=folds)
    predictions = {
        condition: np.empty(len(labels), dtype=object) for condition in CONDITIONS
    }
    fold_records = []
    for fold, (train, test) in enumerate(
        splitter.split(data["siglip_region_features"], labels, scenes)
    ):
        if set(scenes[train]) & set(scenes[test]):
            raise ValueError("scene overlap detected")
        rng = np.random.default_rng(seed + fold * 1000)
        shuffled_train = data["censored_photometric_features"][train][
            deranged_indices(len(train), rng)
        ]
        shuffled_test = data["censored_photometric_features"][test][
            deranged_indices(len(test), rng)
        ]
        for condition in CONDITIONS:
            train_features = build_condition_features(
                condition,
                data,
                train,
                shuffled_source=shuffled_train if condition == SHUFFLED else None,
            )
            test_features = build_condition_features(
                condition,
                data,
                test,
                shuffled_source=shuffled_test if condition == SHUFFLED else None,
            )
            model = build_model(
                len(train), train_features.shape[1], config["shallow_head"], seed + fold
            )
            model.fit(train_features, labels[train])
            predictions[condition][test] = model.predict(test_features)
        fold_records.append(
            {
                "fold": fold,
                "train_scenes": int(len(np.unique(scenes[train]))),
                "test_scenes": int(len(np.unique(scenes[test]))),
                "train_regions": int(len(train)),
                "test_regions": int(len(test)),
            }
        )
    metrics = {
        condition: classification_metrics(labels, predictions[condition])
        for condition in CONDITIONS
    }
    comparisons = {}
    for condition in CONDITIONS:
        if condition == BASELINE:
            continue
        comparisons[f"{condition}_vs_{BASELINE}"] = paired_scene_bootstrap(
            labels,
            predictions[BASELINE],
            predictions[condition],
            scenes,
            bootstrap_draws,
            seed + CONDITIONS.index(condition) * 10000,
            config["metrics"]["ci_level"],
        )
    comparisons[f"{PRIMARY}_vs_{SHUFFLED}"] = paired_scene_bootstrap(
        labels,
        predictions[SHUFFLED],
        predictions[PRIMARY],
        scenes,
        bootstrap_draws,
        seed + 90000,
        config["metrics"]["ci_level"],
    )
    return {
        "seed": seed,
        "folds": fold_records,
        "conditions": metrics,
        "comparisons": comparisons,
    }, predictions


def decide(seed_results, config):
    threshold = config["thresholds"]
    reasons = []
    for result in seed_results:
        seed = result["seed"]
        primary = result["conditions"][PRIMARY]
        baseline = result["conditions"][BASELINE]
        shuffled = result["conditions"][SHUFFLED]
        exposure = result["conditions"][EXPOSURE]
        comparison = result["comparisons"][f"{PRIMARY}_vs_{BASELINE}"]
        if comparison["pooled_region_accuracy_delta"] < threshold["accuracy_delta_min"]:
            reasons.append(f"seed {seed}: primary accuracy delta below minimum")
        if comparison["ci_low"] <= threshold["accuracy_ci_low_above"]:
            reasons.append(f"seed {seed}: primary scene-bootstrap CI crosses threshold")
        if baseline["macro_class_accuracy"] - primary["macro_class_accuracy"] > threshold[
            "macro_accuracy_drop_no_more_than"
        ]:
            reasons.append(f"seed {seed}: macro accuracy guardrail failed")
        if primary["region_accuracy"] - shuffled["region_accuracy"] < threshold[
            "shuffled_margin_min"
        ]:
            reasons.append(f"seed {seed}: shuffled trajectory margin failed")
        if exposure["region_accuracy"] >= primary["region_accuracy"]:
            reasons.append(f"seed {seed}: exposure-only control matches or exceeds primary")
    return {"status": "Go" if not reasons else "No-Go", "go": not reasons, "reasons": reasons}


def main():
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    data = load_features(args.features)
    validate_features(data)
    summary = {
        "experiment_id": config["experiment_id"],
        "status": "Smoke test" if args.dry_run else "Completed",
        "track": "exploratory_oracle_gate",
        "dry_run": bool(args.dry_run),
        "descriptor_cache_sha256": sha256(args.features),
        "region_count": len(data["labels"]),
        "scene_count": len(np.unique(data["scenes"].astype(str))),
        "class_count": len(np.unique(data["labels"].astype(str))),
        "feature_dimensions": {
            key: int(data[key].shape[1])
            for key in (
                "siglip_region_features",
                "censored_photometric_features",
                "uncensored_photometric_features",
                "exposure_only_features",
            )
        },
        "reliable_light_count_distribution": {
            str(value): int(np.sum(data["reliable_light_counts"] == value))
            for value in np.unique(data["reliable_light_counts"])
        },
        "conditions": list(CONDITIONS),
    }
    if args.dry_run:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return

    seeds = list(config["seeds"])
    if args.seed_limit:
        seeds = seeds[: args.seed_limit]
    bootstrap_draws = args.bootstrap_draws or int(config["metrics"]["bootstrap_draws"])
    seed_results = []
    prediction_records = []
    for seed in seeds:
        result, predictions = evaluate_seed(data, config, seed, bootstrap_draws)
        seed_results.append(result)
        if args.predictions_output:
            for index, region_id in enumerate(data["region_ids"].astype(str)):
                prediction_records.append(
                    {
                        "seed": seed,
                        "region_id": region_id,
                        "scene": str(data["scenes"][index]),
                        "label": str(data["labels"][index]),
                        "reliable_light_count": int(data["reliable_light_counts"][index]),
                        "predictions": {
                            condition: str(predictions[condition][index])
                            for condition in CONDITIONS
                        },
                    }
                )
    aggregate = {}
    for condition in CONDITIONS:
        aggregate[condition] = {
            metric: {
                "mean": float(
                    np.mean([result["conditions"][condition][metric] for result in seed_results])
                ),
                "min": float(
                    np.min([result["conditions"][condition][metric] for result in seed_results])
                ),
                "max": float(
                    np.max([result["conditions"][condition][metric] for result in seed_results])
                ),
            }
            for metric in ("region_accuracy", "macro_class_accuracy")
        }
    summary.update(
        {
            "dry_run": False,
            "seeds": seeds,
            "folds": int(config["split"]["folds"]),
            "bootstrap_draws": bootstrap_draws,
            "aggregate": aggregate,
            "seed_results": seed_results,
        }
    )
    summary["decision"] = decide(seed_results, config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if args.predictions_output:
        args.predictions_output.parent.mkdir(parents=True, exist_ok=True)
        with args.predictions_output.open("w", encoding="utf-8") as handle:
            for record in prediction_records:
                handle.write(json.dumps(record) + "\n")
    print(json.dumps(summary["decision"], indent=2))


if __name__ == "__main__":
    main()
