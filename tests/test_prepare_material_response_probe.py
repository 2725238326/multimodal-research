from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.prepare_material_response_probe import (
    build_smoke_rows,
    is_absolute_path,
    normalize_repo_path,
    validate_rows,
)


def make_row(region: str, material: str, light: int, path_prefix: str = "/legacy/multimodal-research") -> dict:
    return {
        "sample_id": f"{region}_d{light:02d}",
        "region_id": region,
        "scene": region.split("_r", 1)[0],
        "light_dir": light,
        "material_id": 12 if material == "glass" else 17,
        "material_label": material,
        "candidate_labels": ["glass", "metal"],
        "bbox": [1, 2, 9, 10],
        "component_area": 64,
        "crop_purity": 1.0,
        "crop_path": f"{path_prefix}/data/processed/rgb/{region}_d{light:02d}.jpg",
        "rgb_crop_path": f"{path_prefix}/data/processed/rgb/{region}_d{light:02d}.jpg",
        "albedo_crop_path": f"{path_prefix}/data/processed/albedo/{region}_d{light:02d}.png",
        "mean_rgb": [0.1 * light, 0.2, 0.3],
        "std_rgb": [0.01, 0.02 * light, 0.03],
    }


class PrepareMaterialResponseProbeTests(unittest.TestCase):
    def test_normalize_repo_path_strips_known_workspace_prefix(self) -> None:
        value = "/legacy/multimodal-research/data/processed/sample.jpg"
        self.assertEqual(normalize_repo_path(value), "data/processed/sample.jpg")
        self.assertFalse(is_absolute_path(normalize_repo_path(value)))

    def test_build_smoke_rows_balances_targets_and_rewrites_paths(self) -> None:
        rows = []
        for light in [0, 1, 2, 3, 4]:
            rows.append(make_row("scene_a_r000_12", "glass", light))
            rows.append(make_row("scene_b_r001_17", "metal", light))

        smoke = build_smoke_rows(
            rows,
            target_material_labels=["glass", "metal"],
            max_regions=2,
            lights_per_region=3,
            source_manifest="fixture",
        )
        summary = validate_rows(smoke, lights_per_region=3)

        self.assertEqual(summary["sample_count"], 6)
        self.assertEqual(summary["region_count"], 2)
        self.assertEqual(summary["regions_per_material"], {"glass": 1, "metal": 1})
        self.assertTrue(all(row["path_mode"] == "repo_relative" for row in smoke))
        self.assertTrue(all(not is_absolute_path(row["rgb_crop_path"]) for row in smoke))
        self.assertTrue(all(not is_absolute_path(row["albedo_crop_path"]) for row in smoke))

    def test_validate_rows_can_check_files_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            rows = [make_row("scene_a_r000_12", "glass", light, path_prefix="multimodal-research") for light in [0, 1, 2]]
            smoke = build_smoke_rows(
                rows,
                target_material_labels=["glass"],
                max_regions=1,
                lights_per_region=3,
                source_manifest="fixture",
            )
            for row in smoke:
                for key in ["rgb_crop_path", "albedo_crop_path"]:
                    path = workspace / row[key]
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(b"fixture")

            summary = validate_rows(smoke, lights_per_region=3, workspace=workspace)
            self.assertEqual(summary["sample_count"], 3)


if __name__ == "__main__":
    unittest.main()
