"""Causal fixed-bar signal suppression for research cohorts."""

from __future__ import annotations

import numpy as np


def accepted_bar_indices(candidate_indices: np.ndarray, cooldown_bars: int) -> np.ndarray:
    """Accept bar i and suppress bars i+1 through i+``cooldown_bars``.

    Candidate indices refer to the complete ordered chart-bar series, not the
    positions within a filtered candidate list. Bar i+``cooldown_bars``+1 is
    eligible; a suppressed candidate does not restart the timer. Cooldown zero
    accepts every candidate. Calls are independent and return an int64 array.

    Apply causal filters before cooldown and select year/session subsets after
    acceptance when the study requires full-history cadence. The helper does
    not inspect timestamps or future-path validity, or reset at boundaries.
    """
    indices = np.asarray(candidate_indices, dtype=np.int64)
    if cooldown_bars < 0 or np.any(np.diff(indices) <= 0):
        raise ValueError("cooldown must be nonnegative and indices strictly increasing")
    selected = []
    last = -cooldown_bars - 1
    for index in indices:
        if index - last > cooldown_bars:
            selected.append(index)
            last = int(index)
    return np.asarray(selected, dtype=np.int64)
