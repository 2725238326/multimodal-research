import argparse
import json
import platform
import sys
from pathlib import Path

import numpy as np
import torch

from evaluate_sgnet_rgbdd_x16 import (
    aggregate,
    calculate_metrics,
    load_pairs,
    prepare_tensors,
    sha256,
)
from sgnet_reliability_gate import SGNetWithReliabilityGate


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sgnet-dir", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--gate-checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--scale", type=int, default=16)
    parser.add_argument("--num-feats", type=int, default=40)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--shift-x", type=int, default=0)
    parser.add_argument("--shift-y", type=int, default=0)
    parser.add_argument("--rgb-scale", type=float, default=1.0)
    parser.add_argument("--texture-amplitude", type=float, default=0.0)
    parser.add_argument("--texture-block-size", type=int, default=4)
    parser.add_argument(
        "--texture-pattern",
        choices=("checkerboard", "sinusoidal", "noise"),
        default="checkerboard",
    )
    parser.add_argument("--texture-period", type=float, default=8.0)
    parser.add_argument("--texture-seed", type=int, default=20260723)
    parser.add_argument(
        "--gate-mode",
        choices=("learned", "identity", "shuffled", "constant_mean"),
        default="learned",
    )
    parser.add_argument(
        "--gate-application",
        choices=(
            "full",
            "high_frequency",
            "adaptive",
            "soft_adaptive",
            "ramp_adaptive",
        ),
        default="full",
    )
    parser.add_argument("--adaptive-threshold", type=float, default=0.75)
    parser.add_argument("--adaptive-temperature", type=float, default=0.01)
    parser.add_argument("--gate-reference-mean", type=float)
    parser.add_argument("--reference-drop-threshold", type=float)
    parser.add_argument("--crop-border", type=int, default=6)
    parser.add_argument("--depth-edge-threshold", type=float, default=2.0)
    parser.add_argument("--rgb-edge-threshold", type=float, default=8.0)
    parser.add_argument("--max-samples", type=int)
    return parser.parse_args()


def main():
    args = parse_args()
    reference_values = (args.gate_reference_mean, args.reference_drop_threshold)
    if (reference_values[0] is None) != (reference_values[1] is None):
        raise ValueError(
            "gate_reference_mean and reference_drop_threshold must be used together"
        )
    effective_threshold = args.adaptive_threshold
    if args.gate_reference_mean is not None:
        effective_threshold = (
            args.gate_reference_mean - args.reference_drop_threshold
        )
    sys.path.insert(0, str(args.sgnet_dir.resolve()))
    from models.SGNet import SGNet

    device = torch.device(args.device)
    base_model = SGNet(num_feats=args.num_feats, kernel_size=3, scale=args.scale)
    base_model.load_state_dict(torch.load(args.checkpoint, map_location=device))
    gate_checkpoint = torch.load(args.gate_checkpoint, map_location=device)
    model = SGNetWithReliabilityGate(
        base_model,
        hidden_channels=gate_checkpoint["hidden_channels"],
        initial_bias=gate_checkpoint["initial_bias"],
    )
    model.reliability_gate.load_state_dict(gate_checkpoint["gate_state_dict"])
    model.to(device).eval()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    with torch.inference_mode():
        for index, (name, rgb, depth) in enumerate(load_pairs(args.data_root, args.scale)):
            if args.max_samples is not None and index >= args.max_samples:
                break
            guidance, low_resolution, shifted_rgb = prepare_tensors(
                rgb,
                depth,
                args.scale,
                args.shift_x,
                args.shift_y,
                device,
                rgb_scale=args.rgb_scale,
                texture_amplitude=args.texture_amplitude,
                texture_block_size=args.texture_block_size,
                texture_pattern=args.texture_pattern,
                texture_period=args.texture_period,
                texture_seed=args.texture_seed,
                sample_index=index,
            )
            prediction, _, gate = model(
                (guidance, low_resolution),
                gate_mode=args.gate_mode,
                gate_application=args.gate_application,
                adaptive_threshold=effective_threshold,
                adaptive_temperature=args.adaptive_temperature,
                return_gate=True,
            )
            prediction = prediction[0, 0].detach().cpu().numpy()
            metrics = calculate_metrics(
                prediction,
                depth,
                shifted_rgb,
                args.crop_border,
                args.depth_edge_threshold,
                args.rgb_edge_threshold,
            )
            gate_mean = float(gate.mean().item())
            if args.gate_application == "high_frequency":
                high_frequency_weight = 1.0
            elif args.gate_application == "soft_adaptive":
                high_frequency_weight = float(
                    1.0
                    / (
                        1.0
                        + np.exp(
                            (gate_mean - effective_threshold)
                            / args.adaptive_temperature
                        )
                    )
                )
            elif args.gate_application == "ramp_adaptive":
                high_frequency_weight = float(
                    np.clip(
                        (effective_threshold - gate_mean)
                        / args.adaptive_temperature,
                        0.0,
                        1.0,
                    )
                )
            elif args.gate_application == "adaptive":
                high_frequency_weight = float(gate_mean < effective_threshold)
            else:
                high_frequency_weight = 0.0
            records.append(
                {
                    "index": index,
                    "name": name,
                    "gate_mean": gate_mean,
                    "gate_std": float(gate.std().item()),
                    "gate_suppressed_fraction": float((gate < 0.9).float().mean().item()),
                    "high_frequency_weight": high_frequency_weight,
                    "high_frequency_selected": bool(high_frequency_weight >= 0.5),
                    **metrics,
                }
            )

    with (args.output_dir / "per_sample.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    summary = {
        "status": "completed",
        "task": "rgb_guided_depth_super_resolution",
        "method": "SGNet_spatial_reliability_gate",
        "gate_mode": args.gate_mode,
        "gate_application": args.gate_application,
        "adaptive_threshold": args.adaptive_threshold,
        "effective_adaptive_threshold": effective_threshold,
        "adaptive_temperature": args.adaptive_temperature,
        "gate_reference_mean": args.gate_reference_mean,
        "reference_drop_threshold": args.reference_drop_threshold,
        "dataset": "RGB-D-D/test2",
        "scale": args.scale,
        "sample_count": len(records),
        "base_checkpoint_sha256": sha256(args.checkpoint),
        "gate_checkpoint_sha256": sha256(args.gate_checkpoint),
        "shift_x": args.shift_x,
        "shift_y": args.shift_y,
        "rgb_scale": args.rgb_scale,
        "texture_amplitude": args.texture_amplitude,
        "texture_block_size": args.texture_block_size,
        "texture_pattern": args.texture_pattern,
        "texture_period": args.texture_period,
        "texture_seed": args.texture_seed,
        "texture_amplitude_semantics": "standard_deviation"
        if args.texture_pattern == "noise"
        else "peak_absolute_offset",
        "crop_border": args.crop_border,
        "metrics_unit": "8-bit depth levels",
        "metrics": aggregate(records),
        "gate_statistics": {
            "mean": float(np.mean([record["gate_mean"] for record in records])),
            "std_mean": float(np.mean([record["gate_std"] for record in records])),
            "suppressed_fraction": float(
                np.mean([record["gate_suppressed_fraction"] for record in records])
            ),
            "high_frequency_selection_fraction": float(
                np.mean([record["high_frequency_selected"] for record in records])
            ),
            "high_frequency_weight_mean": float(
                np.mean([record["high_frequency_weight"] for record in records])
            ),
        },
        "environment": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "cuda_runtime": torch.version.cuda,
            "device": str(device),
            "device_name": torch.cuda.get_device_name(device)
            if device.type == "cuda"
            else "cpu",
        },
    }
    with (args.output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
