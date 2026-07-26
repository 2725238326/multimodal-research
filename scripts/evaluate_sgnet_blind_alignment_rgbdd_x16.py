import argparse
import json
import platform
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as functional

from evaluate_sgnet_rgbdd_x16 import (
    aggregate,
    calculate_metrics,
    load_pairs,
    prepare_tensors,
    sha256,
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sgnet-dir", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--scale", type=int, default=16)
    parser.add_argument("--num-feats", type=int, default=40)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--shift-x", type=int, default=0)
    parser.add_argument("--shift-y", type=int, default=0)
    parser.add_argument("--max-alignment-shift", type=int, default=4)
    parser.add_argument("--smoothing-kernel", type=int, default=9)
    parser.add_argument("--calibrator-checkpoint", type=Path)
    parser.add_argument("--crop-border", type=int, default=6)
    parser.add_argument("--depth-edge-threshold", type=float, default=2.0)
    parser.add_argument("--rgb-edge-threshold", type=float, default=8.0)
    parser.add_argument("--max-samples", type=int)
    return parser.parse_args()


def shift_tensor_edge(image, shift_x):
    if shift_x == 0:
        return image
    padding = abs(shift_x)
    padded = functional.pad(image, (padding, padding, 0, 0), mode="replicate")
    start_x = padding - shift_x
    return padded[..., start_x : start_x + image.shape[-1]]


def gradient_magnitude(image):
    sobel_x = image.new_tensor(
        [[-1.0, 0.0, 1.0], [-2.0, 0.0, 2.0], [-1.0, 0.0, 1.0]]
    ).view(1, 1, 3, 3)
    sobel_y = sobel_x.transpose(2, 3)
    grad_x = functional.conv2d(image, sobel_x, padding=1)
    grad_y = functional.conv2d(image, sobel_y, padding=1)
    return torch.sqrt(grad_x.square() + grad_y.square() + 1e-12)


def standardized_correlation(first, second, border):
    if border:
        first = first[..., border:-border, border:-border]
        second = second[..., border:-border, border:-border]
    first = (first - first.mean()) / first.std().clamp_min(1e-6)
    second = (second - second.mean()) / second.std().clamp_min(1e-6)
    return float((first * second).mean().item())


class ShiftCalibrator(torch.nn.Module):
    def __init__(self, max_shift):
        super().__init__()
        class_count = 2 * max_shift + 1
        self.network = torch.nn.Sequential(
            torch.nn.Linear(class_count, 32),
            torch.nn.GELU(),
            torch.nn.Linear(32, class_count),
        )

    def forward(self, correlation_scores):
        return self.network(correlation_scores)


def correlation_features(
    guidance,
    low_resolution,
    max_shift,
    smoothing_kernel,
):
    luminance = (
        0.299 * guidance[:, 0:1]
        + 0.587 * guidance[:, 1:2]
        + 0.114 * guidance[:, 2:3]
    )
    low_up = functional.interpolate(
        low_resolution,
        size=guidance.shape[-2:],
        mode="bicubic",
        align_corners=False,
    )
    padding = smoothing_kernel // 2
    luminance = functional.avg_pool2d(
        luminance,
        kernel_size=smoothing_kernel,
        stride=1,
        padding=padding,
    )
    rgb_gradient = gradient_magnitude(luminance)
    depth_gradient = gradient_magnitude(low_up)
    comparison_border = max_shift + padding + 1
    rgb_gradient = rgb_gradient[
        ..., comparison_border:-comparison_border, comparison_border:-comparison_border
    ]
    depth_gradient = depth_gradient[
        ..., comparison_border:-comparison_border, comparison_border:-comparison_border
    ]
    depth_flat = depth_gradient.flatten(1)
    depth_flat = (depth_flat - depth_flat.mean(1, keepdim=True)) / depth_flat.std(
        1, keepdim=True
    ).clamp_min(1e-6)
    scores = []
    for correction in range(-max_shift, max_shift + 1):
        corrected_gradient = shift_tensor_edge(rgb_gradient, correction).flatten(1)
        corrected_gradient = (
            corrected_gradient - corrected_gradient.mean(1, keepdim=True)
        ) / corrected_gradient.std(1, keepdim=True).clamp_min(1e-6)
        scores.append((corrected_gradient * depth_flat).mean(1))
    return torch.stack(scores, dim=1)


def estimate_horizontal_correction(
    guidance,
    low_resolution,
    max_shift,
    smoothing_kernel,
    calibrator=None,
):
    features = correlation_features(
        guidance,
        low_resolution,
        max_shift,
        smoothing_kernel,
    )[0]
    scores = {
        correction: float(features[correction + max_shift].item())
        for correction in range(-max_shift, max_shift + 1)
    }
    decision_scores = scores
    if calibrator is not None:
        logits = calibrator(features.unsqueeze(0))[0]
        decision_scores = {
            correction: float(logits[correction + max_shift].item())
            for correction in range(-max_shift, max_shift + 1)
        }
    best_correction = max(decision_scores, key=decision_scores.get)
    sorted_scores = sorted(decision_scores.values(), reverse=True)
    score_margin = sorted_scores[0] - sorted_scores[1]
    return best_correction, score_margin, scores, decision_scores


