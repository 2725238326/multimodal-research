import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("--siglip-features", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_repo_path(raw_path, workspace_root):
    path = Path(raw_path)
    if path.is_absolute() and path.exists():
        return path
    parts = path.parts
    if "multimodal-research" in parts:
        marker = parts.index("multimodal-research")
        return (workspace_root / Path(*parts[marker + 1 :])).resolve()
    return (workspace_root / path).resolve()


def photometry_names(config):
    names = [
        "usable_fraction",
        "clip_all_fraction",
        "clip_any_fraction",
        "dark_fraction",
    ]
    names.extend(f"luminance_q{int(q * 100):02d}" for q in config["luminance_quantiles"])
    names.extend(
        [
            "chromaticity_r_mean",
            "chromaticity_r_std",
            "chromaticity_g_mean",
            "chromaticity_g_std",
            "saturation_mean",
            "saturation_q90",
            "highlight_fraction",
            "achromatic_highlight_fraction",
        ]
    )
    names.extend(f"gradient_q{int(q * 100):02d}" for q in config["gradient_quantiles"])
    names.append("laplacian_abs_mean")
    return names


def sample_photometry(image, config):
    image = np.asarray(image, dtype=np.float64)
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("image must be HxWx3 RGB")
    if image.max() > 1.0:
        image = image / 255.0
    white = float(config["near_white_threshold"])
    dark_threshold = float(config["near_dark_threshold"])
    clip_all = np.all(image >= white, axis=2)
    clip_any = np.any(image >= white, axis=2)
    dark = np.all(image <= dark_threshold, axis=2)
    usable = ~(clip_all | dark)
    usable_fraction = float(usable.mean())
    if not usable.any():
        usable = np.ones(image.shape[:2], dtype=bool)
    luminance = (
        0.2126 * image[:, :, 0]
        + 0.7152 * image[:, :, 1]
        + 0.0722 * image[:, :, 2]
    )
    denominator = image.sum(axis=2)
    chromaticity_r = image[:, :, 0] / np.clip(denominator, 1e-12, None)
    chromaticity_g = image[:, :, 1] / np.clip(denominator, 1e-12, None)
    maximum = image.max(axis=2)
    saturation = (maximum - image.min(axis=2)) / np.clip(maximum, 1e-12, None)
    highlight = luminance >= float(config["absolute_highlight_threshold"])
    achromatic_highlight = highlight & (
        saturation <= float(config["low_saturation_threshold"])
    )
    horizontal = np.diff(luminance, axis=1)
    vertical = np.diff(luminance, axis=0)
    gradient = np.sqrt(horizontal[:-1, :] ** 2 + vertical[:, :-1] ** 2)
    laplacian = (
        -4.0 * luminance[1:-1, 1:-1]
        + luminance[:-2, 1:-1]
        + luminance[2:, 1:-1]
        + luminance[1:-1, :-2]
        + luminance[1:-1, 2:]
    )
    values = [
        usable_fraction,
        float(clip_all.mean()),
        float(clip_any.mean()),
        float(dark.mean()),
    ]
    values.extend(
        float(value)
        for value in np.quantile(luminance[usable], config["luminance_quantiles"])
    )
    values.extend(
        [
            float(chromaticity_r[usable].mean()),
            float(chromaticity_r[usable].std()),
            float(chromaticity_g[usable].mean()),
            float(chromaticity_g[usable].std()),
            float(saturation[usable].mean()),
            float(np.quantile(saturation[usable], 0.9)),
            float(highlight.mean()),
            float(achromatic_highlight.mean()),
        ]
    )
    values.extend(
        float(value)
        for value in np.quantile(gradient, config["gradient_quantiles"])
    )
    values.append(float(np.abs(laplacian).mean()))
    output = np.asarray(values, dtype=np.float32)
    if not np.isfinite(output).all():
        raise ValueError("non-finite photometric descriptor")
    return output


def aggregate_trajectory(values, selected, reliable_count, fallback):
    values = np.asarray(values, dtype=np.float32)
    selected = np.asarray(selected, dtype=bool)
    chosen = values[selected]
    blocks = [
        chosen.mean(axis=0),
        chosen.std(axis=0),
        chosen.min(axis=0),
        chosen.max(axis=0),
        np.ptp(chosen, axis=0),
    ]
    metadata = np.asarray(
        [reliable_count / len(values), chosen.shape[0] / len(values), float(fallback)],
        dtype=np.float32,
    )
    return np.concatenate([*blocks, metadata])


def trajectory_names(sample_names):
    output = []
    for statistic in ("mean", "std", "min", "max", "range"):
        output.extend(f"{statistic}_{name}" for name in sample_names)
    output.extend(["reliable_light_fraction", "used_light_fraction", "fallback_used"])
    return output


def read_manifest(path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main():
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    photometry = config["photometry"]
    rows = read_manifest(args.manifest)
    if not rows:
        raise ValueError("manifest is empty")
    required = {"sample_id", "region_id", "scene", "material_label", "rgb_crop_path", "light_dir"}
    missing = sorted(required - rows[0].keys())
    if missing:
        raise ValueError(f"manifest missing {missing}")
    paths = [resolve_repo_path(row["rgb_crop_path"], args.workspace_root) for row in rows]
    missing_paths = [str(path) for path in paths if not path.is_file()]
    summary = {
        "experiment_id": config["experiment_id"],
        "status": "Smoke test" if args.dry_run else "Completed",
        "dry_run": bool(args.dry_run),
        "manifest_sha256": sha256(args.manifest),
        "siglip_feature_cache_sha256": sha256(args.siglip_features),
        "sample_count": len(rows),
        "region_count": len({row["region_id"] for row in rows}),
        "scene_count": len({row["scene"] for row in rows}),
        "missing_rgb_crops": len(missing_paths),
    }
    if missing_paths:
        raise FileNotFoundError(f"missing RGB crops, first={missing_paths[0]}")
    if args.dry_run:
        args.summary_output.parent.mkdir(parents=True, exist_ok=True)
        args.summary_output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return

    with np.load(args.siglip_features, allow_pickle=False) as cache:
        feature_sample_ids = cache["sample_ids"].astype(str)
        rgb_features = cache["rgb_features"].astype(np.float32)
    feature_lookup = {sample_id: index for index, sample_id in enumerate(feature_sample_ids)}
    manifest_ids = [str(row["sample_id"]) for row in rows]
    absent = sorted(set(manifest_ids) - feature_lookup.keys())
    if absent:
        raise ValueError(f"SigLIP cache missing sample {absent[0]}")

    sample_names = photometry_names(photometry)
    sample_values = []
    for path in paths:
        image = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0
        sample_values.append(sample_photometry(image, photometry))
    sample_values = np.stack(sample_values)
    name_to_index = {name: index for index, name in enumerate(sample_names)}
    exposure_names = [
        name
        for name in sample_names
        if name.startswith(("usable_", "clip_", "dark_", "luminance_"))
        or name == "highlight_fraction"
    ]
    exposure_indices = [name_to_index[name] for name in exposure_names]

    by_region = defaultdict(list)
    for index, row in enumerate(rows):
        by_region[str(row["region_id"])].append(index)
    region_ids = []
    scenes = []
    labels = []
    siglip_regions = []
    censored_regions = []
    uncensored_regions = []
    exposure_regions = []
    reliable_counts = []
    fallback_counts = 0
    clip_index = name_to_index["clip_all_fraction"]
    reliability_limit = float(photometry["reliable_all_channel_clip_fraction_max"])
    minimum_reliable = int(photometry["minimum_reliable_lights"])
    for region_id in sorted(by_region):
        indices = np.asarray(by_region[region_id], dtype=np.int64)
        region_scenes = {str(rows[index]["scene"]) for index in indices}
        region_labels = {str(rows[index]["material_label"]) for index in indices}
        if len(region_scenes) != 1 or len(region_labels) != 1:
            raise ValueError(f"region {region_id} has inconsistent scene or label")
        values = sample_values[indices]
        reliable = values[:, clip_index] <= reliability_limit
        reliable_count = int(reliable.sum())
        fallback = reliable_count < minimum_reliable
        if fallback:
            order = np.argsort(values[:, clip_index], kind="stable")
            reliable = np.zeros(len(indices), dtype=bool)
            reliable[order[:minimum_reliable]] = True
            fallback_counts += 1
        all_lights = np.ones(len(indices), dtype=bool)
        siglip_indices = [feature_lookup[manifest_ids[index]] for index in indices]
        region_ids.append(region_id)
        scenes.append(next(iter(region_scenes)))
        labels.append(next(iter(region_labels)))
        siglip_regions.append(rgb_features[siglip_indices].mean(axis=0))
        censored_regions.append(
            aggregate_trajectory(values, reliable, reliable_count, fallback)
        )
        uncensored_regions.append(
            aggregate_trajectory(values, all_lights, reliable_count, False)
        )
        exposure_regions.append(
            aggregate_trajectory(
                values[:, exposure_indices], all_lights, reliable_count, False
            )
        )
        reliable_counts.append(reliable_count)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.output,
        region_ids=np.asarray(region_ids),
        scenes=np.asarray(scenes),
        labels=np.asarray(labels),
        siglip_region_features=np.stack(siglip_regions).astype(np.float32),
        censored_photometric_features=np.stack(censored_regions).astype(np.float32),
        uncensored_photometric_features=np.stack(uncensored_regions).astype(np.float32),
        exposure_only_features=np.stack(exposure_regions).astype(np.float32),
        reliable_light_counts=np.asarray(reliable_counts, dtype=np.int16),
        sample_photometry_names=np.asarray(sample_names),
        censored_trajectory_names=np.asarray(trajectory_names(sample_names)),
        exposure_trajectory_names=np.asarray(trajectory_names(exposure_names)),
    )
    summary.update(
        {
            "descriptor_cache_sha256": sha256(args.output),
            "sample_descriptor_dimension": len(sample_names),
            "censored_trajectory_dimension": int(np.stack(censored_regions).shape[1]),
            "exposure_trajectory_dimension": int(np.stack(exposure_regions).shape[1]),
            "reliable_light_count_distribution": dict(
                sorted(Counter(reliable_counts).items())
            ),
            "fallback_region_count": fallback_counts,
        }
    )
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
