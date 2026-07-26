import argparse
import hashlib
import io
import json
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

try:
    from scripts.build_material_constancy_pilot import (
        MATERIALS,
        component_candidates,
        select_balanced_regions,
        select_diverse_lights,
    )
except ModuleNotFoundError:
    from build_material_constancy_pilot import (
        MATERIALS,
        component_candidates,
        select_balanced_regions,
        select_diverse_lights,
    )


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def archive_scenes(handle, prefix):
    suffix = "/materials_mip2.png"
    scenes = sorted(
        name[: -len(suffix)]
        for name in handle.namelist()
        if name.endswith(suffix)
    )
    return [scene for scene in scenes if scene.startswith(prefix)]


def downsample_image(raw, factor, resampling):
    image = Image.open(io.BytesIO(raw))
    size = (image.width // factor, image.height // factor)
    return image.resize(size, resampling)


def build_regions(handle, scenes, crop_config):
    factor = int(crop_config["downsample_factor"])
    candidate_config = {
        "crop_size": int(crop_config["crop_size"]),
        "min_component_area": int(crop_config["min_component_area"]),
        "min_crop_purity": float(crop_config["min_crop_purity"]),
        "target_material_ids": [int(value) for value in crop_config["target_material_ids"]],
        "max_regions": int(crop_config["max_regions"]),
        "max_regions_per_scene_class": int(crop_config["max_regions_per_scene_class"]),
    }
    candidates = {}
    mask_shapes = {}
    for scene in scenes:
        mask_image = downsample_image(
            handle.read(f"{scene}/materials_mip2.png"),
            factor,
            Image.Resampling.NEAREST,
        )
        if mask_image.mode != "P":
            raise ValueError(f"expected indexed material mask for {scene}")
        mask = np.asarray(mask_image, dtype=np.uint8)
        mask_shapes[scene] = mask.shape
        rows = component_candidates(mask, candidate_config, scene)
        if rows:
            candidates[scene] = rows
    regions = select_balanced_regions(candidates, sorted(candidates), candidate_config)
    return regions, candidates, mask_shapes


def main():
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    crop_config = config["crop"]
    actual_hash = sha256(args.archive)
    if actual_hash != config["source"]["archive_sha256"]:
        raise ValueError(f"archive SHA-256 mismatch: {actual_hash}")
    with zipfile.ZipFile(args.archive) as handle:
        bad_entry = handle.testzip()
        if bad_entry:
            raise ValueError(f"archive CRC failure: {bad_entry}")
        scenes = archive_scenes(handle, crop_config["test_scene_prefix"])
        regions, candidates, mask_shapes = build_regions(
            handle, scenes, crop_config
        )
        labels_used = sorted({region["material_label"] for region in regions})
        summary = {
            "experiment_id": config["experiment_id"],
            "status": "Smoke test" if args.dry_run else "Completed",
            "dry_run": bool(args.dry_run),
            "source_archive_sha256": actual_hash,
            "source_license": config["source"]["license"],
            "sdk_revision": config["source"]["sdk_revision"],
            "archive_scene_count": len(scenes),
            "usable_scene_count": len(candidates),
            "selected_scene_count": len({region["scene"] for region in regions}),
            "candidate_region_count": sum(len(rows) for rows in candidates.values()),
            "selected_region_count": len(regions),
            "regions_per_class": dict(Counter(region["material_label"] for region in regions)),
            "candidate_labels": labels_used,
            "mask_shapes": [list(shape) for shape in sorted(set(mask_shapes.values()))],
        }
        if len(scenes) != 30:
            raise ValueError(f"expected 30 official test scenes, found {len(scenes)}")
        if len(regions) < int(crop_config["min_regions"]):
            raise ValueError(f"only {len(regions)} regions passed the fixed protocol")
        if len(labels_used) < 8:
            raise ValueError(f"only {len(labels_used)} material classes passed the fixed protocol")
        if args.dry_run:
            print(json.dumps(summary, indent=2))
            return

        experiment_id = config["experiment_id"]
        crop_root = args.output_root / "data" / "processed" / experiment_id / "crops"
        manifest_root = args.output_root / "experiments" / "manifests" / experiment_id
        crop_root.mkdir(parents=True, exist_ok=True)
        manifest_root.mkdir(parents=True, exist_ok=True)
        factor = int(crop_config["downsample_factor"])
        scene_images = {}
        for scene in sorted({region["scene"] for region in regions}):
            images = []
            for direction in range(25):
                image = downsample_image(
                    handle.read(f"{scene}/dir_{direction}_mip2.jpg"),
                    factor,
                    Image.Resampling.LANCZOS,
                ).convert("RGB")
                if image.size[::-1] != mask_shapes[scene]:
                    raise ValueError(f"image/mask shape mismatch for {scene}")
                images.append(np.asarray(image, dtype=np.uint8))
            scene_images[scene] = images

        records = []
        for region_index, region in enumerate(regions):
            scene = region["scene"]
            lights = select_diverse_lights(
                scene_images[scene],
                region["bbox"],
                int(crop_config["lights_per_region"]),
            )
            x0, y0, x1, y1 = region["bbox"]
            region_id = f"{scene}_external_r{region_index:03d}_{region['material_id']}"
            for light in lights:
                crop = Image.fromarray(scene_images[scene][light][y0:y1, x0:x1])
                relative_path = (
                    Path("data")
                    / "processed"
                    / experiment_id
                    / "crops"
                    / scene
                    / f"{region_id}_d{light:02d}.jpg"
                )
                output_path = args.output_root / relative_path
                output_path.parent.mkdir(parents=True, exist_ok=True)
                crop.save(output_path, quality=95)
                pixels = np.asarray(crop, dtype=np.float32) / 255.0
                records.append(
                    {
                        "sample_id": f"{region_id}_d{light:02d}",
                        "region_id": region_id,
                        "scene": scene,
                        "light_dir": light,
                        "material_id": region["material_id"],
                        "material_label": region["material_label"],
                        "candidate_labels": labels_used,
                        "bbox": region["bbox"],
                        "component_area": region["component_area"],
                        "crop_purity": round(region["crop_purity"], 6),
                        "rgb_crop_path": relative_path.as_posix(),
                        "crop_path": relative_path.as_posix(),
                        "mean_rgb": pixels.mean((0, 1)).round(6).tolist(),
                        "std_rgb": pixels.std((0, 1)).round(6).tolist(),
                    }
                )
        manifest_path = manifest_root / "material_external_confirmation_manifest.jsonl"
        with manifest_path.open("w", encoding="utf-8") as stream:
            for record in records:
                stream.write(json.dumps(record) + "\n")
        summary.update(
            {
                "sample_count": len(records),
                "manifest": manifest_path.relative_to(args.output_root).as_posix(),
                "manifest_sha256": sha256(manifest_path),
            }
        )
        summary_path = manifest_root / "build_summary.json"
        summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
