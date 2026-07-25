"""① identifiability partition + ② flip-as-uncertainty — offline, no training.

Tests two claims on the existing material-constancy v2 predictions (330 samples,
66 regions, 30 scenes, two frozen VLMs), reusing the project's exact region
metrics and bootstrap method:

  ②  Does a frozen VLM's *instability* under illumination change (the Shannon
     entropy of its per-region answer distribution) predict its errors?
     -> AUROC(-entropy -> per-sample correct), scene-aware bootstrap CI.
     -> selective-prediction gain: accuracy over the 50% lowest-entropy regions
        minus overall accuracy (abstain on the unstable half).

  ①  Is accuracy lower / instability higher on physically under-identified
     materials (glass, clear plastic, metal — discriminative info lives in
     specular/transparent response) than on identifiable diffuse materials?
     -> descriptive partition table. The full "semantic prior helps only in the
        under-identified partition" test needs the albedo arm and is left as the
        next step; here we establish the partition gap.

Reuses ``scripts/compare_material_conditions.py`` (region_metrics, read_rows,
paired_ci) and ``scripts/analyze_material_gate.py`` (bootstrap_ci) for numeric
parity with the rest of the project (seed=20260719, region unit).
"""

from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from labkit import schema
from labkit.store import REPO_ROOT, Store, runs_local_path

# Reuse the project's canonical helpers instead of re-deriving CI / region logic.
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from compare_material_conditions import read_rows, region_metrics  # noqa: E402
from analyze_material_gate import bootstrap_ci  # noqa: E402

SEED = 20260719

# Material identifiability partition (see docs/semantic-physical-route-audit.md).
UNDER_IDENTIFIED = {"glass", "clear plastic", "metal"}
IDENTIFIABLE = {"wood", "tile", "leather", "fabric/cloth", "paper/tissue"}

DEFAULT_INPUTS = {
    "Qwen3-VL-2B-Instruct": "results/quantitative/material_constancy_rgb_gate_v2/qwen3vl2b_predictions_corrected.jsonl",
    "InternVL3.5-2B-HF": "results/quantitative/material_constancy_rgb_gate_v2/internvl3_5_2b_predictions.jsonl",
}


# --------------------------------------------------------------------------- #
# metrics
# --------------------------------------------------------------------------- #

def shannon_entropy_bits(counts: dict[str, int]) -> float:
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    h = 0.0
    for c in counts.values():
        if c <= 0:
            continue
        p = c / total
        h -= p * math.log2(p)
    return h


def partition_of(material_label: str) -> str:
    if material_label in UNDER_IDENTIFIED:
        return "under_identified"
    if material_label in IDENTIFIABLE:
        return "identifiable"
    return "mixed"


