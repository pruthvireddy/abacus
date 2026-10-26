"""Draw explicitly saved values; no price data or research calculations."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", type=Path)
    args = parser.parse_args()
    stage = args.stage
    spec = json.loads((stage / "chart-spec.json").read_text())
    dest = stage / "figures"
    dest.mkdir(exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.labelcolor": "#284451", "text.color": "#173442",
        "axes.edgecolor": "#bacaca", "xtick.color": "#45616d", "ytick.color": "#45616d",
        "figure.facecolor": "#f8faf9", "axes.facecolor": "#f8faf9",
        "savefig.facecolor": "#f8faf9"})
    colors = ["#176B77", "#9D6426", "#5369A5", "#087B55", "#7B5697", "#B64840"]
    horizons = spec["horizons"]
    fig, ax = plt.subplots(figsize=(11.8, 6.3), layout="constrained")
    for series, color in zip(spec["close_series"], colors):
        ax.plot(range(len(horizons)), series["values"], marker="o", markersize=6,
                linewidth=2.4, color=color, label=series["label"])
    ax.axhline(0, color="#79909a", linewidth=1, linestyle="--")
    ax.set_xticks(range(len(horizons)), [f"H{h}" for h in horizons])
    ax.set_ylabel("Average signed close (% of entry price)")
    ax.set_xlabel("Following 15-minute chart candles · equally spaced horizon categories")
    ax.grid(axis="y", color="#dbe4e5", linewidth=.8)
    ax.set_title("Directional closes change with the holding horizon", loc="left", fontsize=18, weight="bold", pad=24)
    ax.legend(loc="lower left", ncols=3, frameon=False, fontsize=10)
    fig.savefig(dest / "signed-close-horizons.png", dpi=150, metadata={"Software": "Abacus study25 saved-value presentation"})
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11.8, 6.3), layout="constrained")
    positions = list(range(6))
    ax.barh([p+.18 for p in positions], spec["h5_mfe"], height=.32, color="#147C73", label="Average MFE · favorable excursion")
    ax.barh([p-.18 for p in positions], spec["h5_mae"], height=.32, color="#BD7350", label="Average MAE · adverse excursion")
    for p, mfe, mae in zip(positions, spec["h5_mfe"], spec["h5_mae"]):
        ax.text(mfe+.6, p+.18, f"{mfe:.2f}", va="center", fontsize=10)
        ax.text(mae+.6, p-.18, f"{mae:.2f}", va="center", fontsize=10)
    ax.set_yticks(positions, spec["labels"])
    ax.invert_yaxis()
    ax.set_xlim(0, 80)
    ax.set_xlabel("Each instrument's own outright futures ticks · not dollar values")
    ax.grid(axis="x", color="#dbe4e5", linewidth=.8)
    ax.set_axisbelow(True)
    ax.set_title("H5: favorable and adverse paths both matter", loc="left", fontsize=18, weight="bold", pad=24)
    ax.legend(loc="lower right", frameon=False, fontsize=10)
    fig.savefig(dest / "h5-excursions.png", dpi=150, metadata={"Software": "Abacus study25 saved-value presentation"})
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11.8, 6.8), layout="constrained")
    values = spec["category_values"]
    image = ax.imshow(values, cmap="BrBG", norm=TwoSlopeNorm(vmin=-.40, vcenter=0, vmax=.40), aspect="auto")
    ax.set_xticks(range(6), spec["category_labels"])
    ax.set_yticks(range(6), spec["labels"])
    for row in range(6):
        for col in range(6):
            value = values[row][col]
            ax.text(col, row, f"{value:+.3f}%", va="center", ha="center", fontsize=10,
                    color="white" if abs(value) > .26 else "#173442")
    ax.set_title("H5: the news category changes the picture", loc="left", fontsize=18, weight="bold", pad=24)
    ax.set_xlabel("Saved category summaries · CPI / employment / ISM / PMI: n=12; FOMC: n=8")
    ax.tick_params(axis="both", length=0, pad=10)
    bar = fig.colorbar(image, ax=ax, shrink=.8, pad=.025)
    bar.set_label("Average signed close (% of entry price)")
    fig.savefig(dest / "h5-news-categories.png", dpi=150, metadata={"Software": "Abacus study25 saved-value presentation"})
    plt.close(fig)
    (stage / "figure-environment.json").write_text(json.dumps({"python": sys.version,
        "executable": sys.executable, "matplotlib": matplotlib.__version__, "backend": matplotlib.get_backend(),
        "drawing_only": True, "inputs": "chart-spec.json", "percent_values": "Source percentage points unchanged on labelled percent axes."}, indent=2)+"\n")


if __name__ == "__main__":
    main()
