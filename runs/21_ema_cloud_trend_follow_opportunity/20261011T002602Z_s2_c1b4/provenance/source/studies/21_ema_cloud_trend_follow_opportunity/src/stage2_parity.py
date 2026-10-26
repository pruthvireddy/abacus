"""Exact inherited slow-value parity and same-bar dual-path equality.

This module compares saved bytes and scientific values. It runs no event,
feature, path or estimator calculation and never rewrites its inputs.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .stage2_contract import PARITY_EXCLUDED_WRAPPER_FIELDS, SCIENTIFIC_PARITY_TOLERANCE

TABLE_NAMES = ("S1-T00_coverage.csv", "S1-T01_signal_flow.csv", "S1-T02_horizon_scorecard.csv",
    "S1-T03_quantiles.csv", "S1-T04_stability.csv", "S1-T05_calendar.csv", "S1-T06_examples.csv",
    "S1-bootstrap.csv", "S1-comparisons.csv")
LEDGER_KEYS = {"bars": ["product", "interval_minutes", "timestamp"],
    "technical": ["product", "interval_minutes", "timestamp"], "events": ["event_id"],
    "outcomes": ["event_id", "horizon"]}
DUAL_FIELDS = ("timestamp", "signal_timestamp", "available_at", "entry_at", "reference_price", "direction",
    "side", "signal_idx", "entry_atr", "contract", "ema20", "ema50", "width", "horizon", "horizon_minutes",
    "status", "censor_reason", "terminal_at", "elapsed_minutes", "crosses_closure", "same_session", "mfe", "mae",
    "terminal_delta", "mfe_atr", "mae_atr", "terminal_delta_atr", "favorable", "neutral", "adverse", "mfe_gt_mae",
    "mfe_mae_tie", "mfe_attainment_start", "mfe_attainment_end", "mae_attainment_start", "mae_attainment_end")
BOOLEAN_FIELDS = {"usable", "feature_valid", "feature_reset", "width_pass", "slow_touch", "fast_touch", "penetration",
    "full_departure", "armed_before", "armed_after", "technical_candidate", "setup_candidate", "accepted", "favorable",
    "neutral", "adverse", "mfe_gt_mae", "mfe_mae_tie", "crosses_closure", "same_session", "calendar_valid",
    "contains_roll", "bad_source", "duplicate_source", "known_closure_before"}


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _pin(path: Path) -> dict:
    return {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": _hash(path)}


def _verified_path(record: dict, manifest: Path) -> Path:
    path = Path(record["path"])
    if not path.is_absolute():
        if ".." in path.parts:
            raise ValueError("unsafe ledger locator")
        path = manifest.parent / path
    if path.is_symlink() or not path.is_file():
        raise ValueError("ledger must be a retained ordinary file")
    if path.stat().st_size != record["bytes"] or _hash(path) != record["sha256"]:
        raise ValueError("ledger byte identity mismatch: " + str(path))
    return path


def compare_frames(baseline: pd.DataFrame, current: pd.DataFrame, *, keys: list[str],
                   excluded=PARITY_EXCLUDED_WRAPPER_FIELDS, label="frame") -> dict:
    """Compare every inherited non-wrapper field with exact/null-aware values."""
    columns = [column for column in baseline if column not in excluded]
    missing = sorted(set(columns) - set(current.columns))
    result = dict(artifact=label, keys=keys, baseline_rows=len(baseline), current_rows=len(current),
        inherited_fields=columns, excluded_inherited_wrapper_fields=[c for c in baseline if c in excluded],
        tolerance=SCIENTIFIC_PARITY_TOLERANCE, compared_cells=0, mismatch_count=0, mismatches=[])
    if missing:
        result.update(mismatch_count=len(missing), mismatches=[dict(reason="missing_inherited_fields", fields=missing)])
        return result
    if baseline.duplicated(keys).any() or current.duplicated(keys).any():
        result.update(mismatch_count=1, mismatches=[dict(reason="duplicate_scientific_keys")])
        return result
    left = baseline.set_index(keys).sort_index()
    right = current.set_index(keys).sort_index()
    if not left.index.equals(right.index):
        result.update(mismatch_count=1, mismatches=[dict(reason="scientific_key_sets_differ",
            missing_keys=[str(k) for k in left.index.difference(right.index)[:10]],
            extra_keys=[str(k) for k in right.index.difference(left.index)[:10]])])
        return result
    for column in columns:
        if column in keys:
            result["compared_cells"] += len(left)
            continue
        a, b = left[column], right[column]
        same = a.eq(b).fillna(False) | (a.isna() & b.isna())
        # False and numeric zero are distinct event meanings even in object columns.
        if column in BOOLEAN_FIELDS and not (pd.api.types.is_bool_dtype(a.dtype) and pd.api.types.is_bool_dtype(b.dtype)):
            at = a.map(lambda value: isinstance(value, (bool, np.bool_)) if pd.notna(value) else None)
            bt = b.map(lambda value: isinstance(value, (bool, np.bool_)) if pd.notna(value) else None)
            same &= at.eq(bt) | (at.isna() & bt.isna())
        bad = np.flatnonzero(~same.to_numpy(bool))
        result["compared_cells"] += len(left)
        result["mismatch_count"] += len(bad)
        for index in bad[:max(0, 20 - len(result["mismatches"]))]:
            result["mismatches"].append(dict(key=str(left.index[index]), field=column,
                baseline=str(a.iloc[index]), current=str(b.iloc[index])))
    return result


def compare_baseline(baseline_manifest: str | Path, new_manifest: str | Path,
                     baseline_tables: str | Path, new_slow_tables: str | Path) -> dict:
    """Compare all four baseline ledger roles and nine regenerated slow tables.

    The manifests are explicit events manifests. Stage 2 long ledgers are
    filtered by their declared ``touch_mode``; wrapper stage is excluded while
    arm ``episode_id``, IDs, candidates, suppression, timing and every outcome
    remain scientific parity fields. Regenerated table CSV strings must agree
    exactly, providing a stricter zero-tolerance check than parsed floats.
    """
    baseline_manifest, new_manifest = Path(baseline_manifest), Path(new_manifest)
    before = [_pin(baseline_manifest), _pin(new_manifest)]
    baseline = json.loads(baseline_manifest.read_text())
    current = json.loads(new_manifest.read_text())
    comparisons, consumed = [], []
    for record in baseline["records"]:
        role = record["role"]
        if role not in LEDGER_KEYS:
            continue
        matching = [r for r in current["records"] if r["role"] == role and r["product"] == record["product"]
                    and int(r["interval_minutes"]) == int(record["interval_minutes"]) and r.get("branch", "slow") != "fast"]
        if len(matching) != 1:
            comparisons.append(dict(artifact=str(record["path"]), mismatch_count=1,
                mismatches=[dict(reason="missing_or_ambiguous_current_ledger", role=role)], compared_cells=0))
            continue
        old_path, new_path = _verified_path(record, baseline_manifest), _verified_path(matching[0], new_manifest)
        consumed.extend([_pin(old_path), _pin(new_path)])
        old_frame, new_frame = pd.read_parquet(old_path), pd.read_parquet(new_path)
        if "touch_mode" in new_frame:
            new_frame = new_frame.loc[new_frame.touch_mode.eq("slow")]
        comparisons.append(compare_frames(old_frame, new_frame, keys=LEDGER_KEYS[role], label=f'{record["product"]}/{record["interval_minutes"]}m/{role}'))
    for name in TABLE_NAMES:
        old_path, new_path = Path(baseline_tables) / name, Path(new_slow_tables) / name
        consumed.extend([_pin(old_path), _pin(new_path)])
        old_frame = pd.read_csv(old_path, dtype=str, keep_default_na=False)
        new_frame = pd.read_csv(new_path, dtype=str, keep_default_na=False)
        keys = ["row_id"] if "row_id" in old_frame else ["product", "interval_minutes", "year", "split"]
        comparisons.append(compare_frames(old_frame, new_frame, keys=keys, excluded=(), label=name))
    after = [_pin(baseline_manifest), _pin(new_manifest)]
    if before != after:
        raise ValueError("manifest changed during parity verification")
    mismatch_count = sum(r["mismatch_count"] for r in comparisons)
    return dict(schema_version="study21.slow-baseline-parity/v1", status="passed" if not mismatch_count else "failed",
        created_at=datetime.now(timezone.utc).isoformat(), checker=_pin(Path(__file__)),
        manifests=before, consumed_artifacts=consumed, comparisons=comparisons,
        ledger_artifacts_compared=len([r for r in baseline["records"] if r["role"] in LEDGER_KEYS]),
        table_artifacts_compared=len(TABLE_NAMES), compared_cells=sum(r["compared_cells"] for r in comparisons),
        mismatch_count=mismatch_count, tolerance=0.0, outcomes_recomputed=False, estimators_recomputed=False,
        qualification="All inherited ledger scientific fields and all saved strings in nine regenerated Stage 1 tables. Only declared Stage 2 wrapper fields excluded from inherited ledgers; new columns do not replace inherited scientific values.")


def verify_dual_outcomes(outcomes: pd.DataFrame, union: pd.DataFrame) -> dict:
    """Direct exact equality for every horizon of dual accepted signal bars."""
    dual = union.loc[union.accepted_membership.eq("both")]
    records = []
    for row in dual.itertuples():
        fast = outcomes.loc[outcomes.event_id.eq(row.fast_event_id)]
        slow = outcomes.loc[outcomes.event_id.eq(row.slow_event_id)]
        if fast.empty and slow.empty:
            records.append(dict(artifact=row.union_id, baseline_rows=0, current_rows=0, compared_cells=0,
                mismatch_count=1, mismatches=[dict(reason="both_dual_outcome_members_missing")]))
            continue
        missing = sorted(set(DUAL_FIELDS) - set(outcomes.columns))
        if missing:
            raise ValueError("missing dual outcome equality fields: " + ",".join(missing))
        records.append(compare_frames(slow[list(DUAL_FIELDS)], fast[list(DUAL_FIELDS)], keys=["horizon"], excluded=(), label=row.union_id))
    mismatches = sum(r["mismatch_count"] for r in records)
    return dict(schema_version="study21.same-bar-dual-equality/v1", status="passed" if not mismatches else "failed",
        dual_signal_bars=len(dual), compared_horizon_rows=sum(r["baseline_rows"] for r in records),
        compared_cells=sum(r["compared_cells"] for r in records), fields=list(DUAL_FIELDS), tolerance=0.0,
        mismatch_count=mismatches, comparisons=records)
