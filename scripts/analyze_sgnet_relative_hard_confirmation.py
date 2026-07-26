import argparse
import json
from pathlib import Path

import numpy as np


METRICS = ["rmse", "mae", "boundary_rmse", "flat_rmse", "false_edge_rate"]
CORE_METRICS = ["rmse", "boundary_rmse", "false_edge_rate"]
SEEDS = [20260723, 20260724, 20260725]
CONDITIONS = {
    "clean": ("confirmatory/baseline/clean", "adaptive_seed_{seed}/eval/clean"),
    "checker8": (
        "confirmatory/baseline/texture_amp_8_b4",
        "adaptive_seed_{seed}/eval/texture_amp_8_b4",
    ),
    "sinusoidal8": (
        "unseen_texture_generalization/baseline/sinusoidal_amp_8",
        "unseen_texture_generalization/adaptive_seed_{seed}/sinusoidal_amp_8",
    ),
    "noise8": (
        "unseen_texture_generalization/baseline/noise_amp_8",
        "unseen_texture_generalization/adaptive_seed_{seed}/noise_amp_8",
    ),
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--local-root", type=Path, required=True)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def load_records(root):
    records = {}
    with (root / "per_sample.jsonl").open("r", encoding="utf-8") as handle:
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
    rng = np.random.default_rng(20260723)
    output_conditions = {}
    baseline_preservation_pass = True
    core_vs_hard_pass = True
    sinusoidal_reconstruction_pass = True
    agreement_improvements = []

    for condition, (baseline_path, hard_template) in CONDITIONS.items():
        baseline = load_records(args.local_root / baseline_path)
        names = sorted(baseline)
        hard = {
            seed: load_records(
                args.local_root / hard_template.format(seed=seed)
            )
            for seed in SEEDS
        }
        candidate = {20260723: hard[20260723]}
        for seed in SEEDS[1:]:
            candidate[seed] = load_records(
                args.candidate_root / f"seed_{seed}" / condition
            )
        if any(records.keys() != baseline.keys() for records in hard.values()) or any(
            records.keys() != baseline.keys() for records in candidate.values()
        ):
            raise RuntimeError(f"Sample mismatch for {condition}")

        metric_output = {}
        for metric in METRICS:
            baseline_values = np.asarray([baseline[name][metric] for name in names])
            hard_seed_means = []
            candidate_seed_means = []
            per_seed = []
            for seed in SEEDS:
                hard_values = np.asarray([hard[seed][name][metric] for name in names])
                candidate_values = np.asarray(
                    [candidate[seed][name][metric] for name in names]
                )
                hard_seed_means.append(float(hard_values.mean()))
                candidate_seed_means.append(float(candidate_values.mean()))
                candidate_minus_baseline = candidate_values - baseline_values
                candidate_minus_hard = candidate_values - hard_values
                per_seed.append(
                    {
                        "seed": seed,
                        "baseline_mean": float(baseline_values.mean()),
                        "hard_mean": float(hard_values.mean()),
                        "candidate_mean": float(candidate_values.mean()),
                        "candidate_vs_baseline_percent": float(
                            100.0
                            * candidate_minus_baseline.mean()
                            / baseline_values.mean()
                        ),
                        "candidate_vs_hard_percent": float(
                            100.0 * candidate_minus_hard.mean() / hard_values.mean()
                        ),
                        "candidate_vs_baseline_paired_95_ci": bootstrap_interval(
                            candidate_minus_baseline,
                            args.bootstrap_samples,
                            rng,
                        ),
                        "candidate_vs_hard_paired_95_ci": bootstrap_interval(
                            candidate_minus_hard,
                            args.bootstrap_samples,
                            rng,
                        ),
                    }
                )
            baseline_mean = float(baseline_values.mean())
            hard_mean = float(np.mean(hard_seed_means))
            candidate_mean = float(np.mean(candidate_seed_means))
            candidate_vs_baseline = 100.0 * (candidate_mean - baseline_mean) / baseline_mean
            candidate_vs_hard = 100.0 * (candidate_mean - hard_mean) / hard_mean
            if condition in ("clean", "checker8"):
                baseline_preservation_pass = (
                    baseline_preservation_pass
                    and all(record["candidate_mean"] <= baseline_mean for record in per_seed)
                )
            if metric in CORE_METRICS:
                core_vs_hard_pass = core_vs_hard_pass and candidate_mean <= hard_mean
            if condition == "sinusoidal8" and metric in ("mae", "flat_rmse"):
                sinusoidal_reconstruction_pass = (
                    sinusoidal_reconstruction_pass and candidate_mean <= baseline_mean
                )
            metric_output[metric] = {
                "baseline_mean": baseline_mean,
                "hard_three_seed_mean": hard_mean,
                "candidate_three_seed_mean": candidate_mean,
                "candidate_vs_baseline_percent": float(candidate_vs_baseline),
                "candidate_vs_hard_percent": float(candidate_vs_hard),
                "per_seed": per_seed,
            }

        old_patterns = [
            tuple(hard[seed][name]["high_frequency_selected"] for seed in SEEDS)
            for name in names
        ]
        new_patterns = [
            tuple(candidate[seed][name]["high_frequency_selected"] for seed in SEEDS)
            for name in names
        ]
        old_agreement = float(np.mean([len(set(values)) == 1 for values in old_patterns]))
        new_agreement = float(np.mean([len(set(values)) == 1 for values in new_patterns]))
        if condition in ("sinusoidal8", "noise8"):
            agreement_improvements.append(new_agreement > old_agreement)
        output_conditions[condition] = {
            "metrics": metric_output,
            "selection_agreement": {
                "old_absolute_threshold": old_agreement,
                "relative_threshold": new_agreement,
                "change_percentage_points": 100.0 * (new_agreement - old_agreement),
            },
        }

    agreement_pass = all(agreement_improvements)
    go = (
        baseline_preservation_pass
        and core_vs_hard_pass
        and sinusoidal_reconstruction_pass
        and agreement_pass
    )
    output = {
        "status": "completed",
        "phase": "locked_confirmation",
        "method": "relative_clean_calibrated_hard_routing",
        "dataset": "RGB-D-D/test2",
        "scale": 16,
        "sample_count": 405,
        "seeds": SEEDS,
        "reference_drop_threshold": 0.0457255157423608,
        "conditions": output_conditions,
        "decision": {
            "go": go,
            "clean_checker_all_seed_all_metric_vs_baseline_pass": baseline_preservation_pass,
            "core_three_seed_mean_vs_old_hard_pass": core_vs_hard_pass,
            "sinusoidal8_mae_flat_vs_baseline_pass": sinusoidal_reconstruction_pass,
            "medium_texture_selection_agreement_improves": agreement_pass,
            "interpretation": "Retain relative hard routing"
            if go
            else "No-Go; retain original absolute hard routing",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps(output["decision"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
