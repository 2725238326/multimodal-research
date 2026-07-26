import argparse
import json
from pathlib import Path

import numpy as np


METRICS = ["rmse", "mae", "boundary_rmse", "flat_rmse", "false_edge_rate"]
CONDITIONS = ["clean", "shift_x_pos_1", "shift_x_pos_2", "shift_x_pos_4"]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20260722)
    parser.add_argument(
        "--conditions",
        default=",".join(CONDITIONS),
        help="Comma-separated condition directory names",
    )
    return parser.parse_args()


def load_records(path):
    records = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            records[record["name"]] = record
    return records


def bootstrap_interval(differences, samples, rng):
    sample_count = len(differences)
    means = np.empty(samples, dtype=np.float64)
    for start in range(0, samples, 1000):
        block_size = min(1000, samples - start)
        indices = rng.integers(0, sample_count, size=(block_size, sample_count))
        means[start : start + block_size] = differences[indices].mean(axis=1)
    return [float(value) for value in np.percentile(means, [2.5, 97.5])]


def main():
    args = parse_args()
    rng = np.random.default_rng(args.seed)
    output = {
        "status": "completed",
        "difference_definition": "candidate_minus_baseline",
        "lower_is_better": True,
        "bootstrap_samples": args.bootstrap_samples,
        "seed": args.seed,
        "conditions": {},
    }
    conditions = [condition for condition in args.conditions.split(",") if condition]
    for condition in conditions:
        baseline = load_records(args.baseline_root / condition / "per_sample.jsonl")
        candidate = load_records(args.candidate_root / condition / "per_sample.jsonl")
        if baseline.keys() != candidate.keys():
            raise RuntimeError(f"Sample mismatch for {condition}")
        names = sorted(baseline)
        metrics = {}
        for metric in METRICS:
            baseline_values = np.asarray([baseline[name][metric] for name in names])
            candidate_values = np.asarray([candidate[name][metric] for name in names])
            differences = candidate_values - baseline_values
            metrics[metric] = {
                "baseline_mean": float(baseline_values.mean()),
                "candidate_mean": float(candidate_values.mean()),
                "mean_difference": float(differences.mean()),
                "relative_change_percent": float(
                    100.0 * differences.mean() / baseline_values.mean()
                ),
                "paired_95_ci": bootstrap_interval(
                    differences,
                    args.bootstrap_samples,
                    rng,
                ),
                "fraction_candidate_better": float(np.mean(differences < 0)),
            }
        output["conditions"][condition] = {
            "sample_count": len(names),
            "metrics": metrics,
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2)
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
