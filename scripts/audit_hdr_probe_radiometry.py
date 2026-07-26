"""Training-free radiometry audit for one Multi-Illumination HDR scene.

This script answers the feasibility questions that gate the calibrated
HDR + light-probe candidate, without training anything and without touching the
closed LDR response experiments:

1. Are the released linear EXR scene images and light probes readable, and how
   much signal sits above the LDR white point that the JPEG route clipped away?
2. Do the scene images and the gray/chrome probes share a radiometric scale, so
   that dividing scene radiance by measured probe radiance is definable at all?
3. Does probe normalization actually shrink the across-illumination spread of a
   region while preserving between-region separation?

Question 3 is the oracle form of the mechanism claim. It uses only the official
material mask, so it needs no classifier, no labels beyond the mask indices and
no fitted parameters.

Example:
    OPENCV_IO_ENABLE_OPENEXR=1 python scripts/audit_hdr_probe_radiometry.py \
        --scene-dir transfer_staging/hdr_probe_audit_v0/extracted/state_smallbathroom3 \
        --output results/local/hdr_probe_radiometry.json
"""

import argparse
import json
import os
from pathlib import Path

import numpy as np
from PIL import Image

# OpenCV refuses to decode EXR unless this is set before the module is imported.
os.environ.setdefault("OPENCV_IO_ENABLE_OPENEXR", "1")

import cv2  # noqa: E402  (import must follow the OpenEXR opt-in)

NUM_DIRECTIONS = 25
EPSILON = 1e-4


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene-dir", type=Path, required=True)
    parser.add_argument("--jpg-scene-dir", type=Path, default=None, help="matching released JPEG scene directory")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mip", type=int, default=2)
    parser.add_argument("--probe-size", type=int, default=256)
    parser.add_argument("--disc-radius-fraction", type=float, default=0.42)
    parser.add_argument("--min-region-pixels", type=int, default=4096)
    parser.add_argument("--max-regions", type=int, default=24)
    parser.add_argument("--ldr-white-point", type=float, default=1.0)
    return parser.parse_args()


def read_exr(path):
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise RuntimeError(f"failed to decode EXR: {path}")
    if image.ndim != 3 or image.shape[2] != 3:
        raise RuntimeError(f"unexpected EXR shape {image.shape} for {path}")
    # OpenCV returns BGR; the SDK and the material masks are RGB.
    return image[:, :, ::-1].astype(np.float64)


def disc_mask(size, radius_fraction):
    grid = np.arange(size) - (size - 1) / 2.0
    yy, xx = np.meshgrid(grid, grid, indexing="ij")
    return (xx**2 + yy**2) <= (radius_fraction * size) ** 2


def probe_summary(image, mask):
    pixels = image[mask]
    return {
        "mean_rgb": pixels.mean(axis=0).tolist(),
        "median_rgb": np.median(pixels, axis=0).tolist(),
        "mean_luminance": float(pixels.mean()),
        "max_luminance": float(pixels.max()),
    }


def ldr_clipping(jpg_path, linear):
    """Measure released-JPEG saturation and locate it on the linear EXR scale.

    The EXR white point is not documented, so it is measured: pixels sitting on
    the last unclipped JPEG code give the linear value at which the 8-bit
    encoding runs out of range.
    """
    jpeg = np.array(Image.open(jpg_path)).astype(np.int16)
    if jpeg.shape != linear.shape:
        raise RuntimeError(f"JPEG shape {jpeg.shape} and EXR shape {linear.shape} disagree")

    peak = jpeg.max(axis=2)
    edge = (peak >= 253) & (peak <= 254)
    linear_peak = linear.max(axis=2)
    clip_value = float(np.median(linear_peak[edge])) if int(edge.sum()) >= 50 else None

    record = {
        "saturated_any_channel_fraction": float((jpeg >= 255).any(axis=2).mean()),
        "saturated_all_channel_fraction": float((jpeg >= 255).all(axis=2).mean()),
        "linear_value_at_jpeg_clip": clip_value,
        "edge_pixel_count": int(edge.sum()),
    }
    if clip_value:
        record["linear_above_clip_fraction"] = float((linear_peak > clip_value).mean())
        record["linear_max_over_clip"] = float(linear_peak.max() / clip_value)
    return record


def load_regions(mask_path, min_region_pixels, max_regions):
    mask_image = Image.open(mask_path)
    if mask_image.mode != "P":
        raise RuntimeError(f"expected indexed PNG material mask, got mode {mask_image.mode}")
    indices = np.array(mask_image)

    regions = []
    for class_id in sorted(int(v) for v in np.unique(indices)):
        if class_id == 0:
            continue
        count, labels = cv2.connectedComponents((indices == class_id).astype(np.uint8), connectivity=8)
        for label in range(1, count):
            component = labels == label
            size = int(component.sum())
            if size < min_region_pixels:
                continue
            regions.append({"class_id": class_id, "pixels": size, "mask": component})

    regions.sort(key=lambda region: -region["pixels"])
    return regions[:max_regions], indices.shape


