import argparse
import json
import platform
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from evaluate_sgnet_rgbdd_x16 import aggregate, dilate, gradient_magnitude, sha256
from sgnet_reliability_gate import SGNetWithReliabilityGate


CATEGORIES = ("models", "plants", "portraits")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sgnet-dir", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--gate-checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--scale", type=int, default=4)
    parser.add_argument("--num-feats", type=int, default=24)
    parser.add_argument("--gate-mode", choices=("learned", "identity"), default="learned")
    parser.add_argument(
        "--gate-application",
        choices=("full", "high_frequency", "adaptive"),
        default="adaptive",
    )
    parser.add_argument("--adaptive-threshold", type=float, default=0.75)
    parser.add_argument("--crop-border", type=int, default=6)
    parser.add_argument("--depth-edge-threshold-mm", type=float, default=20.0)
    parser.add_argument("--rgb-edge-threshold", type=float, default=8.0)
    parser.add_argument("--max-samples", type=int)
    return parser.parse_args()


def load_samples(data_root):
    for category in CATEGORIES:
        category_root = data_root / category / f"{category}_test"
        for sample_root in sorted(path for path in category_root.iterdir() if path.is_dir()):
            sample_id = sample_root.name
            yield {
                "name": f"{category}/{sample_id}",
                "rgb": sample_root / f"{sample_id}_RGB.jpg",
                "gt": sample_root / f"{sample_id}_HR_gt.png",
                "lr": sample_root / f"{sample_id}_LR_fill_depth.png",
            }


def prepare_tensors(sample, scale, device):
    rgb = np.asarray(Image.open(sample["rgb"]).convert("RGB"), dtype=np.float32)
    target = np.asarray(Image.open(sample["gt"]), dtype=np.float32)
    height, width = target.shape
    low_resolution = np.asarray(
        Image.open(sample["lr"]).resize(
            (width // scale, height // scale),
            Image.Resampling.BICUBIC,
        ),
        dtype=np.float32,
    )
    depth_max = float(low_resolution.max())
    depth_min = float(low_resolution.min())
    depth_range = max(depth_max - depth_min, 1e-6)
    low_resolution = np.ascontiguousarray((low_resolution - depth_min) / depth_range)
    rgb_min = float(rgb.min())
    rgb_range = max(float(rgb.max()) - rgb_min, 1e-6)
    guidance = np.ascontiguousarray((rgb - rgb_min) / rgb_range)
    guidance = torch.from_numpy(guidance.transpose(2, 0, 1)).unsqueeze(0).to(device)
    low_resolution = torch.from_numpy(low_resolution).unsqueeze(0).unsqueeze(0).to(device)
    return guidance.float(), low_resolution.float(), rgb, target, depth_min, depth_max


def calculate_metrics(
    prediction,
    target,
    rgb,
    crop_border,
    depth_edge_threshold_mm,
    rgb_edge_threshold,
):
    if crop_border:
        prediction = prediction[crop_border:-crop_border, crop_border:-crop_border]
        target = target[crop_border:-crop_border, crop_border:-crop_border]
        rgb = rgb[crop_border:-crop_border, crop_border:-crop_border]
    error_cm = (prediction - target) / 10.0
    squared_error = error_cm * error_cm
    target_edges = dilate(gradient_magnitude(target) > depth_edge_threshold_mm)
    prediction_edges = gradient_magnitude(prediction) > depth_edge_threshold_mm
    luminance = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    rgb_edges = gradient_magnitude(luminance) > rgb_edge_threshold
    false_edges = prediction_edges & rgb_edges & ~target_edges
    return {
        "rmse": float(np.sqrt(np.mean(squared_error))),
        "mae": float(np.mean(np.abs(error_cm))),
        "boundary_rmse": float(np.sqrt(np.mean(squared_error[target_edges]))),
        "flat_rmse": float(np.sqrt(np.mean(squared_error[~target_edges]))),
        "false_edge_rate": float(false_edges.sum() / max(prediction_edges.sum(), 1)),
        "target_edge_pixels": int(target_edges.sum()),
        "prediction_edge_pixels": int(prediction_edges.sum()),
        "false_edge_pixels": int(false_edges.sum()),
    }


def main():
    args = parse_args()
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

    records = []
    with torch.inference_mode():
        for index, sample in enumerate(load_samples(args.data_root)):
            if args.max_samples is not None and index >= args.max_samples:
                break
            guidance, low_resolution, rgb, target, depth_min, depth_max = prepare_tensors(
                sample,
                args.scale,
                device,
            )
            output, _, gate = model(
                (guidance, low_resolution),
                gate_mode=args.gate_mode,
                gate_application=args.gate_application,
                adaptive_threshold=args.adaptive_threshold,
                return_gate=True,
            )
            prediction = output[0, 0].detach().cpu().numpy()
            prediction = prediction * (depth_max - depth_min) + depth_min
            metrics = calculate_metrics(
                prediction,
                target,
                rgb,
                args.crop_border,
                args.depth_edge_threshold_mm,
                args.rgb_edge_threshold,
            )
            records.append(
                {
                    "index": index,
                    "name": sample["name"],
                    "gate_mean": float(gate.mean().item()),
                    "gate_std": float(gate.std().item()),
                    "gate_suppressed_fraction": float((gate < 0.9).float().mean().item()),
                    "high_frequency_selected": bool(
                        args.gate_application == "high_frequency"
                        or (
                            args.gate_application == "adaptive"
                            and gate.mean().item() < args.adaptive_threshold
                        )
                    ),
                    **metrics,
                }
            )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "per_sample.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    summary = {
        "status": "completed",
        "completion_level": "real_input_protocol_reproduction",
        "task": "rgb_guided_depth_super_resolution",
        "method": "SGNet_spatial_reliability_gate",
        "dataset": "RGB-D-D_real_test",
        "scale": args.scale,
        "sample_count": len(records),
        "base_checkpoint_sha256": sha256(args.checkpoint),
        "gate_checkpoint_sha256": sha256(args.gate_checkpoint),
        "gate_mode": args.gate_mode,
        "gate_application": args.gate_application,
        "adaptive_threshold": args.adaptive_threshold,
        "crop_border": args.crop_border,
        "metrics_unit": "centimeters",
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
