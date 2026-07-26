import argparse
import json
from pathlib import Path

import numpy as np


METRICS = ["rmse", "mae", "boundary_rmse", "flat_rmse", "false_edge_rate"]
PATTERNS = ["sinusoidal", "noise"]
AMPLITUDES = [8, 16]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--seeds", default="20260723,20260724,20260725")
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    parser.add_argument("--bootstrap-seed", type=int, default=20260723)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def load_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_records(path):
    records = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            records[record["name"]] = record
    return records


def bootstrap_interval(values, samples, rng):
    values = np.asarray(values, dtype=np.float64)
    draws = np.empty(samples, dtype=np.float64)
    for start in range(0, samples, 1000):
        block = min(1000, samples - start)
        indices = rng.integers(0, len(values), size=(block, len(values)))
        draws[start : start + block] = values[indices].mean(axis=1)
    return [float(value) for value in np.percentile(draws, [2.5, 97.5])]


def main():
    args = parse_args()
    seeds = [int(value) for value in args.seeds.split(",") if value]
    rng = np.random.default_rng(args.bootstrap_seed)
    conditions = {}
    all_seed_means_improve = True
    strict_failure_count = 0

    for pattern in PATTERNS:
        for amplitude in AMPLITUDES:
            condition = f"{pattern}_amp_{amplitude}"
            baseline_summary = load_json(
                args.input_root / "baseline" / condition / "summary.json"
            )
            baseline = load_records(
                args.input_root / "baseline" / condition / "per_sample.jsonl"
            )
            names = sorted(baseline)
            seed_summaries = []
            seed_records = []
            for seed in seeds:
                seed_root = args.input_root / f"adaptive_seed_{seed}" / condition
                seed_summaries.append(load_json(seed_root / "summary.json"))
                records = load_records(seed_root / "per_sample.jsonl")
                if records.keys() != baseline.keys():
                    raise RuntimeError(f"Sample mismatch for {seed}/{condition}")
                seed_records.append(records)

            metric_output = {}
            for metric in METRICS:
                baseline_values = np.asarray(
                    [baseline[name][metric] for name in names], dtype=np.float64
                )
                per_seed = []
                for seed, records in zip(seeds, seed_records):
                    candidate_values = np.asarray(
                        [records[name][metric] for name in names], dtype=np.float64
                    )
                    differences = candidate_values - baseline_values
                    interval = bootstrap_interval(
                        differences, args.bootstrap_samples, rng
                    )
                    improved = bool(differences.mean() < 0)
                    significant = bool(interval[1] < 0)
                    all_seed_means_improve = all_seed_means_improve and improved
                    strict_failure_count += int(not significant)
                    per_seed.append(
                        {
                            "seed": seed,
                            "candidate_mean": float(candidate_values.mean()),
                            "mean_difference": float(differences.mean()),
                            "relative_change_percent": float(
                                100.0 * differences.mean() / baseline_values.mean()
                            ),
                            "paired_95_ci": interval,
                            "fraction_candidate_better": float(
                                np.mean(differences < 0)
                            ),
                            "mean_improves": improved,
                            "paired_95_ci_below_zero": significant,
                        }
                    )
                candidate_means = np.asarray(
                    [record["candidate_mean"] for record in per_seed]
                )
                metric_output[metric] = {
                    "baseline_mean": float(baseline_values.mean()),
                    "candidate_seed_mean": float(candidate_means.mean()),
                    "candidate_seed_sample_std": float(candidate_means.std(ddof=1)),
                    "mean_relative_change_percent": float(
                        np.mean(
                            [record["relative_change_percent"] for record in per_seed]
                        )
                    ),
                    "all_seed_means_improve": all(
                        record["mean_improves"] for record in per_seed
                    ),
                    "significant_seed_count": sum(
                        record["paired_95_ci_below_zero"] for record in per_seed
                    ),
                    "per_seed": per_seed,
                }

            selection_fractions = [
                summary["gate_statistics"]["high_frequency_selection_fraction"]
                for summary in seed_summaries
            ]
            selection_patterns = [
                tuple(
                    records[name]["high_frequency_selected"]
                    for records in seed_records
                )
                for name in names
            ]
            branch_differences = []
            for seed, records in zip(seeds, seed_records):
                selected = np.asarray(
                    [records[name]["high_frequency_selected"] for name in names]
                )
                metric_differences = {}
                for metric in METRICS:
                    differences = np.asarray(
                        [records[name][metric] - baseline[name][metric] for name in names]
                    )
                    metric_differences[metric] = {
                        "high_frequency_selected_mean_difference": float(
                            differences[selected].mean()
                        )
                        if np.any(selected)
                        else None,
                        "full_selected_mean_difference": float(
                            differences[~selected].mean()
                        )
                        if np.any(~selected)
                        else None,
                    }
                branch_differences.append(
                    {
                        "seed": seed,
                        "high_frequency_selected_count": int(selected.sum()),
                        "full_selected_count": int((~selected).sum()),
                        "metric_mean_differences": metric_differences,
                    }
                )
            conditions[condition] = {
                "protocol": {
                    "texture_pattern": baseline_summary["texture_pattern"],
                    "texture_amplitude": baseline_summary["texture_amplitude"],
                    "texture_period": baseline_summary["texture_period"],
                    "texture_seed": baseline_summary["texture_seed"],
                    "texture_amplitude_semantics": baseline_summary[
                        "texture_amplitude_semantics"
                    ],
                },
                "metrics": metric_output,
                "gate_statistics": {
                    "high_frequency_selection_fraction_by_seed": selection_fractions,
                    "high_frequency_selection_fraction_mean": float(
                        np.mean(selection_fractions)
                    ),
                    "gate_mean_by_seed": [
                        summary["gate_statistics"]["mean"]
                        for summary in seed_summaries
                    ],
                },
                "selection_diagnostics": {
                    "all_seed_agreement_fraction": float(
                        np.mean([len(set(pattern)) == 1 for pattern in selection_patterns])
                    ),
                    "all_seed_high_frequency_fraction": float(
                        np.mean([all(pattern) for pattern in selection_patterns])
                    ),
                    "all_seed_full_fraction": float(
                        np.mean([not any(pattern) for pattern in selection_patterns])
                    ),
                    "branch_mean_differences_by_seed": branch_differences,
                    "analysis_type": "post_hoc_descriptive_no_model_selection",
                },
            }

    monotonic_checks = []
    for pattern in PATTERNS:
        low = conditions[f"{pattern}_amp_8"]["gate_statistics"][
            "high_frequency_selection_fraction_by_seed"
        ]
        high = conditions[f"{pattern}_amp_16"]["gate_statistics"][
            "high_frequency_selection_fraction_by_seed"
        ]
        for seed, low_value, high_value in zip(seeds, low, high):
            monotonic_checks.append(
                {
                    "pattern": pattern,
                    "seed": seed,
                    "amplitude_8": low_value,
                    "amplitude_16": high_value,
                    "non_decreasing": bool(high_value >= low_value),
                }
            )

    core_metrics = ["rmse", "boundary_rmse", "false_edge_rate"]
    core_majority_pass = all(
        sum(
            record["mean_improves"]
            for record in conditions[condition]["metrics"][metric]["per_seed"]
        )
        >= 2
        for condition in conditions
        for metric in core_metrics
    )
    output = {
        "status": "completed",
        "task": "rgb_guided_depth_super_resolution",
        "method": "SGNet_adaptive_frequency_reliability_gate",
        "dataset": "RGB-D-D/test2",
        "scale": 16,
        "sample_count": 405,
        "seeds": seeds,
        "adaptive_threshold": 0.75,
        "bootstrap_samples": args.bootstrap_samples,
        "bootstrap_seed": args.bootstrap_seed,
        "conditions": conditions,
        "decision": {
            "all_seed_means_improve_all_metrics": all_seed_means_improve,
            "strict_all_seed_paired_significance_pass": strict_failure_count == 0,
            "strict_failure_count": strict_failure_count,
            "core_metrics_majority_seed_pass": core_majority_pass,
            "selection_intensity_monotonic_all": all(
                record["non_decreasing"] for record in monotonic_checks
            ),
            "selection_intensity_checks": monotonic_checks,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps(output["decision"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
