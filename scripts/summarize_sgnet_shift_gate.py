import argparse
import json
from pathlib import Path

import numpy as np


METRICS = ["rmse", "mae", "boundary_rmse", "flat_rmse", "false_edge_rate"]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20260722)
    return parser.parse_args()


def load_records(path):
    records = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            records[record["name"]] = record
    return records


def bootstrap_interval(values, sample_count, rng):
    indices = rng.integers(0, len(values), size=(sample_count, len(values)))
    means = values[indices].mean(axis=1)
    return [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))]


def compare(clean, condition, bootstrap_samples, rng):
    if clean.keys() != condition.keys():
        raise RuntimeError("Condition sample names do not match clean sample names")
    names = sorted(clean)
    metrics = {}
    for metric in METRICS:
        clean_values = np.asarray([clean[name][metric] for name in names], dtype=np.float64)
        condition_values = np.asarray(
            [condition[name][metric] for name in names], dtype=np.float64
        )
        differences = condition_values - clean_values
        clean_mean = float(clean_values.mean())
        condition_mean = float(condition_values.mean())
        metrics[metric] = {
            "clean_mean": clean_mean,
            "condition_mean": condition_mean,
            "mean_difference": float(differences.mean()),
            "relative_change_percent": float(
                100.0 * differences.mean() / clean_mean if clean_mean else 0.0
            ),
            "paired_95_ci": bootstrap_interval(differences, bootstrap_samples, rng),
            "fraction_worse": float(np.mean(differences > 0)),
        }
    rmse_ci = metrics["rmse"]["paired_95_ci"]
    boundary_ci = metrics["boundary_rmse"]["paired_95_ci"]
    return {
        "sample_count": len(names),
        "metrics": metrics,
        "condition_passes": rmse_ci[0] > 0 and boundary_ci[0] > 0,
    }


def main():
    args = parse_args()
    clean_path = args.results_root / "clean" / "per_sample.jsonl"
    clean = load_records(clean_path)
    condition_dirs = sorted(
        path
        for path in args.results_root.iterdir()
        if path.is_dir() and path.name != "clean" and (path / "per_sample.jsonl").is_file()
    )
    rng = np.random.default_rng(args.seed)
    conditions = {
        path.name: compare(
            clean,
            load_records(path / "per_sample.jsonl"),
            args.bootstrap_samples,
            rng,
        )
        for path in condition_dirs
    }
    passed_conditions = [
        name for name, result in conditions.items() if result["condition_passes"]
    ]
    summary = {
        "status": "completed",
        "clean_sample_count": len(clean),
        "bootstrap_samples": args.bootstrap_samples,
        "seed": args.seed,
        "conditions": conditions,
        "passed_conditions": passed_conditions,
        "gate_passes": len(passed_conditions) >= 2,
        "gate_definition": (
            "At least two conditions have paired-bootstrap 95% CI lower bounds "
            "above zero for both RMSE and boundary RMSE."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
