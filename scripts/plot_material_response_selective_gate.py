import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


LABELS = {
    "rgb_confidence_only": "RGB confidence",
    "response_router": "Response router",
    "shuffled_response_router": "Shuffled response",
    "random_score": "Random rejection",
}
COLORS = {
    "rgb_confidence_only": "#303030",
    "response_router": "#B14A3B",
    "shuffled_response_router": "#777777",
    "random_score": "#B9B9B9",
}
MARKERS = {
    "rgb_confidence_only": "o",
    "response_router": "s",
    "shuffled_response_router": "^",
    "random_score": "x",
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def mean_and_range(values):
    values = np.asarray(values, dtype=float)
    return values.mean(axis=0), values.min(axis=0), values.max(axis=0)


def main():
    args = parse_args()
    data = json.loads(args.summary.read_text(encoding="utf-8"))
    seeds = data["seed_results"]
    conditions = list(LABELS)
    coverages = list(seeds[0]["conditions"][conditions[0]]["fixed_coverage"])

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.5,
            "axes.labelsize": 8.5,
            "axes.titlesize": 9.5,
            "axes.linewidth": 0.7,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 7.5,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )
    figure, axes = plt.subplots(1, 3, figsize=(10.2, 3.15))

    ax = axes[0]
    for condition in conditions:
        curves = [
            seed["conditions"][condition]["risk_coverage"] for seed in seeds
        ]
        x = np.asarray(curves[0]["coverages"]) * 100
        mean, low, high = mean_and_range([curve["risks"] for curve in curves])
        ax.plot(
            x,
            mean * 100,
            color=COLORS[condition],
            marker=MARKERS[condition],
            markersize=3.2,
            linewidth=1.25,
            label=LABELS[condition],
        )
        if condition in {"rgb_confidence_only", "response_router"}:
            ax.fill_between(
                x, low * 100, high * 100, color=COLORS[condition], alpha=0.12, linewidth=0
            )
    ax.set_title("a  Risk-coverage profile", loc="left", fontweight="normal")
    ax.set_xlabel("Coverage (%)")
    ax.set_ylabel("Selective risk (%)")
    ax.set_xlim(49, 101)
    ax.grid(axis="y", color="#D8D8D8", linewidth=0.55)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, handlelength=2.2)

    ax = axes[1]
    positions = np.arange(len(coverages), dtype=float)
    offset = 0.12
    for index, coverage in enumerate(coverages):
        baseline = np.asarray(
            [
                seed["conditions"]["rgb_confidence_only"]["fixed_coverage"][coverage][
                    "selective_accuracy"
                ]
                for seed in seeds
            ]
        )
        response = np.asarray(
            [
                seed["conditions"]["response_router"]["fixed_coverage"][coverage][
                    "selective_accuracy"
                ]
                for seed in seeds
            ]
        )
        for first, second in zip(baseline, response):
            ax.plot(
                [positions[index] - offset, positions[index] + offset],
                [first * 100, second * 100],
                color="#B0B0B0",
                linewidth=0.8,
                zorder=1,
            )
        ax.scatter(
            np.full(len(baseline), positions[index] - offset),
            baseline * 100,
            facecolors="white",
            edgecolors=COLORS["rgb_confidence_only"],
            marker=MARKERS["rgb_confidence_only"],
            s=25,
            linewidths=1.0,
            zorder=2,
        )
        ax.scatter(
            np.full(len(response), positions[index] + offset),
            response * 100,
            color=COLORS["response_router"],
            marker=MARKERS["response_router"],
            s=22,
            zorder=3,
        )
        delta = (response - baseline).mean() * 100
        ax.text(
            positions[index],
            max(np.max(baseline), np.max(response)) * 100 + 0.65,
            f"mean delta {delta:+.2f} pp",
            ha="center",
            va="bottom",
            fontsize=7.2,
        )
    ax.set_title("b  Fixed-coverage accuracy", loc="left", fontweight="normal")
    ax.set_ylabel("Selective accuracy (%)")
    ax.set_xticks(positions, [f"{float(value) * 100:.0f}% coverage" for value in coverages])
    ax.set_ylim(67, 78)
    ax.grid(axis="y", color="#D8D8D8", linewidth=0.55)
    ax.spines[["top", "right"]].set_visible(False)

    ax = axes[2]
    metric_names = [("auroc", "AUROC"), ("average_precision", "AUPRC")]
    y = np.arange(len(metric_names), dtype=float)
    for condition_index, condition in enumerate(conditions):
        values = np.asarray(
            [
                [
                    seed["conditions"][condition]["error_detection"][metric]
                    for seed in seeds
                ]
                for metric, _ in metric_names
            ]
        )
        mean = values.mean(axis=1)
        low = mean - values.min(axis=1)
        high = values.max(axis=1) - mean
        shift = (condition_index - 1.5) * 0.075
        ax.errorbar(
            mean,
            y + shift,
            xerr=np.vstack([low, high]),
            fmt=MARKERS[condition],
            color=COLORS[condition],
            markersize=4,
            linewidth=1,
            capsize=2,
            label=LABELS[condition],
        )
    ax.axvline(0.5, color="#A8A8A8", linewidth=0.7, linestyle="--")
    ax.set_title("c  RGB error detection", loc="left", fontweight="normal")
    ax.set_xlabel("Score (mean and seed range)")
    ax.set_yticks(y, [label for _, label in metric_names])
    ax.set_xlim(0.27, 0.71)
    ax.grid(axis="x", color="#D8D8D8", linewidth=0.55)
    ax.spines[["top", "right"]].set_visible(False)

    figure.suptitle(
        "Cross-light response does not improve selective rejection",
        x=0.07,
        y=1.01,
        ha="left",
        fontsize=11,
        fontweight="normal",
    )
    figure.text(
        0.07,
        -0.025,
        "30 scene-grouped units; 66 regions; three nested-CV seeds. Bands/error bars show seed range.",
        ha="left",
        fontsize=7.5,
        color="#4A4A4A",
    )
    figure.tight_layout(w_pad=2.0)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "pdf"):
        figure.savefig(
            args.output_dir / f"material-response-selective-gate.{suffix}",
            dpi=320 if suffix == "png" else None,
            bbox_inches="tight",
            facecolor="white",
        )
    plt.close(figure)


if __name__ == "__main__":
    main()