def main():
    args = parse_args()
    if args.shift_y != 0:
        raise ValueError("This gate estimates horizontal translation only")
    if args.smoothing_kernel < 1 or args.smoothing_kernel % 2 == 0:
        raise ValueError("smoothing-kernel must be a positive odd integer")
    sys.path.insert(0, str(args.sgnet_dir.resolve()))
    from models.SGNet import SGNet

    if not args.checkpoint.is_file():
        raise FileNotFoundError(args.checkpoint)
    device = torch.device(args.device)
    model = SGNet(num_feats=args.num_feats, kernel_size=3, scale=args.scale)
    model.load_state_dict(torch.load(args.checkpoint, map_location=device))
    model.to(device).eval()
    calibrator = None
    calibrator_hash = None
    if args.calibrator_checkpoint is not None:
        checkpoint = torch.load(args.calibrator_checkpoint, map_location=device)
        if checkpoint["max_shift"] != args.max_alignment_shift:
            raise ValueError("Calibrator max_shift does not match evaluation setting")
        if checkpoint["smoothing_kernel"] != args.smoothing_kernel:
            raise ValueError("Calibrator smoothing kernel does not match evaluation setting")
        calibrator = ShiftCalibrator(args.max_alignment_shift).to(device)
        calibrator.load_state_dict(checkpoint["model_state_dict"])
        calibrator.eval()
        calibrator_hash = sha256(args.calibrator_checkpoint)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    with torch.inference_mode():
        for index, (name, rgb, depth) in enumerate(load_pairs(args.data_root, args.scale)):
            if args.max_samples is not None and index >= args.max_samples:
                break
            guidance, low_resolution, shifted_rgb = prepare_tensors(
                rgb, depth, args.scale, args.shift_x, args.shift_y, device
            )
            correction, score_margin, scores, decision_scores = estimate_horizontal_correction(
                guidance,
                low_resolution,
                args.max_alignment_shift,
                args.smoothing_kernel,
                calibrator,
            )
            corrected_guidance = shift_tensor_edge(guidance, correction)
            corrected_rgb = (
                corrected_guidance[0].permute(1, 2, 0).cpu().numpy() * 255.0
            )
            output = model((corrected_guidance, low_resolution))
            prediction = output[0] if isinstance(output, (tuple, list)) else output
            prediction = prediction[0, 0].detach().cpu().numpy()
            metrics = calculate_metrics(
                prediction,
                depth,
                corrected_rgb,
                args.crop_border,
                args.depth_edge_threshold,
                args.rgb_edge_threshold,
            )
            records.append(
                {
                    "index": index,
                    "name": name,
                    "estimated_correction_x": correction,
                    "ideal_correction_x": -args.shift_x,
                    "correction_absolute_error": abs(correction + args.shift_x),
                    "score_margin": score_margin,
                    "alignment_scores": {str(key): value for key, value in scores.items()},
                    "decision_scores": {
                        str(key): value for key, value in decision_scores.items()
                    },
                    **metrics,
                }
            )

    with (args.output_dir / "per_sample.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    corrections = [record["estimated_correction_x"] for record in records]
    correction_errors = [record["correction_absolute_error"] for record in records]
    ideal_correction = -args.shift_x
    summary = {
        "status": "completed",
        "task": "rgb_guided_depth_super_resolution",
        "method": "SGNet_blind_gradient_alignment",
        "dataset": "RGB-D-D/test2",
        "scale": args.scale,
        "sample_count": len(records),
        "checkpoint_sha256": sha256(args.checkpoint),
        "calibrator_checkpoint_sha256": calibrator_hash,
        "injected_shift_x": args.shift_x,
        "ideal_correction_x": ideal_correction,
        "max_alignment_shift": args.max_alignment_shift,
        "smoothing_kernel": args.smoothing_kernel,
        "alignment_uses_ground_truth": False,
        "alignment_decision": "trained_calibrator" if calibrator is not None else "raw_argmax",
        "alignment": {
            "exact_recovery_rate": float(np.mean(np.asarray(corrections) == ideal_correction)),
            "mean_absolute_correction_error": float(np.mean(correction_errors)),
            "median_correction": float(np.median(corrections)),
            "correction_histogram": {
                str(value): corrections.count(value)
                for value in range(-args.max_alignment_shift, args.max_alignment_shift + 1)
            },
        },
        "crop_border": args.crop_border,
        "metrics_unit": "8-bit depth levels",
        "metrics": aggregate(records),
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
