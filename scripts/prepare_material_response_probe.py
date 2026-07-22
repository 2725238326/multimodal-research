#!/usr/bin/env python3
"""Prepare and validate the material-response probe smoke manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "sample_id",
    "region_id",
    "scene",
    "light_dir",
    "material_id",
    "material_label",
    "candidate_labels",
    "bbox",
    "crop_purity",
    "mean_rgb",
    "std_rgb",
    "rgb_crop_path",
    "albedo_crop_path",
}

PATH_KEYS = {
    "crop_path",
    "rgb_crop_path",
    "albedo_crop_path",
    "albedo_full_path",
    "rgb_full_path",
    "rgb_marked_path",
    "albedo_marked_path",
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_absolute_path(value: str) -> bool:
    normalized = value.replace("\\", "/")
    return normalized.startswith("/") or re.match(r"^[A-Za-z]:/", normalized) is not None


def normalize_repo_path(value: str, repo_name: str = "multimodal-research") -> str:
    normalized = value.replace("\\", "/")
    marker = f"/{repo_name}/"
    if marker in normalized:
        return normalized.split(marker, 1)[1]
    prefix = f"{repo_name}/"
    if normalized.startswith(prefix):
        return normalized[len(prefix) :]
    return normalized


def normalize_path_fields(row: dict[str, Any], repo_name: str = "multimodal-research") -> dict[str, Any]:
    output = dict(row)
    for key, value in list(output.items()):
        if key in PATH_KEYS and isinstance(value, str):
            output[key] = normalize_repo_path(value, repo_name=repo_name)
    return output


def light_feature(row: dict[str, Any]) -> list[float]:
    mean_rgb = [float(x) for x in row["mean_rgb"]]
    std_rgb = [float(x) for x in row["std_rgb"]]
    return mean_rgb + std_rgb


def select_diverse_lights(group: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    ordered = sorted(group, key=lambda row: (int(row["light_dir"]), row["sample_id"]))
    if len(ordered) <= count:
        return ordered

    luminance = [sum(float(channel) for channel in row["mean_rgb"]) / 3.0 for row in ordered]
    selected = list(dict.fromkeys([min(range(len(ordered)), key=luminance.__getitem__), max(range(len(ordered)), key=luminance.__getitem__)]))

    while len(selected) < count:
        best_index = None
        best_distance = -1.0
        for index, row in enumerate(ordered):
            if index in selected:
                continue
            feature = light_feature(row)
            nearest = min(
                math.dist(feature, light_feature(ordered[selected_index])) for selected_index in selected
            )
            if nearest > best_distance:
                best_index = index
                best_distance = nearest
        if best_index is None:
            break
        selected.append(best_index)

    return [ordered[index] for index in sorted(selected[:count])]


def grouped_by_region(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["region_id"])].append(row)
    return dict(grouped)


def select_regions(
    rows: list[dict[str, Any]], target_material_labels: list[str], max_regions: int, lights_per_region: int
) -> list[list[dict[str, Any]]]:
    grouped = grouped_by_region(rows)
    eligible = [
        group
        for group in grouped.values()
        if len({int(row["light_dir"]) for row in group}) >= lights_per_region
    ]
    by_material: dict[str, list[list[dict[str, Any]]]] = defaultdict(list)
    for group in eligible:
        label = str(group[0]["material_label"])
        by_material[label].append(group)
    for label in by_material:
        by_material[label].sort(key=lambda group: (str(group[0]["scene"]), str(group[0]["region_id"])))

    selected: list[list[dict[str, Any]]] = []
    used_regions: set[str] = set()
    for label in target_material_labels:
        for group in by_material.get(label, []):
            region_id = str(group[0]["region_id"])
            if region_id not in used_regions:
                selected.append(group)
                used_regions.add(region_id)
                break
        if len(selected) >= max_regions:
            return selected

    remaining = sorted(eligible, key=lambda group: (str(group[0]["material_label"]), str(group[0]["scene"]), str(group[0]["region_id"])))
    for group in remaining:
        region_id = str(group[0]["region_id"])
        if region_id in used_regions:
            continue
        selected.append(group)
        used_regions.add(region_id)
        if len(selected) >= max_regions:
            break
    return selected


def build_smoke_rows(
    rows: list[dict[str, Any]],
    target_material_labels: list[str],
    max_regions: int,
    lights_per_region: int,
    source_manifest: str,
) -> list[dict[str, Any]]:
    selected_groups = select_regions(rows, target_material_labels, max_regions, lights_per_region)
    output_rows: list[dict[str, Any]] = []
    for group in selected_groups:
        for row in select_diverse_lights(group, lights_per_region):
            normalized = normalize_path_fields(row)
            normalized["source_manifest"] = source_manifest
            normalized["path_mode"] = "repo_relative"
            output_rows.append(normalized)
    output_rows.sort(key=lambda row: (str(row["material_label"]), str(row["scene"]), str(row["region_id"]), int(row["light_dir"])))
    return output_rows


def validate_rows(
    rows: list[dict[str, Any]],
    lights_per_region: int,
    workspace: Path | None = None,
    required_path_keys: set[str] | None = None,
) -> dict[str, Any]:
    if not rows:
        raise ValueError("Manifest is empty")

    sample_ids = [str(row.get("sample_id")) for row in rows]
    if len(set(sample_ids)) != len(sample_ids):
        raise ValueError("Duplicate sample_id values found")

    for index, row in enumerate(rows, start=1):
        missing = sorted(REQUIRED_FIELDS - set(row))
        if missing:
            raise ValueError(f"Row {index} missing required fields: {missing}")
        if row["material_label"] not in row["candidate_labels"]:
            raise ValueError(f"Row {index} material_label is not in candidate_labels: {row['sample_id']}")
        bbox = row["bbox"]
        if not isinstance(bbox, list) or len(bbox) != 4 or not all(isinstance(value, int) for value in bbox):
            raise ValueError(f"Row {index} bbox must be four integers: {row['sample_id']}")
        if bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
            raise ValueError(f"Row {index} bbox has non-positive extent: {row['sample_id']}")
        for key in ("mean_rgb", "std_rgb"):
            value = row[key]
            if not isinstance(value, list) or len(value) != 3:
                raise ValueError(f"Row {index} {key} must contain three values: {row['sample_id']}")
        for key in PATH_KEYS:
            value = row.get(key)
            if isinstance(value, str) and is_absolute_path(value):
                raise ValueError(f"Row {index} has absolute path in {key}: {value}")
            should_check = required_path_keys is None or key in required_path_keys
            if workspace is not None and should_check and isinstance(value, str) and not (workspace / value).exists():
                raise FileNotFoundError(f"Row {index} path does not exist for {key}: {value}")

    groups = grouped_by_region(rows)
    for region_id, group in groups.items():
        if len(group) != lights_per_region:
            raise ValueError(f"Region {region_id} has {len(group)} samples; expected {lights_per_region}")
        if len({row["scene"] for row in group}) != 1:
            raise ValueError(f"Region {region_id} spans multiple scenes")
        if len({row["material_label"] for row in group}) != 1:
            raise ValueError(f"Region {region_id} spans multiple materials")
        if len({int(row["light_dir"]) for row in group}) != len(group):
            raise ValueError(f"Region {region_id} has duplicate light_dir values")

    scenes = sorted({str(row["scene"]) for row in rows})
    materials = Counter(str(group[0]["material_label"]) for group in groups.values())
    return {
        "sample_count": len(rows),
        "region_count": len(groups),
        "scene_count": len(scenes),
        "scenes": scenes,
        "regions_per_material": dict(sorted(materials.items())),
        "lights_per_region": lights_per_region,
        "path_mode": "repo_relative",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path)
    parser.add_argument("--output-manifest", type=Path)
    parser.add_argument("--summary-json", type=Path)
    parser.add_argument("--workspace", type=Path, default=Path("."))
    parser.add_argument("--check-files", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cfg = read_json(args.config)
    smoke_cfg = cfg["smoke_manifest"]
    source_key = smoke_cfg["source"]
    source_manifest = args.source_manifest or Path(cfg["source_manifests"][source_key])
    output_manifest = args.output_manifest or Path(smoke_cfg["output_manifest"])
    summary_json = args.summary_json or Path(smoke_cfg["summary_output"])

    rows = read_jsonl(source_manifest)
    source_hash = sha256_file(source_manifest)
    expected_hash = cfg.get("source_manifest_sha256", {}).get(source_key)
    if expected_hash and expected_hash != source_hash:
        raise ValueError(f"Source manifest hash mismatch for {source_key}: {source_hash} != {expected_hash}")

    output_rows = build_smoke_rows(
        rows=rows,
        target_material_labels=list(smoke_cfg["target_material_labels"]),
        max_regions=int(smoke_cfg["max_regions"]),
        lights_per_region=int(smoke_cfg["lights_per_region"]),
        source_manifest=source_key,
    )
    workspace = args.workspace.resolve() if args.check_files else None
    required_path_keys = {
        key
        for condition in cfg.get("probe_conditions", [])
        for key in condition.get("input_keys", [])
    }
    summary = validate_rows(
        output_rows,
        int(smoke_cfg["lights_per_region"]),
        workspace=workspace,
        required_path_keys=required_path_keys,
    )
    summary.update(
        {
            "experiment_id": cfg["experiment_id"],
            "source_manifest_key": source_key,
            "source_manifest": str(source_manifest.as_posix()),
            "source_manifest_sha256": source_hash,
            "output_manifest": str(output_manifest.as_posix()),
        }
    )

    if not args.dry_run:
        write_jsonl(output_manifest, output_rows)
        summary["output_manifest_sha256"] = sha256_file(output_manifest)
        summary_json.parent.mkdir(parents=True, exist_ok=True)
        summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
