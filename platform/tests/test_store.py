"""Store roundtrip + validation tests (stdlib unittest)."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_PLATFORM_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PLATFORM_DIR not in sys.path:
    sys.path.insert(0, _PLATFORM_DIR)

from labkit import schema  # noqa: E402
from labkit.store import Store  # noqa: E402


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(registry_dir=Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_idea_roundtrip(self):
        idea = schema.Idea(id="idea-x", title="X", slot="mainline", status="active")
        self.store.save(idea)
        loaded = self.store.load("ideas", "idea-x")
        self.assertEqual(loaded.title, "X")
        self.assertEqual(loaded.slot, "mainline")

    def test_run_metric_and_nested_roundtrip(self):
        exp = schema.Experiment(id="exp-x", title="E")
        self.store.save(exp)
        run = schema.Run(
            id="run-x",
            experiment_id="exp-x",
            metrics={"acc": schema.Metric(value=0.53, ci95=[0.44, 0.62], unit="accuracy")},
            verdict="uncertain",
        )
        self.store.save(run)
        loaded = self.store.load("runs", "run-x")
        self.assertIsInstance(loaded.metrics["acc"], schema.Metric)
        self.assertEqual(loaded.metrics["acc"].ci95, [0.44, 0.62])

    def test_invalid_slot_rejected(self):
        idea = schema.Idea(id="idea-y", title="Y", slot="not-a-slot")
        with self.assertRaises(ValueError):
            self.store.save(idea)

    def test_bad_ci_rejected(self):
        exp = schema.Experiment(id="exp-z", title="Z")
        self.store.save(exp)
        run = schema.Run(
            id="run-z", experiment_id="exp-z", metrics={"m": schema.Metric(value=1.0, ci95=[0.9, 0.1])}
        )
        with self.assertRaises(ValueError):
            self.store.save(run)

    def test_untracked_artifact_must_be_runs_local(self):
        exp = schema.Experiment(id="exp-a", title="A")
        self.store.save(exp)
        bad = schema.Run(
            id="run-a",
            experiment_id="exp-a",
            artifacts=[schema.Artifact(name="p", path="results/leak.json", tracked=False)],
        )
        with self.assertRaises(ValueError):
            self.store.save(bad)
        ok = schema.Run(
            id="run-a2",
            experiment_id="exp-a",
            artifacts=[schema.Artifact(name="p", path="runs_local/run-a2/p.json", tracked=False)],
        )
        self.store.save(ok)  # should not raise

    def test_validate_all_detects_dangling_run(self):
        run = schema.Run(id="run-orphan", experiment_id="exp-missing")
        self.store.save(run)
        problems = self.store.validate_all()
        self.assertTrue(any("dangling experiment_id" in p for p in problems))

    def test_linking(self):
        self.store.save(schema.Idea(id="idea-l", title="L"))
        self.store.save(schema.Experiment(id="exp-l", title="EL"))
        self.store.link_experiment_to_idea("exp-l", "idea-l")
        idea = self.store.load("ideas", "idea-l")
        exp = self.store.load("experiments", "exp-l")
        self.assertIn("exp-l", idea.experiment_ids)
        self.assertEqual(exp.idea_id, "idea-l")

    def test_content_id_deterministic(self):
        a = schema.content_id("idea", "Flip as Uncertainty")
        b = schema.content_id("idea", "Flip as Uncertainty")
        self.assertEqual(a, b)
        self.assertTrue(a.startswith("idea-flip-as-uncertainty-"))


if __name__ == "__main__":
    unittest.main()
