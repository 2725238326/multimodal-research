import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ORDER = [
    "single_rgb",
    "multi_light_mean",
    "multi_light_mean_variance",
    "pairwise_response",
    "rgb_albedo_concat",
    "rgb_albedo_residual",
    "shuffled_light_pair",
    "wrong_region_albedo",
    "random_residual",
    "equal_parameter_branch",
]
LABELS = {
    "single_rgb": "Single RGB",
    "multi_light_mean": "Multi-light mean",
    "multi_light_mean_variance": "Mean + variance",
    "pairwise_response": "Pairwise response",
    "rgb_albedo_concat": "RGB + albedo",
    "rgb_albedo_residual": "RGB + residual",
    "shuffled_light_pair": "Shuffled response",
    "wrong_region_albedo": "Wrong-region albedo",
    "random_residual": "Random residual",
    "equal_parameter_branch": "Equal-capacity RGB",
}
COLORS = {
    "single_rgb": "#2F2F2F",
    "multi_light_mean": "#5E7D8A",
    "multi_light_mean_variance": "#466A7F",
    "pairwise_response": "#1F4E79",
    "rgb_albedo_concat": "#8A6D3B",
    "rgb_albedo_residual": "#A07845",
    "shuffled_light_pair": "#9A9A9A",
    "wrong_region_albedo": "#787878",
    "random_residual": "#B0B0B0",
    "equal_parameter_branch": "#4D4D4D",
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-prefix", type=Path, required=True)
    return parser.parse_args()


def metric_arrays(result, metric):
    means = np.asarray(
        [result["conditions"][condition][metric]["mean"] * 100 for condition in ORDER]
    )
    lows = np.asarray(
        [result["conditions"][condition][metric]["min"] * 100 for condition in ORDER]
    )
    highs = np.asarray(
        [result["conditions"][condition][metric]["max"] * 100 for condition in ORDER]
    )
    return means, lows, highs


def condition_panel(ax, result, metric, title, x_label):
    means, lows, highs = metric_arrays(result, metric)
    y = np.arange(len(ORDER))[::-1]
    for index, condition in enumerate(ORDER):
        position = y[index]
        ax.plot(
            [lows[index], highs[index]],
            [position, position],
            color=COLORS[condition],
            linewidth=1.2,
            solid_capstyle="round",
        )
        ax.scatter(
            means[index],
            position,
            s=34,
            color=COLORS[condition],
            edgecolor="white",
            linewidth=0.6,
            zorder=3,
        )
        ax.text(
            means[index] + 1.1,
            position,
            f"{means[index]:.1f}",
            va="center",
            fontsize=8,
            color="#262626",
        )
    baseline = result["conditions"]["single_rgb"][metric]["mean"] * 100
    ax.axvline(baseline, color="#2F2F2F", linewidth=0.8, linestyle=(0, (3, 3)))
    ax.set_yticks(y, [LABELS[condition] for condition in ORDER])
    ax.set_xlabel(x_label)
    ax.set_title(title, loc="left", fontweight="bold")
    ax.grid(axis="x", color="#D7D7D7", linewidth=0.55)
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)


def delta_panel(ax, result):
    comparison = result["comparisons"]["pairwise_response"]
    seeds = result["seeds"]
    y_accuracy = np.arange(len(seeds))[::-1] + 0.18
    y_flip = np.arange(len(seeds))[::-1] - 0.18
    for index, seed in enumerate(seeds):
        accuracy = comparison["region_accuracy_delta_vs_single_rgb"][index]
        flip = comparison["region_flip_delta_vs_single_rgb"][index]
        for stat, y, color, marker in (
            (accuracy, y_accuracy[index], "#A23B3B", "o"),
            (flip, y_flip[index], "#1F4E79", "s"),
        ):
            mean = stat["mean_delta"] * 100
            low = stat["ci_low"] * 100
            high = stat["ci_high"] * 100
            ax.plot([low, high], [y, y], color=color, linewidth=1.35)
            ax.scatter(mean, y, s=30, color=color, marker=marker, zorder=3)
    ax.axvline(0, color="#333333", linewidth=0.8)
    ax.set_yticks(np.arange(len(seeds))[::-1], [str(seed) for seed in seeds])
    ax.set_xlabel("Delta vs single RGB (percentage points)")
    ax.set_title("C  Paired scene-bootstrap effects", loc="left", fontweight="bold")
    ax.grid(axis="x", color="#D7D7D7", linewidth=0.55)
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.scatter([], [], color="#A23B3B", marker="o", label="Region accuracy")
    ax.scatter([], [], color="#1F4E79", marker="s", label="Region flip rate")
    ax.legend(frameon=False, loc="lower left", fontsize=8)


def main():
    args = parse_args()
    result = json.loads(args.input.read_text(encoding="utf-8"))
    plt.rcParams.update(
        {
            "font.family": "DejaVu Serif",
            "font.size": 9,
            "axes.labelcolor": "#262626",
            "axes.edgecolor": "#5A5A5A",
            "xtick.color": "#333333",
            "ytick.color": "#333333",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )
    figure = plt.figure(figsize=(12.2, 7.4))
    grid = figure.add_gridspec(1, 3, width_ratios=[1.05, 1.05, 1.0])
    accuracy_ax = figure.add_subplot(grid[0, 0])
    flip_ax = figure.add_subplot(grid[0, 1])
    delta_ax = figure.add_subplot(grid[0, 2])
    condition_panel(
        accuracy_ax,
        result,
        "mean_region_accuracy",
        "A  Held-out region accuracy",
        "Accuracy (%)",
    )
    condition_panel(
        flip_ax,
        result,
        "region_flip_rate",
        "B  Cross-light prediction flips",
        "Regions with a flip (%)",
    )
    flip_ax.set_yticklabels([])
    delta_panel(delta_ax, result)
    figure.suptitle(
        "Frozen SigLIP2 material-response gate: discrimination-stability trade-off",
        fontsize=12,
        fontweight="bold",
        x=0.01,
        ha="left",
    )
    figure.text(
        0.01,
        0.025,
        "330 samples, 66 regions, 30 scenes; five scene-grouped folds; three seeds. "
        "Dots show seed means or paired deltas; horizontal intervals show seed ranges (A-B) "
        "or 95% scene-bootstrap confidence intervals (C).",
        fontsize=7.6,
        color="#444444",
    )
    figure.subplots_adjust(left=0.17, right=0.99, bottom=0.16, top=0.88, wspace=0.12)
    args.output_prefix.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output_prefix.with_suffix(".png"), dpi=300, bbox_inches="tight")
    figure.savefig(args.output_prefix.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(figure)


if __name__ == "__main__":
    main()
