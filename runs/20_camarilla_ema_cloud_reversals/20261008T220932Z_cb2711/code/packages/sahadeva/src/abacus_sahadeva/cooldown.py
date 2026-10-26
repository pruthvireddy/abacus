"""Causal fixed-bar signal suppression for research cohorts."""

from __future__ import annotations

import numpy as np


def accepted_bar_indices(candidate_indices: np.ndarray, cooldown_bars: int) -> np.ndarray:
    """Keep a signal and suppress its next ``cooldown_bars`` chart bars.

    Candidate indices refer to the complete ordered chart-bar series, not the
    candidate ordinal positions. Rejected candidates do not restart the timer.
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
