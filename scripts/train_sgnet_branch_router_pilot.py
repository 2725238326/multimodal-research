import argparse
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as functional

from evaluate_sgnet_rgbdd_x16 import calculate_metrics
from sgnet_reliability_gate import SGNetWithReliabilityGate
from train_rgb_depth_shift_calibrator import NYUPairs


METRICS = ["rmse", "mae", "boundary_rmse", "flat_rmse", "false_edge_rate"]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sgnet-dir", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--gate-checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--scale", type=int, default=16)
    parser.add_argument("--crop-size", type=int, default=256)
    parser.add_argument("--train-samples", type=int, default=200)
    parser.add_argument("--validation-samples", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20260723)
    parser.add_argument("--texture-amplitude", type=float, default=8.0)
    parser.add_argument("--epochs", type=int, default=400)
    return parser.parse_args()


def add_checkerboard(rgb, amplitude):
    height, width = rgb.shape[-2:]
    rows = torch.arange(height, device=rgb.device)[:, None] // 4
    columns = torch.arange(width, device=rgb.device)[None, :] // 4
    pattern = ((rows + columns) % 2).float() * 2.0 - 1.0
    return (rgb + amplitude / 255.0 * pattern[None, None]).clamp(0.0, 1.0)


def train_router(features, labels, epochs, seed):
    torch.manual_seed(seed)
    feature_mean = features.mean(0)
    feature_std = features.std(0).clamp_min(1e-6)
    normalized = (features - feature_mean) / feature_std
    model = torch.nn.Linear(features.shape[1], 1)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.05)
    positive = labels.sum().clamp_min(1.0)
    negative = (labels.numel() - labels.sum()).clamp_min(1.0)
    pos_weight = negative / positive
    criterion = torch.nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    for _ in range(epochs):
        logits = model(normalized).squeeze(1)
        loss = criterion(logits, labels)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    return model, feature_mean, feature_std