def _rankdata_avg(values: np.ndarray) -> np.ndarray:
    """Ranks with ties averaged (scipy-free)."""
    order = values.argsort(kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    ranks[order] = np.arange(1, len(values) + 1, dtype=float)
    sorted_vals = values[order]
    i = 0
    n = len(values)
    while i < n:
        j = i
        while j + 1 < n and sorted_vals[j + 1] == sorted_vals[i]:
            j += 1
        if j > i:
            ranks[order[i : j + 1]] = np.arange(i + 1, j + 2, dtype=float).mean()
        i = j + 1
    return ranks


def auroc(score: np.ndarray, positive: np.ndarray) -> float:
    """AUROC that a higher score marks a positive (correct) sample."""
    n_pos = int(positive.sum())
    n_neg = int((~positive).sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    ranks = _rankdata_avg(score)
    return float((ranks[positive].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def _scene_bootstrap_auroc(
    scenes: np.ndarray, score: np.ndarray, positive: np.ndarray, draws: int = 2000
) -> list[float]:
    unique = np.array(sorted(set(scenes.tolist())))
    idx_by_scene = {s: np.where(scenes == s)[0] for s in unique}
    rng = np.random.default_rng(SEED)
    vals = []
    for _ in range(draws):
        picked = unique[rng.integers(0, len(unique), size=len(unique))]
        idx = np.concatenate([idx_by_scene[s] for s in picked])
        a = auroc(score[idx], positive[idx])
        if not math.isnan(a):
            vals.append(a)
    if not vals:
        return [float("nan"), float("nan")]
    return [round(float(np.quantile(vals, 0.025)), 4), round(float(np.quantile(vals, 0.975)), 4)]


# --------------------------------------------------------------------------- #
# per-model analysis
# --------------------------------------------------------------------------- #

def analyze_model(model_name: str, jsonl_path: Path) -> dict[str, Any]:
    rows = read_rows(jsonl_path)  # dict keyed by sample_id, validates dup ids
    region_base = region_metrics(rows)  # {region_id: {accuracy, consistency, flip}}

    # group rows by region for entropy + illumination sensitivity + scene/label
    by_region: defaultdict[str, list[dict]] = defaultdict(list)
    for row in rows.values():
        by_region[row["region_id"]].append(row)

    regions: list[dict[str, Any]] = []
    for region_id, group in sorted(by_region.items()):
        preds = [r["predicted_label"] or "<invalid>" for r in group]
        counts = dict(Counter(preds))
        mean_rgb = np.asarray([r["mean_rgb"] for r in group], dtype=float)  # (lights, 3)
        illum_sensitivity = float(mean_rgb.std(axis=0).mean()) if len(group) > 1 else 0.0
        label = group[0]["material_label"]
        regions.append(
            {
                "region_id": region_id,
                "scene": group[0]["scene"],
                "material_label": label,
                "partition": partition_of(label),
                "n_lights": len(group),
                "accuracy": region_base[region_id]["accuracy"],
                "consistency": region_base[region_id]["consistency"],
                "flip": region_base[region_id]["flip"],
                "flip_entropy_bits": round(shannon_entropy_bits(counts), 4),
                "illumination_sensitivity": round(illum_sensitivity, 4),
                "prediction_counts": counts,
            }
        )

    # -- ② per-sample AUROC(-entropy -> correct), scene-aware bootstrap ------
    entropy_by_region = {r["region_id"]: r["flip_entropy_bits"] for r in regions}
    sample_score, sample_pos, sample_scene = [], [], []
    for row in rows.values():
        sample_score.append(-entropy_by_region[row["region_id"]])  # low entropy => high score
        sample_pos.append(bool(row["correct"]))
        sample_scene.append(row["scene"])
    score = np.asarray(sample_score, dtype=float)
    positive = np.asarray(sample_pos, dtype=bool)
    scenes = np.asarray(sample_scene)
    auc = auroc(score, positive)
    auc_ci = _scene_bootstrap_auroc(scenes, score, positive)

    # -- ② selective prediction over regions (abstain on unstable half) ------
    reg_sorted = sorted(regions, key=lambda r: r["flip_entropy_bits"])
    acc_all = float(np.mean([r["accuracy"] for r in reg_sorted]))
    n = len(reg_sorted)
    curve = []
    for k in range(1, n + 1):
        cov = k / n
        acc = float(np.mean([r["accuracy"] for r in reg_sorted[:k]]))
        curve.append({"coverage": round(cov, 4), "accuracy": round(acc, 4)})
    half = max(1, n // 2)
    acc_low_half = float(np.mean([r["accuracy"] for r in reg_sorted[:half]]))
    selective_gain = round(acc_low_half - acc_all, 4)
    # scene-aware bootstrap of the gain
    gain_ci = _scene_bootstrap_selective_gain(regions)

    # -- ① identifiability partition table ----------------------------------
    partitions = {}
    for name in ("identifiable", "mixed", "under_identified"):
        members = [r for r in regions if r["partition"] == name]
        if not members:
            continue
        partitions[name] = {
            "regions": len(members),
            "accuracy": round(float(np.mean([m["accuracy"] for m in members])), 4),
            "accuracy_ci95": bootstrap_ci([m["accuracy"] for m in members]),
            "flip_rate": round(float(np.mean([m["flip"] for m in members])), 4),
            "mean_entropy_bits": round(float(np.mean([m["flip_entropy_bits"] for m in members])), 4),
            "mean_illumination_sensitivity": round(
                float(np.mean([m["illumination_sensitivity"] for m in members])), 4
            ),
        }

    return {
        "model": model_name,
        "region_count": n,
        "scene_count": len(set(scenes.tolist())),
        "sample_count": len(rows),
        "overall_region_accuracy": round(acc_all, 4),
        "auroc_entropy_predicts_correct": round(auc, 4),
        "auroc_ci95": auc_ci,
        "selective_gain_at_50pct": selective_gain,
        "selective_gain_ci95": gain_ci,
        "selective_curve": curve,
        "partitions": partitions,
        "regions": regions,
    }


def _scene_bootstrap_selective_gain(regions: list[dict[str, Any]], draws: int = 2000) -> list[float]:
    by_scene: defaultdict[str, list[dict]] = defaultdict(list)
    for r in regions:
        by_scene[r["scene"]].append(r)
    scenes = np.array(sorted(by_scene))
    rng = np.random.default_rng(SEED)
    vals = []
    for _ in range(draws):
        picked = scenes[rng.integers(0, len(scenes), size=len(scenes))]
        members: list[dict] = []
        for s in picked:
            members.extend(by_scene[s])
        if len(members) < 2:
            continue
        members_sorted = sorted(members, key=lambda r: r["flip_entropy_bits"])
        acc_all = float(np.mean([m["accuracy"] for m in members_sorted]))
        half = max(1, len(members_sorted) // 2)
        acc_low = float(np.mean([m["accuracy"] for m in members_sorted[:half]]))
        vals.append(acc_low - acc_all)
    if not vals:
        return [float("nan"), float("nan")]
    return [round(float(np.quantile(vals, 0.025)), 4), round(float(np.quantile(vals, 0.975)), 4)]


# --------------------------------------------------------------------------- #
# build the Run
# --------------------------------------------------------------------------- #

def _verdict(per_model: list[dict[str, Any]]) -> tuple[str, str]:
    """Go if, for every model, AUROC CI lower bound > 0.5 AND selective gain CI lower > 0."""
    ok_auc = all(m["auroc_ci95"][0] > 0.5 for m in per_model)
    ok_gain = all(m["selective_gain_ci95"][0] > 0 for m in per_model)
    if ok_auc and ok_gain:
        return "go", (
            "Both models: AUROC(-entropy->correct) CI lower bound > 0.5 and "
            "selective-accuracy gain @50% coverage CI lower bound > 0. Illumination "
            "instability is a usable, training-free error/uncertainty signal."
        )
    if ok_auc or ok_gain:
        return "uncertain", (
            "Signal present but not on every model / both metrics; treat as exploratory."
        )
    return "no_go", "Instability does not predict correctness above chance with CI margin."


def _charts_and_datasets(per_model: list[dict[str, Any]], experiment_id: str) -> dict[str, Any]:
    # partition accuracy bars (artifact.json-style)
    part_rows = []
    for m in per_model:
        for name, p in m["partitions"].items():
            part_rows.append(
                {
                    "model": m["model"],
                    "partition": name,
                    "accuracy": p["accuracy"],
                    "ci_lo": p["accuracy_ci95"][0],
                    "ci_hi": p["accuracy_ci95"][1],
                    "flip_rate": p["flip_rate"],
                    "mean_entropy_bits": p["mean_entropy_bits"],
                    "regions": p["regions"],
                }
            )
    scatter_rows = [
        {
            "model": m["model"],
            "region_id": r["region_id"],
            "material_label": r["material_label"],
            "partition": r["partition"],
            "flip_entropy_bits": r["flip_entropy_bits"],
            "accuracy": r["accuracy"],
            "illumination_sensitivity": r["illumination_sensitivity"],
        }
        for m in per_model
        for r in m["regions"]
    ]
    selective_rows = [
        {"model": m["model"], **pt} for m in per_model for pt in m["selective_curve"]
    ]
    charts = [
        {
            "id": "partition_accuracy",
            "title": "① 可识别性分区准确率",
            "subtitle": "under-identified (glass/clear plastic/metal) vs identifiable diffuse",
            "type": "grouped_bar",
            "dataset": "partition_accuracy",
            "valueFormat": "percent",
            "encodings": {
                "x": {"field": "partition", "type": "nominal"},
                "y": {"field": "accuracy", "type": "quantitative", "format": "percent"},
                "series": {"field": "model", "type": "nominal"},
                "ciLo": {"field": "ci_lo"},
                "ciHi": {"field": "ci_hi"},
            },
        },
        {
            "id": "entropy_vs_accuracy",
            "title": "② 翻转熵 vs 区域准确率",
            "subtitle": "each point = one region; higher entropy should track lower accuracy",
            "type": "scatter",
            "dataset": "entropy_vs_accuracy",
            "encodings": {
                "x": {"field": "flip_entropy_bits", "type": "quantitative"},
                "y": {"field": "accuracy", "type": "quantitative", "format": "percent"},
                "series": {"field": "model", "type": "nominal"},
                "color": {"field": "partition", "type": "nominal"},
            },
        },
        {
            "id": "selective_prediction",
            "title": "② 选择性预测曲线（按翻转熵升序纳入）",
            "subtitle": "abstaining on the highest-entropy regions should raise accuracy",
            "type": "line",
            "dataset": "selective_prediction",
            "valueFormat": "percent",
            "encodings": {
                "x": {"field": "coverage", "type": "quantitative", "format": "percent"},
                "y": {"field": "accuracy", "type": "quantitative", "format": "percent"},
                "series": {"field": "model", "type": "nominal"},
            },
        },
    ]
    datasets = {
        "partition_accuracy": part_rows,
        "entropy_vs_accuracy": scatter_rows,
        "selective_prediction": selective_rows,
    }
    return {"charts": charts, "datasets": datasets}


def run_analysis(
    inputs: dict[str, str] | None = None,
    experiment_id: str = "exp-flip-identifiability-v0",
    store: Store | None = None,
    persist: bool = True,
) -> schema.Run:
    store = store or Store()
    inputs = inputs or DEFAULT_INPUTS

    per_model = []
    for model_name, rel in inputs.items():
        path = REPO_ROOT / rel
        per_model.append(analyze_model(model_name, path))

    verdict, reason = _verdict(per_model)
    cd = _charts_and_datasets(per_model, experiment_id)

    metrics: dict[str, schema.Metric] = {}
    for m in per_model:
        tag = m["model"].split("-")[0].lower()
        metrics[f"auroc_{tag}"] = schema.Metric(
            value=m["auroc_entropy_predicts_correct"], ci95=m["auroc_ci95"], unit="auroc"
        )
        metrics[f"selective_gain_{tag}"] = schema.Metric(
            value=m["selective_gain_at_50pct"], ci95=m["selective_gain_ci95"], unit="accuracy_delta"
        )

    run_id = "run-flip-identifiability-v0"
    artifacts = []
    if persist:
        per_region_path = runs_local_path(run_id, "per_region.json")
        per_region_path.parent.mkdir(parents=True, exist_ok=True)
        import json

        per_region_path.write_text(
            json.dumps(
                {m["model"]: m["regions"] for m in per_model}, ensure_ascii=False, indent=2
            ),
            encoding="utf-8",
        )
        artifacts.append(
            schema.Artifact(
                name="per_region",
                path=f"runs_local/{run_id}/per_region.json",
                tracked=False,
            )
        )

    run = schema.Run(
        id=run_id,
        experiment_id=experiment_id,
        title="Flip-as-uncertainty + identifiability partition (RGB-only, no training)",
        seed=SEED,
        command="python -m labkit.cli analyze flip-identifiability",
        exit_status="ok",
        metrics=metrics,
        conditions_metrics=[
            {
                "model": m["model"],
                "overall_region_accuracy": m["overall_region_accuracy"],
                "auroc": m["auroc_entropy_predicts_correct"],
                "auroc_ci95": m["auroc_ci95"],
                "selective_gain_at_50pct": m["selective_gain_at_50pct"],
                "selective_gain_ci95": m["selective_gain_ci95"],
                "partitions": m["partitions"],
            }
            for m in per_model
        ],
        charts=cd["charts"],
        datasets=cd["datasets"],
        verdict=verdict,
        verdict_reason=reason,
        artifacts=artifacts,
        notes=(
            "No training. Reuses scripts/compare_material_conditions.region_metrics and "
            "scripts/analyze_material_gate.bootstrap_ci (seed 20260719, region unit). "
            "① partition test is descriptive; the semantic-prior arm is the next step."
        ),
    )
    if persist:
        store.save(run)
        if store.exists("experiments", experiment_id):
            store.link_run_to_experiment(run_id, experiment_id)
    return run


def main() -> None:
    run = run_analysis()
    print(f"[labkit] analysis complete -> verdict = {run.verdict.upper()}")
    for cm in run.conditions_metrics:
        print(
            f"  {cm['model']:>24}: AUROC={cm['auroc']:.3f} CI{cm['auroc_ci95']}"
            f"  selective_gain@50%={cm['selective_gain_at_50pct']:+.3f} CI{cm['selective_gain_ci95']}"
        )
    print(f"  reason: {run.verdict_reason}")


if __name__ == "__main__":
    main()
