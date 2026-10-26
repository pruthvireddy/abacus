"""Retain manual interpretation with exact saved table rows, without estimation."""
from datetime import datetime, timezone
from pathlib import Path
import csv
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
STAGE = HERE.parents[1]


def record(path):
    return {"path": str(path), "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def rows(name, predicate, columns):
    with (STAGE / "tables" / name).open(newline="") as stream:
        return [{"artifact": "tables/" + name, "data_row": i, "csv_line": i + 1,
                 "row_id": row.get("row_id"),
                 "selector": {key: row[key] for key in ("product", "interval_minutes", "year") if key in row},
                 "values": {key: row[key] for key in columns}}
                for i, row in enumerate(csv.DictReader(stream), 1) if predicate(row)]


def main():
    before = json.loads((HERE / "interpretation-write-before.json").read_text())
    for item in before["pinned_files"]:
        assert record(Path(item["path"])) == item, item["path"]
    h15 = lambda r: r["horizon"] == "15" and r["support"] == "all"
    all_points = lambda r: r["direction"] == "All" and r["unit"] == "points"
    terminal = lambda r: r["metric"] == "terminal_delta"
    score_columns = ("accepted", "completed", "censored", "contributing_sessions", "contributing_weeks",
                     "mean_mfe", "mean_mae", "mean_terminal_delta", "median_terminal_delta",
                     "session_mean_terminal_delta", "favorable_share", "session_favorable_share",
                     "mfe_gt_mae_share", "mfe_mae_tie_share", "normalization_missing", "sparse_warning")
    ci_columns = ("estimate", "ci_low", "ci_high", "block_weeks", "weighting", "metric", "defined_draws", "undefined_draws")
    primary = rows("S1-T02_horizon_scorecard.csv", lambda r: h15(r) and all_points(r), score_columns)
    sides = rows("S1-T02_horizon_scorecard.csv", lambda r: h15(r) and r["unit"] == "points", score_columns)
    annual = rows("S1-T04_stability.csv", lambda r: h15(r) and all_points(r) and r["period_kind"] == "year",
                  ("period", "accepted", "completed", "contributing_sessions", "mean_terminal_delta",
                   "session_mean_terminal_delta", "eligible_slots", "scheduled_slots", "unknown_signal_slots",
                   "coverage_complete", "sparse_warning"))
    coverage = rows("S1-T00_coverage.csv", lambda r: r["split"] == "development",
                    ("year", "scheduled_slots", "usable_slots", "mapped_ready_slots", "ready_share", "ready_sessions"))
    sensitivity = rows("S1-bootstrap.csv", lambda r: r["kind"] == "cohort" and h15(r) and all_points(r) and terminal(r), ci_columns)
    side_negative = rows("S1-bootstrap.csv", lambda r: r["kind"] == "cohort" and h15(r) and
                         r["unit"] == "points" and terminal(r) and r["weighting"] == "session" and
                         (r["product"], r["interval_minutes"], r["direction"]) in
                         (("ES", "3", "Sell"), ("NQ", "3", "Buy"), ("NQ", "3", "Sell"), ("NQ", "5", "Sell")), ci_columns)
    equal = rows("S1-comparisons.csv", lambda r: all_points(r) and r["support"] == "all" and
                 r["comparison"].startswith("equal_active"),
                 ("comparison", "horizon_a", "horizon_b", "minutes_a", "minutes_b", "completed_a", "completed_b",
                  "difference_mean_mfe", "difference_mean_mae", "difference_mean_terminal_delta",
                  "difference_session_mean_terminal_delta"))
    equal_ci = rows("S1-bootstrap.csv", lambda r: r["kind"] == "contrast" and all_points(r) and
                    r["support"] == "all" and r["comparison"].startswith("equal_active") and
                    (terminal(r) or r["block_weeks"] == "4"), ci_columns)
    atr_ci = rows("S1-bootstrap.csv", lambda r: r["kind"] == "cohort" and h15(r) and
                  r["direction"] == "All" and r["unit"] == "atr" and terminal(r) and r["block_weeks"] == "4", ci_columns)
    primary_share_ci = rows("S1-bootstrap.csv", lambda r: r["kind"] == "cohort" and h15(r) and all_points(r) and
                            r["block_weeks"] == "4" and r["weighting"] == "event" and
                            r["metric"] in ("favorable", "mfe_gt_mae"), ci_columns)
    assert len(primary) == 6 and len(sides) == 18 and len(annual) == 18 and len(coverage) == 18
    assert len(sensitivity) == 36 and len(equal) == 6 and len(atr_ci) == 12
    for r in sensitivity:
        if r["values"]["block_weeks"] == "4":
            assert float(r["values"]["ci_low"]) <= 0 <= float(r["values"]["ci_high"])
    for r in equal_ci:
        if r["values"]["metric"] == "terminal_delta":
            assert float(r["values"]["ci_low"]) <= 0 <= float(r["values"]["ci_high"])
    findings = [
      {"id": "pooled-primary", "assessment": "Current six pooled raw-point H15 numeric claims and advice are accurate and restrained.",
       "interpretation": "Five event means are negative and ES5 is positive. Every frozen four-week pooled terminal interval includes zero for event and contributing-session means, also in ATR units. This is inconclusive descriptive signed-close evidence; zero inclusion does not prove equivalence or absence of an effect.",
       "qualification": "The conclusion applies to the pooled primary statistic. Positive MFE is a path maximum and does not imply an executable profit, stop, target or trading edge."},
      {"id": "directions-and-session-denominators", "assessment": "Preserve both direction and session-balanced panels; do not extend pooled ambiguity to every subgroup.",
       "interpretation": "All twelve side-specific raw-point event terminal intervals include zero at four weeks. Session-balanced ES3 Sell, NQ3 Buy, NQ3 Sell and NQ5 Sell intervals are below zero at four weeks. The first three remain below zero at one/eight weeks; NQ5 Sell includes zero at eight weeks.",
       "qualification": "These are pointwise descriptive subgroup intervals, without multiplicity adjustment or side selection. Each side conditions on its own contributing sessions. The pooled session mean is computed within every pooled contributing session and cannot be reconstructed by averaging the Buy and Sell session means. For example, ES5 pooled session mean is +0.104509 while Buy/Sell session means are -0.917743/-0.811646; different conditioning and within-session composition explain why these are different estimands."},
      {"id": "annual-coverage-and-composition", "assessment": "Annual outcomes require coverage and sparse-support qualifications.",
       "interpretation": "Audited mapped readiness increases in every cell from 2018 to 2020: roughly 38% to 83% in ES, 27% to 57% in GC, and 45% to 84% in NQ. GC H15 completed counts are 10/39/296 on 3m and 5/29/236 on 5m for 2018/2019/2020; early GC annual panels are sparse. All cells have much larger 2020 cohorts.",
       "qualification": "These are observed eligible populations with year-varying readiness. Pooled means do not establish annual stability, and annual shifts cannot be attributed solely to market regime. Incomplete signal coverage is not a verified zero-opportunity period. GC pooled sparse_warning=False does not make its early-year strata well supported."},
      {"id": "equal-active-duration", "assessment": "No demonstrated signed-close ranking between candle intervals on the pooled equal-active panels.",
       "interpretation": "All 60/150-minute pooled raw-point terminal contrasts, event and session balanced, include zero at one/four/eight weeks. Several four-week MFE or MAE contrast intervals exclude zero; these are descriptive path differences and must not be collapsed into a blanket claim that every metric is indistinguishable.",
       "qualification": "Contrasts are 3m minus 5m with paired calendar block weights, but accepted event populations differ. They are neither matched-event causal effects nor a profitability comparison. H15 is 45 active minutes on 3m and 75 on 5m, so its larger 5m excursions do not isolate a candle-interval effect."},
      {"id": "block-sensitivity", "assessment": "The frozen four-week definition must remain primary.",
       "interpretation": "The GC3 pooled event terminal one-week interval is [-1.285218,-0.121044], excluding zero, while four-week is [-1.270003,+0.082878] and eight-week is [-1.226894,+0.142859]. Other pooled raw-point primary terminal intervals continue to include zero across these block lengths. Reviewed primary and equal-active draws are all defined.",
       "qualification": "Do not choose the one-week GC result after inspection. Block-length sensitivity reflects dependence and calendar composition; interval width need not grow monotonically with block length. Retain one/eight-week results as sensitivity evidence."},
      {"id": "shares-and-excursions", "assessment": "Favorable-share and excursion statements require their own statistic and tie definition.",
       "interpretation": "All six pooled four-week favorable-share intervals include 0.5. Mean MAE exceeds mean MFE in all six pooled H15 cells. ES3 pooled MFE>MAE share interval is below 0.5, unlike most pooled share panels.",
       "qualification": "Shares include the frozen tie conventions and do not yield a stop/target win rate. The MFE>MAE share is distinct from terminal favorable share and mean-MFE/mean-MAE ordering."},
      {"id": "conditional-support-and-holdout", "assessment": "Existing development and execution caveats should remain explicit.",
       "qualification": "Same-session and uninterrupted supplementary views select completed paths after observing support, so their denominators are conditional. Session-balanced statistics condition on contributing sessions. Outcomes are 2018–2020 development only; later outcomes are reserved but prior market-history exposure prevents claiming a pristine market holdout. Original vendor-receipt timing is unavailable; available_at is modeled bar completion."}
    ]
    recommendations = [
      "Retain the current six exact pooled numeric claims and no-profitability advice.",
      "If adding a synthesis before sealing, state that pooled primary signed-close evidence is inconclusive, coverage improves substantially over years, and early GC support is sparse.",
      "Qualify subgroup and equal-active statements by estimand, pointwise uncertainty, different accepted populations and prespecified four-week primary; do not select a side, year or block length after inspection.",
      "Keep the observed negative side/session evidence and all sensitivity rows visible in the retained tables."
    ]
    output = {"status": "passed_with_qualifications", "run_id": STAGE.name,
      "reviewed_at_utc": datetime.now(timezone.utc).isoformat(), "reviewer": "study_engine_saved_table_interpretation",
      "scope": "Only saved table rows and existing report/advice claims; no additional estimator/scoring runs.",
      "command": {"argv": sys.argv, "cwd": str(Path.cwd()), "python": sys.executable, "version": sys.version},
      "before_execution": record(HERE / "interpretation-write-before.json"),
      "table_and_claim_identities": [r for r in before["pinned_files"] if r["path"] != str(Path(__file__).resolve())],
      "current_six_numeric_claims_supported": True, "numerical_corrections_needed": False,
      "sealing_blockers": [], "scientific_parameters_or_methods_changed": False,
      "reserved_outcomes_computed_or_examined": False, "findings": findings,
      "recommendations_before_sealing": recommendations,
      "exact_saved_rows": {"primary_six": primary, "directions_and_session_balance": sides,
        "annual": annual, "annual_coverage": coverage, "pooled_primary_block_sensitivity": sensitivity,
        "negative_side_session_sensitivity": side_negative, "equal_active_contrasts": equal,
        "equal_active_uncertainty": equal_ci, "atr_primary_four_week_uncertainty": atr_ci,
        "primary_share_uncertainty": primary_share_ci}}
    for item in before["pinned_files"]:
        assert record(Path(item["path"])) == item, item["path"]
    with (HERE / "interpretation-review.json").open("x") as stream:
        json.dump(output, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": output["status"], "result": record(HERE / "interpretation-review.json")}))


if __name__ == "__main__":
    main()
