"""Entity schema for the labkit registry.

Every entity mirrors this project's research methodology (see
``docs/research-design-patterns.md``), not a generic ML run:

- Idea       — a research candidate/territory, placed in one WIP slot.
- Experiment — a falsifiable pre-registered contract (RP-01).
- Run        — a reproducible experiment capsule (RP-12) with a Go/No-Go verdict.
- Dataset    — a fixed data asset with independent-unit accounting.
- Module     — a reusable code component (encoder / head / aggregator / analysis).

Dataclasses only; stdlib only. ``validate()`` raises ``ValueError`` on a broken
entity. Serialization is plain ``dataclasses.asdict`` -> JSON.
"""

from __future__ import annotations

import dataclasses
import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Controlled vocabularies (kept small and explicit so the UI can rely on them)
# ---------------------------------------------------------------------------

IDEA_SLOTS = ("mainline", "adjacent", "high_risk", "pool")
IDEA_STATUSES = ("proposed", "active", "blocked", "parked", "done")
EXPERIMENT_TRACKS = ("exploratory", "confirmatory")
EXPERIMENT_STATUSES = ("planned", "smoke_test", "running", "completed", "no_go", "blocked")
RUN_VERDICTS = ("go", "no_go", "uncertain", "pending")
MODULE_KINDS = ("encoder", "head", "aggregator", "analysis", "dataset_builder", "other")

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    """Lowercase kebab-ish slug (deterministic, no timestamps)."""
    return _SLUG_RE.sub("-", text.strip().lower()).strip("-") or "item"


def content_id(prefix: str, *parts: str) -> str:
    """Deterministic id: ``<prefix>-<slug>-<hash6>``.

    Uses a content hash rather than a timestamp / random so ids are
    reproducible across machines and re-runs (see RP-12).
    """
    slug = slugify(parts[0]) if parts else "item"
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:6]
    return f"{prefix}-{slug}-{digest}"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _check_choice(value: str, allowed: tuple[str, ...], field_name: str) -> None:
    _require(value in allowed, f"{field_name!r} must be one of {allowed}, got {value!r}")


# ---------------------------------------------------------------------------
# Nested value objects
# ---------------------------------------------------------------------------


@dataclass
class Condition:
    """One experimental condition (RP-04 single-mechanism increment)."""

    name: str
    purpose: str = ""
    changed_var: str = ""


@dataclass
class ControlSet:
    """RP-05 counterfactual four-tuple (+ equal-compute control)."""

    correct: str = ""
    wrong: str = ""
    shuffled: str = ""
    irrelevant: str = ""
    equal_param: str = ""


@dataclass
class Metric:
    value: float
    ci95: list[float] | None = None
    unit: str = ""

    def validate(self, where: str) -> None:
        if self.ci95 is not None:
            _require(
                len(self.ci95) == 2 and self.ci95[0] <= self.ci95[1],
                f"{where}: ci95 must be [lo, hi] with lo<=hi, got {self.ci95}",
            )


@dataclass
class Artifact:
    name: str
    path: str
    tracked: bool = False  # tracked=False artifacts MUST live under runs_local/


@dataclass
class IndependentUnits:
    scenes: int = 0
    regions: int = 0
    samples: int = 0


# ---------------------------------------------------------------------------
# Top-level entities
# ---------------------------------------------------------------------------


@dataclass
class Idea:
    id: str
    title: str
    slot: str = "pool"
    status: str = "proposed"
    thesis: str = ""  # link to the mother-thesis in one line
    detail: str = ""
    design_patterns: list[str] = field(default_factory=list)
    collision_notes: str = ""
    experiment_ids: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)  # [[other-idea-id]] style refs

    kind = "idea"

    def validate(self) -> None:
        _require(bool(self.id), "idea.id required")
        _require(bool(self.title), "idea.title required")
        _check_choice(self.slot, IDEA_SLOTS, "idea.slot")
        _check_choice(self.status, IDEA_STATUSES, "idea.status")


