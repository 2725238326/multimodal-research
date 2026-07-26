import tempfile
import unittest
from pathlib import Path

import numpy as np

from scripts.evaluate_material_response_probe import (
    build_condition_features,
    metrics,
    paired_scene_bootstrap,
    region_statistics,
)
from scripts.extract_material_response_features import feature_tensor, resolve_repo_path


class MaterialResponseFeatureTests(unittest.TestCase):
    def test_feature_tensor_accepts_pooler_output(self):
        import torch

        class Output:
            pooler_output = torch.ones((2, 3))

        self.assertEqual(tuple(feature_tensor(Output()).shape), (2, 3))

    def test_resolve_repo_path_strips_legacy_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            expected = root / "data" / "processed" / "crop.jpg"
            actual = resolve_repo_path(
                "/home/legacy/multimodal-research/data/processed/crop.jpg", root
            )
            self.assertEqual(actual, expected.resolve())

    def test_region_statistics_repeat_group_values(self):
        regions = np.asarray(["a", "a", "b", "b"])
        features = np.asarray([[1, 2], [3, 4], [10, 20], [14, 24]], dtype=np.float32)
        means, stds = region_statistics(regions, features)
        np.testing.assert_allclose(means[:2], [[2, 3], [2, 3]])
        np.testing.assert_allclose(means[2:], [[12, 22], [12, 22]])
        np.testing.assert_allclose(stds[:2], [[1, 1], [1, 1]])

    def test_pairwise_response_has_expected_blocks(self):
        regions = np.asarray(["a", "a", "b", "b"])
        rgb = np.asarray([[1, 2], [3, 4], [10, 20], [14, 24]], dtype=np.float32)
        albedo = rgb * 0.5
        features = build_condition_features(
            "pairwise_response", rgb, albedo, regions, seed=7
        )
        self.assertEqual(features.shape, (4, 8))
        np.testing.assert_allclose(features[:, :2], rgb)
        np.testing.assert_allclose(features[0, 4:6], [-1, -1])

    def test_equal_parameter_branch_is_seed_deterministic(self):
        regions = np.asarray(["a", "a"])
        rgb = np.asarray([[1, 2], [3, 4]], dtype=np.float32)
        first = build_condition_features("equal_parameter_branch", rgb, rgb, regions, 9)
        second = build_condition_features("equal_parameter_branch", rgb, rgb, regions, 9)
        np.testing.assert_array_equal(first, second)

    def test_metrics_use_region_majority_and_flip(self):
        labels = np.asarray(["metal", "metal", "wood", "wood"])
        predictions = np.asarray(["metal", "wood", "wood", "wood"])
        regions = np.asarray(["a", "a", "b", "b"])
        lights = np.asarray([1, 2, 1, 2])
        result = metrics(labels, predictions, regions, lights)
        self.assertEqual(result["mean_region_accuracy"], 1.0)
        self.assertEqual(result["region_flip_rate"], 0.5)

    def test_paired_scene_bootstrap_reports_exact_constant_delta(self):
        baseline = {"a": 0.0, "b": 0.5, "c": 0.25}
        candidate = {"a": 0.25, "b": 0.75, "c": 0.5}
        result = paired_scene_bootstrap(
            baseline, candidate, draws=500, seed=11, ci_level=0.95
        )
        self.assertAlmostEqual(result["mean_delta"], 0.25)
        self.assertAlmostEqual(result["ci_low"], 0.25)
        self.assertAlmostEqual(result["ci_high"], 0.25)


if __name__ == "__main__":
    unittest.main()
