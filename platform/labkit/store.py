"""File-backed registry store.

Source of truth is plain JSON under ``platform/registry/<folder>/<id>.json``.
Paths resolve from the package location, so the store works regardless of the
current working directory. Stdlib only.

Governance: registry lives under ``platform/`` (a fresh, git-tracked path) so
aggregate summaries are versioned — unlike ``results/`` which is fully
gitignored. Per-sample / large artifacts belong under ``platform/runs_local/``
(gitignored); ``Run.validate`` enforces that untracked artifacts live there.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from labkit import schema

# platform/labkit/store.py -> platform/ -> repo root
LABKIT_DIR = Path(__file__).resolve().parent
PLATFORM_DIR = LABKIT_DIR.parent
REPO_ROOT = PLATFORM_DIR.parent
REGISTRY_DIR = PLATFORM_DIR / "registry"
RUNS_LOCAL_DIR = PLATFORM_DIR / "runs_local"

FOLDERS = tuple(schema.ENTITY_TYPES.keys())


class Store:
    def __init__(self, registry_dir: Path | None = None) -> None:
        self.registry_dir = Path(registry_dir) if registry_dir else REGISTRY_DIR

    # -- paths ---------------------------------------------------------------
    def _folder(self, folder: str) -> Path:
        if folder not in schema.ENTITY_TYPES:
            raise KeyError(f"unknown entity folder: {folder}")
        return self.registry_dir / folder

    def _path(self, folder: str, entity_id: str) -> Path:
        return self._folder(folder) / f"{entity_id}.json"

    # -- generic read/write --------------------------------------------------
    def save(self, entity: Any) -> Path:
        entity.validate()
        folder = _folder_for(entity)
        path = self._path(folder, entity.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = schema.to_dict(entity)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return path

    def load(self, folder: str, entity_id: str) -> Any:
        path = self._path(folder, entity_id)
        if not path.exists():
            raise FileNotFoundError(f"{folder}/{entity_id} not found at {path}")
        return schema.from_dict(folder, json.loads(path.read_text(encoding="utf-8")))

    def load_raw(self, folder: str, entity_id: str) -> dict[str, Any]:
        return json.loads(self._path(folder, entity_id).read_text(encoding="utf-8"))

    def list(self, folder: str) -> list[Any]:
        d = self._folder(folder)
        if not d.exists():
            return []
        out = []
        for p in sorted(d.glob("*.json")):
            out.append(schema.from_dict(folder, json.loads(p.read_text(encoding="utf-8"))))
        return out

    def list_raw(self, folder: str) -> list[dict[str, Any]]:
        d = self._folder(folder)
        if not d.exists():
            return []
        return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(d.glob("*.json"))]

    def exists(self, folder: str, entity_id: str) -> bool:
        return self._path(folder, entity_id).exists()

    # -- linking -------------------------------------------------------------
    def link_experiment_to_idea(self, experiment_id: str, idea_id: str) -> None:
        idea = self.load("ideas", idea_id)
        if experiment_id not in idea.experiment_ids:
            idea.experiment_ids.append(experiment_id)
            self.save(idea)
        exp = self.load("experiments", experiment_id)
        if exp.idea_id != idea_id:
            exp.idea_id = idea_id
            self.save(exp)

    def link_run_to_experiment(self, run_id: str, experiment_id: str) -> None:
        exp = self.load("experiments", experiment_id)
        if run_id not in exp.run_ids:
            exp.run_ids.append(run_id)
            self.save(exp)

    # -- validation ----------------------------------------------------------
    def validate_all(self) -> list[str]:
        """Return a list of problems (empty == healthy)."""
        problems: list[str] = []
        ids_by_folder: dict[str, set[str]] = {}
        for folder in FOLDERS:
            ids_by_folder[folder] = set()
            for raw in self.list_raw(folder):
                try:
                    entity = schema.from_dict(folder, raw)
                    entity.validate()
                    ids_by_folder[folder].add(entity.id)
                except Exception as exc:  # noqa: BLE001 - report, don't crash
                    problems.append(f"{folder}/{raw.get('id', '?')}: {exc}")
        # referential integrity
        for exp in self.list("experiments"):
            if exp.idea_id and exp.idea_id not in ids_by_folder["ideas"]:
                problems.append(f"experiments/{exp.id}: dangling idea_id {exp.idea_id}")
        for run in self.list("runs"):
            if run.experiment_id not in ids_by_folder["experiments"]:
                problems.append(
                    f"runs/{run.id}: dangling experiment_id {run.experiment_id}"
                )
        return problems

    # -- export --------------------------------------------------------------
    def export(self) -> dict[str, list[dict[str, Any]]]:
        return {folder: self.list_raw(folder) for folder in FOLDERS}


def _folder_for(entity: Any) -> str:
    for folder, cls in schema.ENTITY_TYPES.items():
        if isinstance(entity, cls):
            return folder
    raise TypeError(f"unknown entity type: {type(entity)!r}")


def runs_local_path(run_id: str, *parts: str) -> Path:
    """Path under the gitignored runs_local/ tree for per-sample artifacts."""
    p = RUNS_LOCAL_DIR / run_id
    for part in parts:
        p = p / part
    return p


def rel_to_platform(path: Path) -> str:
    """Path relative to platform/ using forward slashes (for artifact refs)."""
    try:
        return path.resolve().relative_to(PLATFORM_DIR).as_posix()
    except ValueError:
        return path.as_posix()
