import argparse
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as functional
from torch.utils.data import DataLoader, Subset

from evaluate_sgnet_blind_alignment_rgbdd_x16 import shift_tensor_edge
from train_rgb_depth_shift_calibrator import NYUPairs


TRAINABLE_PREFIXES = (
    "conv_rgb1",
    "rgb_rb2",
    "rgb_rb3",
    "rgb_rb4",
    "bridge1",
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sgnet-dir", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--scale", type=int, default=16)
    parser.add_argument("--num-feats", type=int, default=40)
    parser.add_argument("--crop-size", type=int, default=256)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--learning-rate", type=float, default=1e-5)
    parser.add_argument("--max-shift", type=int, default=4)
    parser.add_argument("--consistency-weight", type=float, default=0.5)
    parser.add_argument("--clean-reconstruction-weight", type=float, default=0.0)
    parser.add_argument("--flat-reconstruction-weight", type=float, default=0.0)
    parser.add_argument("--flat-gradient-threshold", type=float, default=2.0 / 255.0)
    parser.add_argument("--frozen-clean-teacher", action="store_true")
    parser.add_argument("--train-samples", type=int, default=400)
    parser.add_argument("--seed", type=int, default=20260722)
    parser.add_argument("--max-train-batches", type=int)
    return parser.parse_args()


def set_trainable_parameters(model):
    trainable_names = []
    for name, parameter in model.named_parameters():
        parameter.requires_grad = name.startswith(TRAINABLE_PREFIXES)
        if parameter.requires_grad:
            trainable_names.append(name)
    return trainable_names


def apply_individual_shifts(rgb, shifts):
    return torch.cat(
        [shift_tensor_edge(image.unsqueeze(0), int(shift)) for image, shift in zip(rgb, shifts)],
        dim=0,
    )


def flat_region_mask(depth, threshold):
    horizontal = functional.pad(
        torch.abs(depth[..., 1:] - depth[..., :-1]),
        (0, 1, 0, 0),
        mode="replicate",
    )
    vertical = functional.pad(
        torch.abs(depth[..., 1:, :] - depth[..., :-1, :]),
        (0, 0, 0, 1),
        mode="replicate",
    )
    return torch.maximum(horizontal, vertical) <= threshold


