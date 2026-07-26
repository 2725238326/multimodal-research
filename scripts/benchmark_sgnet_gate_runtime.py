import argparse
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import torch

from evaluate_sgnet_rgbdd_x16 import load_pairs, prepare_tensors, sha256
from sgnet_reliability_gate import SGNetWithReliabilityGate


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sgnet-dir", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--gate-checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--scale", type=int, default=16)
    parser.add_argument("--num-feats", type=int, default=40)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--adaptive-threshold", type=float, default=0.75)
    return parser.parse_args()


def percentile(values, level):
    return float(np.percentile(np.asarray(values, dtype=np.float64), level))


def main():
    args = parse_args()
    device = torch.device(args.device)
    sys.path.insert(0, str(args.sgnet_dir.resolve()))
    from models.SGNet import SGNet

    base = SGNet(num_feats=args.num_feats, kernel_size=3, scale=args.scale)
    base.load_state_dict(torch.load(args.checkpoint, map_location=device))
    base.to(device).eval()
    gate_checkpoint = torch.load(args.gate_checkpoint, map_location=device)
    gate_model = SGNetWithReliabilityGate(
        SGNet(num_feats=args.num_feats, kernel_size=3, scale=args.scale),
        hidden_channels=gate_checkpoint["hidden_channels"],
        initial_bias=gate_checkpoint["initial_bias"],
    )
    gate_model.base_model.load_state_dict(torch.load(args.checkpoint, map_location=device))
    gate_model.reliability_gate.load_state_dict(gate_checkpoint["gate_state_dict"])
    gate_model.to(device).eval()
    pairs = list(load_pairs(args.data_root, args.scale))[: args.samples]

    results = {}
    for mode in ("baseline", "full", "high_frequency", "adaptive"):
        model = base if mode == "baseline" else gate_model
        timings = []
        with torch.inference_mode():
            for index, (_, rgb, depth) in enumerate(pairs):
                guidance, low_resolution, _ = prepare_tensors(
                    rgb,
                    depth,
                    args.scale,
                    0,
                    0,
                    device,
                )
                if mode == "baseline":
                    call = lambda: model((guidance, low_resolution))
                else:
                    call = lambda: model(
                        (guidance, low_resolution),
                        gate_mode="learned",
                        gate_application=mode,
                        adaptive_threshold=args.adaptive_threshold,
                        return_gate=True,
                    )
                if index < args.warmup:
                    call()
                    continue
                if device.type == "cuda":
                    torch.cuda.synchronize(device)
                start = time.perf_counter()
                call()
                if device.type == "cuda":
                    torch.cuda.synchronize(device)
                timings.append((time.perf_counter() - start) * 1000.0)
        results[mode] = {
            "timed_samples": len(timings),
            "mean_ms": float(np.mean(timings)),
            "p50_ms": percentile(timings, 50),
            "p95_ms": percentile(timings, 95),
            "peak_cuda_memory_mb": float(torch.cuda.max_memory_allocated(device) / 1024**2)
            if device.type == "cuda"
            else None,
            "parameter_count": sum(parameter.numel() for parameter in model.parameters()),
        }
        if device.type == "cuda":
            torch.cuda.reset_peak_memory_stats(device)

    output = {
        "status": "completed",
        "dataset": "RGB-D-D/test2",
        "scale": args.scale,
        "sample_count": len(pairs),
        "warmup_samples": args.warmup,
        "metrics_unit": "milliseconds per image",
        "checkpoint_sha256": sha256(args.checkpoint),
        "gate_checkpoint_sha256": sha256(args.gate_checkpoint),
        "adaptive_threshold": args.adaptive_threshold,
        "environment": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "cuda_runtime": torch.version.cuda,
            "device": str(device),
            "device_name": torch.cuda.get_device_name(device)
            if device.type == "cuda"
            else "cpu",
        },
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
