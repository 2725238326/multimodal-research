import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

try:
    from scripts.evaluate_photometric_trajectory_gate import (
        build_model,
        classification_metrics,
        deranged_indices,
        paired_scene_bootstrap,
    )
except ModuleNotFoundError:
    from evaluate_photometric_trajectory_gate import (
        build_model,
        classification_metrics,
        deranged_indices,
        paired_scene_bootstrap,
    )


SAMPLE_BASELINE = "siglip_sample_majority"
REGION_BASELINE = "siglip_region_mean"
PRIMARY = "siglip_plus_censored"
EXPOSURE = "siglip_plus_exposure_only"
SHUFFLED = "siglip_plus_shuffled"
CONDITIONS = (
    SAMPLE_BASELINE,
    REGION_BASELINE,
    "photometric_censored_only",
    PRIMARY,
    EXPOSURE,
    SHUFFLED,
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-descriptors", type=Path, required=True)
    parser.add_argument("--train-sample-features", type=Path, required=True)
    parser.add_argument("--test-descriptors", type=Path, required=True)
    parser.add_argument("--test-sample-features", type=Path, required=True)
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


def load_npz(path):
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key] for key in data.files}


def validate_descriptor_pair(train, test):
    required = {
        "region_ids",
        "scenes",
        "labels",
        "siglip_region_features",
        "censored_photometric_features",
        "exposure_only_features",
    }
    for name, data in (("train", train), ("test", test)):
        missing = sorted(required - data.keys())
        if missing:
            raise ValueError(f"{name} descriptors missing {missing}")
        if len(np.unique(data["region_ids"].astype(str))) != len(data["region_ids"]):
            raise ValueError(f"{name} descriptors contain duplicate regions")
    if set(train["scenes"].astype(str)) & set(test["scenes"].astype(str)):
        raise ValueError("train/test scene overlap")
    for key in (
        "siglip_region_features",
        "censored_photometric_features",
        "exposure_only_features",
    ):
        if train[key].shape[1] != test[key].shape[1]:
            raise ValueError(f"train/test feature dimension mismatch for {key}")


def validate_sample_features(data, descriptor_regions, name):
    required = {"region_ids", "scenes", "labels", "rgb_features"}
    missing = sorted(required - data.keys())
    if missing:
        raise ValueError(f"{name} sample features missing {missing}")
    sample_regions = set(data["region_ids"].astype(str))
    if sample_regions != set(descriptor_regions.astype(str)):
        raise ValueError(f"{name} sample/descriptor region mismatch")
    if data["rgb_features"].ndim != 2 or len(data["rgb_features"]) != len(data["labels"]):
        raise ValueError(f"{name} RGB sample feature shape invalid")


def majority(values):
    labels, counts = np.unique(np.asarray(values).astype(str), return_counts=True)
    return str(labels[np.argmax(counts)])


def aggregate_sample_predictions(sample_regions, predictions, target_regions):
    sample_regions = np.asarray(sample_regions).astype(str)
    predictions = np.asarray(predictions).astype(str)
    output = []
    for region in np.asarray(target_regions).astype(str):
        mask = sample_regions == region
        if not mask.any():
            raise ValueError(f"sample predictions missing region {region}")
        output.append(majority(predictions[mask]))
    return np.asarray(output)


def region_features(condition, data, shuffled=None):
    siglip = data["siglip_region_features"].astype(np.float32)
    censored = data["censored_photometric_features"].astype(np.float32)
    if condition == REGION_BASELINE:
        return siglip
    if condition == "photometric_censored_only":
        return censored
    if condition == PRIMARY:
        return np.concatenate([siglip, censored], axis=1)
    if condition == EXPOSURE:
        return np.concatenate(
            [siglip, data["exposure_only_features"].astype(np.float32)], axis=1
        )
    if condition == SHUFFLED:
        if shuffled is None:
            raise ValueError("shuffled features required")
        return np.concatenate([siglip, np.asarray(shuffled, dtype=np.float32)], axis=1)
    raise ValueError(condition)


def evaluate_seed(train_desc, train_samples, test_desc, test_samples, config, seed, draws):
    train_labels = train_desc["labels"].astype(str)
    test_labels = test_desc["labels"].astype(str)
    test_scenes = test_desc["scenes"].astype(str)
    predictions = {}

    sample_model = build_model(
        len(train_samples["labels"]),
        train_samples["rgb_features"].shape[1],
        config["rgb_sample_head"],
        seed,
    )
    sample_model.fit(
        train_samples["rgb_features"].astype(np.float32),
        train_samples["labels"].astype(str),
    )
    sample_predictions = sample_model.predict(
        test_samples["rgb_features"].astype(np.float32)
    )
    predictions[SAMPLE_BASELINE] = aggregate_sample_predictions(
        test_samples["region_ids"], sample_predictions, test_desc["region_ids"]
    )

    rng = np.random.default_rng(seed)
    shuffled_train = train_desc["censored_photometric_features"][
        deranged_indices(len(train_labels), rng)
    ]
    shuffled_test = test_desc["censored_photometric_features"][
        deranged_indices(len(test_labels), rng)
    ]
    for condition in CONDITIONS:
        if condition == SAMPLE_BASELINE:
            continue
        train_features = region_features(
            condition,
            train_desc,
            shuffled=shuffled_train if condition == SHUFFLED else None,
        )
        test_features = region_features(
            condition,
            test_desc,
            shuffled=shuffled_test if condition == SHUFFLED else None,
        )
        model = build_model(
            len(train_labels), train_features.shape[1], config["region_head"], seed
        )
        model.fit(train_features, train_labels)
        predictions[condition] = model.predict(test_features)

    metrics = {
        condition: classification_metrics(test_labels, predictions[condition])
        for condition in CONDITIONS
    }
    comparisons = {}
    for baseline_index, baseline in enumerate((SAMPLE_BASELINE, REGION_BASELINE, SHUFFLED)):
        comparisons[f"{PRIMARY}_vs_{baseline}"] = paired_scene_bootstrap(
            test_labels,
            predictions[baseline],
            predictions[PRIMARY],
            test_scenes,
            draws,
            seed + baseline_index * 10000,
            config["metrics"]["ci_level"],
        )
    return {"seed": seed, "conditions": metrics, "comparisons": comparisons}, predictions


