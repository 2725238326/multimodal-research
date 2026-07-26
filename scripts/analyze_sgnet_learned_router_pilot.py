import argparse
import json
from pathlib import Path

import numpy as np


METRICS = ["rmse", "mae", "boundary_rmse", "flat_rmse", "false_edge_rate"]
CORE_METRICS = ["rmse", "boundary_rmse", "false_edge_rate"]
SEEDS = [20260723, 20260724, 20260725]
CONDITIONS = ["clean", "texture_amp_8_b4"]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--train-images", type=int, default=200)
    return parser.parse_args()


def load_records(path):
    records = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            records[record["name"]] = record
    return records


def relative_change(candidate, baseline):
    return float(100.0 * (candidate - baseline) / baseline)


def main():
    args = parse_args()
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    baseline = {
        condition: load_records(
            args.input_root
            / "confirmatory"
            / "baseline"
            / condition
            / "per_sample.jsonl"
        )
        for condition in CONDITIONS
    }
    names = sorted(baseline["clean"])
    train_names = names[: args.train_images]
    holdout_names = names[args.train_images :]
    full = {}
    high = {}
    hard = {}
    reference_means = {}
    for seed in SEEDS:
        full[seed] = {}
        high[seed] = {}
        hard[seed] = {}
        for condition in CONDITIONS:
            full[seed][condition] = load_records(
                args.input_root
                / "confirmatory"
                / f"seed_{seed}"
                / "eval"
                / condition
                / "per_sample.jsonl"
            )
            high[seed][condition] = load_records(
                args.input_root
                / f"high_frequency_seed_{seed}"
                / "eval"
                / condition
                / "per_sample.jsonl"
            )
            hard[seed][condition] = load_records(
                args.input_root
                / f"adaptive_seed_{seed}"
                / "eval"
                / condition
                / "per_sample.jsonl"
            )
        reference_means[seed] = float(
            np.mean(
                [full[seed]["clean"][name]["gate_mean"] for name in names]
            )
        )

    def features(record, seed):
        return [
            reference_means[seed] - record["gate_mean"],
            record["gate_std"],
            record["gate_suppressed_fraction"],
        ]

    objectives = {}
    for objective in ("rmse", "balanced_five_metric"):
        train_features = []
        train_labels = []
        for condition in CONDITIONS:
            baseline_means = {
                metric: float(
                    np.mean([baseline[condition][name][metric] for name in names])
                )
                for metric in METRICS
            }
            for name in train_names:
                train_features.append(
                    features(full[20260723][condition][name], 20260723)
                )
                if objective == "rmse":
                    choose_high = (
                        high[20260723][condition][name]["rmse"]
                        < full[20260723][condition][name]["rmse"]
                    )
                else:
                    utility_difference = np.mean(
                        [
                            (
                                high[20260723][condition][name][metric]
                                - full[20260723][condition][name][metric]
                            )
                            / baseline_means[metric]
                            for metric in METRICS
                        ]
                    )
                    choose_high = utility_difference < 0
                train_labels.append(choose_high)

        model = make_pipeline(
            StandardScaler(),
            LogisticRegression(
                C=1.0,
                max_iter=1000,
                random_state=20260723,
            ),
        )
        model.fit(train_features, train_labels)
        condition_output = {}
        all_baseline_pass = True
        all_core_vs_hard_pass = True
        for seed in SEEDS:
            condition_output[str(seed)] = {}
            for condition in CONDITIONS:
                predicted_high = model.predict(
                    [
                        features(full[seed][condition][name], seed)
                        for name in holdout_names
                    ]
                ).astype(bool)
                metric_output = {}
                for metric in METRICS:
                    baseline_values = np.asarray(
                        [baseline[condition][name][metric] for name in holdout_names]
                    )
                    hard_values = np.asarray(
                        [hard[seed][condition][name][metric] for name in holdout_names]
                    )
                    candidate_values = np.asarray(
                        [
                            (
                                high[seed][condition][name][metric]
                                if use_high
                                else full[seed][condition][name][metric]
                            )
                            for name, use_high in zip(holdout_names, predicted_high)
                        ]
                    )
                    candidate_mean = float(candidate_values.mean())
                    baseline_mean = float(baseline_values.mean())
                    hard_mean = float(hard_values.mean())
                    all_baseline_pass = (
                        all_baseline_pass and candidate_mean <= baseline_mean
                    )
                    if metric in CORE_METRICS:
                        all_core_vs_hard_pass = (
                            all_core_vs_hard_pass and candidate_mean <= hard_mean
                        )
                    metric_output[metric] = {
                        "candidate_vs_baseline_percent": relative_change(
                            candidate_mean, baseline_mean
                        ),
                        "hard_vs_baseline_percent": relative_change(
                            hard_mean, baseline_mean
                        ),
                        "candidate_vs_hard_percent": relative_change(
                            candidate_mean, hard_mean
                        ),
                    }
                condition_output[str(seed)][condition] = {
                    "high_frequency_fraction": float(predicted_high.mean()),
                    "metrics": metric_output,
                }
        classifier = model[-1]
        objectives[objective] = {
            "training_high_frequency_fraction": float(np.mean(train_labels)),
            "standardized_coefficients": classifier.coef_[0].tolist(),
            "standardized_intercept": classifier.intercept_.tolist(),
            "conditions": condition_output,
            "decision": {
                "all_holdout_metrics_vs_baseline_pass": all_baseline_pass,
                "all_holdout_core_metrics_vs_hard_pass": all_core_vs_hard_pass,
                "go": all_baseline_pass and all_core_vs_hard_pass,
            },
        }

    oracle = {}
    for condition in CONDITIONS:
        oracle[condition] = {}
        for seed in SEEDS:
            baseline_values = {
                metric: np.asarray(
                    [baseline[condition][name][metric] for name in holdout_names]
                )
                for metric in METRICS
            }
            full_values = {
                metric: np.asarray(
                    [full[seed][condition][name][metric] for name in holdout_names]
                )
                for metric in METRICS
            }
            high_values = {
                metric: np.asarray(
                    [high[seed][condition][name][metric] for name in holdout_names]
                )
                for metric in METRICS
            }
            rmse_high = high_values["rmse"] < full_values["rmse"]
            oracle[condition][str(seed)] = {
                "rmse_oracle_high_frequency_fraction": float(rmse_high.mean()),
                "rmse_selected_metrics_vs_baseline_percent": {
                    metric: relative_change(
                        float(
                            np.where(
                                rmse_high,
                                high_values[metric],
                                full_values[metric],
                            ).mean()
                        ),
                        float(baseline_values[metric].mean()),
                    )
                    for metric in METRICS
                },
            }

    output = {
        "status": "completed",
        "phase": "exploratory_image_holdout_pilot",
        "dataset": "RGB-D-D/test2",
        "scale": 16,
        "training_seed": 20260723,
        "train_image_count": len(train_names),
        "holdout_image_count": len(holdout_names),
        "features": [
            "clean_reference_minus_gate_mean",
            "gate_spatial_std",
            "gate_suppressed_fraction",
        ],
        "oracle": oracle,
        "objectives": objectives,
        "decision": {
            "oracle_has_headroom": True,
            "pilot_router_go": any(
                record["decision"]["go"] for record in objectives.values()
            ),
            "interpretation": "Train on a separate dataset before external confirmation"
            if any(record["decision"]["go"] for record in objectives.values())
            else "Pilot is mixed; do not tune further on this holdout",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps(output["decision"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
