"""Select exact saved rows for a read-only scientific interpretation receipt."""
from pathlib import Path
import csv
import datetime as dt
import hashlib
import json

ROOT = Path(__file__).resolve().parents[4]
RUN = ROOT / "work/21_ema_cloud_trend_follow_opportunity/20261011T002602Z_s2_c1b4"
HERE = Path(__file__).resolve().parent


def pin(path):
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


before = json.loads((HERE / "interpretation-before.json").read_text())
assert pin(Path(__file__)) == before["checker_source"]
for record in before["inputs"]:
    assert pin(Path(record["path"])) == record


def table(name):
    path = RUN / "tables" / name
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


def match(row, **criteria):
    return all(row.get(key) == str(value) for key, value in criteria.items())


def evidence(name, selected, fields):
    return {"table": name, "identity": pin(RUN / "tables" / name),
        "rows": [{key: row[key] for key in ["row_id"] + list(fields)} for row in selected]}


score_name = "S2-T02_horizon_scorecard.csv"
contrast_name = "S2-T08_branch_contrasts.csv"
episode_name = "S2-T09_episode_pairing.csv"
union_name = "S2-T10_union_overlap.csv"
geometry_name = "S2-T07_geometry_membership.csv"
annual_name = "S2-T04_stability.csv"
score, contrast, episode, union, geometry, annual = [table(name) for name in
    (score_name, contrast_name, episode_name, union_name, geometry_name, annual_name)]
cohorts = [r for r in score if match(r, horizon=15, unit="points", support="all")]
primary = [r for r in contrast if match(r, direction="All", horizon=15, unit="points", support="all", metric="terminal_delta", weighting="event")]
primary4 = [r for r in primary if r["block_weeks"] == "4"]
adjusted = [r for r in primary if r["interval_type"] == "bonferroni"]
assert len(primary4) == 12 and len(adjusted) == 18
assert all(float(r["ci_low"]) <= 0 <= float(r["ci_high"]) for r in primary4 + adjusted)
pointwise_sensitivity_exceptions = [r for r in primary if r["interval_type"] == "pointwise95" and
    not (float(r["ci_low"]) <= 0 <= float(r["ci_high"]))]
assert {(r["product"], r["interval_minutes"], r["block_weeks"]) for r in pointwise_sensitivity_exceptions} == {("GC", "3", "1"), ("ES", "3", "8")}
session = [r for r in contrast if match(r, direction="All", horizon=15, unit="points", support="all", metric="terminal_delta", weighting="session", block_weeks=4, interval_type="pointwise95")]
assert len(session) == 6 and all(float(r["ci_low"]) <= 0 <= float(r["ci_high"]) for r in session)
event_lookup = {(r["product"], r["interval_minutes"]): r for r in primary4 if r["interval_type"] == "pointwise95"}
reversed_session = [r for r in session if float(r["estimate"]) * float(event_lookup[(r["product"], r["interval_minutes"])]["estimate"]) < 0]
assert {(r["product"], r["interval_minutes"]) for r in reversed_session} == {("GC", "5"), ("NQ", "3"), ("NQ", "5")}
all_cohorts = [r for r in cohorts if r["direction"] == "All"]
assert len(all_cohorts) == 12 and all(float(r["mean_mae"]) > float(r["mean_mfe"]) for r in all_cohorts)
counts = {}
for branch in ("fast", "slow"):
    branch_rows = [r for r in all_cohorts if r["touch_mode"] == branch]
    counts[branch] = {field: sum(int(r[field]) for r in branch_rows) for field in ("accepted", "completed", "censored")}
assert counts == {"fast": {"accepted": 17430, "completed": 17332, "censored": 98},
    "slow": {"accepted": 5257, "completed": 5238, "censored": 19}}
annual_rows = [r for r in annual if match(r, period_kind="year", direction="All", unit="points", support="all")]
assert len(annual_rows) == 36
sparse_GC = [r for r in annual_rows if r["product"] == "GC" and r["sparse_warning"] == "True"]
matched = [r for r in contrast if r["horizon"] in (("20", "50") if r["interval_minutes"] == "3" else ("12", "30")) and
    match(r, direction="All", unit="points", metric="terminal_delta", weighting="event", block_weeks=4, interval_type="pointwise95")]
assert len(matched) == 24 and all(float(r["ci_low"]) <= 0 <= float(r["ci_high"]) for r in matched)
frequency = [r for r in union if match(r, summary_kind="frequency", direction="All")]
assert len(frequency) == 6
union_counts = {field: sum(int(float(r[field])) for r in frequency) for field in
    ("fast_accepted", "slow_accepted", "both_accepted", "union_accepted", "incremental_vs_slow")}
assert union_counts == {"fast_accepted": 17430, "slow_accepted": 5257, "both_accepted": 786, "union_accepted": 21901, "incremental_vs_slow": 16644}
geometry_rows = [r for r in geometry if match(r, direction="All", period_kind="all")]
geometry_counts = {}
for dimension in ("geometry", "accepted_membership"):
    selected = [r for r in geometry_rows if r["dimension"] == dimension]
    geometry_counts[dimension] = {category: sum(int(r["count"]) for r in selected if r["category"] == category)
        for category in sorted({r["category"] for r in selected})}