@dataclass
class Experiment:
    id: str
    title: str
    idea_id: str = ""
    question: str = ""
    hypothesis: str = ""
    track: str = "exploratory"
    status: str = "planned"
    conditions: list[Condition] = field(default_factory=list)
    controls: ControlSet = field(default_factory=ControlSet)
    primary_metric: str = ""
    guardrail_metrics: list[str] = field(default_factory=list)
    go_threshold: str = ""
    no_go_threshold: str = ""
    statistical_unit: str = "region"
    bootstrap_unit: str = "scene"
    plan_md_path: str = ""
    config_path: str = ""
    run_ids: list[str] = field(default_factory=list)

    kind = "experiment"

    def validate(self) -> None:
        _require(bool(self.id), "experiment.id required")
        _require(bool(self.title), "experiment.title required")
        _check_choice(self.track, EXPERIMENT_TRACKS, "experiment.track")
        _check_choice(self.status, EXPERIMENT_STATUSES, "experiment.status")


@dataclass
class Run:
    id: str
    experiment_id: str
    title: str = ""
    commit: str = ""
    config_hash: str = ""
    manifest_hash: str = ""
    model_revision: str = ""
    seed: int | None = None
    device: str = ""
    command: str = ""
    started: str = ""
    ended: str = ""
    exit_status: str = ""
    metrics: dict[str, Metric] = field(default_factory=dict)
    conditions_metrics: list[dict[str, Any]] = field(default_factory=list)
    charts: list[dict[str, Any]] = field(default_factory=list)  # artifact.json-style
    datasets: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    verdict: str = "pending"
    verdict_reason: str = ""
    artifacts: list[Artifact] = field(default_factory=list)
    notes: str = ""

    kind = "run"

    def validate(self) -> None:
        _require(bool(self.id), "run.id required")
        _require(bool(self.experiment_id), "run.experiment_id required")
        _check_choice(self.verdict, RUN_VERDICTS, "run.verdict")
        for name, metric in self.metrics.items():
            metric.validate(f"run.metrics[{name}]")
        for art in self.artifacts:
            if not art.tracked:
                norm = art.path.replace("\\", "/")
                _require(
                    "runs_local/" in norm or norm.startswith("runs_local"),
                    f"untracked artifact {art.name!r} must live under runs_local/, got {art.path!r}",
                )


@dataclass
class Dataset:
    id: str
    name: str
    version: str = ""
    manifest_hash: str = ""
    license_status: str = "needs_verification"
    path: str = ""
    independent_units: IndependentUnits = field(default_factory=IndependentUnits)
    notes: str = ""

    kind = "dataset"

    def validate(self) -> None:
        _require(bool(self.id), "dataset.id required")
        _require(bool(self.name), "dataset.name required")


@dataclass
class Module:
    id: str
    name: str
    kind_: str = "other"
    path: str = ""
    notes: str = ""

    kind = "module"

    def validate(self) -> None:
        _require(bool(self.id), "module.id required")
        _check_choice(self.kind_, MODULE_KINDS, "module.kind_")


# Map folder name -> (dataclass, nested-field reconstruction)
ENTITY_TYPES: dict[str, type] = {
    "ideas": Idea,
    "experiments": Experiment,
    "runs": Run,
    "datasets": Dataset,
    "modules": Module,
}


# ---------------------------------------------------------------------------
# (de)serialization helpers that reconstruct nested dataclasses
# ---------------------------------------------------------------------------


def to_dict(entity: Any) -> dict[str, Any]:
    return dataclasses.asdict(entity)


def _build(cls: type, data: dict[str, Any]) -> Any:
    """Rebuild a dataclass (with nested dataclasses) from a plain dict."""
    if cls is Experiment:
        data = dict(data)
        data["conditions"] = [Condition(**c) for c in data.get("conditions", [])]
        ctrl = data.get("controls") or {}
        data["controls"] = ControlSet(**ctrl) if isinstance(ctrl, dict) else ctrl
    elif cls is Run:
        data = dict(data)
        data["metrics"] = {
            k: (v if isinstance(v, Metric) else Metric(**v))
            for k, v in (data.get("metrics") or {}).items()
        }
        data["artifacts"] = [
            a if isinstance(a, Artifact) else Artifact(**a) for a in data.get("artifacts", [])
        ]
    elif cls is Dataset:
        data = dict(data)
        iu = data.get("independent_units") or {}
        data["independent_units"] = IndependentUnits(**iu) if isinstance(iu, dict) else iu
    known = {f.name for f in dataclasses.fields(cls)}
    return cls(**{k: v for k, v in data.items() if k in known})


def from_dict(folder: str, data: dict[str, Any]) -> Any:
    cls = ENTITY_TYPES[folder]
    return _build(cls, data)
