"""Aggregate per-scene HDR/light-probe radiometry audits into one committable summary.

Reads the per-scene JSON produced by ``scripts/audit_hdr_probe_radiometry.py``
and emits scene-level aggregates only. Per-direction records, per-region masks
and the downloaded archives stay out of Git.

Example:
    python scripts/summarize_hdr_probe_audit.py \
        --input-glob 'transfer_staging/hdr_probe_audit_v0/radiometry_*.json' \
        --output results/quantitative/hdr_light_probe_oracle_audit_v0/summary.json
"""

import argparse
import glob
import json
from pathlib import Path

import numpy as np


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-glob", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--experiment-id", default="hdr_light_probe_oracle_audit_v0")
    parser.add_argument("--gray-probe-coupling-min", type=float, default=0.5)
    parser.add_argument("--discriminability-gain-min", type=float, default=1.10)
    parser.add_argument("--scene-majority-fraction", type=float, default=0.5)
    return parser.parse_args()


def scene_record(payload):
    directions = payload["directions"]
    scene_means = np.array([d["scene_mean"] for d in directions])
    gray_means = np.array([d["gray_probe"]["mean_luminance"] for d in directions])
    chrome_means = np.array([d["chrome_probe"]["mean_luminance"] for d in directions])

    raw = payload["discriminability"]["raw_linear_log"]
    normalized = payload["discriminability"]["gray_probe_normalized_log"]

    record = {
        "scene": payload["scene"],
        "num_regions": payload["num_regions"],
        "num_directions": payload["num_directions"],
        "scene_mean_dynamic_range": float(scene_means.max() / scene_means.min()),
        "gray_probe_dynamic_range": float(gray_means.max() / gray_means.min()),
        "chrome_probe_dynamic_range": float(chrome_means.max() / chrome_means.min()),
        "pearson_scene_vs_gray_probe": payload["radiometric_coupling"]["pearson_scene_vs_gray_probe"],
        "pearson_scene_vs_chrome_probe": payload["radiometric_coupling"]["pearson_scene_vs_chrome_probe"],
        "within_region_variance_raw": raw["within_region_variance_mean"],
        "within_region_variance_normalized": normalized["within_region_variance_mean"],
        "between_over_within_raw": raw["between_over_within_mean"],
        "between_over_within_normalized": normalized["between_over_within_mean"],
        "discriminability_gain": payload["discriminability"]["normalized_over_raw_ratio"],
    }
    if payload.get("ldr_clipping"):
        record["ldr_saturated_any_channel_fraction_mean"] = payload["ldr_clipping"][
            "saturated_any_channel_fraction_mean"
        ]
        record["ldr_saturated_any_channel_fraction_max"] = payload["ldr_clipping"][
            "saturated_any_channel_fraction_max"
        ]
        record["linear_value_at_jpeg_clip_mean"] = payload["ldr_clipping"]["linear_value_at_jpeg_clip_mean"]
        record["linear_max_over_clip_mean"] = payload["ldr_clipping"]["linear_max_over_clip_mean"]
    return record


def median_of(records, key):
    values = [r[key] for r in records if r.get(key) is not None]
    return float(np.median(values)) if values else None


def main():
    args = parse_args()
    paths = sorted(Path(p) for p in glob.glob(args.input_glob))
    if not paths:
        raise SystemExit(f"no audit files matched {args.input_glob}")

    records = [scene_record(json.loads(path.read_text(encoding="utf-8"))) for path in paths]
    records.sort(key=lambda r: r["scene"])

    gains = [r["discriminability_gain"] for r in records]
    couplings = [r["pearson_scene_vs_gray_probe"] for r in records]
    scenes_with_gain = sum(1 for g in gains if g >= args.discriminability_gain_min)
    scenes_with_coupling = sum(1 for c in couplings if c >= args.gray_probe_coupling_min)
    required = args.scene_majority_fraction * len(records)

    gate = {
        "gray_probe_coupling_min": args.gray_probe_coupling_min,
        "discriminability_gain_min": args.discriminability_gain_min,
        "scene_majority_fraction": args.scene_majority_fraction,
        "scenes_meeting_coupling": scenes_with_coupling,
        "scenes_meeting_gain": scenes_with_gain,
        "scenes_required": required,
        "coupling_passed": scenes_with_coupling > required,
        "gain_passed": scenes_with_gain > required,
    }
    gate["verdict"] = "Go" if gate["coupling_passed"] and gate["gain_passed"] else "No-Go"

    summary = {
        "experiment_id": args.experiment_id,
        "status": "Completed training-free audit gate",
        "verdict": gate["verdict"],
        "dataset": "Multi-Illumination (CC BY 4.0), official per-scene mip2 EXR + 256px light probes",
        "scene_count": len(records),
        "unit": "scene",
        "trained_parameters": 0,
        "aggregates": {
            "median_scene_mean_dynamic_range": median_of(records, "scene_mean_dynamic_range"),
            "median_gray_probe_dynamic_range": median_of(records, "gray_probe_dynamic_range"),
            "median_chrome_probe_dynamic_range": median_of(records, "chrome_probe_dynamic_range"),
            "median_pearson_scene_vs_gray_probe": median_of(records, "pearson_scene_vs_gray_probe"),
            "median_pearson_scene_vs_chrome_probe": median_of(records, "pearson_scene_vs_chrome_probe"),
            "median_between_over_within_raw": median_of(records, "between_over_within_raw"),
            "median_between_over_within_normalized": median_of(records, "between_over_within_normalized"),
            "median_discriminability_gain": median_of(records, "discriminability_gain"),
            "median_ldr_saturated_any_channel_fraction": median_of(records, "ldr_saturated_any_channel_fraction_mean"),
            "max_ldr_saturated_any_channel_fraction": max(
                (r["ldr_saturated_any_channel_fraction_max"] for r in records if "ldr_saturated_any_channel_fraction_max" in r),
                default=None,
            ),
            "median_linear_max_over_clip": median_of(records, "linear_max_over_clip_mean"),
        },
        "gate": gate,
        "caveats": [
            "Thresholds were chosen after inspecting the measurements; this is a feasibility audit, not a pre-registered confirmatory gate.",
            "The load-bearing evidence is the raw measurement, not the threshold verdict: the gray probe spans a far narrower range than the scene it is meant to normalize, and normalization does not reduce within-region spread.",
            "Scenes are drawn from the official train pool and were selected for room-type diversity, not at random.",
            "The audit uses official material masks as region definitions; no classifier is fitted and no label beyond the mask index is used.",
        ],
        "scenes": records,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "scenes"}, indent=2))


if __name__ == "__main__":
    main()