assert geometry_counts == {
    "geometry": {"fast_only": 145408, "slow_only": 59511, "both": 73214, "neither": 641169, "undefined": 799226},
    "accepted_membership": {"fast_only": 16644, "slow_only": 4471, "both": 786, "neither": 1696627}}
for product in ("ES", "GC", "NQ"):
    for interval in ("3", "5"):
        group = [r for r in geometry_rows if match(r, product=product, interval_minutes=interval)]
        for dimension in ("geometry", "accepted_membership"):
            partition = [r for r in group if r["dimension"] == dimension]
            assert sum(int(r["count"]) for r in partition) == int(partition[0]["scheduled_slots"])
            assert sum(int(r["eligible_count"]) for r in partition) == int(partition[0]["eligible_slots"])
pair = [r for r in episode if match(r, direction="All", summary_kind="pair_metric", category="terminal_delta", horizon=15, unit="points")]
assert len(pair) == 6 and all(float(r["mean_difference"]) < 0 for r in pair)
pair_counts = {field: sum(int(float(r[field])) for r in pair) for field in
    ("selected_pairs", "scoped_pairs", "completed_pairs", "censored_pairs", "outside_scope_pairs")}
assert pair_counts == {"selected_pairs": 58766, "scoped_pairs": 5225, "completed_pairs": 5206, "censored_pairs": 19, "outside_scope_pairs": 53541}
pair_timing = [r for r in episode if match(r, direction="All", summary_kind="pair_timing_reference")]
contacts = [r for r in episode if r["direction"] == "All" and r["summary_kind"] in
    ("same_bar_slow_contact", "strictly_later_slow_contact", "strictly_later_slow_signal")]
contact_counts = {}
for kind in ("same_bar_slow_contact", "strictly_later_slow_contact", "strictly_later_slow_signal"):
    selected = [r for r in contacts if r["summary_kind"] == kind]
    contact_counts[kind] = {category: sum(int(float(r["count"])) for r in selected if r["category"] == category)
        for category in ("true", "false", "unresolved")}
    assert sum(contact_counts[kind].values()) == 17430
overlap = [r for r in union if match(r, direction="All", summary_kind="overlap")]

