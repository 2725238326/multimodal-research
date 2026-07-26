import tempfile
import unittest
import zipfile
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

from scripts.build_material_external_confirmation import archive_scenes, downsample_image
from scripts.evaluate_photometric_trajectory_gate import (
    PRIMARY,
    build_condition_features,
    deranged_indices,
    paired_scene_bootstrap,
    validate_features,
)
from scripts.evaluate_photometric_external_confirmation import (
    aggregate_sample_predictions,
    majority,
    validate_descriptor_pair,
)
from scripts.extract_photometric_trajectory_features import (
    aggregate_trajectory,
    photometry_names,
    resolve_repo_path,
    sample_photometry,
)


PHOTOMETRY_CONFIG = {
    "near_white_threshold": 0.98,
    "near_dark_threshold": 0.02,
    "absolute_highlight_threshold": 0.9,
    "low_saturation_threshold": 0.2,
    "luminance_quantiles": [0.1, 0.25, 0.5, 0.75, 0.9],
    "gradient_quantiles": [0.5, 0.9],
}


class PhotometricExtractionTests(unittest.TestCase):
    def test_external_archive_scene_filter_is_sorted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.zip"
            with zipfile.ZipFile(path, "w") as handle:
                handle.writestr("everett_b/materials_mip2.png", b"x")
                handle.writestr("train_a/materials_mip2.png", b"x")
                handle.writestr("everett_a/materials_mip2.png", b"x")
            with zipfile.ZipFile(path) as handle:
                self.assertEqual(archive_scenes(handle, "everett"), ["everett_a", "everett_b"])

    def test_external_downsample_preserves_indexed_mask_mode(self):
        image = Image.fromarray(np.arange(64, dtype=np.uint8).reshape(8, 8), mode="P")
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        result = downsample_image(buffer.getvalue(), 2, Image.Resampling.NEAREST)
        self.assertEqual(result.mode, "P")
        self.assertEqual(result.size, (4, 4))

    def test_uniform_gray_has_no_clipping_or_spatial_energy(self):
        image = np.full((8, 8, 3), 0.5, dtype=np.float32)
        names = photometry_names(PHOTOMETRY_CONFIG)
        values = dict(zip(names, sample_photometry(image, PHOTOMETRY_CONFIG)))
        self.assertEqual(values["usable_fraction"], 1.0)
        self.assertEqual(values["clip_all_fraction"], 0.0)
        self.assertEqual(values["gradient_q90"], 0.0)
        self.assertEqual(values["laplacian_abs_mean"], 0.0)

    def test_white_image_records_censoring_before_fallback(self):
        image = np.ones((8, 8, 3), dtype=np.float32)
        names = photometry_names(PHOTOMETRY_CONFIG)
        values = dict(zip(names, sample_photometry(image, PHOTOMETRY_CONFIG)))
        self.assertEqual(values["usable_fraction"], 0.0)
        self.assertEqual(values["clip_all_fraction"], 1.0)
        self.assertEqual(values["highlight_fraction"], 1.0)

    def test_aggregate_trajectory_uses_only_selected_lights(self):
        values = np.asarray([[1.0, 10.0], [3.0, 30.0], [99.0, 99.0]])
        result = aggregate_trajectory(
            values, np.asarray([True, True, False]), reliable_count=2, fallback=False
        )
        np.testing.assert_allclose(result[:2], [2.0, 20.0])
        np.testing.assert_allclose(result[2:4], [1.0, 10.0])
        np.testing.assert_allclose(result[-3:], [2 / 3, 2 / 3, 0.0])

    def test_resolve_repo_path_strips_legacy_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = resolve_repo_path(
                "/home/legacy/multimodal-research/data/crop.jpg", root
            )
            self.assertEqual(result, (root / "data/crop.jpg").resolve())


class PhotometricEvaluationTests(unittest.TestCase):
    def test_external_majority_uses_deterministic_tie_break(self):
        self.assertEqual(majority(["wood", "metal"]), "metal")

    def test_external_sample_predictions_follow_target_region_order(self):
        result = aggregate_sample_predictions(
            np.asarray(["b", "a", "a", "b"]),
            np.asarray(["wood", "metal", "metal", "glass"]),
            np.asarray(["a", "b"]),
        )
        np.testing.assert_array_equal(result, ["metal", "glass"])

    def test_external_descriptor_validation_rejects_scene_overlap(self):
        base = {
            "region_ids": np.asarray(["r"]),
            "scenes": np.asarray(["s"]),
            "labels": np.asarray(["wood"]),
            "siglip_region_features": np.ones((1, 2)),
            "censored_photometric_features": np.ones((1, 3)),
            "exposure_only_features": np.ones((1, 2)),
        }
        with self.assertRaisesRegex(ValueError, "scene overlap"):
            validate_descriptor_pair(base, base)

    def test_derangement_has_no_fixed_points(self):
        result = deranged_indices(12, np.random.default_rng(7))
        self.assertTrue(np.all(result != np.arange(12)))
        np.testing.assert_array_equal(np.sort(result), np.arange(12))

    def test_primary_condition_concatenates_measurements(self):
        data = {
            "siglip_region_features": np.ones((3, 4), dtype=np.float32),
            "censored_photometric_features": np.ones((3, 6), dtype=np.float32),
            "uncensored_photometric_features": np.ones((3, 6), dtype=np.float32),
            "exposure_only_features": np.ones((3, 2), dtype=np.float32),
        }
        result = build_condition_features(PRIMARY, data, np.asarray([0, 2]))
        self.assertEqual(result.shape, (2, 10))

    def test_validate_features_rejects_duplicate_regions(self):
        data = {
            "region_ids": np.asarray(["a", "a"]),
            "scenes": np.asarray(["s", "s"]),
            "labels": np.asarray(["x", "x"]),
            "siglip_region_features": np.ones((2, 2)),
            "censored_photometric_features": np.ones((2, 2)),
            "uncensored_photometric_features": np.ones((2, 2)),
            "exposure_only_features": np.ones((2, 2)),
            "reliable_light_counts": np.asarray([5, 5]),
        }
        with self.assertRaisesRegex(ValueError, "unique region"):
            validate_features(data)

    def test_scene_bootstrap_constant_delta(self):
        result = paired_scene_bootstrap(
            labels=np.asarray(["a", "b", "a", "b"]),
            baseline_predictions=np.asarray(["b", "b", "b", "b"]),
            candidate_predictions=np.asarray(["a", "b", "a", "b"]),
            scenes=np.asarray(["s1", "s1", "s2", "s2"]),
            draws=500,
            seed=9,
            ci_level=0.95,
        )
        self.assertEqual(result["pooled_region_accuracy_delta"], 0.5)
        self.assertEqual(result["ci_low"], 0.5)
        self.assertEqual(result["ci_high"], 0.5)


if __name__ == "__main__":
    unittest.main()
