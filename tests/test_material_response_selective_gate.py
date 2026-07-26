import unittest

import numpy as np

from scripts.evaluate_material_response_selective_gate import (
    exact_acceptance,
    normalized_entropy,
    paired_scene_bootstrap,
    response_statistics,
    selective_metrics,
    validate_features,
)


class MaterialResponseSelectiveGateTests(unittest.TestCase):
    def test_normalized_entropy_bounds(self):
        self.assertAlmostEqual(normalized_entropy(np.asarray([1.0, 0.0])), 0.0)
        self.assertAlmostEqual(normalized_entropy(np.asarray([0.5, 0.5])), 1.0)

    def test_response_statistics_zero_for_identical_embeddings(self):
        result = response_statistics(np.ones((3, 4), dtype=np.float32))
        np.testing.assert_allclose(result, np.zeros(3), atol=1e-12)

    def test_response_statistics_detects_cross_light_change(self):
        features = np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
        variance, residual, dispersion = response_statistics(features)
        self.assertGreater(variance, 0.0)
        self.assertGreater(residual, 0.0)
        self.assertAlmostEqual(dispersion, 1.0)

    def test_exact_acceptance_has_identical_count_and_stable_ties(self):
        scores = np.asarray([0.2, 0.1, 0.1, 0.9])
        regions = np.asarray(["d", "c", "a", "b"])
        accepted = exact_acceptance(scores, regions, 0.5)
        np.testing.assert_array_equal(accepted, [False, True, True, False])
        self.assertEqual(int(accepted.sum()), 2)

    def test_selective_metrics_use_only_accepted_regions(self):
        result = selective_metrics(
            np.asarray(["a", "a", "b"]),
            np.asarray(["a", "b", "b"]),
            np.asarray([True, False, True]),
        )
        self.assertEqual(result["selective_accuracy"], 1.0)
        self.assertAlmostEqual(result["coverage"], 2 / 3)

    def test_scene_bootstrap_constant_delta(self):
        result = paired_scene_bootstrap(
            labels=np.asarray(["a", "b", "a", "b"]),
            predictions=np.asarray(["a", "a", "a", "a"]),
            candidate_accept=np.asarray([True, False, True, False]),
            baseline_accept=np.asarray([False, True, False, True]),
            scenes=np.asarray(["s1", "s1", "s2", "s2"]),
            draws=500,
            seed=7,
            ci_level=0.95,
        )
        self.assertEqual(result["mean_delta"], 1.0)
        self.assertEqual(result["ci_low"], 1.0)
        self.assertEqual(result["ci_high"], 1.0)

    def test_validate_features_rejects_region_crossing_scenes(self):
        data = {
            "sample_ids": np.asarray(["a", "b"]),
            "region_ids": np.asarray(["r", "r"]),
            "scenes": np.asarray(["s1", "s2"]),
            "labels": np.asarray(["wood", "wood"]),
            "light_dirs": np.asarray([1, 2]),
            "rgb_features": np.ones((2, 3), dtype=np.float32),
        }
        with self.assertRaisesRegex(ValueError, "crosses scenes"):
            validate_features(data)


if __name__ == "__main__":
    unittest.main()
