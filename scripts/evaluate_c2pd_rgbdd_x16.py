import argparse
import json
import platform
import sys
from pathlib import Path

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
    parser.add_argument("--c2pd-dir", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--scale", type=int, default=16)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--shift-x", type=int, default=0)
    parser.add_argument("--shift-y", type=int, default=0)
    parser.add_argument("--crop-border", type=int, default=6)
    parser.add_argument("--depth-edge-threshold", type=float, default=2.0)
    parser.add_argument("--rgb-edge-threshold", type=float, default=8.0)
    parser.add_argument("--max-samples", type=int)
    return parser.parse_args()


def normalize_state_dict(checkpoint):
    if isinstance(checkpoint, dict) and "state_dict" in checkpoint:
        checkpoint = checkpoint["state_dict"]
    if not isinstance(checkpoint, dict):
        raise TypeError("Checkpoint is not a state dictionary")
    return {
        key.removeprefix("module."): value for key, value in checkpoint.items()
    }


def main():
    args = parse_args()
    sys.path.insert(0, str(args.c2pd_dir.resolve()))
    from model.c2pd import C2PD

    if not args.checkpoint.is_file():
        raise FileNotFoundError(args.checkpoint)
    device = torch.device(args.device)
    model = C2PD()
    checkpoint = torch.load(args.checkpoint, map_location=device)
    model.load_state_dict(normalize_state_dict(checkpoint))
    model.to(device).eval()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    with torch.inference_mode():
        for index, (name, rgb, depth) in enumerate(load_pairs(args.data_root, args.scale)):
            if args.max_samples is not None and index >= args.max_samples:
                break
            guidance, low_resolution, shifted_rgb = prepare_tensors(
                rgb, depth, args.scale, args.shift_x, args.shift_y, device
            )
            low_resolution_up = functional.interpolate(
                low_resolution,
                size=guidance.shape[-2:],
                mode="bicubic",
                align_corners=False,
            )
            prediction = model(rgb=guidance, lr_up=low_resolution_up)
            prediction = prediction[0, 0].detach().cpu().numpy()
            metrics = calculate_metrics(
                prediction,
                depth,
                shifted_rgb,
                args.crop_border,
                args.depth_edge_threshold,
                args.rgb_edge_threshold,
            )
            records.append({"index": index, "name": name, **metrics})

    with (args.output_dir / "per_sample.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    summary = {
        "status": "completed",
        "task": "rgb_guided_depth_super_resolution",
        "method": "C2PD",
        "dataset": "RGB-D-D/test2",
        "scale": args.scale,
        "sample_count": len(records),
        "checkpoint_sha256": sha256(args.checkpoint),
        "shift_x": args.shift_x,
        "shift_y": args.shift_y,
        "crop_border": args.crop_border,
        "depth_edge_threshold": args.depth_edge_threshold,
        "rgb_edge_threshold": args.rgb_edge_threshold,
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