def decide(seed_results, config):
    thresholds = config["thresholds"]
    reasons = []
    for result in seed_results:
        seed = result["seed"]
        primary = result["conditions"][PRIMARY]
        baselines = [result["conditions"][SAMPLE_BASELINE], result["conditions"][REGION_BASELINE]]
        strongest = max(baselines, key=lambda item: item["region_accuracy"])
        for baseline in (SAMPLE_BASELINE, REGION_BASELINE):
            comparison = result["comparisons"][f"{PRIMARY}_vs_{baseline}"]
            if comparison["pooled_region_accuracy_delta"] < thresholds["accuracy_delta_min"]:
                reasons.append(f"seed {seed}: primary delta below minimum vs {baseline}")
            if comparison["ci_low"] <= thresholds["accuracy_ci_low_above"]:
                reasons.append(f"seed {seed}: CI crosses threshold vs {baseline}")
        if strongest["macro_class_accuracy"] - primary["macro_class_accuracy"] > thresholds[
            "macro_accuracy_drop_no_more_than"
        ]:
            reasons.append(f"seed {seed}: macro accuracy guardrail failed")
        if primary["region_accuracy"] - result["conditions"][SHUFFLED]["region_accuracy"] < thresholds[
            "shuffled_margin_min"
        ]:
            reasons.append(f"seed {seed}: shuffled margin failed")
        if result["conditions"][EXPOSURE]["region_accuracy"] >= primary["region_accuracy"]:
            reasons.append(f"seed {seed}: exposure-only matches or exceeds primary")
    return {"status": "Go" if not reasons else "No-Go", "go": not reasons, "reasons": reasons}


def main():
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    train_desc = load_npz(args.train_descriptors)
    test_desc = load_npz(args.test_descriptors)
    train_samples = load_npz(args.train_sample_features)
    test_samples = load_npz(args.test_sample_features)
    validate_descriptor_pair(train_desc, test_desc)
    validate_sample_features(train_samples, train_desc["region_ids"], "train")
    validate_sample_features(test_samples, test_desc["region_ids"], "test")
    summary = {
        "experiment_id": config["experiment_id"],
        "status": "Smoke test" if args.dry_run else "Completed",
        "track": "confirmatory_external_stress_test",
        "dry_run": bool(args.dry_run),
        "input_sha256": {
            "train_descriptors": sha256(args.train_descriptors),
            "train_sample_features": sha256(args.train_sample_features),
            "test_descriptors": sha256(args.test_descriptors),
            "test_sample_features": sha256(args.test_sample_features),
        },
        "train": {
            "samples": len(train_samples["labels"]),
            "regions": len(train_desc["labels"]),
            "scenes": len(np.unique(train_desc["scenes"].astype(str))),
        },
        "test": {
            "samples": len(test_samples["labels"]),
            "regions": len(test_desc["labels"]),
            "scenes": len(np.unique(test_desc["scenes"].astype(str))),
            "classes": len(np.unique(test_desc["labels"].astype(str))),
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
    draws = args.bootstrap_draws or int(config["metrics"]["bootstrap_draws"])
    seed_results = []
    prediction_records = []
    for seed in seeds:
        result, predictions = evaluate_seed(
            train_desc, train_samples, test_desc, test_samples, config, seed, draws
        )
        seed_results.append(result)
        if args.predictions_output:
            for index, region in enumerate(test_desc["region_ids"].astype(str)):
                prediction_records.append(
                    {
                        "seed": seed,
                        "region_id": region,
                        "scene": str(test_desc["scenes"][index]),
                        "label": str(test_desc["labels"][index]),
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
                "mean": float(np.mean([r["conditions"][condition][metric] for r in seed_results])),
                "min": float(np.min([r["conditions"][condition][metric] for r in seed_results])),
                "max": float(np.max([r["conditions"][condition][metric] for r in seed_results])),
            }
            for metric in ("region_accuracy", "macro_class_accuracy")
        }
    summary.update(
        {
            "dry_run": False,
            "seeds": seeds,
            "bootstrap_draws": draws,
            "aggregate": aggregate,
            "seed_results": seed_results,
        }
    )
    summary["decision"] = decide(seed_results, config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if args.predictions_output:
        args.predictions_output.parent.mkdir(parents=True, exist_ok=True)
        with args.predictions_output.open("w", encoding="utf-8") as stream:
            for record in prediction_records:
                stream.write(json.dumps(record) + "\n")
    print(json.dumps(summary["decision"], indent=2))


if __name__ == "__main__":
    main()
