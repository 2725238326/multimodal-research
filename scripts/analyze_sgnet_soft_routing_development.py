import argparse
import json
from pathlib import Path

import numpy as np


METRICS = ["rmse", "mae", "boundary_rmse", "flat_rmse", "false_edge_rate"]
CORE_METRICS = ["rmse", "boundary_rmse", "false_edge_rate"]
PRESERVATION_METRICS = ["mae", "flat_rmse"]
CONDITION_PATHS = {
    "clean": "clean",
    "checker8": "texture_amp_8_b4",
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--hard-root", type=Path, required=True)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--temperatures", default="0.005,0.01,0.02")
    parser.add_argument("--core-tolerance-percent", type=float, default=0.05)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def load_records(path):
    records = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            records[record["name"]] = record
    return records


def relative_change(candidate, reference):
    return float(100.0 * (candidate - reference) / reference)


def main():
    args = parse_args()
    temperatures = [value for value in args.temperatures.split(",") if value]
    candidates = {}
    for temperature in temperatures:
        condition_results = {}
        baseline_pass = True
        core_tolerance_pass = True
        preservation_changes = []
        for condition, existing_name in CONDITION_PATHS.items():
            candidate = load_records(
                args.candidate_root
                / f"temperature_{temperature}"
                / condition
                / "per_sample.jsonl"
            )
            baseline_all = load_records(
                args.baseline_root / existing_name / "per_sample.jsonl"
            )
            hard_all = load_records(args.hard_root / existing_name / "per_sample.jsonl")
            names = sorted(candidate)
            if not names or not set(names).issubset(baseline_all) or not set(names).issubset(
                hard_all
            ):
                raise RuntimeError(f"Sample mismatch for {temperature}/{condition}")
            metrics = {}
            for metric in METRICS:
                candidate_mean = float(np.mean([candidate[name][metric] for name in names]))
                baseline_mean = float(
                    np.mean([baseline_all[name][metric] for name in names])
                )
                hard_mean = float(np.mean([hard_all[name][metric] for name in names]))
                versus_baseline = relative_change(candidate_mean, baseline_mean)
                versus_hard = relative_change(candidate_mean, hard_mean)
                baseline_pass = baseline_pass and candidate_mean <= baseline_mean
                if metric in CORE_METRICS:
                    core_tolerance_pass = (
                        core_tolerance_pass
                        and versus_hard <= args.core_tolerance_percent
                    )
                if metric in PRESERVATION_METRICS:
                    preservation_changes.append(versus_hard)
                metrics[metric] = {
                    "baseline_mean": baseline_mean,
                    "hard_adaptive_mean": hard_mean,
                    "candidate_mean": candidate_mean,
                    "relative_change_vs_baseline_percent": versus_baseline,
                    "relative_change_vs_hard_percent": versus_hard,
                }
            summary = json.load(
                (
                    args.candidate_root
                    / f"temperature_{temperature}"
                    / condition
                    / "summary.json"
                ).open("r", encoding="utf-8")
            )
            condition_results[condition] = {
                "sample_count": len(names),
                "metrics": metrics,
                "high_frequency_weight_mean": summary["gate_statistics"][
                    "high_frequency_weight_mean"
                ],
            }
        preservation_score = float(np.mean(preservation_changes))
        feasible = (
            baseline_pass and core_tolerance_pass and preservation_score < 0.0
        )
        candidates[temperature] = {
            "conditions": condition_results,
            "baseline_all_metrics_non_degrading": baseline_pass,
            "core_vs_hard_within_tolerance": core_tolerance_pass,
            "preservation_score_vs_hard_percent": preservation_score,
            "feasible": feasible,
        }

    feasible_temperatures = [
        temperature
        for temperature, record in candidates.items()
        if record["feasible"]
    ]
    selected = None
    if feasible_temperatures:
        selected = min(
            feasible_temperatures,
            key=lambda value: candidates[value][
                "preservation_score_vs_hard_percent"
            ],
        )
    output = {
        "status": "completed",
        "phase": "development",
        "dataset": "RGB-D-D/test2 first 100 sorted samples",
        "scale": 16,
        "seed": 20260723,
        "conditions": list(CONDITION_PATHS),
        "temperatures": temperatures,
        "selection_rule": {
            "baseline_all_metrics_non_degrading": True,
            "core_vs_hard_tolerance_percent": args.core_tolerance_percent,
            "preservation_score_definition": "mean MAE/flat relative change versus hard adaptive across clean and checker8",
            "preservation_score_must_be_below_zero": True,
        },
        "candidates": candidates,
        "decision": {
            "go": selected is not None,
            "selected_temperature": selected,
            "interpretation": "Lock selected temperature for confirmation"
            if selected is not None
            else "No candidate passes; retain hard adaptive routing",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps(output["decision"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
