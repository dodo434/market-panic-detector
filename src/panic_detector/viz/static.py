"""Static and animated figures for the Market Panic Detector."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

from panic_detector.data.sectors import SECTOR_COLORS, SECTOR_MAP
from panic_detector.networks.threshold import threshold_edges
from panic_detector.networks.weighted import all_pairs
from panic_detector.networks.mst import tree_edges


def build_network(corr: pd.DataFrame, kind: str, threshold: float) -> nx.Graph:
    matrix = corr.to_numpy()
    pairs = all_pairs(len(matrix))
    if kind == "mst":
        pairs = tree_edges(matrix)
    elif kind == "threshold":
        pairs = threshold_edges(matrix, pairs, threshold)
    elif kind != "weighted":
        raise ValueError("Choose threshold, mst or weighted.")
    graph = nx.Graph()
    graph.add_nodes_from(corr.columns)
    graph.add_weighted_edges_from(
        (corr.columns[i], corr.columns[j], matrix[i, j]) for i, j in pairs
    )
    return graph


STRESS_PERIODS = [
    ("COVID crash", "2020-02-15", "2020-04-15"),
    ("2022 selloff", "2022-01-01", "2022-10-31"),
]


def draw_network(
    ax,
    corr: pd.DataFrame,
    layout: dict,
    kind: str,
    threshold: float,
) -> None:
    graph = build_network(corr, kind=kind, threshold=threshold)
    node_colors = [
        SECTOR_COLORS.get(SECTOR_MAP.get(node, "Other"), "#7F7F7F") for node in graph.nodes()
    ]

    if kind == "weighted":
        edge_widths = [
            max(0.15, 2.5 * max(0.0, float(graph[u][v]["weight"]))) for u, v in graph.edges()
        ]
    elif kind == "mst":
        edge_widths = [1.4 for _ in graph.edges()]
    else:
        edge_widths = [0.8 + 2.5 * float(graph[u][v]["weight"]) for u, v in graph.edges()]

    nx.draw_networkx_edges(graph, layout, ax=ax, width=edge_widths, alpha=0.45)
    nx.draw_networkx_nodes(
        graph,
        layout,
        ax=ax,
        node_size=95,
        node_color=node_colors,
        edgecolors="white",
        linewidths=0.4,
    )
    nx.draw_networkx_labels(graph, layout, ax=ax, font_size=5)
    ax.set_axis_off()


def static_comparison(
    calm_corr: pd.DataFrame,
    crash_corr: pd.DataFrame,
    layout: dict,
    calm_date: pd.Timestamp,
    crash_date: pd.Timestamp,
    network_kind: str,
    threshold: float,
    output_dir: str | Path,
) -> Path:
    output_dir = Path(output_dir)
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    draw_network(axes[0], calm_corr, layout, network_kind, threshold)
    draw_network(axes[1], crash_corr, layout, network_kind, threshold)
    axes[0].set_title(f"Calm period: {calm_date.date()}")
    axes[1].set_title(f"Crash period: {crash_date.date()}")

    handles = [
        plt.Line2D(
            [0], [0], marker="o", color="w", markerfacecolor=color, markersize=8, label=sector
        )
        for sector, color in SECTOR_COLORS.items()
    ]
    fig.legend(handles=handles, loc="lower center", ncol=5, frameon=False, fontsize=8)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    path = output_dir / "static_calm_vs_crash.png"
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_metrics(metrics: pd.DataFrame, output_dir: str | Path) -> Path:
    output_dir = Path(output_dir)
    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
    axes[0].plot(metrics.index, metrics["average_correlation"], color="#4C78A8", lw=1.2)
    axes[0].set_ylabel("Average pairwise correlation")
    axes[0].grid(alpha=0.2)
    axes[1].plot(
        metrics.index, metrics["top_eigenvalue"], color="#E45756", lw=1.2, label="Top eigenvalue"
    )
    axes[1].plot(
        metrics.index,
        metrics["mp_upper_bound"],
        color="#777777",
        ls="--",
        lw=1.0,
        label="MP upper bound",
    )
    axes[1].set_ylabel("Top eigenvalue")
    axes[1].set_xlabel("Date")
    axes[1].legend(loc="upper left")
    axes[1].grid(alpha=0.2)
    shade_stress_periods(axes)
    fig.tight_layout()
    path = output_dir / "metrics.png"
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return path


def shade_stress_periods(axes) -> None:
    for name, start, end in STRESS_PERIODS:
        for ax in axes:
            ax.axvspan(pd.Timestamp(start), pd.Timestamp(end), color="#D62728", alpha=0.10)


def animate(
    metrics: pd.DataFrame,
    matrices: dict[tuple[pd.Timestamp, pd.Timestamp], pd.DataFrame],
    layout: dict,
    network_kind: str,
    threshold: float,
    output_dir: str | Path,
    stride: int = 5,
) -> Path:
    """Create an animated network and moving time-series marker."""
    try:
        import imageio.v2 as imageio
    except ImportError as exc:
        raise RuntimeError("imageio is required for GIF export") from exc

    output_dir = Path(output_dir)
    gif_path = output_dir / "market_panic_detector.gif"
    frames = []
    sample_dates = metrics.index[::stride]
    for date in sample_dates:
        window_match = next(
            ((start, end, corr) for (start, end), corr in matrices.items() if end == date),
            None,
        )
        if window_match is None:
            continue
        start, end, corr = window_match
        fig = plt.figure(figsize=(14, 6), constrained_layout=True)
        grid = fig.add_gridspec(2, 2, width_ratios=(1.15, 1.0))
        ax_net = fig.add_subplot(grid[:, 0])
        ax_avg = fig.add_subplot(grid[0, 1])
        ax_top = fig.add_subplot(grid[1, 1])
        draw_network(ax_net, corr, layout, network_kind, threshold)
        ax_net.set_title(
            f"{network_kind.title()} network | {date.date()} | Window {start.date()}–{end.date()}"
        )

        ax_avg.plot(metrics.index, metrics["average_correlation"], color="#4C78A8", lw=1.0)
        ax_avg.axvline(date, color="#222222", lw=1.2)
        ax_avg.scatter(
            [date], [metrics.loc[date, "average_correlation"]], color="#222222", s=25, zorder=3
        )
        ax_avg.set_ylabel("Average correlation")
        ax_avg.grid(alpha=0.2)

        ax_top.plot(
            metrics.index,
            metrics["top_eigenvalue"],
            color="#E45756",
            lw=1.0,
            label="Top eigenvalue",
        )
        ax_top.plot(
            metrics.index,
            metrics["mp_upper_bound"],
            color="#777777",
            ls="--",
            lw=0.8,
            label="MP bound",
        )
        ax_top.axvline(date, color="#222222", lw=1.2)
        ax_top.scatter(
            [date], [metrics.loc[date, "top_eigenvalue"]], color="#222222", s=25, zorder=3
        )
        ax_top.set_ylabel("Top eigenvalue")
        ax_top.set_xlabel("Date")
        ax_top.legend(loc="upper left", fontsize=8)
        ax_top.grid(alpha=0.2)
        shade_stress_periods([ax_avg, ax_top])

        frame_path = output_dir / "_frame.png"
        fig.savefig(frame_path, dpi=100)
        plt.close(fig)
        frames.append(imageio.imread(frame_path))
    if not frames:
        raise RuntimeError("No animation frames were generated.")
    imageio.mimsave(gif_path, [np.asarray(frame) for frame in frames], duration=0.12, loop=0)
    (output_dir / "_frame.png").unlink(missing_ok=True)
    return gif_path
