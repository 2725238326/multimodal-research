import argparse
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as functional
from PIL import Image
from torch.utils.data import DataLoader, Subset

from evaluate_sgnet_blind_alignment_rgbdd_x16 import shift_tensor_edge
from sgnet_reliability_gate import SGNetWithReliabilityGate, build_reliability_target
from train_rgb_depth_shift_calibrator import NYUPairs


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sgnet-dir", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument(
        "--dataset-format",
        choices=("nyu_npy", "rgbdd_real"),
        default="nyu_npy",
    )
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--scale", type=int, default=16)
    parser.add_argument("--num-feats", type=int, default=40)
    parser.add_argument("--crop-size", type=int, default=256)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--max-shift", type=int, default=4)
    parser.add_argument("--consistency-weight", type=float, default=0.5)
    parser.add_argument("--identity-weight", type=float, default=0.01)
    parser.add_argument("--gate-supervision-weight", type=float, default=0.0)
    parser.add_argument("--minimum-reliability", type=float, default=0.2)
    parser.add_argument(
        "--gate-application",
        choices=("full", "high_frequency", "adaptive"),
        default="full",
    )
    parser.add_argument("--adaptive-threshold", type=float, default=0.75)
    parser.add_argument("--hidden-channels", type=int, default=8)
    parser.add_argument("--initial-bias", type=float, default=4.0)
    parser.add_argument("--initial-gate-checkpoint", type=Path)
    parser.add_argument("--texture-probability", type=float, default=0.0)
    parser.add_argument("--texture-max-amplitude", type=float, default=0.0)
    parser.add_argument("--texture-block-size", type=int, default=4)
    parser.add_argument("--texture-min-patch-fraction", type=float, default=0.25)
    parser.add_argument("--texture-max-patch-fraction", type=float, default=0.5)
    parser.add_argument("--train-samples", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20260723)
    parser.add_argument("--max-train-batches", type=int)
    return parser.parse_args()


def apply_individual_shifts(rgb, shifts):
    return torch.cat(
        [shift_tensor_edge(image.unsqueeze(0), int(shift)) for image, shift in zip(rgb, shifts)],
        dim=0,
    )


