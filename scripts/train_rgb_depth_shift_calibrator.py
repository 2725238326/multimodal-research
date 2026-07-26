import argparse
import json
import random
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as functional
from torch.utils.data import DataLoader, Dataset, Subset

from evaluate_sgnet_blind_alignment_rgbdd_x16 import (
    ShiftCalibrator,
    correlation_features,
    shift_tensor_edge,
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--scale", type=int, default=16)
    parser.add_argument("--max-shift", type=int, default=4)
    parser.add_argument("--smoothing-kernel", type=int, default=9)
    parser.add_argument("--crop-size", type=int, default=256)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--validation-count", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20260722)
    parser.add_argument("--max-train-batches", type=int)
    parser.add_argument("--max-validation-batches", type=int)
    return parser.parse_args()


class NYUPairs(Dataset):
    def __init__(self, data_root, crop_size):
        self.rgb = np.load(data_root / "train_images_split.npy", mmap_mode="r")
        self.depth = np.load(data_root / "train_depth_split.npy", mmap_mode="r")
        if len(self.rgb) != len(self.depth):
            raise RuntimeError("RGB/depth sample counts differ")
        self.crop_size = crop_size

    def __len__(self):
        return len(self.rgb)

    def __getitem__(self, index):
        rgb = np.array(self.rgb[index], dtype=np.float32, copy=True) / 255.0
        depth = np.array(self.depth[index], dtype=np.float32, copy=True)
        depth_min = float(depth.min())
        depth_range = max(float(depth.max()) - depth_min, 1e-6)
        depth = (depth - depth_min) / depth_range
        height, width = depth.shape
        top = (height - self.crop_size) // 2
        left = (width - self.crop_size) // 2
        rgb = rgb[top : top + self.crop_size, left : left + self.crop_size]
        depth = depth[top : top + self.crop_size, left : left + self.crop_size]
        rgb = torch.from_numpy(np.ascontiguousarray(rgb.transpose(2, 0, 1)))
        depth = torch.from_numpy(np.ascontiguousarray(depth[None]))
        return rgb, depth


def apply_individual_shifts(rgb, shifts):
    return torch.cat(
        [shift_tensor_edge(image.unsqueeze(0), int(shift)) for image, shift in zip(rgb, shifts)],
        dim=0,
    )


def prepare_features(rgb, depth, shifts, args):
    shifted_rgb = apply_individual_shifts(rgb, shifts)
    low_resolution = functional.interpolate(
        depth,
        scale_factor=1 / args.scale,
        mode="bicubic",
        align_corners=False,
    )
    return correlation_features(
        shifted_rgb,
        low_resolution,
        args.max_shift,
        args.smoothing_kernel,
    )


def run_validation(model, loader, args, device):
    model.eval()
    correct = 0
    total = 0
    with torch.inference_mode():
        for batch_index, (rgb, depth) in enumerate(loader):
            if args.max_validation_batches is not None and batch_index >= args.max_validation_batches:
                break
            rgb = rgb.to(device)
            depth = depth.to(device)
            shifts = torch.arange(total, total + len(rgb), device=device)
            shifts = shifts.remainder(2 * args.max_shift + 1) - args.max_shift
            features = prepare_features(rgb, depth, shifts, args)
            targets = -shifts + args.max_shift
            predictions = model(features).argmax(1)
            correct += int((predictions == targets).sum().item())
            total += len(rgb)
    return correct / max(total, 1), total


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

    dataset = NYUPairs(args.data_root, args.crop_size)
    validation_count = min(args.validation_count, len(dataset) // 5)
    train_set = Subset(dataset, range(0, len(dataset) - validation_count))
    validation_set = Subset(dataset, range(len(dataset) - validation_count, len(dataset)))
    train_loader = DataLoader(train_set, batch_size=args.batch_size, shuffle=True, num_workers=0)
    validation_loader = DataLoader(validation_set, batch_size=args.batch_size, shuffle=False, num_workers=0)

    model = ShiftCalibrator(args.max_shift).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)
    history = []
    start_time = time.time()
    last_gradient_norm = None
    for epoch in range(args.epochs):
        model.train()
        loss_sum = 0.0
        correct = 0
        total = 0
        for batch_index, (rgb, depth) in enumerate(train_loader):
            if args.max_train_batches is not None and batch_index >= args.max_train_batches:
                break
            rgb = rgb.to(device)
            depth = depth.to(device)
            shifts = torch.randint(
                -args.max_shift,
                args.max_shift + 1,
                (len(rgb),),
                device=device,
            )
            features = prepare_features(rgb, depth, shifts, args)
            targets = -shifts + args.max_shift
            optimizer.zero_grad(set_to_none=True)
            logits = model(features)
            loss = functional.cross_entropy(logits, targets)
            loss.backward()
            squared_norm = sum(
                parameter.grad.detach().square().sum()
                for parameter in model.parameters()
                if parameter.grad is not None
            )
            last_gradient_norm = float(torch.sqrt(squared_norm).item())
            optimizer.step()
            loss_sum += float(loss.item()) * len(rgb)
            correct += int((logits.argmax(1) == targets).sum().item())
            total += len(rgb)
        validation_accuracy, validation_samples = run_validation(
            model,
            validation_loader,
            args,
            device,
        )
        history.append(
            {
                "epoch": epoch + 1,
                "train_samples": total,
                "train_loss": loss_sum / max(total, 1),
                "train_accuracy": correct / max(total, 1),
                "validation_samples": validation_samples,
                "validation_accuracy": validation_accuracy,
            }
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = args.output_dir / "shift_calibrator.pth"
    checkpoint = {
        "model_state_dict": model.state_dict(),
        "max_shift": args.max_shift,
        "smoothing_kernel": args.smoothing_kernel,
        "scale": args.scale,
        "seed": args.seed,
    }
    torch.save(checkpoint, checkpoint_path)
    restored = ShiftCalibrator(args.max_shift).to(device)
    restored_checkpoint = torch.load(checkpoint_path, map_location=device)
    restored.load_state_dict(restored_checkpoint["model_state_dict"])
    restore_matches = all(
        torch.equal(first, second)
        for first, second in zip(model.state_dict().values(), restored.state_dict().values())
    )
    summary = {
        "status": "completed",
        "task": "rgb_depth_horizontal_shift_calibration",
        "dataset": "NYU_v2_train",
        "dataset_samples": len(dataset),
        "train_split_samples": len(train_set),
        "validation_split_samples": len(validation_set),
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "max_train_batches": args.max_train_batches,
        "max_validation_batches": args.max_validation_batches,
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