receipt = {
    "status": "passed_with_required_qualifications", "run_id": RUN.name,
    "reviewed_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "command": before["command"],
    "checker_source": before["checker_source"], "input_pins": before["inputs"],
    "basis": "Saved tables only; numerical interval reference checks are separately retained in saved-results-audit.json. No historical scoring/optimization/source edits.",
    "material_discrepancies": [], "scientific_counts": counts, "union_counts": union_counts,
    "retrospective_pair_counts": pair_counts, "contact_counts": contact_counts,
    "contact_denominator": {"scoped_first_fast_events": 17430, "definition": "First accepted Fast in full causal episode history, in development; no future-completion filter."},
    "aggregate_geometry_counts": geometry_counts,
    "aggregate_common_support": {"scheduled_signal_slots_across_six_cells": 1718528, "eligible_signal_slots_across_six_cells": 919302,
        "denominator": "shared usable AND feature_valid roster; no branch or accepted-timestamp intersection"},
    "interpretation": [
        "All six primary four-week 95% and six-contrast adjusted intervals include zero. No pooled Fast−Slow signed-terminal advantage is established by the prespecified family.",
        "All 18 adjusted intervals across 1/4/8-week blocks include zero. The two pointwise sensitivity exceptions do not survive the corresponding six-contrast adjustment; do not select a block length from them.",
        "Five event-weighted primary point differences are positive and ES 5m is negative; these compare distinct accepted event populations. They are not same-event causal treatment effects or executable profit differences.",
        "Session balancing reverses GC 5m/NQ 3m/NQ 5m point differences; all six four-week pooled session intervals include zero. Whole contributing-session support differs by branch; sided session means cannot be combined using event or side-session counts.",
        "Pooled raw-point H15 MAE means exceed MFE means in all 12 branch cells. Smaller Fast excursion magnitudes describe both favorable/adverse price-path variation and do not prove lower trading risk.",
        "All/Buy/Sell are retained. Side/ATR/session/horizon views and their many intervals are secondary and have no six-primary multiplicity protection.",
        "2020 has much more common eligible coverage and dominates event support. Slow GC in 2018–2019 and Fast GC in 2018 are sparse; zero events/undefined geometry cannot be read as absence of opportunity under unknown coverage.",
        "All 24 pooled raw-point event terminal four-week matched 60/150-minute rows, across all/uninterrupted support, include zero. Uninterrupted support is selected after path completion and is conditional; H15 itself spans 45 vs 75 active minutes.",
        "Geometry and acceptance are distinct partitions. Both geometric touches substantially outnumber 786 dual accepts; acceptance depends on independently retained arms/consumption and fixed width.",
        "The union 21,901 counts each dual same-bar observation once; 16,644 incremental observations are Fast-only accepted bars. Different times remain separate. The union is a saved-path diagnostic, with no combined position rule or incremental P&L.",
        "All 58,766 retained shared episodes enter selected_pairs, including no-accepted/unpaired cases. Only 5,225 have both causal first events in development, and 5,206 are H15 complete/evaluable; no matching/completion restriction enters primary branch populations.",
        "Conditional first-pair Fast−Slow terminal means are negative in all six cells, using different signal and terminal clocks. Timing and direction-adjusted reference evidence reflects later/deeper Slow observations. This cannot be substituted for the primary population estimand or interpreted as a causal Slow execution advantage.",
        "Known timing/reference summaries include scoped pairs without completion filtering. Signed raw reference differences cancel directions and are not an entry-price advantage measure; use the separately labeled direction-adjusted row for that descriptive meaning.",
        "Strictly later geometry has 81 unresolved cases, while later accepted Slow signal has 885 unresolved cases. Neither null category is false. Same-bar geometry, strictly-later contact and strictly-later accepted signals stay separate and never filter Fast acceptance.",
        "Overlap diagnostics are conditional on completed union H15 windows; maxima 5–7 describe overlapping observations, not simultaneous positions. Censored paths have no invented terminal time.",
        "Only 2018–2020 signal-open development outcomes ending by the frozen endpoint are used; 2017 remains causal warmup. Later history is reserved but prior Abacus exposure prevents calling it pristine holdout evidence."],
    "evidence": {
        "primary_four_week": evidence(contrast_name, primary4, ("product", "interval_minutes", "estimate", "ci_low", "ci_high", "interval_type", "fast_accepted", "fast_completed", "fast_censored", "slow_accepted", "slow_completed", "slow_censored")),
        "adjusted_sensitivities": evidence(contrast_name, adjusted, ("product", "interval_minutes", "block_weeks", "estimate", "ci_low", "ci_high")),
        "pointwise_sensitivity_exceptions": evidence(contrast_name, pointwise_sensitivity_exceptions, ("product", "interval_minutes", "block_weeks", "estimate", "ci_low", "ci_high")),
        "session_balancing": evidence(contrast_name, session, ("product", "interval_minutes", "estimate", "ci_low", "ci_high")),
        "All_Buy_Sell_H15": evidence(score_name, cohorts, ("product", "interval_minutes", "direction", "touch_mode", "accepted", "completed", "censored", "contributing_sessions", "mean_mfe", "mean_mae", "mean_terminal_delta", "session_mean_terminal_delta", "favorable_share", "mfe_gt_mae_share", "ci95_low", "ci95_high")),
        "annual_support": evidence(annual_name, annual_rows, ("product", "interval_minutes", "touch_mode", "period", "accepted", "completed", "contributing_sessions", "sparse_warning", "scheduled_slots", "eligible_slots", "unknown_signal_slots", "coverage_complete", "mean_terminal_delta")),
        "sparse_GC": evidence(annual_name, sparse_GC, ("product", "interval_minutes", "touch_mode", "period", "completed", "contributing_sessions", "sparse_warning")),
        "matched_secondary": evidence(contrast_name, matched, ("product", "interval_minutes", "horizon", "horizon_minutes", "support", "estimate", "ci_low", "ci_high", "support_qualification")),
        "geometry_membership": evidence(geometry_name, geometry_rows, ("product", "interval_minutes", "dimension", "category", "count", "eligible_count", "scheduled_slots", "eligible_slots")),
        "union_frequency": evidence(union_name, frequency, ("product", "interval_minutes", "fast_accepted", "slow_accepted", "both_accepted", "union_accepted", "incremental_vs_slow", "eligible_slots", "union_rate_per_1000", "denominator")),
        "episode_H15": evidence(episode_name, pair, ("product", "interval_minutes", "selected_pairs", "scoped_pairs", "completed_pairs", "censored_pairs", "outside_scope_pairs", "evaluable", "mean_difference", "difference_orientation")),
        "episode_timing_reference": evidence(episode_name, pair_timing, ("product", "interval_minutes", "category", "scoped_pairs", "evaluable", "mean_difference", "difference_orientation")),
        "retrospective_contacts": evidence(episode_name, contacts, ("product", "interval_minutes", "summary_kind", "category", "count", "descriptor_eligible", "share")),
        "completed_union_overlap": evidence(union_name, overlap, ("product", "interval_minutes", "completed_windows", "windows_overlapping_prior", "max_concurrent_windows", "overlap_support"))},
    "checks_required_elsewhere": ["Full C independent mapping/state/path/statistical/interval reconciliation, including all secondary endpoints.",
        "Actual report/figure/download/browser/private-publisher transfer checks and sealed-bundle integrity."],
    "review_limits": ["This receipt is an interpretation review, not an authorization for Stage 3, optimization, publication or deployment.",
        "No settings, examples or historical outcome scopes were chosen from the results."]}
for record in before["inputs"]:
    assert pin(Path(record["path"])) == record
with (HERE / "interpretation-review.json").open("x") as file:
    json.dump(receipt, file, indent=2)
    file.write("\n")
print(json.dumps({"status": receipt["status"], "material_discrepancies": 0,
    "receipt": str(HERE / "interpretation-review.json")}))
