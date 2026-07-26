import argparse
import json
from pathlib import Path

import numpy as np


METRICS = ["rmse", "mae", "boundary_rmse", "flat_rmse", "false_edge_rate"]
CONDITIONS = [
    "clean",
    "shift_x_pos_4",
    "shift_y_pos_4",
    "scale_098",
    "scale_102",
    "texture_amp_8_b4",
    "texture_amp_16_b4",
]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirmatory-root", type=Path, required=True)
    parser.add_argument("--high-frequency-root", type=Path, required=True)
    parser.add_argument("--seeds", default="20260723,20260724,20260725")
    parser.add_argument("--thresholds", default="0.70,0.72,0.74,0.75,0.76,0.78,0.80")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    return parser.parse_args()


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
    thresholds = [float(value) for value in args.thresholds.split(",") if value]
    rng = np.random.default_rng(20260723)
    output = {
        "status": "completed",
        "method": "SGNet_adaptive_frequency_reliability_gate",
        "dataset": "RGB-D-D/test2",
        "sample_count": 405,
        "seeds": seeds,
        "thresholds": thresholds,
        "conditions": {},
    }
    for threshold in thresholds:
        threshold_key = f"{threshold:.2f}"
        output["conditions"][threshold_key] = {}
        for condition in CONDITIONS:
            baseline = load_records(
                args.confirmatory_root / "baseline" / condition / "per_sample.jsonl"
            )
            seed_metrics = {metric: [] for metric in METRICS}
            seed_selection = []
            for seed in seeds:
                full = load_records(
                    args.confirmatory_root
                    / f"seed_{seed}"
                    / "eval"
                    / condition
                    / "per_sample.jsonl"
                )
                high = load_records(
                    args.high_frequency_root
                    / f"high_frequency_seed_{seed}"
                    / "eval"
                    / condition
                    / "per_sample.jsonl"
                )
                if full.keys() != high.keys() or full.keys() != baseline.keys():
                    raise RuntimeError(f"Sample mismatch for {seed}/{condition}")
                selected = {
                    name: (high[name] if full[name]["gate_mean"] < threshold else full[name])
                    for name in full
                }
                seed_selection.append(
                    float(
                        np.mean(
                            [full[name]["gate_mean"] < threshold for name in full]
                        )
                    )
                )
                for metric in METRICS:
                    seed_metrics[metric].append(
                        float(np.mean([selected[name][metric] for name in selected]))
                    )
            metric_output = {}
            for metric in METRICS:
                baseline_values = np.asarray(
                    [baseline[name][metric] for name in sorted(baseline)]
                )
                candidate_values = np.asarray(seed_metrics[metric])
                differences = candidate_values.mean() - baseline_values.mean()
                paired_differences = []
                for seed in seeds:
                    full = load_records(
                        args.confirmatory_root
                        / f"seed_{seed}"
                        / "eval"
                        / condition
                        / "per_sample.jsonl"
                    )
                    high = load_records(
                        args.high_frequency_root
                        / f"high_frequency_seed_{seed}"
                        / "eval"
                        / condition
                        / "per_sample.jsonl"
                    )
                    selected_values = np.asarray(
                        [
                            (
                                high[name][metric]
                                if full[name]["gate_mean"] < threshold
                                else full[name][metric]
                            )
                            for name in sorted(full)
                        ]
                    )
                    paired_differences.extend(
                        (selected_values - baseline_values).tolist()
                    )
                paired_differences = np.asarray(paired_differences)
                metric_output[metric] = {
                    "candidate_seed_mean": float(candidate_values.mean()),
                    "candidate_seed_sample_std": float(candidate_values.std(ddof=1)),
                    "baseline_mean": float(baseline_values.mean()),
                    "relative_change_percent": float(
                        100.0 * differences / baseline_values.mean()
                    ),
                    "paired_95_ci": bootstrap_interval(
                        paired_differences,
                        args.bootstrap_samples,
                        rng,
                    ),
                    "all_seed_means_improve": bool(
                        np.all(candidate_values < baseline_values.mean())
                    ),
                }
            output["conditions"][threshold_key][condition] = {
                "high_frequency_selection_fraction_by_seed": seed_selection,
                "high_frequency_selection_fraction_mean": float(np.mean(seed_selection)),
                "metrics": metric_output,
            }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({"thresholds": thresholds, "conditions": CONDITIONS}, indent=2))


if __name__ == "__main__":
    main()
