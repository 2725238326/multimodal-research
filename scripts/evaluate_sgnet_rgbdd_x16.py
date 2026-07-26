import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image


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
    parser.add_argument("--crop-border", type=int, default=6)
    parser.add_argument("--depth-edge-threshold", type=float, default=2.0)
    parser.add_argument("--rgb-edge-threshold", type=float, default=8.0)
    parser.add_argument("--max-samples", type=int)
    return parser.parse_args()


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def shift_with_edge_padding(image, shift_x, shift_y):
    if shift_x == 0 and shift_y == 0:
        return image
    height, width = image.shape[:2]
    pad_x = abs(shift_x)
    pad_y = abs(shift_y)
    padding = ((pad_y, pad_y), (pad_x, pad_x), (0, 0))
    padded = np.pad(image, padding, mode="edge")
    start_x = pad_x - shift_x
    start_y = pad_y - shift_y
    return padded[start_y : start_y + height, start_x : start_x + width]


def center_scale_with_edge_padding(image, scale):
    if scale <= 0:
        raise ValueError("rgb_scale must be positive")
    if scale == 1.0:
        return image
    height, width = image.shape[:2]
    resized_height = max(1, int(round(height * scale)))
    resized_width = max(1, int(round(width * scale)))
    resized = np.asarray(
        Image.fromarray(np.clip(image, 0, 255).astype(np.uint8)).resize(
            (resized_width, resized_height), Image.Resampling.BICUBIC
        ),
        dtype=np.float32,
    )
    if resized_height >= height and resized_width >= width:
        start_y = (resized_height - height) // 2
        start_x = (resized_width - width) // 2
        return resized[start_y : start_y + height, start_x : start_x + width]
    pad_top = max(0, (height - resized_height) // 2)
    pad_bottom = max(0, height - resized_height - pad_top)
    pad_left = max(0, (width - resized_width) // 2)
    pad_right = max(0, width - resized_width - pad_left)
    padded = np.pad(
        resized,
        ((pad_top, pad_bottom), (pad_left, pad_right), (0, 0)),
        mode="edge",
    )
    start_y = max(0, (padded.shape[0] - height) // 2)
    start_x = max(0, (padded.shape[1] - width) // 2)
    return padded[start_y : start_y + height, start_x : start_x + width]


def add_checkerboard_luminance_texture(image, amplitude, block_size):
    if amplitude < 0:
        raise ValueError("texture_amplitude must be non-negative")
    if block_size <= 0:
        raise ValueError("texture_block_size must be positive")
    if amplitude == 0:
        return image
    height, width = image.shape[:2]
    rows = np.arange(height)[:, None] // block_size
    columns = np.arange(width)[None, :] // block_size
    pattern = ((rows + columns) % 2).astype(np.float32) * 2.0 - 1.0
    return np.clip(image + amplitude * pattern[..., None], 0.0, 255.0)


def add_luminance_texture(
    image,
    amplitude,
    pattern="checkerboard",
    block_size=4,
    period=8.0,
    seed=20260723,
    sample_index=0,
):
    if amplitude < 0:
        raise ValueError("texture_amplitude must be non-negative")
    if amplitude == 0:
        return image
    if pattern == "checkerboard":
        return add_checkerboard_luminance_texture(image, amplitude, block_size)

    height, width = image.shape[:2]
    if pattern == "sinusoidal":
        if period <= 0:
            raise ValueError("texture_period must be positive")
        rows = np.arange(height, dtype=np.float32)[:, None]
        columns = np.arange(width, dtype=np.float32)[None, :]
        texture = np.sin(2.0 * np.pi * (rows + columns) / period)
    elif pattern == "noise":
        seed_sequence = np.random.SeedSequence([seed, sample_index])
        rng = np.random.default_rng(seed_sequence)
        texture = rng.standard_normal((height, width), dtype=np.float32)
    else:
        raise ValueError(f"Unsupported texture_pattern: {pattern}")
    return np.clip(image + amplitude * texture[..., None], 0.0, 255.0)


def perturb_rgb(
    image,
    shift_x=0,
    shift_y=0,
    rgb_scale=1.0,
    texture_amplitude=0.0,
    texture_block_size=4,
    texture_pattern="checkerboard",
    texture_period=8.0,
    texture_seed=20260723,
    sample_index=0,
):
    output = center_scale_with_edge_padding(image, rgb_scale)
    output = shift_with_edge_padding(output, shift_x, shift_y)
    return add_luminance_texture(
        output,
        texture_amplitude,
        pattern=texture_pattern,
        block_size=texture_block_size,
        period=texture_period,
        seed=texture_seed,
        sample_index=sample_index,
    )


def gradient_magnitude(image):
    grad_y, grad_x = np.gradient(image.astype(np.float32))
    return np.sqrt(grad_x * grad_x + grad_y * grad_y)


def dilate(mask):
    padded = np.pad(mask, ((1, 1), (1, 1)), mode="constant")
    output = np.zeros_like(mask, dtype=bool)
    for row_offset in range(3):
        for column_offset in range(3):
            output |= padded[
                row_offset : row_offset + mask.shape[0],
                column_offset : column_offset + mask.shape[1],
            ]
    return output


def load_pairs(data_root, scale):
    rgb_dir = data_root / "rgb"
    depth_dir = data_root / "depth"
    rgb_paths = {path.name: path for path in rgb_dir.iterdir() if path.is_file()}
    depth_paths = {path.name: path for path in depth_dir.iterdir() if path.is_file()}
    if rgb_paths.keys() != depth_paths.keys():
        missing_rgb = sorted(depth_paths.keys() - rgb_paths.keys())
        missing_depth = sorted(rgb_paths.keys() - depth_paths.keys())
        raise RuntimeError(
            f"Pair mismatch: missing_rgb={missing_rgb[:5]}, "
            f"missing_depth={missing_depth[:5]}"
        )
    for name in sorted(rgb_paths):
        rgb = np.asarray(Image.open(rgb_paths[name]).convert("RGB"), dtype=np.float32)
        depth = np.asarray(Image.open(depth_paths[name]), dtype=np.float32)
        height = depth.shape[0] - depth.shape[0] % scale
        width = depth.shape[1] - depth.shape[1] % scale
        yield name, rgb[:height, :width], depth[:height, :width]


def prepare_tensors(
    rgb,
    depth,
    scale,
    shift_x,
    shift_y,
    device,
    rgb_scale=1.0,
    texture_amplitude=0.0,
    texture_block_size=4,
    texture_pattern="checkerboard",
    texture_period=8.0,
    texture_seed=20260723,
    sample_index=0,
):
    perturbed_rgb = perturb_rgb(
        rgb,
        shift_x=shift_x,
        shift_y=shift_y,
        rgb_scale=rgb_scale,
        texture_amplitude=texture_amplitude,
        texture_block_size=texture_block_size,
        texture_pattern=texture_pattern,
        texture_period=texture_period,
        texture_seed=texture_seed,
        sample_index=sample_index,
    )
    rgb = np.ascontiguousarray(perturbed_rgb / 255.0)
    depth_normalized = np.ascontiguousarray(depth / 255.0)
    height, width = depth_normalized.shape
    low_resolution = np.array(
        Image.fromarray(depth_normalized).resize(
            (width // scale, height // scale), Image.Resampling.BICUBIC
        ),
        dtype=np.float32,
        copy=True,
    )
    guidance = torch.from_numpy(rgb.transpose(2, 0, 1)).unsqueeze(0).to(device)
    low_resolution = torch.from_numpy(low_resolution).unsqueeze(0).unsqueeze(0).to(device)
    return guidance.float(), low_resolution.float(), perturbed_rgb


def calculate_metrics(
    prediction,
    depth,
    rgb,
    crop_border,
    depth_edge_threshold,
    rgb_edge_threshold,
):
    prediction = np.clip(prediction, 0.0, 1.0) * 255.0
    target = depth.astype(np.float32)
    if crop_border:
        prediction = prediction[crop_border:-crop_border, crop_border:-crop_border]
        target = target[crop_border:-crop_border, crop_border:-crop_border]
        rgb = rgb[crop_border:-crop_border, crop_border:-crop_border]
    error = prediction - target
    squared_error = error * error
    target_edges = dilate(gradient_magnitude(target) > depth_edge_threshold)
    prediction_edges = gradient_magnitude(prediction) > depth_edge_threshold
    luminance = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    rgb_edges = gradient_magnitude(luminance) > rgb_edge_threshold
    false_edges = prediction_edges & rgb_edges & ~target_edges
    metrics = {
        "rmse": float(np.sqrt(np.mean(squared_error))),
        "mae": float(np.mean(np.abs(error))),
        "boundary_rmse": float(np.sqrt(np.mean(squared_error[target_edges])))
        if np.any(target_edges)
        else None,
        "flat_rmse": float(np.sqrt(np.mean(squared_error[~target_edges])))
        if np.any(~target_edges)
        else None,
        "false_edge_rate": float(false_edges.sum() / max(prediction_edges.sum(), 1)),
        "target_edge_pixels": int(target_edges.sum()),
        "prediction_edge_pixels": int(prediction_edges.sum()),
        "false_edge_pixels": int(false_edges.sum()),
    }
    return metrics


def aggregate(records):
    metric_names = ["rmse", "mae", "boundary_rmse", "flat_rmse", "false_edge_rate"]
    output = {}
    for name in metric_names:
        values = [record[name] for record in records if record[name] is not None]
        output[name] = {
            "mean": float(np.mean(values)),
            "std": float(np.std(values)),
            "median": float(np.median(values)),
        }
    return output


def main():
    args = parse_args()
    sys.path.insert(0, str(args.sgnet_dir.resolve()))
    from models.SGNet import SGNet

    if not args.checkpoint.is_file():
        raise FileNotFoundError(args.checkpoint)
    device = torch.device(args.device)
    model = SGNet(num_feats=args.num_feats, kernel_size=3, scale=args.scale)
    state_dict = torch.load(args.checkpoint, map_location=device)
    model.load_state_dict(state_dict)
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
            output = model((guidance, low_resolution))
            prediction = output[0] if isinstance(output, (tuple, list)) else output
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
        "dataset": "RGB-D-D/test2",
        "scale": args.scale,
        "sample_count": len(records),
        "checkpoint_sha256": sha256(args.checkpoint),
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
