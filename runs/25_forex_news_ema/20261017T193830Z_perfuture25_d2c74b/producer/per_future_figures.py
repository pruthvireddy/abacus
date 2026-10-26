"""Render only the explicitly saved, hash-mapped per-future chart inputs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm


COLORS = {"combined": "#147b78", "us_only": "#cf8651", "local_only": "#526eb4"}
LABELS = {"combined": "U.S. + domestic", "us_only": "U.S. only", "local_only": "Domestic only"}


def render(directory: Path) -> None:
    spec = json.loads((directory / "chart-spec.json").read_text())
    dest = directory / "figures"
    dest.mkdir(exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.labelcolor": "#294957", "text.color": "#183b48", "axes.edgecolor": "#c4d2d6",
        "xtick.color": "#48626b", "ytick.color": "#48626b",
        "figure.facecolor": "#f8faf9", "axes.facecolor": "#f8faf9", "savefig.facecolor": "#f8faf9"})
    symbol = spec["symbol"]
    fig, ax = plt.subplots(figsize=(12, 6.4), layout="constrained")
    for mode, series in spec["horizons"].items():
        ax.plot(range(len(series)), [r["close"] for r in series], marker="o", linewidth=2.5,
                color=COLORS[mode], label=LABELS[mode])
    ax.axhline(0, color="#82949b", linewidth=1, linestyle="--")
    ax.set_xticks(range(5), ["H5", "H10", "H15", "H50", "H100"])
    ax.set_ylabel("Average directional close (% of entry price)")
    ax.set_xlabel("Following 15-minute chart candles · horizons shown as categories")
    ax.grid(axis="y", color="#dce5e6", linewidth=.8)
    ax.set_title(f"{symbol} · how the horizon changes the close", loc="left", fontsize=19, weight="bold", pad=23)
    ax.legend(loc="best", frameon=False, ncols=3)
    fig.savefig(dest / "horizon-comparison.png", dpi=145)
    plt.close(fig)

    types = spec["types"]
    values = [[r["mfe"], r["mae"], r["close"]] for r in types]
    fig, axes = plt.subplots(1, 2, figsize=(12, max(6.5, len(types) * .43)),
                             gridspec_kw={"width_ratios": [2, 1.12]}, layout="constrained")
    positions = list(range(len(types)))
    axes[0].barh([p-.16 for p in positions], [r["mfe"] for r in types], height=.29, color="#147b78", label="Average MFE")
    axes[0].barh([p+.16 for p in positions], [r["mae"] for r in types], height=.29, color="#cf8651", label="Average MAE")
    axes[0].set_yticks(positions, [r["type"] for r in types], fontsize=9)
    axes[0].invert_yaxis()
    axes[0].set_xlabel("Own-contract ticks · favorable and adverse excursions")
    axes[0].grid(axis="x", color="#dce5e6", linewidth=.7)
    axes[0].set_axisbelow(True)
    axes[0].legend(frameon=False, ncols=2, fontsize=9, loc="lower right")
    bars = axes[1].barh(positions, [r["close"] for r in types], color=["#147b78" if r["close"] >= 0 else "#af5d56" for r in types], height=.55)
    axes[1].axvline(0, color="#82949b", linewidth=1)
    axes[1].set_yticks(positions, [f"N={r['n']}" for r in types], fontsize=9)
    axes[1].invert_yaxis()
    axes[1].bar_label(bars, fmt="%+.1f", padding=4, fontsize=8)
    lo, hi = axes[1].get_xlim()
    axes[1].set_xlim(lo-(hi-lo)*.2, hi+(hi-lo)*.2)
    axes[1].set_xlabel("Average directional close · ticks")
    axes[1].grid(axis="x", color="#dce5e6", linewidth=.7)
    axes[1].set_axisbelow(True)
    fig.suptitle(f"{symbol} · H5 news types, with their sample sizes", fontsize=19, weight="bold", ha="left", x=.02)
    fig.savefig(dest / "news-type-excursions.png", dpi=145)
    plt.close(fig)

    months = spec["months"]
    fig, axes = plt.subplots(2, 1, figsize=(12, 7.3), gridspec_kw={"height_ratios": [2.1, 1]}, layout="constrained", sharex=True)
    x = list(range(len(months)))
    bars = axes[0].bar(x, [r["close"] for r in months], color=["#147b78" if r["close"] >= 0 else "#af5d56" for r in months], width=.72)
    axes[0].bar_label(bars, fmt="%+.3f", padding=3, fontsize=8)
    axes[0].axhline(0, color="#82949b", linewidth=1)
    axes[0].set_ylabel("Average directional close\n(% of entry price)")
    axes[0].margins(y=.25)
    axes[0].grid(axis="y", color="#dce5e6", linewidth=.7)
    axes[0].set_axisbelow(True)
    axes[0].set_title(f"{symbol} · H5 monthly results and their denominators", loc="left", fontsize=19, weight="bold", pad=20)
    bars = axes[1].bar(x, [r["n"] for r in months], color="#899fa9", width=.72)
    axes[1].bar_label(bars, padding=3, fontsize=9)
    axes[1].set_ylabel("Completed N")
    axes[1].set_xticks(x, [r["period"] for r in months], rotation=45, ha="right")
    axes[1].set_xlabel("Entry month · America/Chicago · combined calendar")
    axes[1].margins(y=.35)
    fig.savefig(dest / "monthly-direction.png", dpi=145)
    plt.close(fig)
    (directory / "figure-environment.json").write_text(json.dumps({"python": sys.version,
        "executable": sys.executable, "matplotlib": matplotlib.__version__,
        "backend": matplotlib.get_backend(), "drawing_only": True,
        "inputs": "chart-spec.json", "units": "Source ticks and percentage points, unchanged."}, indent=2)+"\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    render(parser.parse_args().directory)
