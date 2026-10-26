"""Read-only Stage 2 frozen-method review; no research module imports/scoring."""
from pathlib import Path
import ast
import datetime as dt
import hashlib
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
RUN = ROOT / "work/21_ema_cloud_trend_follow_opportunity/20261011T002602Z_s2_c1b4"
HERE = Path(__file__).resolve().parent
STARTED = dt.datetime.now(dt.timezone.utc).isoformat()
T0 = time.perf_counter()


def identity(path):
    blob = path.read_bytes()
    return {"path": str(path), "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest()}


before = json.loads((HERE / "frozen-method-before.json").read_text())
for record in before["inputs"]:
    assert identity(Path(record["path"])) == record, record["path"]
assert identity(Path(__file__)) == before["checker_source"]
inventory = json.loads((RUN / "provenance/source-inventory.json").read_text())
for record in inventory["sources"]:
    for path in (ROOT / record["workspace_path"], RUN / record["snapshot_path"]):
        actual = identity(path)
        assert actual["bytes"] == record["bytes"] and actual["sha256"] == record["sha256"], str(path)

study = ROOT / "studies/21_ema_cloud_trend_follow_opportunity"
assert (RUN / "config.json").read_bytes() == (study / "config-stage2.json").read_bytes()
assert (RUN / "protocol.md").read_bytes() == (study / "protocol-stage2.md").read_bytes()
config = json.loads((RUN / "config.json").read_text())
constants = {}
for node in ast.parse((study / "src/stage2_contract.py").read_text()).body:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                try:
                    constants[target.id] = ast.literal_eval(node.value)
                except (ValueError, TypeError):
                    pass
family = config["primary_comparison_family"]
assert config["products"] == ["ES", "GC", "NQ"] and config["interval_minutes"] == [3, 5]
assert family["id"] == constants["PRIMARY_FAMILY_ID"]
assert family["size"] == constants["PRIMARY_FAMILY_SIZE"] == 6
assert family["alpha"] == constants["PRIMARY_ALPHA"] == .05
assert {k: family[k] for k in ("direction", "horizon", "unit", "support", "weighting", "metric", "contrast")} == {
    "direction": "All", "horizon": 15, "unit": "points", "support": "all",
    "weighting": "event", "metric": "terminal_delta", "contrast": "fast_minus_slow"}
assert family["bonferroni_quantile_tails"] == [.05 / 12, 1 - .05 / 12]
assert family["bonferroni_marginal_coverage"] == 1 - .05 / 6
assert family["primary_block_weeks"] == 4 and family["sensitivity_block_weeks"] == [1, 8]
boot = config["bootstrap"]
assert (boot["resamples"], boot["seed"], boot["block_weeks"], boot["sensitivity_block_weeks"]) == (10000, 20261010, 4, [1, 8])
assert boot["method"] == "paired_circular_calendar_week_moving_blocks"
assert boot["session_week_assignment"] == "whole_contributing_session_mean_at_ny_trading_date_monday_week"
weeks = []
cursor, end = dt.date(2018, 1, 1), dt.date(2020, 12, 28)
while cursor <= end:
    weeks.append(cursor.isoformat())
    cursor += dt.timedelta(days=7)
assert len(weeks) == 157
assert config["development_start_ny"] == "2018-01-01T00:00:00-05:00"
assert config["development_endpoint_ny"] == "2021-01-01T00:00:00-05:00"
assert config["reserved_outcomes_computed"] is False and config["public_staging_authorized"] is False
comparison = (study / "src/stage2_comparisons.py").read_text()
statistic = (study / "src/stage2_statistics.py").read_text()
inherited = (study / "src/statistics.py").read_text()
assert 'pd.date_range("2018-01-01", "2020-12-28", freq="W-MON")' in comparison
assert 'pd.date_range("2018-01-01", "2020-12-28", freq="W-MON")' in inherited
assert 'PRIMARY_ALPHA / (2 * PRIMARY_FAMILY_SIZE)' in comparison
assert 'difference = draws["fast"] - draws["slow"]' in comparison
assert 'where=denominator > 0' in comparison
assert 'np.quantile(finite, tails, method="linear")' in comparison
assert 'vals = vals.groupby("session", as_index=False)[metric].mean()' in comparison
assert '((15, 20, 50) if interval == 3 else (15, 12, 30))' in comparison
assert 'inherited.bootstrap(group, resamples, seed, block_lengths)' in statistic
assert 'inherited.comparisons(group)' in statistic
assert 'union_summary(member, union, cell_out, saved_union)' in statistic

result = {
    "status": "passed", "run_id": RUN.name, "review_started_at_utc": STARTED,
    "runtime_seconds": time.perf_counter() - T0, "command": before["command"],
    "checker_source": before["checker_source"], "input_pins": before["inputs"],
    "source_inventory_records_checked": len(inventory["sources"]),
    "workspace_and_snapshot_byte_checks": 2 * len(inventory["sources"]),
    "frozen_settings": {"weeks": len(weeks), "week_start": weeks[0], "week_end": weeks[-1],
        "resamples": boot["resamples"], "seed": boot["seed"], "primary_block_weeks": 4,
        "sensitivity_block_weeks": [1, 8], "primary_family": family},
    "expected_complete_table_inventory": {"T08_descriptive_rows": 8100,
        "T08_pointwise_CI_rows": 6480, "T08_Bonferroni_rows": 18, "T08_total_rows": 14598,
        "calendar_sufficient_rows": 678240, "original_branch_bootstrap_rows": 8424,
        "original_branch_duration_comparison_rows": 972},
    "semantic_read_only_review": [
        "Primary contrasts use separate accepted Fast and Slow populations; shared calendar draws do not match event IDs/timestamps.",
        "Completion/evaluability is measured after branch acceptance. Uninterrupted/same-session views are qualified conditional post-path support.",
        "Whole contributing-session means precede assignment to Monday of New York trading-session date; event means retain signal-open week.",
        "Both branches share the same 157-week circular draws, including zero-event weeks; absent denominators remain undefined and are counted.",
        "H15 and equal-active60/150 views receive new paired intervals; same-session/other horizons remain descriptive.",
        "Bonferroni exact alpha/(2*6) tails apply only to six pooled All/H15/points/all/event terminal differences; 1/8-week results are sensitivities.",
        "Original within-branch Stage1 estimators and Slow scientific fields are unchanged; root slow-parity gate runs before Fast outcomes.",
        "Episode forward differences require both selected causal first events scoped and complete; known timing/reference differences require scope only.",
        "Union projection uses saved deterministic representatives, with same-bar scientific equality required; no extra union path is scored.",
        "Frozen independent checker rebuilds sampled indices/session reductions and checks complete scientific row populations and six-cell claim family."],
    "wording_qualification": "Protocol's percentile-coverage wording denotes nominal confidence levels, not guaranteed empirical coverage. Report interpretation should say nominal95%/nominal Bonferroni intervals.",
    "material_discrepancies": [],
    "limits": ["Static source/method review and byte checks; not historical numerical revalidation.",
        "No outcomes, historical estimators, result tables, reports or canonical source were mutated or produced.",
        "Scientific conclusions await saved results, independent numerical reconciliation and reporting checks."]}
for record in before["inputs"]:
    assert identity(Path(record["path"])) == record, record["path"]
with (HERE / "frozen-method-review.json").open("x") as handle:
    json.dump(result, handle, indent=2)
    handle.write("\n")
print(json.dumps({"status": result["status"], "sources": len(inventory["sources"]),
    "byte_checks": result["workspace_and_snapshot_byte_checks"], "runtime_seconds": result["runtime_seconds"],
    "receipt": str(HERE / "frozen-method-review.json")}))