def masked_l1(prediction, target, mask):
    selected = torch.abs(prediction - target)[mask]
    return selected.mean() if selected.numel() else prediction.new_zeros(())


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

    model = SGNet(num_feats=args.num_feats, kernel_size=3, scale=args.scale)
    model.load_state_dict(torch.load(args.checkpoint, map_location=device))
    model.to(device)
    trainable_names = set_trainable_parameters(model)
    trainable_parameters = [
        parameter for parameter in model.parameters() if parameter.requires_grad
    ]
    optimizer = torch.optim.Adam(trainable_parameters, lr=args.learning_rate)
    teacher = None
    if args.frozen_clean_teacher:
        teacher = SGNet(num_feats=args.num_feats, kernel_size=3, scale=args.scale)
        teacher.load_state_dict(torch.load(args.checkpoint, map_location=device))
        teacher.to(device).eval()
        for parameter in teacher.parameters():
            parameter.requires_grad = False

    dataset = NYUPairs(args.data_root, args.crop_size)
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
        model.train()
        reconstruction_sum = 0.0
        consistency_sum = 0.0
        clean_reconstruction_sum = 0.0
        flat_reconstruction_sum = 0.0
        total = 0
        shift_histogram = {str(value): 0 for value in range(-args.max_shift, args.max_shift + 1)}
        for batch_index, (rgb, depth) in enumerate(loader):
            if args.max_train_batches is not None and batch_index >= args.max_train_batches:
                break
            rgb = rgb.to(device)
            depth = depth.to(device)
            low_resolution = functional.interpolate(
                depth,
                scale_factor=1 / args.scale,
                mode="bicubic",
                align_corners=False,
            )
            shifts = torch.randint(
                -args.max_shift,
                args.max_shift + 1,
                (len(rgb),),
                device=device,
            )
            shifted_rgb = apply_individual_shifts(rgb, shifts)
            for shift in shifts.tolist():
                shift_histogram[str(shift)] += 1

            with torch.no_grad():
                clean_reference = (
                    teacher((rgb, low_resolution))[0]
                    if teacher is not None
                    else model((rgb, low_resolution))[0]
                ).detach()
            optimizer.zero_grad(set_to_none=True)
            shifted_output = model((shifted_rgb, low_resolution))[0]
            reconstruction_loss = functional.l1_loss(shifted_output, depth)
            consistency_loss = functional.l1_loss(shifted_output, clean_reference)
            clean_output = None
            clean_reconstruction_loss = shifted_output.new_zeros(())
            flat_reconstruction_loss = shifted_output.new_zeros(())
            if args.clean_reconstruction_weight or args.flat_reconstruction_weight:
                clean_output = model((rgb, low_resolution))[0]
                clean_reconstruction_loss = functional.l1_loss(clean_output, depth)
            if args.flat_reconstruction_weight:
                flat_mask = flat_region_mask(depth, args.flat_gradient_threshold)
                flat_reconstruction_loss = 0.5 * (
                    masked_l1(shifted_output, depth, flat_mask)
                    + masked_l1(clean_output, depth, flat_mask)
                )
            loss = (
                reconstruction_loss
                + args.consistency_weight * consistency_loss
                + args.clean_reconstruction_weight * clean_reconstruction_loss
                + args.flat_reconstruction_weight * flat_reconstruction_loss
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
            clean_reconstruction_sum += float(clean_reconstruction_loss.item()) * len(rgb)
            flat_reconstruction_sum += float(flat_reconstruction_loss.item()) * len(rgb)
            total += len(rgb)
        history.append(
            {
                "epoch": epoch + 1,
                "train_samples": total,
                "reconstruction_l1": reconstruction_sum / max(total, 1),
                "consistency_l1": consistency_sum / max(total, 1),
                "clean_reconstruction_l1": clean_reconstruction_sum / max(total, 1),
                "flat_reconstruction_l1": flat_reconstruction_sum / max(total, 1),
                "shift_histogram": shift_histogram,
            }
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    adapter_state = {
        name: tensor.detach().cpu()
        for name, tensor in model.state_dict().items()
        if name.startswith(TRAINABLE_PREFIXES)
    }
    checkpoint_path = args.output_dir / "sgnet_misalignment_adapter.pth"
    torch.save(
        {
            "adapter_state_dict": adapter_state,
            "trainable_prefixes": TRAINABLE_PREFIXES,
            "base_checkpoint_name": args.checkpoint.name,
            "scale": args.scale,
            "seed": args.seed,
            "frozen_clean_teacher": args.frozen_clean_teacher,
            "clean_reconstruction_weight": args.clean_reconstruction_weight,
            "flat_reconstruction_weight": args.flat_reconstruction_weight,
            "flat_gradient_threshold": args.flat_gradient_threshold,
        },
        checkpoint_path,
    )
    restored_checkpoint = torch.load(checkpoint_path, map_location="cpu")
    restore_matches = all(
        torch.equal(adapter_state[name], restored_checkpoint["adapter_state_dict"][name])
        for name in adapter_state
    )
    summary = {
        "status": "completed",
        "task": "sgnet_misalignment_consistency_adapter",
        "dataset": "NYU_v2_train",
        "dataset_samples": len(dataset),
        "selected_train_samples": sample_count,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "max_train_batches": args.max_train_batches,
        "learning_rate": args.learning_rate,
        "max_shift": args.max_shift,
        "consistency_weight": args.consistency_weight,
        "clean_reconstruction_weight": args.clean_reconstruction_weight,
        "flat_reconstruction_weight": args.flat_reconstruction_weight,
        "flat_gradient_threshold": args.flat_gradient_threshold,
        "frozen_clean_teacher": args.frozen_clean_teacher,
        "trainable_parameter_count": sum(parameter.numel() for parameter in trainable_parameters),
        "frozen_parameter_count": sum(
            parameter.numel() for parameter in model.parameters() if not parameter.requires_grad
        ),
        "history": history,
        "last_gradient_norm": last_gradient_norm,
        "peak_cuda_memory_mb": float(torch.cuda.max_memory_allocated(device) / 1024**2)
        if device.type == "cuda"
        else None,
        "elapsed_seconds": time.time() - start_time,
        "checkpoint_restore_matches": restore_matches,
        "checkpoint_file": checkpoint_path.name,
        "adapter_tensor_count": len(adapter_state),
    }
    with (args.output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
