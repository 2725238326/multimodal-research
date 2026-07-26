import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch

from evaluate_sgnet_rgbdd_x16 import load_pairs, prepare_tensors
from sgnet_reliability_gate import SGNetWithReliabilityGate


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sgnet-dir", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--gate-checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--names", required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--scale", type=int, default=16)
    parser.add_argument("--num-feats", type=int, default=40)
    parser.add_argument("--shift-x", type=int, default=0)
    parser.add_argument("--shift-y", type=int, default=0)
    parser.add_argument("--rgb-scale", type=float, default=1.0)
    parser.add_argument("--texture-amplitude", type=float, default=0.0)
    parser.add_argument("--texture-block-size", type=int, default=4)
    parser.add_argument("--adaptive-threshold", type=float, default=0.75)
    return parser.parse_args()


def main():
    args = parse_args()
    requested = set(args.names.split(","))
    device = torch.device(args.device)
    sys.path.insert(0, str(args.sgnet_dir.resolve()))
    from models.SGNet import SGNet

    base = SGNet(num_feats=args.num_feats, kernel_size=3, scale=args.scale)
    base.load_state_dict(torch.load(args.checkpoint, map_location=device))
    base.to(device).eval()
    checkpoint = torch.load(args.gate_checkpoint, map_location=device)
    gated = SGNetWithReliabilityGate(
        SGNet(num_feats=args.num_feats, kernel_size=3, scale=args.scale),
        hidden_channels=checkpoint["hidden_channels"],
        initial_bias=checkpoint["initial_bias"],
    )
    gated.base_model.load_state_dict(torch.load(args.checkpoint, map_location=device))
    gated.reliability_gate.load_state_dict(checkpoint["gate_state_dict"])
    gated.to(device).eval()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    with torch.inference_mode():
        for name, rgb, target in load_pairs(args.data_root, args.scale):
            if name not in requested:
                continue
            guidance, low_resolution, perturbed_rgb = prepare_tensors(
                rgb,
                target,
                args.scale,
                args.shift_x,
                args.shift_y,
                device,
                rgb_scale=args.rgb_scale,
                texture_amplitude=args.texture_amplitude,
                texture_block_size=args.texture_block_size,
            )
            base_output = base((guidance, low_resolution))[0][0, 0]
            adaptive_output, _, gate = gated(
                (guidance, low_resolution),
                gate_mode="learned",
                gate_application="adaptive",
                adaptive_threshold=args.adaptive_threshold,
                return_gate=True,
            )
            base_depth = np.clip(base_output.detach().cpu().numpy(), 0, 1) * 255.0
            adaptive_depth = (
                np.clip(adaptive_output[0, 0].detach().cpu().numpy(), 0, 1) * 255.0
            )
            gate_map = gate[0, 0].detach().cpu().numpy()
            base_error = np.abs(base_depth - target)
            adaptive_error = np.abs(adaptive_depth - target)
            delta_error = base_error - adaptive_error
            depth_min, depth_max = float(target.min()), float(target.max())
            error_max = max(
                1.0,
                float(np.percentile(np.concatenate((base_error.ravel(), adaptive_error.ravel())), 99)),
            )
            delta_max = max(0.1, float(np.percentile(np.abs(delta_error), 99)))
            selected = gate_map.mean() < args.adaptive_threshold

            figure, axes = plt.subplots(2, 4, figsize=(16, 8), constrained_layout=True)
            axes[0, 0].imshow(np.clip(perturbed_rgb / 255.0, 0, 1))
            axes[0, 0].set_title("RGB guidance")
            axes[0, 1].imshow(target, cmap="viridis", vmin=depth_min, vmax=depth_max)
            axes[0, 1].set_title("GT depth")
            axes[0, 2].imshow(base_depth, cmap="viridis", vmin=depth_min, vmax=depth_max)
            axes[0, 2].set_title("SGNet")
            axes[0, 3].imshow(adaptive_depth, cmap="viridis", vmin=depth_min, vmax=depth_max)
            axes[0, 3].set_title("Adaptive gate")
            axes[1, 0].imshow(base_error, cmap="magma", vmin=0, vmax=error_max)
            axes[1, 0].set_title("SGNet absolute error")
            axes[1, 1].imshow(adaptive_error, cmap="magma", vmin=0, vmax=error_max)
            axes[1, 1].set_title("Adaptive absolute error")
            axes[1, 2].imshow(gate_map, cmap="gray", vmin=0, vmax=1)
            axes[1, 2].set_title(
                f"Gate mean {gate_map.mean():.3f} ({'high-freq' if selected else 'full'})"
            )
            axes[1, 3].imshow(
                delta_error,
                cmap="coolwarm",
                vmin=-delta_max,
                vmax=delta_max,
            )
            axes[1, 3].set_title("Error reduction (red = better)")
            for axis in axes.flat:
                axis.axis("off")
            figure.suptitle(name, fontsize=14)
            figure.savefig(args.output_dir / name, dpi=150)
            plt.close(figure)


if __name__ == "__main__":
    main()
