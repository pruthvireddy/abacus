from __future__ import annotations

from itertools import combinations
from typing import Any

import numpy as np
import pandas as pd

from .statistics import holm_adjust, paired_session_bootstrap_difference, split_frame, stable_seed


def paired_comparisons(all_events: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    reps = int(config["bootstrap"]["replicates"])
    base_seed = int(config["bootstrap"]["seed"])
    for asset, asset_frame in all_events.groupby("asset", observed=True):
        ranges = sorted(asset_frame["range_setting"].unique())
        for split in ("development", "validation", "test", "full"):
            split_data = split_frame(asset_frame, split)
            for left_range, right_range in combinations(ranges, 2):
                left = split_data.loc[split_data["range_setting"].eq(left_range)]
                right = split_data.loc[split_data["range_setting"].eq(right_range)]
                row: dict[str, Any] = {
                    "asset": asset,
                    "contract": "/".join(sorted(asset_frame["contract"].unique())),
                    "left_range": int(left_range),
                    "right_range": int(right_range),
                    "split": split,
                    "direction": "all",
                    "cohort": "primary reversals; complete three-bar windows",
                    "horizon": "L>=3",
                    "units": "probability-point difference (left minus right)",
                    "chart_identity_status": config["chart_identity_status"],
                    "timing_status": config["timing_status"],
                    "date_window": _date_window(split_data),
                }
                one = paired_session_bootstrap_difference(
                    left,
                    right,
                    "eligible_L_ge_3",
                    "success_L_ge_3",
                    reps,
                    stable_seed(base_seed, asset, split, left_range, right_range, 1),
                    block_length=1,
                )
                three = paired_session_bootstrap_difference(
                    left,
                    right,
                    "eligible_L_ge_3",
                    "success_L_ge_3",
                    reps,
                    stable_seed(base_seed, asset, split, left_range, right_range, 3),
                    block_length=3,
                )
                row.update(one)
                row.update({f"block3_{key}": value for key, value in three.items() if key not in {"difference", "paired_dates"}})
                row["denominator"] = int(
                    left["eligible_L_ge_3"].fillna(False).sum() + right["eligible_L_ge_3"].fillna(False).sum()
                )
                rows.append(row)
    result = pd.DataFrame(rows)
    if not result.empty:
        result["holm_adjusted_p"] = np.nan
        for split, index in result.groupby("split").groups.items():
            result.loc[index, "holm_adjusted_p"] = holm_adjust(result.loc[index, "p_value"])
    return result


def _date_window(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "unavailable"
    return f"{frame['export_date'].min()} to {frame['export_date'].max()}"


def select_and_freeze_candidates(
    headline: pd.DataFrame, comparisons: pd.DataFrame, config: dict[str, Any]
) -> tuple[pd.DataFrame, dict[str, Any]]:
    combined = headline.loc[
        headline["direction"].eq("all")
        & headline["range_setting"].notna()
        & headline["eligible_n"].notna()
    ].copy()
    rows: list[dict[str, Any]] = []
    ledger: dict[str, Any] = {
        "selection_rule": "Highest development P(L>=3), using only prespecified available requested ranges",
        "validation_rule": "Candidate must retain the highest point estimate, have >=200 eligible reversals and >=10 export dates",
        "test_winner_rule": "Frozen candidate must remain highest and beat every alternative with Holm-adjusted p<0.05; otherwise no clear winner",
        "assets": {},
    }
    for asset in ("ES", "GC", "NQ"):
        asset_rows = combined.loc[combined["asset"].eq(asset)]
        ranges = sorted(
            asset_rows.loc[asset_rows["split"].eq("development"), "range_setting"].unique()
        )
        if len(ranges) < 2:
            reason = "Requested comparison unavailable: GC20 dataset missing" if asset == "GC" else "Fewer than two available settings"
            row = {
                "asset": asset,
                "development_candidate": ranges[0] if ranges else np.nan,
                "validation_supported": False,
                "test_clear_winner": False,
                "recommendation": "No range comparison possible",
                "reason": reason,
            }
            rows.append(row)
            ledger["assets"][asset] = row
            continue
        development = asset_rows.loc[asset_rows["split"].eq("development")]
        candidate = int(development.sort_values(["probability", "range_setting"], ascending=[False, True]).iloc[0]["range_setting"])
        validation = asset_rows.loc[asset_rows["split"].eq("validation")]
        val_candidate = validation.loc[validation["range_setting"].eq(candidate)].iloc[0]
        val_highest = float(val_candidate["probability"]) >= float(validation["probability"].max()) - 1e-15
        val_support = int(val_candidate["eligible_n"]) >= int(config["support_flags"]["minimum_eligible_reversals"])
        val_dates = int(val_candidate["export_dates"]) >= int(config["support_flags"]["minimum_export_dates"])
        validation_supported = bool(val_highest and val_support and val_dates)

        test = asset_rows.loc[asset_rows["split"].eq("test")]
        test_candidate = test.loc[test["range_setting"].eq(candidate)].iloc[0]
        remains_highest = float(test_candidate["probability"]) >= float(test["probability"].max()) - 1e-15
        test_pairs = comparisons.loc[comparisons["split"].eq("test") & comparisons["asset"].eq(asset)].copy()
        candidate_tests: list[bool] = []
        for pair in test_pairs.itertuples(index=False):
            if int(pair.left_range) == candidate:
                favorable = pair.difference > 0
            elif int(pair.right_range) == candidate:
                favorable = pair.difference < 0
            else:
                continue
            candidate_tests.append(bool(favorable and pair.holm_adjusted_p < 0.05))
        clear = bool(validation_supported and remains_highest and candidate_tests and all(candidate_tests))
        recommendation = f"Range {candidate}" if clear else "No clear winner"
        reason = (
            "Development leader passed the prespecified validation and held-out multiplicity-controlled tests"
            if clear
            else "The development leader did not satisfy every prespecified validation and held-out significance condition"
        )
        row = {
            "asset": asset,
            "development_candidate": candidate,
            "validation_supported": validation_supported,
            "test_clear_winner": clear,
            "recommendation": recommendation,
            "reason": reason,
        }
        rows.append(row)
        ledger["assets"][asset] = row
    return pd.DataFrame(rows), ledger
