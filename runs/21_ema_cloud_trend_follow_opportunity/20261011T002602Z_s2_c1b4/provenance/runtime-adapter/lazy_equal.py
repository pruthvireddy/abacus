"""Verification-only success diagnostic optimization; frozen helper semantics."""
import math
import numpy as np
import pandas as pd


def lazy_equal(actual, expected, context):
    actual_missing = actual is None or (not isinstance(actual, (list, dict)) and pd.isna(actual))
    expected_missing = expected is None or (not isinstance(expected, (list, dict)) and pd.isna(expected))
    if actual_missing or expected_missing:
        if not bool(actual_missing and expected_missing):
            raise ValueError(f"{context}: null mismatch {actual!r}/{expected!r}")
        return
    if isinstance(expected, (int, float, np.number)) and not isinstance(expected, (bool, np.bool_)):
        if not bool(math.isfinite(float(actual)) and math.isclose(float(actual), float(expected), rel_tol=2e-10, abs_tol=2e-10)):
            raise ValueError(f"{context}: value mismatch {actual!r}/{expected!r}")
    else:
        if not bool(actual == expected):
            raise ValueError(f"{context}: value mismatch {actual!r}/{expected!r}")


def install():
    """Patch only the two explicitly approved references in this process."""
    from src import reconcile, stage2_reconcile
    original = reconcile._equal
    if stage2_reconcile.base_equal is not original:
        raise ValueError('pre-patch helper aliases differ')
    reconcile._equal = lazy_equal
    stage2_reconcile.base_equal = lazy_equal
    return original


def restore(original):
    from src import reconcile, stage2_reconcile
    reconcile._equal = original
    stage2_reconcile.base_equal = original
