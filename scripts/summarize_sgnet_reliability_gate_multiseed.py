import argparse
import json
from pathlib import Path

import numpy as np


METRICS = ["rmse", "mae", "boundary_rmse", "flat_rmse", "false_edge_rate"]
CONDITIONS = [
    "clean",
    "shift_x_pos_1",
    "shift_x_pos_2",
    "shift_x_pos_4",
    "shift_y_pos_1",
    "shift_y_pos_2",
    "shift_y_pos_4",
    "scale_098",
    "scale_102",
    "texture_amp_8_b4",
    "texture_amp_16_b4",
]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--seeds", default="20260723,20260724,20260725")
    parser.add_argument("--seed-directory-template", default="seed_{seed}")
    parser.add_argument("--conditions", default=",".join(CONDITIONS))
    parser.add_argument("--skip-training", action="store_true")
    parser.add_argument("--method-name", default="SGNet_spatial_reliability_gate")
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def load_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main():
    args = parse_args()
    seeds = [int(seed) for seed in args.seeds.split(",") if seed]
    selected_conditions = [
        condition for condition in args.conditions.split(",") if condition
    ]
    seed_directories = {
        seed: args.input_root / args.seed_directory_template.format(seed=seed)
        for seed in seeds
    }
    paired = {
        seed: load_json(seed_directories[seed] / "vs_baseline_paired.json")
        for seed in seeds
    }
    training = None
    if not args.skip_training:
        training = {
            seed: load_json(seed_directories[seed] / "training_summary.json")
            for seed in seeds
        }

    conditions = {}
    strict_failures = []
    all_seed_means_improve = True
    for condition in selected_conditions:
        evaluation_summaries = [
            load_json(seed_directories[seed] / "eval" / condition / "summary.json")
            for seed in seeds
        ]
        metric_summaries = {}
        for metric in METRICS:
            records = [paired[seed]["conditions"][condition]["metrics"][metric] for seed in seeds]
            candidate_values = np.asarray([record["candidate_mean"] for record in records])
            relative_changes = np.asarray(
                [record["relative_change_percent"] for record in records]
            )
            significant = [record["paired_95_ci"][1] < 0 for record in records]
            lower_for_all_seeds = all(
                record["candidate_mean"] < record["baseline_mean"] for record in records
            )
            all_seed_means_improve = all_seed_means_improve and lower_for_all_seeds
            for seed, record, passed in zip(seeds, records, significant):
                if not passed:
                    strict_failures.append(
                        {
                            "seed": seed,
                            "condition": condition,
                            "metric": metric,
                            "paired_95_ci": record["paired_95_ci"],
                        }
                    )
            metric_summaries[metric] = {
                "baseline_mean": records[0]["baseline_mean"],
                "candidate_seed_values": candidate_values.tolist(),
                "candidate_seed_mean": float(candidate_values.mean()),
                "candidate_seed_sample_std": float(candidate_values.std(ddof=1)),
                "mean_relative_change_percent": float(relative_changes.mean()),
                "all_seed_means_improve": lower_for_all_seeds,
                "significant_seed_count": int(sum(significant)),
                "all_seed_paired_95_ci_below_zero": all(significant),
            }
        gate_means = np.asarray(
            [summary["gate_statistics"]["mean"] for summary in evaluation_summaries]
        )
        gate_spatial_std = np.asarray(
            [summary["gate_statistics"]["std_mean"] for summary in evaluation_summaries]
        )
        gate_suppressed = np.asarray(
            [
                summary["gate_statistics"]["suppressed_fraction"]
                for summary in evaluation_summaries
            ]
        )
        high_frequency_selection = np.asarray(
            [
                summary["gate_statistics"].get(
                    "high_frequency_selection_fraction",
                    0.0,
                )
                for summary in evaluation_summaries
            ]
        )
        conditions[condition] = {
            "metrics": metric_summaries,
            "gate_statistics": {
                "mean_by_seed": gate_means.tolist(),
                "mean_across_seeds": float(gate_means.mean()),
                "spatial_std_mean_across_seeds": float(gate_spatial_std.mean()),
                "suppressed_fraction_across_seeds": float(gate_suppressed.mean()),
                "high_frequency_selection_fraction_by_seed": (
                    high_frequency_selection.tolist()
                ),
                "high_frequency_selection_fraction_across_seeds": float(
                    high_frequency_selection.mean()
                ),
            },
        }

    gate_training_means = None
    if training is not None:
        gate_training_means = [
            training[seed]["history"][-1]["gate_mean"] for seed in seeds
        ]
    fully_improved_conditions = [
        condition
        for condition, summary in conditions.items()
        if all(
            metric["all_seed_means_improve"]
            for metric in summary["metrics"].values()
        )
    ]
    mixed_conditions = [
        condition
        for condition in selected_conditions
        if condition not in fully_improved_conditions
    ]
    output = {
        "status": "completed",
        "task": "rgb_guided_depth_super_resolution",
        "method": args.method_name,
        "dataset": "RGB-D-D/test2",
        "scale": 16,
        "sample_count": 405,
        "training_dataset": "NYU_v2_train",
        "training_samples_per_seed": 2000,
        "epochs": 1,
        "trainable_parameter_count": 881,
        "seeds": seeds,
        "gate_training_mean_by_seed": gate_training_means,
        "conditions": conditions,
        "decision": {
            "all_seed_means_improve_all_metrics": all_seed_means_improve,
            "strict_all_seed_paired_significance_pass": not strict_failures,
            "strict_failure_count": len(strict_failures),
            "strict_failures": strict_failures,
            "fully_improved_conditions": fully_improved_conditions,
            "mixed_conditions": mixed_conditions,
            "interpretation": (
                "All selected conditions improve every seed mean metric."
                if all_seed_means_improve
                else "Some selected conditions have mixed mean-metric directions."
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps(output["decision"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