def main():
    args = parse_args()
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    sys.path.insert(0, str(args.sgnet_dir.resolve()))
    from models.SGNet import SGNet

    device = torch.device(args.device)
    base = SGNet(num_feats=40, kernel_size=3, scale=args.scale)
    base.load_state_dict(torch.load(args.checkpoint, map_location=device))
    gate_checkpoint = torch.load(args.gate_checkpoint, map_location=device)
    model = SGNetWithReliabilityGate(
        base,
        hidden_channels=gate_checkpoint["hidden_channels"],
        initial_bias=gate_checkpoint["initial_bias"],
    )
    model.reliability_gate.load_state_dict(gate_checkpoint["gate_state_dict"])
    model.to(device).eval()
    dataset = NYUPairs(args.data_root, args.crop_size)
    total_required = args.train_samples + args.validation_samples
    if total_required > len(dataset):
        raise ValueError("train + validation samples exceed NYU dataset")
    indices = list(range(total_required))
    records = []
    start_time = time.time()
    with torch.inference_mode():
        for index in indices:
            rgb, target = dataset[index]
            rgb = rgb.unsqueeze(0).to(device)
            target = target.unsqueeze(0).to(device)
            low_resolution = functional.interpolate(
                target,
                scale_factor=1 / args.scale,
                mode="bicubic",
                align_corners=False,
            )
            for condition, guidance in (
                ("clean", rgb),
                ("checker8", add_checkerboard(rgb, args.texture_amplitude)),
            ):
                full_output, _, gate = model(
                    (guidance, low_resolution),
                    gate_application="full",
                    return_gate=True,
                )
                high_output, _, _ = model(
                    (guidance, low_resolution),
                    gate_application="high_frequency",
                    return_gate=True,
                )
                target_np = target[0, 0].cpu().numpy() * 255.0
                guidance_np = guidance[0].permute(1, 2, 0).cpu().numpy() * 255.0
                branch_metrics = {}
                for name, output in (("full", full_output), ("high", high_output)):
                    prediction = output[0, 0].cpu().numpy()
                    branch_metrics[name] = calculate_metrics(
                        prediction,
                        target_np,
                        guidance_np,
                        crop_border=0,
                        depth_edge_threshold=2.0,
                        rgb_edge_threshold=8.0,
                    )
                records.append(
                    {
                        "index": index,
                        "split": "train" if index < args.train_samples else "validation",
                        "condition": condition,
                        "gate_mean": float(gate.mean().item()),
                        "gate_std": float(gate.std().item()),
                        "gate_suppressed_fraction": float(
                            (gate < 0.9).float().mean().item()
                        ),
                        "metrics": branch_metrics,
                    }
                )

    train_records = [record for record in records if record["split"] == "train"]
    validation_records = [
        record for record in records if record["split"] == "validation"
    ]
    reference_mean = float(
        np.mean(
            [
                record["gate_mean"]
                for record in train_records
                if record["condition"] == "clean"
            ]
        )
    )
    def feature_vector(record):
        return [
            reference_mean - record["gate_mean"],
            record["gate_std"],
            record["gate_suppressed_fraction"],
        ]

    train_features = torch.tensor(
        [feature_vector(record) for record in train_records], dtype=torch.float32
    )
    validation_features = torch.tensor(
        [feature_vector(record) for record in validation_records], dtype=torch.float32
    )
    metric_scales = {
        metric: float(
            np.mean([record["metrics"]["full"][metric] for record in train_records])
        )
        for metric in METRICS
    }
    objectives = {}
    for objective in ("rmse", "balanced_five_metric"):
        labels = []
        for record in train_records:
            if objective == "rmse":
                choose_high = (
                    record["metrics"]["high"]["rmse"]
                    < record["metrics"]["full"]["rmse"]
                )
            else:
                difference = np.mean(
                    [
                        (
                            record["metrics"]["high"][metric]
                            - record["metrics"]["full"][metric]
                        )
                        / metric_scales[metric]
                        for metric in METRICS
                    ]
                )
                choose_high = difference < 0
            labels.append(float(choose_high))
        labels_tensor = torch.tensor(labels, dtype=torch.float32)
        router, feature_mean, feature_std = train_router(
            train_features, labels_tensor, args.epochs, args.seed
        )
        with torch.inference_mode():
            probabilities = torch.sigmoid(
                router((validation_features - feature_mean) / feature_std).squeeze(1)
            ).numpy()
        objective_records = []
        for record, probability in zip(validation_records, probabilities):
            selected = "high" if probability >= 0.5 else "full"
            hard_selected = (
                "high" if record["gate_mean"] < 0.75 else "full"
            )
            objective_records.append(
                {
                    "condition": record["condition"],
                    "selected": selected,
                    "hard_selected": hard_selected,
                    "high_probability": float(probability),
                    "metrics": record["metrics"],
                }
            )
        summary_conditions = {}
        all_metrics_non_degrading = True
        mae_flat_improves = []
        for condition in ("clean", "checker8"):
            subset = [
                record
                for record in objective_records
                if record["condition"] == condition
            ]
            metric_summary = {}
            for metric in METRICS:
                candidate = np.asarray(
                    [record["metrics"][record["selected"]][metric] for record in subset]
                )
                hard = np.asarray(
                    [record["metrics"][record["hard_selected"]][metric] for record in subset]
                )
                candidate_mean = float(candidate.mean())
                hard_mean = float(hard.mean())
                metric_summary[metric] = {
                    "candidate_mean": candidate_mean,
                    "hard_mean": hard_mean,
                    "candidate_vs_hard_percent": float(
                        100.0 * (candidate_mean - hard_mean) / hard_mean
                    ),
                }
                all_metrics_non_degrading = (
                    all_metrics_non_degrading and candidate_mean <= hard_mean
                )
                if metric in ("mae", "flat_rmse"):
                    mae_flat_improves.append(candidate_mean - hard_mean)
            summary_conditions[condition] = {
                "high_frequency_fraction": float(
                    np.mean([record["selected"] == "high" for record in subset])
                ),
                "metrics": metric_summary,
            }
        mae_flat_improves = bool(np.mean(mae_flat_improves) < 0)
        checkpoint_path = args.output_dir / f"router_{objective}.pth"
        args.output_dir.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "objective": objective,
                "feature_mean": feature_mean,
                "feature_std": feature_std,
                "router_state_dict": router.state_dict(),
                "reference_mean": reference_mean,
            },
            checkpoint_path,
        )
        objectives[objective] = {
            "train_high_frequency_fraction": float(np.mean(labels)),
            "validation": summary_conditions,
            "all_metrics_non_degrading_vs_hard": all_metrics_non_degrading,
            "mae_flat_improves_vs_hard": mae_flat_improves,
            "go": all_metrics_non_degrading and mae_flat_improves,
            "checkpoint": checkpoint_path.name,
        }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "branch_records.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    summary = {
        "status": "completed",
        "task": "rgb_guided_depth_super_resolution",
        "phase": "nyu_branch_router_pilot",
        "dataset": "NYU_v2_train",
        "scale": args.scale,
        "train_samples": args.train_samples,
        "validation_samples": args.validation_samples,
        "conditions": ["clean", "checker8"],
        "trainable_module": "three_feature_logistic_branch_router",
        "reference_mean": reference_mean,
        "features": [
            "clean_reference_minus_gate_mean",
            "gate_spatial_std",
            "gate_suppressed_fraction",
        ],
        "objectives": objectives,
        "elapsed_seconds": time.time() - start_time,
        "decision": {
            "go": any(record["go"] for record in objectives.values()),
            "interpretation": "Expand to full NYU only if a router dominates hard routing"
            if any(record["go"] for record in objectives.values())
            else "No-Go; do not expand this router pilot",
        },
    }
    with (args.output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    print(json.dumps(summary["decision"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