class RGBDDRealPairs(torch.utils.data.Dataset):
    categories = ("models", "plants", "portraits")

    def __init__(self, data_root, crop_size, scale):
        self.crop_size = crop_size
        self.scale = scale
        self.samples = []
        for category in self.categories:
            category_root = data_root / category / f"{category}_train"
            for sample_root in sorted(path for path in category_root.iterdir() if path.is_dir()):
                sample_id = sample_root.name
                self.samples.append(
                    (
                        sample_root / f"{sample_id}_RGB.jpg",
                        sample_root / f"{sample_id}_HR_gt.png",
                        sample_root / f"{sample_id}_LR_fill_depth.png",
                    )
                )

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):
        rgb_path, target_path, low_resolution_path = self.samples[index]
        rgb = np.asarray(Image.open(rgb_path).convert("RGB"), dtype=np.float32)
        target = np.asarray(Image.open(target_path), dtype=np.float32)
        height, width = target.shape
        low_resolution = np.asarray(
            Image.open(low_resolution_path).resize(
                (width // self.scale, height // self.scale),
                Image.Resampling.BICUBIC,
            ),
            dtype=np.float32,
        )
        depth_min = float(low_resolution.min())
        depth_range = max(float(low_resolution.max()) - depth_min, 1e-6)
        low_resolution = (low_resolution - depth_min) / depth_range
        target = (target - depth_min) / depth_range
        rgb_min = float(rgb.min())
        rgb_range = max(float(rgb.max()) - rgb_min, 1e-6)
        rgb = (rgb - rgb_min) / rgb_range

        low_crop_size = self.crop_size // self.scale
        max_top = low_resolution.shape[0] - low_crop_size
        max_left = low_resolution.shape[1] - low_crop_size
        top_low = random.randint(0, max_top)
        left_low = random.randint(0, max_left)
        top = top_low * self.scale
        left = left_low * self.scale
        rgb = rgb[top : top + self.crop_size, left : left + self.crop_size]
        target = target[top : top + self.crop_size, left : left + self.crop_size]
        low_resolution = low_resolution[
            top_low : top_low + low_crop_size,
            left_low : left_low + low_crop_size,
        ]
        rgb = torch.from_numpy(np.ascontiguousarray(rgb.transpose(2, 0, 1)))
        target = torch.from_numpy(np.ascontiguousarray(target)).unsqueeze(0)
        low_resolution = torch.from_numpy(np.ascontiguousarray(low_resolution)).unsqueeze(0)
        return rgb.float(), target.float(), low_resolution.float()


def apply_random_texture_patches(
    rgb,
    probability,
    max_amplitude,
    block_size,
    min_patch_fraction,
    max_patch_fraction,
):
    if not 0.0 <= probability <= 1.0:
        raise ValueError("texture_probability must be between 0 and 1")
    if max_amplitude < 0:
        raise ValueError("texture_max_amplitude must be non-negative")
    if block_size <= 0:
        raise ValueError("texture_block_size must be positive")
    if not 0.0 < min_patch_fraction <= max_patch_fraction <= 1.0:
        raise ValueError("texture patch fractions must satisfy 0 < min <= max <= 1")
    output = rgb.clone()
    applied = 0
    amplitude_sum = 0.0
    coverage_sum = 0.0
    _, _, height, width = rgb.shape
    rows = torch.arange(height, device=rgb.device)[:, None] // block_size
    columns = torch.arange(width, device=rgb.device)[None, :] // block_size
    pattern = ((rows + columns) % 2).to(rgb.dtype) * 2.0 - 1.0
    for index in range(len(rgb)):
        if max_amplitude == 0 or torch.rand((), device=rgb.device) >= probability:
            continue
        fraction = float(
            torch.empty((), device=rgb.device)
            .uniform_(min_patch_fraction, max_patch_fraction)
            .item()
        )
        patch_height = max(1, int(round(height * fraction)))
        patch_width = max(1, int(round(width * fraction)))
        top = int(torch.randint(0, height - patch_height + 1, (), device=rgb.device).item())
        left = int(torch.randint(0, width - patch_width + 1, (), device=rgb.device).item())
        amplitude = float(
            torch.empty((), device=rgb.device)
            .uniform_(0.5 * max_amplitude, max_amplitude)
            .item()
        )
        patch = output[index, :, top : top + patch_height, left : left + patch_width]
        texture = pattern[top : top + patch_height, left : left + patch_width]
        patch.add_(texture.unsqueeze(0) * (amplitude / 255.0)).clamp_(0.0, 1.0)
        applied += 1
        amplitude_sum += amplitude
        coverage_sum += patch_height * patch_width / (height * width)
    return output, applied, amplitude_sum, coverage_sum


def main():
    args = parse_args()
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device(args.device)
    if device.type == "cuda":
        torch.cuda.set_device(device)
        torch.cuda.init()
        torch.cuda.manual_seed_all(args.seed)
        torch.cuda.reset_peak_memory_stats(device)

    sys.path.insert(0, str(args.sgnet_dir.resolve()))
    from models.SGNet import SGNet

    base_model = SGNet(num_feats=args.num_feats, kernel_size=3, scale=args.scale)
    base_model.load_state_dict(torch.load(args.checkpoint, map_location=device))
    model = SGNetWithReliabilityGate(
        base_model,
        hidden_channels=args.hidden_channels,
        initial_bias=args.initial_bias,
    ).to(device)
    if args.initial_gate_checkpoint is not None:
        initial_gate_checkpoint = torch.load(args.initial_gate_checkpoint, map_location=device)
        model.reliability_gate.load_state_dict(initial_gate_checkpoint["gate_state_dict"])
    for parameter in model.base_model.parameters():
        parameter.requires_grad = False
    model.base_model.eval()
    model.reliability_gate.train()
    trainable_parameters = list(model.reliability_gate.parameters())
    optimizer = torch.optim.Adam(trainable_parameters, lr=args.learning_rate)

    if args.dataset_format == "nyu_npy":
        dataset = NYUPairs(args.data_root, args.crop_size)
    else:
        dataset = RGBDDRealPairs(args.data_root, args.crop_size, args.scale)
    sample_count = min(args.train_samples, len(dataset))
    generator = torch.Generator().manual_seed(args.seed)
    indices = torch.randperm(len(dataset), generator=generator)[:sample_count].tolist()
    loader = DataLoader(
        Subset(dataset, indices),
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=0,
        generator=generator,
    )

    history = []
    start_time = time.time()
    last_gradient_norm = None
    for epoch in range(args.epochs):
        reconstruction_sum = 0.0
        consistency_sum = 0.0
        identity_sum = 0.0
        gate_supervision_sum = 0.0
        target_mean_sum = 0.0
        gate_mean_sum = 0.0
        gate_suppressed_sum = 0.0
        texture_applied = 0
        texture_amplitude_sum = 0.0
        texture_coverage_sum = 0.0
        total = 0
        shift_histogram = {str(value): 0 for value in range(-args.max_shift, args.max_shift + 1)}
        for batch_index, batch in enumerate(loader):
            if args.max_train_batches is not None and batch_index >= args.max_train_batches:
                break
            if args.dataset_format == "nyu_npy":
                rgb, depth = batch
                low_resolution = functional.interpolate(
                    depth,
                    scale_factor=1 / args.scale,
                    mode="bicubic",
                    align_corners=False,
                )
            else:
                rgb, depth, low_resolution = batch
            rgb = rgb.to(device)
            depth = depth.to(device)
            low_resolution = low_resolution.to(device)
            shifts = torch.randint(
                -args.max_shift,
                args.max_shift + 1,
                (len(rgb),),
                device=device,
            )
            shifted_rgb = apply_individual_shifts(rgb, shifts)
            corrupted_rgb, applied, amplitude_sum, coverage_sum = apply_random_texture_patches(
                shifted_rgb,
                probability=args.texture_probability,
                max_amplitude=args.texture_max_amplitude,
                block_size=args.texture_block_size,
                min_patch_fraction=args.texture_min_patch_fraction,
                max_patch_fraction=args.texture_max_patch_fraction,
            )
            texture_applied += applied
            texture_amplitude_sum += amplitude_sum
            texture_coverage_sum += coverage_sum
            for shift in shifts.tolist():
                shift_histogram[str(shift)] += 1

            with torch.no_grad():
                clean_reference = model(
                    (rgb, low_resolution),
                    gate_mode="identity",
                    gate_application=args.gate_application,
                    adaptive_threshold=args.adaptive_threshold,
                )[0].detach()
            optimizer.zero_grad(set_to_none=True)
            shifted_output, _, gate = model(
                (corrupted_rgb, low_resolution),
                gate_mode="learned",
                gate_application=args.gate_application,
                adaptive_threshold=args.adaptive_threshold,
                return_gate=True,
            )
            reconstruction_loss = functional.l1_loss(shifted_output, depth)
            consistency_loss = functional.l1_loss(shifted_output, clean_reference)
            identity_loss = torch.mean(1.0 - gate)
            with torch.no_grad():
                reliability_target = build_reliability_target(
                    corrupted_rgb,
                    depth,
                    minimum_reliability=args.minimum_reliability,
                )
            gate_supervision_loss = functional.smooth_l1_loss(
                gate,
                reliability_target,
            )
            loss = (
                reconstruction_loss
                + args.consistency_weight * consistency_loss
                + args.identity_weight * identity_loss
                + args.gate_supervision_weight * gate_supervision_loss
            )
            loss.backward()
            squared_norm = sum(
                parameter.grad.detach().square().sum()
                for parameter in trainable_parameters
                if parameter.grad is not None
            )
            last_gradient_norm = float(torch.sqrt(squared_norm).item())
            optimizer.step()

            reconstruction_sum += float(reconstruction_loss.item()) * len(rgb)
            consistency_sum += float(consistency_loss.item()) * len(rgb)
            identity_sum += float(identity_loss.item()) * len(rgb)
            gate_supervision_sum += float(gate_supervision_loss.item()) * len(rgb)
            target_mean_sum += float(reliability_target.mean().item()) * len(rgb)
            gate_mean_sum += float(gate.mean().item()) * len(rgb)
            gate_suppressed_sum += float((gate < 0.9).float().mean().item()) * len(rgb)
            total += len(rgb)
        history.append(
            {
                "epoch": epoch + 1,
                "train_samples": total,
                "reconstruction_l1": reconstruction_sum / max(total, 1),
                "consistency_l1": consistency_sum / max(total, 1),
                "identity_loss": identity_sum / max(total, 1),
                "gate_supervision_loss": gate_supervision_sum / max(total, 1),
                "target_mean": target_mean_sum / max(total, 1),
                "gate_mean": gate_mean_sum / max(total, 1),
                "gate_suppressed_fraction": gate_suppressed_sum / max(total, 1),
                "texture_applied_samples": texture_applied,
                "texture_mean_amplitude_8bit": texture_amplitude_sum
                / max(texture_applied, 1),
                "texture_mean_coverage": texture_coverage_sum / max(texture_applied, 1),
                "shift_histogram": shift_histogram,
            }
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = args.output_dir / "sgnet_reliability_gate.pth"
    gate_state = {
        name: tensor.detach().cpu()
        for name, tensor in model.reliability_gate.state_dict().items()
    }
    torch.save(
        {
            "gate_state_dict": gate_state,
            "hidden_channels": args.hidden_channels,
            "initial_bias": args.initial_bias,
            "scale": args.scale,
            "seed": args.seed,
            "gate_supervision_weight": args.gate_supervision_weight,
            "minimum_reliability": args.minimum_reliability,
            "gate_application": args.gate_application,
            "adaptive_threshold": args.adaptive_threshold,
            "texture_probability": args.texture_probability,
            "texture_max_amplitude": args.texture_max_amplitude,
            "texture_block_size": args.texture_block_size,
        },
        checkpoint_path,
    )
    restored_checkpoint = torch.load(checkpoint_path, map_location="cpu")
    restore_matches = all(
        torch.equal(gate_state[name], restored_checkpoint["gate_state_dict"][name])
        for name in gate_state
    )
    summary = {
        "status": "completed",
        "task": "sgnet_spatial_reliability_gate",
        "dataset": (
            "NYU_v2_train" if args.dataset_format == "nyu_npy" else "RGB-D-D_real_train"
        ),
        "dataset_format": args.dataset_format,
        "dataset_samples": len(dataset),
        "selected_train_samples": sample_count,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "max_train_batches": args.max_train_batches,
        "learning_rate": args.learning_rate,
        "max_shift": args.max_shift,
        "consistency_weight": args.consistency_weight,
        "identity_weight": args.identity_weight,
        "gate_supervision_weight": args.gate_supervision_weight,
        "minimum_reliability": args.minimum_reliability,
        "gate_application": args.gate_application,
        "adaptive_threshold": args.adaptive_threshold,
        "initialized_from_gate_checkpoint": args.initial_gate_checkpoint is not None,
        "texture_probability": args.texture_probability,
        "texture_max_amplitude": args.texture_max_amplitude,
        "texture_block_size": args.texture_block_size,
        "texture_min_patch_fraction": args.texture_min_patch_fraction,
        "texture_max_patch_fraction": args.texture_max_patch_fraction,
        "trainable_parameter_count": sum(parameter.numel() for parameter in trainable_parameters),
        "frozen_parameter_count": sum(parameter.numel() for parameter in model.base_model.parameters()),
        "history": history,
        "last_gradient_norm": last_gradient_norm,
        "peak_cuda_memory_mb": float(torch.cuda.max_memory_allocated(device) / 1024**2)
        if device.type == "cuda"
        else None,
        "elapsed_seconds": time.time() - start_time,
        "checkpoint_restore_matches": restore_matches,
        "checkpoint_file": checkpoint_path.name,
    }
    with (args.output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
