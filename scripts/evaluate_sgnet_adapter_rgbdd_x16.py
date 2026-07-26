import argparse
import json
import platform
import sys
from pathlib import Path

import torch

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
    parser.add_argument("--adapter-checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--scale", type=int, default=16)
    parser.add_argument("--num-feats", type=int, default=40)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--shift-x", type=int, default=0)
    parser.add_argument("--shift-y", type=int, default=0)
    parser.add_argument("--crop-border", type=int, default=6)
    parser.add_argument("--depth-edge-threshold", type=float, default=2.0)
    parser.add_argument("--rgb-edge-threshold", type=float, default=8.0)
    parser.add_argument("--max-samples", type=int)
    return parser.parse_args()


def main():
    args = parse_args()
    sys.path.insert(0, str(args.sgnet_dir.resolve()))
    from models.SGNet import SGNet

    device = torch.device(args.device)
    model = SGNet(num_feats=args.num_feats, kernel_size=3, scale=args.scale)
    model.load_state_dict(torch.load(args.checkpoint, map_location=device))
    adapter = torch.load(args.adapter_checkpoint, map_location=device)
    incompatible = model.load_state_dict(adapter["adapter_state_dict"], strict=False)
    if incompatible.unexpected_keys:
        raise RuntimeError(f"Unexpected adapter keys: {incompatible.unexpected_keys}")
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
            prediction = model((guidance, low_resolution))[0]
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
        "method": "SGNet_misalignment_consistency_adapter",
        "dataset": "RGB-D-D/test2",
        "scale": args.scale,
        "sample_count": len(records),
        "base_checkpoint_sha256": sha256(args.checkpoint),
        "adapter_checkpoint_sha256": sha256(args.adapter_checkpoint),
        "shift_x": args.shift_x,
        "shift_y": args.shift_y,
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
