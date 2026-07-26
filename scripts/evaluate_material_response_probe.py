import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np


CONDITIONS = (
    "single_rgb",
    "multi_light_mean",
    "multi_light_mean_variance",
    "pairwise_response",
    "rgb_albedo_concat",
    "rgb_albedo_residual",
    "shuffled_light_pair",
    "wrong_region_albedo",
    "random_residual",
    "equal_parameter_branch",
)
PRIMARY = "pairwise_response"
BASELINE = "single_rgb"
CONTROLS = (
    "shuffled_light_pair",
    "wrong_region_albedo",
    "random_residual",
    "equal_parameter_branch",
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--predictions-output", type=Path)
    parser.add_argument("--bootstrap-draws", type=int)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def region_statistics(region_ids, features):
    means = np.empty_like(features)
    stds = np.empty_like(features)
    for region_id in np.unique(region_ids):
        mask = region_ids == region_id
        means[mask] = features[mask].mean(axis=0)
        stds[mask] = features[mask].std(axis=0)
    return means, stds


def _permuted_region_values(values, region_ids, rng):
    unique = np.unique(region_ids)
    permuted = unique.copy()
    if len(unique) > 1:
        while True:
            rng.shuffle(permuted)
            if np.all(permuted != unique):
                break
    mapping = dict(zip(unique, permuted))
    output = np.empty_like(values)
    for target, source in mapping.items():
        target_indices = np.flatnonzero(region_ids == target)
        source_indices = np.flatnonzero(region_ids == source)
        source_mean = values[source_indices].mean(axis=0)
        output[target_indices] = source_mean
    return output


def build_condition_features(condition, rgb, albedo, region_ids, seed):
    mean, std = region_statistics(region_ids, rgb)
    rng = np.random.default_rng(seed)
    if condition == "single_rgb":
        return rgb
    if condition == "multi_light_mean":
        return mean
    if condition == "multi_light_mean_variance":
        return np.concatenate([rgb, mean, std], axis=1)
    if condition == "pairwise_response":
        return np.concatenate([rgb, mean, rgb - mean, std], axis=1)
    if condition == "rgb_albedo_concat":
        return np.concatenate([rgb, albedo], axis=1)
    if condition == "rgb_albedo_residual":
        return np.concatenate([rgb, rgb - albedo], axis=1)
    if condition == "shuffled_light_pair":
        shuffled_mean = _permuted_region_values(mean, region_ids, rng)
        shuffled_std = _permuted_region_values(std, region_ids, rng)
        return np.concatenate([rgb, shuffled_mean, rgb - shuffled_mean, shuffled_std], axis=1)
    if condition == "wrong_region_albedo":
        wrong = _permuted_region_values(albedo, region_ids, rng)
        return np.concatenate([rgb, wrong], axis=1)
    if condition == "random_residual":
        random = rng.standard_normal(rgb.shape).astype(np.float32)
        return np.concatenate([rgb, random], axis=1)
    if condition == "equal_parameter_branch":
        dimension = rgb.shape[1]
        projections = []
        for _ in range(3):
            signs = rng.choice((-1.0, 1.0), size=dimension).astype(np.float32)
            projections.append(rgb * signs)
        return np.concatenate([rgb, *projections], axis=1)
    raise ValueError(condition)


def majority(values):
    labels, counts = np.unique(values, return_counts=True)
    return str(labels[np.argmax(counts)])


def metrics(labels, predictions, region_ids, light_dirs):
    region_records = []
    for region_id in np.unique(region_ids):
        mask = region_ids == region_id
        region_records.append(
            {
                "region_id": str(region_id),
                "label": str(labels[mask][0]),
                "prediction": majority(predictions[mask]),
                "flip": len(np.unique(predictions[mask])) > 1,
            }
        )
    region_accuracy = np.mean(
        [record["label"] == record["prediction"] for record in region_records]
    )
    per_class = []
    for label in np.unique(labels):
        records = [record for record in region_records if record["label"] == label]
        per_class.append(
            np.mean([record["prediction"] == label for record in records])
        )
    light_accuracies = []
    for light_dir in np.unique(light_dirs):
        mask = light_dirs == light_dir
        light_accuracies.append(np.mean(predictions[mask] == labels[mask]))
    return {
        "sample_accuracy": float(np.mean(predictions == labels)),
        "mean_region_accuracy": float(region_accuracy),
        "macro_class_accuracy": float(np.mean(per_class)),
        "region_flip_rate": float(np.mean([record["flip"] for record in region_records])),
        "worst_light_accuracy": float(np.min(light_accuracies)),
        "region_count": len(region_records),
    }


def scene_metric(labels, predictions, region_ids, light_dirs, scenes, metric_name):
    output = {}
    for scene in np.unique(scenes):
        mask = scenes == scene
        output[str(scene)] = metrics(
            labels[mask], predictions[mask], region_ids[mask], light_dirs[mask]
        )[metric_name]
    return output


def paired_scene_bootstrap(baseline, candidate, draws, seed, ci_level):
    scenes = sorted(set(baseline) & set(candidate))
    differences = np.asarray([candidate[s] - baseline[s] for s in scenes])
    rng = np.random.default_rng(seed)
    samples = differences[rng.integers(0, len(differences), size=(draws, len(differences)))]
    means = samples.mean(axis=1)
    alpha = (1.0 - ci_level) / 2.0
    return {
        "mean_delta": float(differences.mean()),
        "ci_low": float(np.quantile(means, alpha)),
        "ci_high": float(np.quantile(means, 1.0 - alpha)),
        "scene_count": len(scenes),
        "draws": draws,
    }


def load_features(path):
    with np.load(path) as data:
        return {key: data[key] for key in data.files}


def main():
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    data = load_features(args.features)
    required = {
        "sample_ids",
        "region_ids",
        "scenes",
        "labels",
        "light_dirs",
        "rgb_features",
        "albedo_features",
    }
    missing = sorted(required - data.keys())
    if missing:
        raise ValueError(f"feature cache missing {missing}")
    if args.dry_run:
        summary = {
            "status": "smoke_test",
            "dry_run": True,
            "sample_count": len(data["labels"]),
            "region_count": len(np.unique(data["region_ids"])),
            "scene_count": len(np.unique(data["scenes"])),
            "feature_dimension": int(data["rgb_features"].shape[1]),
            "conditions": list(CONDITIONS),
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return

    from sklearn.decomposition import PCA
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupKFold
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    labels = data["labels"].astype(str)
    scenes = data["scenes"].astype(str)
    region_ids = data["region_ids"].astype(str)
    light_dirs = data["light_dirs"]
    rgb = data["rgb_features"].astype(np.float32)
    albedo = data["albedo_features"].astype(np.float32)
    seeds = config.get("seeds", [config["seed"]])
    head = config["shallow_head"]
    folds = min(int(config["split"]["folds"]), len(np.unique(scenes)))
    predictions_by_seed = {}
    records = []
    for seed in seeds:
        predictions_by_seed[str(seed)] = {}
        splitter = GroupKFold(n_splits=folds)
        for condition in CONDITIONS:
            oof = np.empty(len(labels), dtype=object)
            for fold, (train, test) in enumerate(splitter.split(rgb, labels, groups=scenes)):
                train_features = build_condition_features(
                    condition, rgb[train], albedo[train], region_ids[train], seed + fold
                )
                test_features = build_condition_features(
                    condition,
                    rgb[test],
                    albedo[test],
                    region_ids[test],
                    seed + fold
                    if condition == "equal_parameter_branch"
                    else seed + 100 + fold,
                )
                components = min(
                    int(head["pca_components_max"]),
                    len(train) - 1,
                    train_features.shape[1],
                )
                model = make_pipeline(
                    StandardScaler(),
                    PCA(n_components=components, whiten=True, random_state=seed),
                    LogisticRegression(
                        C=float(head["C"]),
                        l1_ratio=0.0,
                        class_weight=head["class_weight"],
                        max_iter=int(head["max_iter"]),
                        random_state=seed,
                    ),
                )
                model.fit(train_features, labels[train])
                oof[test] = model.predict(test_features)
            predictions_by_seed[str(seed)][condition] = oof.astype(str)
            metric = metrics(labels, oof, region_ids, light_dirs)
            records.append({"seed": seed, "condition": condition, **metric})

    aggregate = {}
    for condition in CONDITIONS:
        condition_records = [r for r in records if r["condition"] == condition]
        aggregate[condition] = {
            key: {
                "mean": float(np.mean([record[key] for record in condition_records])),
                "min": float(np.min([record[key] for record in condition_records])),
                "max": float(np.max([record[key] for record in condition_records])),
            }
            for key in (
                "sample_accuracy",
                "mean_region_accuracy",
                "macro_class_accuracy",
                "region_flip_rate",
                "worst_light_accuracy",
            )
        }

    bootstrap_draws = args.bootstrap_draws or int(config["metrics"]["bootstrap_draws"])
    ci_level = float(config["thresholds"]["ci_level"])
    comparisons = {}
    for condition in CONDITIONS:
        if condition == BASELINE:
            continue
        accuracy_stats = []
        flip_stats = []
        for seed in seeds:
            baseline_predictions = predictions_by_seed[str(seed)][BASELINE]
            candidate_predictions = predictions_by_seed[str(seed)][condition]
            baseline_accuracy = scene_metric(
                labels,
                baseline_predictions,
                region_ids,
                light_dirs,
                scenes,
                "mean_region_accuracy",
            )
            candidate_accuracy = scene_metric(
                labels,
                candidate_predictions,
                region_ids,
                light_dirs,
                scenes,
                "mean_region_accuracy",
            )
            baseline_flip = scene_metric(
                labels,
                baseline_predictions,
                region_ids,
                light_dirs,
                scenes,
                "region_flip_rate",
            )
            candidate_flip = scene_metric(
                labels,
                candidate_predictions,
                region_ids,
                light_dirs,
                scenes,
                "region_flip_rate",
            )
            accuracy_stats.append(
                paired_scene_bootstrap(
                    baseline_accuracy,
                    candidate_accuracy,
                    bootstrap_draws,
                    seed,
                    ci_level,
                )
            )
            flip_stats.append(
                paired_scene_bootstrap(
                    baseline_flip,
                    candidate_flip,
                    bootstrap_draws,
                    seed + 1000,
                    ci_level,
                )
            )
        comparisons[condition] = {
            "region_accuracy_delta_vs_single_rgb": accuracy_stats,
            "region_flip_delta_vs_single_rgb": flip_stats,
        }

    thresholds = config["thresholds"]
    primary_accuracy = comparisons[PRIMARY]["region_accuracy_delta_vs_single_rgb"]
    primary_flip = comparisons[PRIMARY]["region_flip_delta_vs_single_rgb"]
    control_margin = min(
        aggregate[PRIMARY]["mean_region_accuracy"]["mean"]
        - aggregate[control]["mean_region_accuracy"]["mean"]
        for control in CONTROLS
    )
    macro_drop = (
        aggregate[BASELINE]["macro_class_accuracy"]["mean"]
        - aggregate[PRIMARY]["macro_class_accuracy"]["mean"]
    )
    go = (
        all(
            stat["mean_delta"] >= thresholds["go_accuracy_delta_min"]
            and stat["ci_low"] > 0
            for stat in primary_accuracy
        )
        and all(
            stat["mean_delta"] <= thresholds["go_flip_rate_delta_max"]
            and stat["ci_high"] < 0
            for stat in primary_flip
        )
        and control_margin >= thresholds["control_margin_min"]
        and macro_drop <= thresholds["macro_accuracy_drop_no_more_than"]
    )
    decision = {
        "status": "Go" if go else "No-Go",
        "go": go,
        "primary_condition": PRIMARY,
        "minimum_control_margin": float(control_margin),
        "macro_accuracy_drop": float(macro_drop),
    }
    output = {
        "experiment_id": config["experiment_id"],
        "status": "Completed",
        "track": "exploratory_gate",
        "feature_cache_sha256": sha256(args.features),
        "sample_count": len(labels),
        "region_count": len(np.unique(region_ids)),
        "scene_count": len(np.unique(scenes)),
        "seeds": seeds,
        "folds": folds,
        "conditions": aggregate,
        "comparisons": comparisons,
        "decision": decision,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    if args.predictions_output:
        args.predictions_output.parent.mkdir(parents=True, exist_ok=True)
        with args.predictions_output.open("w", encoding="utf-8") as handle:
            for index, sample_id in enumerate(data["sample_ids"].astype(str)):
                record = {
                    "sample_id": sample_id,
                    "region_id": region_ids[index],
                    "scene": scenes[index],
                    "label": labels[index],
                    "predictions": {
                        seed: {
                            condition: predictions_by_seed[seed][condition][index]
                            for condition in CONDITIONS
                        }
                        for seed in predictions_by_seed
                    },
                }
                handle.write(json.dumps(record) + "\n")
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    main()