def descriptor_statistics(descriptors):
    """Return within-region, between-region and ratio statistics.

    ``descriptors`` has shape (num_regions, num_directions, 3) in log space.
    """
    within = descriptors.var(axis=1, ddof=1).mean(axis=0)
    region_means = descriptors.mean(axis=1)
    between = region_means.var(axis=0, ddof=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(within > 0, between / within, np.nan)
    return {
        "within_region_variance_rgb": within.tolist(),
        "between_region_variance_rgb": between.tolist(),
        "between_over_within_rgb": ratio.tolist(),
        "within_region_variance_mean": float(within.mean()),
        "between_region_variance_mean": float(between.mean()),
        "between_over_within_mean": float(np.nanmean(ratio)),
    }


def main():
    args = parse_args()
    scene_dir = args.scene_dir
    scene_name = scene_dir.name

    probe_disc = disc_mask(args.probe_size, args.disc_radius_fraction)
    regions, mask_shape = load_regions(
        scene_dir / f"materials_mip{args.mip}.png",
        args.min_region_pixels,
        args.max_regions,
    )
    if not regions:
        raise RuntimeError("no material region met the minimum size")

    directions = []
    region_radiance = np.zeros((len(regions), NUM_DIRECTIONS, 3), dtype=np.float64)
    gray_rgb = np.zeros((NUM_DIRECTIONS, 3), dtype=np.float64)

    for direction in range(NUM_DIRECTIONS):
        scene = read_exr(scene_dir / f"dir_{direction}_mip{args.mip}.exr")
        if scene.shape[:2] != mask_shape:
            raise RuntimeError(f"scene {scene.shape[:2]} and mask {mask_shape} disagree")
        gray = read_exr(scene_dir / "probes" / f"dir_{direction}_gray{args.probe_size}.exr")
        chrome = read_exr(scene_dir / "probes" / f"dir_{direction}_chrome{args.probe_size}.exr")

        gray_stats = probe_summary(gray, probe_disc)
        chrome_stats = probe_summary(chrome, probe_disc)
        gray_rgb[direction] = np.asarray(gray_stats["mean_rgb"])

        clipping = None
        if args.jpg_scene_dir is not None:
            clipping = ldr_clipping(args.jpg_scene_dir / f"dir_{direction}_mip{args.mip}.jpg", scene)

        directions.append(
            {
                "direction": direction,
                "ldr_clipping": clipping,
                "scene_mean": float(scene.mean()),
                "scene_median": float(np.median(scene)),
                "scene_p999": float(np.percentile(scene, 99.9)),
                "scene_max": float(scene.max()),
                "above_ldr_white_fraction": float((scene > args.ldr_white_point).mean()),
                "negative_fraction": float((scene < 0).mean()),
                "gray_probe": gray_stats,
                "chrome_probe": chrome_stats,
            }
        )

        for index, region in enumerate(regions):
            region_radiance[index, direction] = np.median(scene[region["mask"]], axis=0)

    scene_means = np.array([d["scene_mean"] for d in directions])
    gray_means = np.array([d["gray_probe"]["mean_luminance"] for d in directions])
    chrome_means = np.array([d["chrome_probe"]["mean_luminance"] for d in directions])

    raw_log = np.log10(np.maximum(region_radiance, EPSILON))
    normalized_log = raw_log - np.log10(np.maximum(gray_rgb, EPSILON))[None, :, :]

    summary = {
        "scene": scene_name,
        "mip": args.mip,
        "num_directions": NUM_DIRECTIONS,
        "num_regions": len(regions),
        "region_classes": sorted({region["class_id"] for region in regions}),
        "region_pixels": [region["pixels"] for region in regions],
        "hdr_headroom": {
            "ldr_white_point": args.ldr_white_point,
            "above_white_fraction_mean": float(np.mean([d["above_ldr_white_fraction"] for d in directions])),
            "above_white_fraction_max": float(np.max([d["above_ldr_white_fraction"] for d in directions])),
            "scene_max_over_white": float(np.max([d["scene_max"] for d in directions]) / args.ldr_white_point),
            "negative_fraction_max": float(np.max([d["negative_fraction"] for d in directions])),
        },
        "radiometric_coupling": {
            "pearson_scene_vs_gray_probe": float(np.corrcoef(scene_means, gray_means)[0, 1]),
            "pearson_scene_vs_chrome_probe": float(np.corrcoef(scene_means, chrome_means)[0, 1]),
            "pearson_log_scene_vs_log_gray_probe": float(
                np.corrcoef(np.log10(np.maximum(scene_means, EPSILON)), np.log10(np.maximum(gray_means, EPSILON)))[0, 1]
            ),
            "scene_mean_dynamic_range": float(scene_means.max() / max(scene_means.min(), EPSILON)),
            "gray_probe_dynamic_range": float(gray_means.max() / max(gray_means.min(), EPSILON)),
        },
        "discriminability": {
            "raw_linear_log": descriptor_statistics(raw_log),
            "gray_probe_normalized_log": descriptor_statistics(normalized_log),
        },
        "directions": directions,
    }

    if args.jpg_scene_dir is not None:
        clip_records = [d["ldr_clipping"] for d in directions]
        measured = [r["linear_value_at_jpeg_clip"] for r in clip_records if r["linear_value_at_jpeg_clip"]]
        summary["ldr_clipping"] = {
            "saturated_any_channel_fraction_mean": float(
                np.mean([r["saturated_any_channel_fraction"] for r in clip_records])
            ),
            "saturated_any_channel_fraction_max": float(
                np.max([r["saturated_any_channel_fraction"] for r in clip_records])
            ),
            "saturated_all_channel_fraction_mean": float(
                np.mean([r["saturated_all_channel_fraction"] for r in clip_records])
            ),
            "linear_value_at_jpeg_clip_mean": float(np.mean(measured)) if measured else None,
            "linear_max_over_clip_mean": float(
                np.mean([r["linear_max_over_clip"] for r in clip_records if "linear_max_over_clip" in r])
            )
            if measured
            else None,
        }

    ratio_raw = summary["discriminability"]["raw_linear_log"]["between_over_within_mean"]
    ratio_norm = summary["discriminability"]["gray_probe_normalized_log"]["between_over_within_mean"]
    summary["discriminability"]["normalized_over_raw_ratio"] = float(ratio_norm / ratio_raw) if ratio_raw else None

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({k: v for k, v in summary.items() if k != "directions"}, indent=2))


if __name__ == "__main__":
    main()
