"""Pinned study inputs, figure output, and small numerical primitives."""
from __future__ import annotations

from datetime import date
import json
from math import sqrt
from pathlib import Path

import numpy as np
import pandas as pd

from abacus_bhishma.daily_facts import PRICE_SCALE, window_bounds
from abacus_bhishma.daily_facts_loader import load_daily_facts
from abacus_bhishma.nq_opening_range import FACTS_MANIFEST, PINS, load_opening_range, open_nq_minutes, yearly_minutes
from abacus_bhishma.paths import resolve_publication_root


def load_study(workspace, pin):
    root = resolve_publication_root(workspace=workspace)
    facts = load_opening_range(root, manifest_sha256=pin["feature_manifest_sha256"])
    source = open_nq_minutes(root)
    overlap = {row["session_date"]: row for row in load_daily_facts(
        root, manifest_path=FACTS_MANIFEST, manifest_sha256=PINS[FACTS_MANIFEST], assets=("NQ",),
        columns=["session_date", "rth_high", "rth_low", "rth_open", "first60_high", "first60_low"],
    ).to_pylist()}
    rows, paths, overlap_checks = facts.to_pylist(), {}, 0
    for year in sorted({row["session_date"].year for row in rows}):
        minutes, _ = yearly_minutes(source, year)
        for row in rows:
            day = row["session_date"]
            if day.year != year or row["rth_status"] != "complete":
                continue
            arrays = minutes[day]
            begin, end = (int(when.timestamp()) * 10**9 for when in window_bounds("NQ", day)["rth"])
            left, right = arrays["ts_event"].searchsorted([begin, end])
            selected = slice(left, right)
            if (not np.array_equal(arrays["ts_event"][selected], np.arange(begin, end, 60 * 10**9))
                    or not (arrays["instrument_id"][selected] == row["contract_id"]).all()
                    or not (arrays["roll_id"][selected] == row["roll_id"]).all()
                    or not (arrays["raw_symbol"][selected] == row["contract_symbol"]).all()
                    or not arrays["valid"][selected].all()):
                raise ValueError(f"invalid pinned RTH path for {day}")
            path = np.column_stack([arrays[key][selected] for key in ("open", "high", "low")]) / PRICE_SCALE
            if path[0, 0] != float(row["rth_open"]):
                raise ValueError(f"opening price differs for {day}")
            if day in overlap:
                reference = overlap[day]
                actual = (path[:, 1].max(), path[:, 2].min(), path[:60, 1].max(), path[:60, 2].min())
                expected = tuple(float(reference[key]) for key in
                                 ("rth_high", "rth_low", "first60_high", "first60_low"))
                if actual != expected:
                    raise ValueError(f"Daily Facts RTH extrema differ for {day}")
                overlap_checks += 1
            paths[day] = path
    return pd.DataFrame(rows), paths, overlap_checks


def wilson(hits, count):
    if not count:
        return np.nan, np.nan
    z = 1.959963984540054
    rate = hits / count
    center = (rate + z * z / (2 * count)) / (1 + z * z / count)
    radius = z * sqrt(rate * (1 - rate) / count + z * z / (4 * count * count)) / (1 + z * z / count)
    return max(0.0, min(rate, center - radius)), min(1.0, max(rate, center + radius))


def rates(groups, metrics):
    records = []
    for label, group in groups:
        for name in metrics:
            sample = group[name].dropna()
            hits, count = int(sample.sum()), len(sample)
            low, high = wilson(hits, count)
            records.append({"group": label, "metric": name, "hits": hits, "n": count,
                            "rate": hits / count if count else np.nan, "low": low, "high": high})
    return pd.DataFrame(records)


def ridge_probabilities(train, labels, evaluation, penalty=1.0):
    """Small regularized logistic model with training-only centering/scaling."""
    center, scale = train.mean(axis=0), train.std(axis=0)
    scale = np.where(scale > 0, scale, 1)
    x = np.column_stack((np.ones(len(train)), (train - center) / scale))
    holdout = np.column_stack((np.ones(len(evaluation)), (evaluation - center) / scale))
    weights = np.zeros(x.shape[1])
    ridge = np.diag([0, *([penalty] * (x.shape[1] - 1))])

    def sigmoid(value):
        return 1 / (1 + np.exp(-np.clip(value, -35, 35)))

    for _ in range(100):
        fitted = sigmoid(x @ weights)
        hessian = x.T @ (x * (fitted * (1 - fitted))[:, None]) + ridge
        step = np.linalg.solve(hessian, x.T @ (fitted - labels) + ridge @ weights)
        weights -= step
        if np.max(np.abs(step)) < 1e-9:
            return sigmoid(holdout @ weights)
    raise ValueError("logistic model did not converge")


def block_interval(values, seed, block=5, draws=2500):
    values = np.asarray(values)
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, len(values) - block + 1, size=(draws, int(np.ceil(len(values) / block))))
    indices = (starts[..., None] + np.arange(block)).reshape(draws, -1)[:, :len(values)]
    return tuple(np.quantile(values[indices].mean(axis=1), [.025, .975]))


def save_table(stage, key, frame):
    frame.to_csv(stage / "tables" / f"{key}.csv", index=False)


def save_figure(stage, key, figure):
    from IPython.display import Image, display
    import matplotlib.pyplot as plt

    path = stage / "figures" / f"{key}.png"
    figure.tight_layout()
    figure.savefig(path, dpi=125, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    display(Image(filename=str(path)))
