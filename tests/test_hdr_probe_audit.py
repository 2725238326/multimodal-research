import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from scripts.audit_hdr_probe_radiometry import descriptor_statistics, disc_mask
from scripts.fetch_ranged_asset import plan_ranges
from scripts.summarize_hdr_probe_audit import median_of, scene_record


class RangePlanTests(unittest.TestCase):
    def test_ranges_cover_every_byte_without_overlap(self):
        ranges = plan_ranges(1000, 7)
        self.assertEqual(ranges[0][0], 0)
        self.assertEqual(ranges[-1][1], 999)
        for previous, current in zip(ranges, ranges[1:]):
            self.assertEqual(current[0], previous[1] + 1)
        self.assertEqual(sum(end - start + 1 for start, end in ranges), 1000)

    def test_part_count_never_exceeds_length(self):
        self.assertEqual(len(plan_ranges(3, 16)), 3)

    def test_single_part_is_the_whole_file(self):
        self.assertEqual(plan_ranges(42, 1), [(0, 41)])

    def test_zero_parts_rejected(self):
        with self.assertRaises(ValueError):
            plan_ranges(10, 0)


class DiscMaskTests(unittest.TestCase):
    def test_mask_is_centered_and_bounded(self):
        mask = disc_mask(256, 0.42)
        self.assertTrue(mask[128, 128])
        self.assertFalse(mask[0, 0])
        self.assertLess(mask.mean(), 1.0)
        self.assertGreater(mask.mean(), 0.0)

    def test_mask_is_symmetric(self):
        mask = disc_mask(64, 0.4)
        np.testing.assert_array_equal(mask, mask[::-1])
        np.testing.assert_array_equal(mask, mask[:, ::-1])


class DescriptorStatisticsTests(unittest.TestCase):
    def test_per_direction_offset_leaves_between_region_variance_unchanged(self):
        rng = np.random.default_rng(0)
        descriptors = rng.normal(size=(5, 25, 3))
        offset = rng.normal(size=(1, 25, 3))

        base = descriptor_statistics(descriptors)
        shifted = descriptor_statistics(descriptors - offset)

        self.assertAlmostEqual(
            base["between_region_variance_mean"],
            shifted["between_region_variance_mean"],
            places=12,
        )

    def test_removing_a_shared_illumination_term_reduces_within_variance(self):
        rng = np.random.default_rng(1)
        identity = rng.normal(size=(6, 1, 3)) * 3.0
        illumination = rng.normal(size=(1, 25, 3))
        descriptors = identity + illumination

        raw = descriptor_statistics(descriptors)
        corrected = descriptor_statistics(descriptors - illumination)

        self.assertLess(corrected["within_region_variance_mean"], raw["within_region_variance_mean"])
        self.assertGreater(corrected["between_over_within_mean"], raw["between_over_within_mean"])


class SummaryTests(unittest.TestCase):
    def _payload(self):
        return {
            "scene": "demo_scene",
            "num_regions": 4,
            "num_directions": 2,
            "radiometric_coupling": {
                "pearson_scene_vs_gray_probe": 0.1,
                "pearson_scene_vs_chrome_probe": 0.6,
            },
            "discriminability": {
                "raw_linear_log": {"within_region_variance_mean": 0.2, "between_over_within_mean": 2.0},
                "gray_probe_normalized_log": {
                    "within_region_variance_mean": 0.1,
                    "between_over_within_mean": 4.0,
                },
                "normalized_over_raw_ratio": 2.0,
            },
            "directions": [
                {"scene_mean": 1.0, "gray_probe": {"mean_luminance": 0.2}, "chrome_probe": {"mean_luminance": 0.3}},
                {"scene_mean": 4.0, "gray_probe": {"mean_luminance": 0.4}, "chrome_probe": {"mean_luminance": 1.2}},
            ],
        }

    def test_scene_record_computes_dynamic_ranges(self):
        record = scene_record(self._payload())
        self.assertAlmostEqual(record["scene_mean_dynamic_range"], 4.0)
        self.assertAlmostEqual(record["gray_probe_dynamic_range"], 2.0)
        self.assertAlmostEqual(record["discriminability_gain"], 2.0)
        self.assertNotIn("ldr_saturated_any_channel_fraction_mean", record)

    def test_scene_record_includes_clipping_when_present(self):
        payload = self._payload()
        payload["ldr_clipping"] = {
            "saturated_any_channel_fraction_mean": 0.05,
            "saturated_any_channel_fraction_max": 0.4,
            "linear_value_at_jpeg_clip_mean": 1.1,
            "linear_max_over_clip_mean": 20.0,
        }
        record = scene_record(payload)
        self.assertAlmostEqual(record["ldr_saturated_any_channel_fraction_mean"], 0.05)

    def test_median_of_ignores_missing_values(self):
        records = [{"a": 1.0}, {"a": None}, {"a": 3.0}]
        self.assertAlmostEqual(median_of(records, "a"), 2.0)
        self.assertIsNone(median_of(records, "missing"))


class CommittedSummaryTests(unittest.TestCase):
    def test_committed_summary_is_parseable_and_marked_no_go(self):
        path = Path("results/quantitative/hdr_light_probe_oracle_audit_v0/summary.json")
        if not path.exists():
            self.skipTest("summary not generated in this checkout")
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["verdict"], "No-Go")
        self.assertEqual(payload["trained_parameters"], 0)
        self.assertTrue(payload["caveats"])


if __name__ == "__main__":
    unittest.main()
