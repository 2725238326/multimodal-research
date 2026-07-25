"""flip_identifiability analysis unit tests (stdlib unittest + numpy)."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_PLATFORM_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PLATFORM_DIR not in sys.path:
    sys.path.insert(0, _PLATFORM_DIR)

import numpy as np  # noqa: E402

from labkit.analyses import flip_identifiability as fi  # noqa: E402


def _row(region, scene, light, label, pred, correct, mean_rgb):
    return {
        "sample_id": f"{region}_d{light:02d}",
        "region_id": region,
        "scene": scene,
        "light_dir": light,
        "material_id": 1,
        "material_label": label,
        "candidate_labels": ["glass", "wood", "metal"],
        "predicted_label": pred,
        "correct": correct,
        "mean_rgb": mean_rgb,
        "std_rgb": [0.1, 0.1, 0.1],
    }


class HelperTest(unittest.TestCase):
    def test_entropy(self):
        self.assertAlmostEqual(fi.shannon_entropy_bits({"a": 4}), 0.0)
        self.assertAlmostEqual(fi.shannon_entropy_bits({"a": 2, "b": 2}), 1.0)
        self.assertAlmostEqual(fi.shannon_entropy_bits({"a": 1, "b": 1, "c": 1, "d": 1}), 2.0)

    def test_partition(self):
        self.assertEqual(fi.partition_of("glass"), "under_identified")
        self.assertEqual(fi.partition_of("wood"), "identifiable")
        self.assertEqual(fi.partition_of("ceramic"), "mixed")

    def test_auroc_perfect(self):
        # higher score for positives -> AUROC 1.0
        score = np.array([0.1, 0.2, 0.9, 0.8])
        pos = np.array([False, False, True, True])
        self.assertAlmostEqual(fi.auroc(score, pos), 1.0)

    def test_auroc_ties_half(self):
        score = np.array([0.5, 0.5])
        pos = np.array([True, False])
        self.assertAlmostEqual(fi.auroc(score, pos), 0.5)

    def test_auroc_degenerate(self):
        score = np.array([0.5, 0.6])
        pos = np.array([True, True])
        self.assertTrue(np.isnan(fi.auroc(score, pos)))


class AnalyzeModelTest(unittest.TestCase):
    def _write(self, rows):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
        for r in rows:
            tmp.write(json.dumps(r) + "\n")
        tmp.close()
        return Path(tmp.name)

    def test_stable_region_beats_unstable(self):
        rows = []
        # identifiable wood region: stable + correct (low entropy, high accuracy)
        for lg in range(4):
            rows.append(_row("sceneA_r0_1", "sceneA", lg, "wood", "wood", True, [0.5, 0.4, 0.3]))
        # under-identified glass region: flips + wrong (high entropy, low accuracy)
        flips = ["glass", "metal", "wood", "metal"]
        for lg, pred in enumerate(flips):
            rows.append(
                _row(
                    "sceneB_r0_1", "sceneB", lg, "glass", pred, pred == "glass",
                    [0.1 + 0.3 * lg, 0.2, 0.4],  # big illumination swing
                )
            )
        path = self._write(rows)
        try:
            out = fi.analyze_model("TestModel", path)
        finally:
            os.unlink(path)

        regions = {r["region_id"]: r for r in out["regions"]}
        self.assertAlmostEqual(regions["sceneA_r0_1"]["flip_entropy_bits"], 0.0)
        self.assertGreater(regions["sceneB_r0_1"]["flip_entropy_bits"], 1.0)
        # wood region more illumination-stable than glass region
        self.assertLess(
            regions["sceneA_r0_1"]["illumination_sensitivity"],
            regions["sceneB_r0_1"]["illumination_sensitivity"],
        )
        # partitions present
        self.assertIn("identifiable", out["partitions"])
        self.assertIn("under_identified", out["partitions"])
        self.assertGreater(
            out["partitions"]["identifiable"]["accuracy"],
            out["partitions"]["under_identified"]["accuracy"],
        )
        # low-entropy-first selective accuracy >= overall
        self.assertGreaterEqual(out["selective_curve"][0]["accuracy"], out["overall_region_accuracy"])


if __name__ == "__main__":
    unittest.main()
