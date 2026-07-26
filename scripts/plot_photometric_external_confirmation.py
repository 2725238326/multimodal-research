import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


CHARCOAL = "#303030"
VERMILION = "#B14A3B"
MID_GRAY = "#777777"
LIGHT_GRAY = "#B9B9B9"
GRID = "#D8D8D8"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--development-summary", type=Path, required=True)
    parser.add_argument("--external-summary", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def condition_values(data, condition):
    return np.asarray(
        [result["conditions"][condition]["region_accuracy"] for result in data["seed_results"]]
    ) * 100


def dot_range(ax, y, values, color, marker, label):
    mean = float(np.mean(values))
    ax.plot([float(np.min(values)), float(np.max(values))], [y, y], color=color, linewidth=1.1)
    ax.scatter(mean, y, color=color, marker=marker, s=30, zorder=3)
    ax.text(mean + 1.6, y, f"{mean:.1f}", va="center", ha="left", fontsize=7.5)
    ax.text(0.0, y, label, va="center", ha="left", fontsize=8)


def main():
    args = parse_args()
    development = json.loads(args.development_summary.read_text(encoding="utf-8"))
    external = json.loads(args.external_summary.read_text(encoding="utf-8"))
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.5,
            "axes.labelsize": 8.5,
            "axes.titlesize": 9.5,
            "axes.linewidth": 0.7,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )
    figure, axes = plt.subplots(1, 3, figsize=(10.5, 3.35))

    ax = axes[0]
    dev_conditions = [
        ("siglip_region_mean", "SigLIP region mean", CHARCOAL, "o"),
        ("siglip_plus_uncensored", "Uncensored trajectory", MID_GRAY, "^"),
        ("siglip_plus_censored", "Censor-aware trajectory", VERMILION, "s"),
        ("siglip_plus_exposure_only", "Exposure only", LIGHT_GRAY, "x"),
    ]
    for row, (condition, label, color, marker) in enumerate(dev_conditions[::-1]):
        dot_range(ax, row, condition_values(development, condition), color, marker, label)
    ax.set_title("a  Development scene CV", loc="left", fontweight="normal")
    ax.set_xlabel("Region accuracy (%)")
    ax.set_xlim(0, 75)
    ax.set_yticks([])
    ax.grid(axis="x", color=GRID, linewidth=0.55)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.text(73.5, 2.62, "+5.6 pp vs region mean", color=VERMILION, ha="right", fontsize=7.5)

    ax = axes[1]
    ext_conditions = [
        ("siglip_sample_majority", "RGB sample majority", CHARCOAL, "o"),
        ("siglip_region_mean", "SigLIP region mean", MID_GRAY, "o"),
        ("siglip_plus_censored", "Censor-aware trajectory", VERMILION, "s"),
        ("siglip_plus_exposure_only", "Exposure only", LIGHT_GRAY, "x"),
        ("siglip_plus_shuffled", "Shuffled trajectory", MID_GRAY, "^"),
        ("photometric_censored_only", "Photometric only", LIGHT_GRAY, "d"),
    ]
    for row, (condition, label, color, marker) in enumerate(ext_conditions[::-1]):
        dot_range(ax, row, condition_values(external, condition), color, marker, label)
    ax.set_title("b  Official external test", loc="left", fontweight="normal")
    ax.set_xlabel("Region accuracy (%)")
    ax.set_xlim(0, 50)
    ax.set_yticks([])
    ax.grid(axis="x", color=GRID, linewidth=0.55)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.text(48.8, 3.35, "primary -12.5 pp", color=VERMILION, ha="right", fontsize=7.5)

    ax = axes[2]
    deltas = []
    lows = []
    highs = []
    seed_labels = []
    key = "siglip_plus_censored_vs_siglip_sample_majority"
    for result in external["seed_results"]:
        comparison = result["comparisons"][key]
        delta = comparison["pooled_region_accuracy_delta"] * 100
        deltas.append(delta)
        lows.append(comparison["ci_low"] * 100)
        highs.append(comparison["ci_high"] * 100)
        seed_labels.append(str(result["seed"]))
    y = np.arange(len(deltas))[::-1]
    for row, delta, low, high, seed in zip(y, deltas, lows, highs, seed_labels):
        ax.plot([low, high], [row, row], color=VERMILION, linewidth=1.2)
        ax.scatter(delta, row, color=VERMILION, marker="s", s=28, zorder=3)
        ax.text(high + 0.7, row, f"{delta:+.1f} pp", va="center", fontsize=7.5)
    ax.axvline(0, color=MID_GRAY, linewidth=0.8, linestyle="--")
    ax.set_yticks(y, seed_labels)
    ax.set_xlim(-27, 4)
    ax.set_xlabel("Primary minus RGB majority (pp)")
    ax.set_title("c  Test-scene bootstrap", loc="left", fontweight="normal")
    ax.grid(axis="x", color=GRID, linewidth=0.55)
    ax.spines[["top", "right"]].set_visible(False)

    figure.suptitle(
        "Photometric trajectory gain does not transfer to the official test split",
        x=0.055,
        y=1.015,
        ha="left",
        fontsize=11,
        fontweight="normal",
    )
    figure.text(
        0.055,
        -0.015,
        "Development: 66 regions / 30 scenes. External test: 80 regions / 30 untouched scenes; points show seed means and ranges.",
        ha="left",
        fontsize=7.5,
        color="#4A4A4A",
    )
    figure.tight_layout(w_pad=2.2)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "pdf"):
        figure.savefig(
            args.output_dir / f"photometric-external-confirmation.{suffix}",
            dpi=320 if suffix == "png" else None,
            bbox_inches="tight",
            facecolor="white",
        )
    plt.close(figure)


if __name__ == "__main__":
    main()
