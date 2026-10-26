"""Audit staged filter statistics against sealed inputs and event-level rows."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from study_provenance import run_phase

import numpy as np
import pandas as pd

from src.engine import FILTERS, event_scores


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def verify(stage: Path) -> dict:
    root = Path(__file__).resolve().parents[2]
    lock = json.loads((stage / "inputs.lock.json").read_text())
    for key in ("source_bars", "band_features", "source_outcomes"):
        item = lock[key]
        if sha256(root / item["manifest_path"]) != item["sha256"]:
            raise ValueError(f"manifest changed: {key}")
    if sha256(root / lock["source_outcomes"]["event_ledger_path"]) != lock["source_outcomes"]["event_ledger_sha256"]:
        raise ValueError("source events changed")
    primary = pd.read_csv(stage / "tables/primary.csv")
    sensitivity = pd.read_csv(stage / "tables/sensitivity.csv")
    context = pd.read_parquet(stage / "tables/candidate_context.parquet")
    outcomes = pd.read_parquet(stage / "tables/candidate_outcomes.parquet")
    decision = json.loads((stage / "decision.json").read_text())
    if len(primary) != 20 or len(sensitivity) != 140 or len(context) != 3280:
        raise ValueError("incomplete candidate evidence")
    if len(outcomes) != 3280 * 7:
        raise ValueError("outcome rows do not match raw candidate and horizon grid")
    if set(primary.year) != {2025, 2026} or set(primary.rule) != {"unfiltered", *FILTERS}:
        raise ValueError("primary comparison grid incomplete")
    old = pd.read_csv(root / "runs/12_gc_ema_band_excursions/20260925T223721Z_gc_ema_excursions_v1/tables/yearly.csv")
    old = old.loc[old.year.isin([2025, 2026])]
    baseline = sensitivity.loc[sensitivity.rule == "unfiltered"]
    joined = baseline.merge(old, on=["year", "cooldown", "horizon"], validate="one_to_one", suffixes=("_new", "_old"))
    for left, right in (("accepted_signals_new", "accepted_signals_old"),
                        ("valid_n_new", "valid_n_old"),
                        ("mean_mae_points", "mean_mae"),
                        ("mean_mfe_points", "mean_mfe"),
                        ("mean_terminal_points", "mean_terminal")):
        np.testing.assert_allclose(joined[left], joined[right], atol=1e-8, rtol=0)
    recount = outcomes.loc[outcomes.horizon == 20].merge(
        context[["bar_index"] + [f"accepted_c10_{x}" for x in ["unfiltered", *FILTERS]]],
        on="bar_index", validate="one_to_one")
    for rule in ["unfiltered", *FILTERS]:
        for year in (2025, 2026):
            rows = recount.loc[(recount.year == year) & recount[f"accepted_c10_{rule}"]]
            valid = event_scores(rows.loc[rows.status == "valid"])
            saved = primary.loc[(primary.rule == rule) & (primary.year == year)].iloc[0]
            if len(rows) != saved.accepted_signals or len(valid) != saved.valid_n:
                raise ValueError(f"event counts disagree for {rule}/{year}")
            np.testing.assert_allclose(valid.clipped_score.mean(), saved.mean_clipped_score, atol=1e-8, rtol=0)
            np.testing.assert_allclose(valid.mae_sigma.mean(), saved.mean_mae_sigma, atol=1e-8, rtol=0)
            np.testing.assert_allclose(valid.mfe_sigma.mean(), saved.mean_mfe_sigma, atol=1e-8, rtol=0)
    base = primary.loc[(primary.year == 2025) & (primary.rule == "unfiltered")].iloc[0]
    eligible = []
    for rule in FILTERS:
        row = primary.loc[(primary.year == 2025) & (primary.rule == rule)].iloc[0]
        if (row.valid_n >= 45 and row.sessions >= 20 and row.weeks >= 10 and
            row.mean_mae_sigma < base.mean_mae_sigma and
            row.mean_mfe_sigma >= .9 * base.mean_mfe_sigma and
            row.score_delta_vs_unfiltered > 0):
            eligible.append(rule)
    selected = max(eligible, key=lambda name: primary.loc[(primary.year == 2025) &
                   (primary.rule == name), "score_delta_vs_unfiltered"].iloc[0]) if eligible else None
    if selected != decision["selected_rule"] or eligible != decision["eligible_training_rules"]:
        raise ValueError("2025-only selection does not reproduce")
    page = (stage / "report.html").read_text()
    if "<script" in page or page.count("<table>") < 5 or "2026 YTD" not in page:
        raise ValueError("static report is incomplete")
    return {"status": "pass", "primary_cells": len(primary),
            "sensitivity_cells": len(sensitivity),
            "recounted_primary_cells": 20,
            "baseline_cells_matching_sealed_study_12": len(joined),
            "selected_rule": selected,
            "checks": ["pinned manifest and ledger hashes", "complete two-year candidate grid",
                       "event-level scores and counts", "2025-only selection reproduction",
                       "70 unfiltered cooldown/horizon cells equal sealed study 12",
                       "static HTML contains saved results"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, type=Path)
    args = parser.parse_args()
    study = Path(__file__).resolve().parent
    result = run_phase(study.parents[1], study.name, args.stage, "verification",
                       lambda: verify(args.stage.absolute()))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
