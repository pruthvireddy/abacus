"""Independent saved-ledger reconciliation without importing numerical producers.

Checks reject mutations with ordinary exceptions, including under Python -O.
Byte pins, independent scalar calculations, and presentation transfers are
reported separately. Nothing here establishes native TradingView equivalence.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

METRICS = ("mfe", "mae", "terminal_delta")
FLAGS = ("favorable", "neutral", "adverse", "mfe_gt_mae", "mfe_mae_tie")
NY = "America/New_York"
END = pd.Timestamp("2021-01-01", tz=NY).tz_convert("UTC")


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require(condition, message):
    if not bool(condition):
        raise ValueError(message)


def _equal(actual, expected, context):
    actual_missing = actual is None or (not isinstance(actual, (list, dict)) and pd.isna(actual))
    expected_missing = expected is None or (not isinstance(expected, (list, dict)) and pd.isna(expected))
    if actual_missing or expected_missing:
        _require(actual_missing and expected_missing, f"{context}: null mismatch {actual!r}/{expected!r}")
        return
    if isinstance(expected, (int, float, np.number)) and not isinstance(expected, (bool, np.bool_)):
        _require(math.isfinite(float(actual)) and math.isclose(float(actual), float(expected), rel_tol=2e-10, abs_tol=2e-10),
                 f"{context}: value mismatch {actual!r}/{expected!r}")
    else:
        _require(actual == expected, f"{context}: value mismatch {actual!r}/{expected!r}")


def linear_quantile(values, probability):
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    rank = probability * (len(ordered) - 1)
    left = math.floor(rank)
    right = math.ceil(rank)
    return ordered[left] + (rank - left) * (ordered[right] - ordered[left])


def reconcile_signals(technical: pd.DataFrame, events: pd.DataFrame):
    """Whole-roster scalar arm/consume reference plus exact accepted event identity."""
    examined = 0
    fields = ("direction", "width_pass", "slow_touch", "fast_touch", "penetration", "full_departure",
              "armed_before", "armed_after", "technical_candidate", "setup_candidate", "accepted")
    for (product, interval), group in technical.groupby(["product", "interval_minutes"], sort=False):
        armed = False
        last_direction, last_contract, last_reset_source = 0, None, None
        expected_ids = []
        threshold = {"ES": 2.4, "GC": 2., "NQ": 10.}[product]
        for item in group.itertuples(index=False):
            row = item._asdict()
            valid = bool(row["usable"]) and bool(row["feature_valid"]) and math.isfinite(float(row["ema20"])) and math.isfinite(float(row["ema50"]))
            direction = ((row["ema20"] > row["ema50"]) - (row["ema20"] < row["ema50"])) if valid else 0
            reset_source = row.get("feature_source_timestamp", row["timestamp"])
            explicit = bool(row.get("feature_reset", False)) and reset_source != last_reset_source
            if not valid or direction == 0 or (last_contract is not None and last_contract != row["contract"]) or explicit or direction != last_direction:
                armed = False
            before = armed
            slow = fast = penetration = departure = gate = accepted = False
            if valid and direction:
                slow = row["low"] <= row["ema50"] <= row["high"]
                fast = row["low"] <= row["ema20"] <= row["high"]
                penetration = row["low"] <= row["ema50"] if direction > 0 else row["high"] >= row["ema50"]
                departure = row["low"] > max(row["ema20"], row["ema50"]) if direction > 0 else row["high"] < min(row["ema20"], row["ema50"])
                width = abs(row["ema20"] - row["ema50"])
                gate = width >= threshold - 1e-10 * max(1., threshold)
                accepted = slow and before and gate
                if penetration:
                    armed = False
                if departure:
                    armed = True
            expected = (direction, gate, slow, fast, penetration, departure, before, armed, slow, slow and before, accepted)
            for key, value in zip(fields, expected):
                _equal(row[key], value, f"signal {product}/{interval}/{row['timestamp']}/{key}")
            if accepted:
                side = "Buy" if direction == 1 else "Sell"
                event_id = f"{product}|{int(interval)}m|{row['contract']}|{pd.Timestamp(row['timestamp']).isoformat()}|{side}|slow"
                _equal(row["event_id"], event_id, "accepted stable ID")
                expected_ids.append(event_id)
            last_direction, last_contract = direction, row["contract"]
            if row.get("feature_reset", False):
                last_reset_source = reset_source
            examined += 1
        accepted_rows = group.loc[group.accepted.astype(bool)]
        # Event ledgers contain the development interval only; technical warmup precedes it.
        local = pd.to_datetime(accepted_rows.timestamp, utc=True).dt.tz_convert(NY)
        expected = accepted_rows.loc[local.dt.year.between(2018, 2020), "event_id"].tolist()
        actual = events.loc[(events["product"] == product) & (events.interval_minutes == interval), "event_id"].tolist()
        _require(actual == expected, f"{product}/{interval}: accepted-to-events identity/order mismatch")
    _require(not events.event_id.duplicated().any(), "duplicate event IDs")
    return {"check": "independent_signal_state_and_accepted_identity", "status": "passed",
            "technical_rows": examined, "development_events": len(events)}


def reconcile_mapping(technical, five_bars):
    """Latest expected source identity checked against complete saved scheduled roster."""
    examined = 0
    for product, group in technical.groupby("product", sort=False):
        sources = five_bars[five_bars["product"] == product].sort_values("available_at")
        completed = sources.available_at.array.asi8.tolist()
        columns = ("timestamp", "available_at", "usable", "feature_valid", "contract", "ema20", "ema50", "atr14")
        source_arrays = {column: sources[column].to_numpy() for column in columns}
        import bisect
        for item in group.itertuples(index=False):
            row = item._asdict()
            reference = row["timestamp"] if row["interval_minutes"] == 3 else row["available_at"]
            position = bisect.bisect_right(completed, pd.Timestamp(reference).value) - 1
            if position < 0:
                _require(not row["feature_valid"], "no source cannot be ready")
                continue
            source = {column: source_arrays[column][position] for column in columns}
            _equal(pd.Timestamp(row["feature_source_timestamp"]), pd.Timestamp(source["timestamp"]), "latest scheduled source")
            _equal(pd.Timestamp(row["feature_available_at"]), pd.Timestamp(source["available_at"]), "source modeled availability")
            expected = bool(source["usable"] and source["feature_valid"] and source["contract"] == row["contract"])
            if row["interval_minutes"] == 5:
                expected = expected and pd.Timestamp(source["timestamp"]) == pd.Timestamp(row["timestamp"])
            _equal(row["feature_valid"], expected, "latest missing/partial source invalidates immediately")
            for metric in ("ema20", "ema50", "atr14"):
                _equal(row[metric], source[metric] if expected else None, f"mapping {metric}")
            examined += 1
    return {"check": "independent_latest_scheduled_mapping", "status": "passed", "rows": examined}


def reconcile_outcomes(bars, events, outcomes, *, roster_end_is_endpoint=True):
    """Independent scalar min/max reference for every saved outcome and null."""
    _require(not outcomes.duplicated(["event_id", "horizon"]).any(), "duplicate event/horizon key")
    event_lookup = {row["event_id"]: row for row in events.to_dict("records")}
    required_columns = ("timestamp", "available_at", "contract", "usable", "high", "low", "close", "quality_reason")
    rosters = {(p, i): group[[column for column in required_columns if column in group]].to_dict("records")
               for (p, i), group in bars.groupby(["product", "interval_minutes"], sort=False)}
    examined, completed, censored = 0, 0, 0
    for row in outcomes.to_dict("records"):
        _require(row["event_id"] in event_lookup, "outcome without accepted event")
        event = event_lookup[row["event_id"]]
        local_year = pd.Timestamp(event["timestamp"]).tz_convert(NY).year
        _require(2018 <= local_year <= 2020, "reserved outcome event")
        source = rosters[(event["product"], event["interval_minutes"])]
        i, horizon = int(event["signal_idx"]), int(row["horizon"])
        _equal(pd.Timestamp(source[i]["timestamp"]), pd.Timestamp(event["timestamp"]), "outcome roster identity")
        required = source[i + 1:i + horizon + 1]
        reason = None
        if len(required) != horizon:
            reason = "development_endpoint" if roster_end_is_endpoint else "data_edge"
        elif any(pd.Timestamp(slot["available_at"]) > END for slot in required):
            reason = "development_endpoint"
        else:
            for slot in required:
                if not slot["usable"] or any(pd.isna(slot[key]) for key in ("high", "low", "close")):
                    reason = "invalid_future_slot:" + str(slot.get("quality_reason", "unusable"))
                    break
                if slot["contract"] != event["contract"]:
                    reason = "contract_switch"
                    break
        if reason:
            _equal(row["status"], "censored", "null outcome status")
            _equal(row["censor_reason"], reason, "censor reason")
            for key in METRICS + tuple(metric + "_atr" for metric in METRICS) + FLAGS:
                _equal(row.get(key), None, f"censored {key}")
            censored += 1
        else:
            reference, sign = float(event["reference_price"]), int(event["direction"])
            highest = max(float(slot["high"]) for slot in required)
            lowest = min(float(slot["low"]) for slot in required)
            mfe = max(0., highest - reference) if sign == 1 else max(0., reference - lowest)
            mae = max(0., reference - lowest) if sign == 1 else max(0., highest - reference)
            delta = sign * (float(required[-1]["close"]) - reference)
            epsilon = 1e-10 * max(1., mfe, mae)
            expected = {"mfe": mfe, "mae": mae, "terminal_delta": delta, "favorable": delta > 0,
                        "neutral": delta == 0, "adverse": delta < 0,
                        "mfe_gt_mae": mfe - mae > epsilon, "mfe_mae_tie": abs(mfe - mae) <= epsilon}
            _equal(row["status"], "completed", "complete path status")
            for key, value in expected.items():
                _equal(row[key], value, f"outcome {row['event_id']}/{horizon}/{key}")
            atr = event.get("entry_atr")
            for key in METRICS:
                normalized = expected[key] / atr if pd.notna(atr) and math.isfinite(atr) and atr > 0 else None
                _equal(row[key + "_atr"], normalized, f"normalized {key}")
            for key, favorable in (("mfe", True), ("mae", False)):
                value = expected[key]
                start = end = None
                if value > 0:
                    raw = [sign * ((slot["high"] if sign == 1 else slot["low"]) - reference) if favorable
                           else sign * (reference - (slot["low"] if sign == 1 else slot["high"])) for slot in required]
                    attainment = raw.index(max(raw))
                    start, end = required[attainment]["timestamp"], required[attainment]["available_at"]
                _equal(row.get(key + "_attainment_start"), start, f"first {key} attainment start")
                _equal(row.get(key + "_attainment_end"), end, f"first {key} attainment end")
            _equal(row["elapsed_minutes"], (pd.Timestamp(required[-1]["available_at"]) - pd.Timestamp(event["entry_at"])).total_seconds() / 60, "elapsed minutes")
            completed += 1
        _equal(row["horizon_minutes"], horizon * event["interval_minutes"], "nominal active minutes")
        examined += 1
    # Every accepted event receives every frozen horizon, with no missing rows.
    for (product, interval), group in events.groupby(["product", "interval_minutes"]):
        hs = (5, 10, 15, 20, 30, 50, 100) if interval == 3 else (5, 10, 12, 15, 20, 30, 50, 100)
        subset = outcomes[(outcomes["product"] == product) & (outcomes.interval_minutes == interval)]
        _require(len(subset) == len(group) * len(hs), "missing scheduled outcome ledger rows")
        _require(set(subset.horizon) == set(hs), "horizon roster differs from frozen protocol")
    return {"check": "independent_scalar_outcomes_all_rows", "status": "passed", "rows": examined,
            "completed": completed, "censored": censored}


def _cohort(outcomes, row):
    cohort = outcomes[(outcomes["product"] == row["product"]) &
                      (outcomes.interval_minutes == int(row["interval_minutes"])) & (outcomes.horizon == int(row["horizon"]))]
    if row.get("direction", "All") != "All":
        cohort = cohort[cohort.side == row["direction"]]
    if row.get("support", "all") == "same_session":
        cohort = cohort[cohort.same_session == True]
    elif row.get("support", "all") == "uninterrupted":
        cohort = cohort[cohort.crosses_closure == False]
    if "period_kind" in row:
        column = row["period_kind"]
        cohort = cohort[cohort[column].astype(str) == str(row["period"])]
    complete = cohort[cohort.status == "completed"]
    suffix = "_atr" if row["unit"] == "atr" else ""
    good = complete[complete[[metric + suffix for metric in METRICS]].notna().all(axis=1)]
    return cohort, complete, good, suffix


def _raw_csv(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        _require(reader.fieldnames and len(reader.fieldnames) == len(set(reader.fieldnames)), "unique CSV headers required")
        rows = list(reader)
    _require(all(None not in row and all(value is not None for value in row.values()) for row in rows), "well-formed CSV rows required")
    return rows


def _cell(raw, expected, context):
    actual = None if raw == "" else (raw in ("True", "true") if isinstance(expected, (bool, np.bool_)) else float(raw))
    _equal(actual, expected, context)


def reconcile_tables(outcomes: pd.DataFrame, tables: dict[str, Path], technical: pd.DataFrame | None = None):
    """Independently reconstruct every reported base/quantile/stability summary."""
    checked = 0
    cohort_cache = {}
    def cohort_for(row):
        keys = ("product", "interval_minutes", "horizon", "direction", "support", "unit")
        key = tuple(row.get(column, "all" if column == "support" else "All" if column == "direction" else "") for column in keys)
        if key not in cohort_cache:
            unstratified = {column: row[column] for column in row if column not in ("period_kind", "period")}
            cohort_cache[key] = _cohort(outcomes, unstratified)
        cohort, complete, good, suffix = cohort_cache[key]
        if "period_kind" in row:
            kind, period = row["period_kind"], str(row["period"])
            return (cohort[cohort[kind].astype(str) == period], complete[complete[kind].astype(str) == period],
                    good[good[kind].astype(str) == period], suffix)
        return cohort, complete, good, suffix
    for name in ("S1-T02", "S1-T04", "S1-T05"):
        for row in _raw_csv(tables[name]):
            if row.get("period_kind") == "week":
                week_start = pd.Timestamp(row["period"])
                _require(week_start.weekday() == 0 and week_start < pd.Timestamp("2021-01-01") and
                         week_start + pd.Timedelta(days=7) > pd.Timestamp("2018-01-01"),
                         "calendar-week summary does not intersect development")
            cohort, complete, good, suffix = cohort_for(row)
            n, accepted = len(good), len(cohort)
            sessions = good.session.nunique()
            expected = {"accepted": accepted, "completed": len(complete), "censored": accepted - len(complete),
                        "evaluable": n, "normalization_missing": len(complete) - n,
                        "contributing_sessions": sessions, "contributing_weeks": good.week.nunique(),
                        "sparse_warning": n < 100 or sessions < 30}
            for metric in METRICS:
                values = good[metric + suffix].astype(float).tolist()
                expected["mean_" + metric] = math.fsum(values) / n if n else None
                expected["median_" + metric] = linear_quantile(values, .5)
                session_values = good.groupby("session")[metric + suffix].mean().tolist()
                expected["session_mean_" + metric] = math.fsum(session_values) / len(session_values) if session_values else None
                for q in (.1, .25, .5, .75, .9, .95):
                    expected[f"{metric}_p{int(q * 100):02d}"] = linear_quantile(values, q)
            for flag in FLAGS:
                total = sum(bool(value) for value in good[flag])
                expected[flag + "_count"] = total
                expected[flag + "_share"] = total / n if n else None
                by_session = good[flag].astype(float).groupby(good.session).mean().tolist()
                expected["session_" + flag + "_share"] = math.fsum(by_session) / len(by_session) if by_session else None
            favorable = int(complete.favorable.fillna(False).sum()) if len(complete) else 0
            expected["missing_worst_favorable_share"] = favorable / accepted if accepted else None
            expected["missing_best_favorable_share"] = (favorable + accepted - len(complete)) / accepted if accepted else None
            expected["mean_elapsed_minutes"] = float(good.elapsed_minutes.mean()) if n else None
            expected["closure_crossing_completed"] = int(complete.crosses_closure.eq(True).sum())
            expected["same_session_completed"] = int(complete.same_session.eq(True).sum())
            for key, value in expected.items():
                if key in row:
                    _cell(row[key], value, f"table {name}/{row['row_id']}/{key}")
                    checked += 1
    for row in _raw_csv(tables["S1-T03"]):
        _, _, good, suffix = cohort_for(row)
        expected = linear_quantile(good[row["metric"] + suffix].tolist(), float(row["quantile"]))
        _cell(row["value"], expected, f"exact quantile {row['row_id']}")
        checked += 1
    if technical is not None:
        local = pd.to_datetime(technical.timestamp, utc=True).dt.tz_convert(NY)
        technical = technical[local.dt.year.between(2018, 2020)]
        for row in _raw_csv(tables["S1-T01"]):
            interval = int(row["interval_minutes"])
            if row["flow_kind"] == "outcome":
                cohort = outcomes[(outcomes["product"] == row["product"]) & (outcomes.interval_minutes == interval) & (outcomes.horizon == int(row["horizon"]))]
                if row["direction"] != "All":
                    cohort = cohort[cohort.side == row["direction"]]
                reason = row["reason"]
                expected = len(cohort) if reason == "accepted" else int((cohort.status == reason).sum()) if reason in ("completed", "censored") else int(((cohort.status == "censored") & (cohort.censor_reason == reason.removeprefix("censor:"))).sum())
            else:
                cohort = technical[(technical["product"] == row["product"]) & (technical.interval_minutes == interval)]
                if row["direction"] != "All":
                    cohort = cohort[cohort.side == row["direction"]]
                reason = row["reason"]
                columns = {"usable_slots": "usable", "feature_valid_slots": "feature_valid", "technical_candidates": "technical_candidate", "setup_candidates": "setup_candidate", "accepted": "accepted"}
                if reason == "scheduled_slots":
                    expected = len(cohort)
                elif reason == "eligible_slots":
                    expected = int((cohort.usable & cohort.feature_valid).sum())
                elif reason == "eligible_sessions":
                    expected = cohort[cohort.usable & cohort.feature_valid].session.nunique()
                elif reason in columns:
                    expected = int(cohort[columns[reason]].sum())
                else:
                    expected = int((cohort.suppression_reason == reason.removeprefix("suppressed:")).sum())
            _cell(row["count"], expected, f"flow {row['row_id']}")
            checked += 1
    for name, path in tables.items():
        rows = _raw_csv(path)
        if rows and "row_id" in rows[0]:
            _require(len({row["row_id"] for row in rows}) == len(rows), f"{name}: duplicate stable row IDs")
    return {"check": "independent_ledger_to_tables", "status": "passed", "checked_numeric_cells": checked}


def verify_publication(stage: Path):
    """Verify all public numerical cells, selected CSV strings, claims and plot sources."""
    stage = Path(stage)
    publication = json.loads((stage / "publication.json").read_text())
    bindings = json.loads((stage / "source-bindings.json").read_text())
    _require(sha256(stage / "publication.json") == bindings["publication_sha256"], "publication identity changed")
    sections = {section["id"]: section for section in publication["sections"]}
    source_cache = {}
    def source(path, pin):
        target = stage / path
        target.resolve().relative_to(stage.resolve())
        _require(sha256(target) == pin, f"source hash changed: {path}")
        if path not in source_cache:
            source_cache[path] = _raw_csv(target) if target.suffix == ".csv" else pd.read_parquet(target).to_dict("records")
        return source_cache[path]
    count = 0
    claimed_cells = set()
    for binding in bindings["cells"]:
        rows = source(binding["source_artifact"], binding["source_sha256"])
        row = rows[binding["data_row_1_based"] - 1]
        _equal(row[binding["column"]], binding["source_raw"], "cell original string")
        _equal(row.get("row_id", ""), binding["row_id"], "cell stable row")
        raw = row[binding["column"]]
        expected = None if raw == "" else float(raw) if binding["conversion"] == "finite_float_or_null" else raw
        actual = sections[binding["section"]]["rows"][binding["output_row"]][binding["column"]]
        _equal(actual, expected, "public cell transfer")
        claimed_cells.add((binding["section"], binding["output_row"], binding["column"]))
        count += 1
    public_cells = {(section["id"], index, key) for section in publication["sections"] if section["kind"] == "table" for index, row in enumerate(section["rows"]) for key in row}
    _require(public_cells == claimed_cells, "unbound or duplicate/missing public cells")
    declarations = {item["id"]: item for item in publication.get("downloads", [])}
    download_cells = 0
    for binding in bindings["downloads"]:
        declaration = declarations[binding["download"]]
        _equal(declaration["sha256"], binding["sha256"], "download declaration hash")
        _require(sha256(stage / binding["path"]) == binding["sha256"], "selected download mutated")
        originals = source(binding["source_artifact"], binding["source_sha256"])
        downloaded = _raw_csv(stage / binding["path"])
        _require(len(downloaded) == binding["row_count"] == declaration["rowCount"], "download count mismatch")
        selected_indices = [i for i, row in enumerate(originals, 1) if all(row[key] in [str(v) for v in values] for key, values in binding["selector"].items())]
        _require(selected_indices == binding["data_rows_1_based"], "download selector transfer mismatch")
        for target, index in zip(downloaded, selected_indices):
            for key in binding["columns"]:
                _equal(target[key], originals[index - 1][key], "download preserves original source string")
                download_cells += 1
    _require(set(declarations) == {item["download"] for item in bindings["downloads"]}, "unbound download")
    for claim in bindings["claims"]:
        originals = source(claim["source_artifact"], claim["source_sha256"])
        row = originals[claim["data_row_1_based"] - 1]
        _equal(row["row_id"], claim["row_id"], "claim stable row")
        for key, raw in claim["source_raw"].items():
            _equal(row[key], raw, "claim source original string")
        low, high = row.get("ci95_low", ""), row.get("ci95_high", "")
        qualifier = "95% interval unavailable"
        if low and high:
            qualifier = f"95% interval [{low}, {high}], " + ("includes zero" if float(low) <= 0 <= float(high) else "entirely positive" if float(low) > 0 else "entirely negative")
        fmt = lambda raw: "undefined" if raw == "" else raw
        reconstructed = (f"{row['product']} {row['interval_minutes']}m H15: {row['completed']} completed of {row['accepted']} accepted paths; "
                         f"{row['censored']} censored. Mean signed terminal movement {fmt(row['mean_terminal_delta'])} points; "
                         f"{qualifier}. Mean MFE {fmt(row['mean_mfe'])}, MAE {fmt(row['mean_mae'])} points. "
                         f"Sparse support: {row.get('sparse_warning', 'not recorded')}. Evidence row {row['row_id']}.")
        _equal(claim["claim"], reconstructed, "independent numerical claim reconstruction")
        _require(claim["claim"] in sections["findings"]["body"], "claim absent from public findings")
        _require(claim["claim"] in (stage / "report.md").read_text() and claim["claim"] in (stage / "advice.md").read_text(), "offline/advice claim mismatch")
    for binding in bindings["figures"]:
        _require(sha256(stage / binding["path"]) == binding["sha256"], "figure bytes changed")
        _equal(sections[binding["figure"]]["path"], binding["path"], "figure public identity")
        for item in binding["sources"]:
            rows = source(item["source_artifact"], item["source_sha256"])
            selected = [str(row["row_id"]) for row in rows if all(str(row[key]) in [str(v) for v in values] for key, values in item["selector"].items())]
            # Some render selections also remove non-plotted metrics; selected IDs
            # are recorded explicitly, checked for unique existence and selector membership.
            _require(len(item["row_ids"]) == len(set(item["row_ids"])), "duplicate figure source row")
            _require(set(item["row_ids"]) <= set(selected), "figure source rows outside frozen selector")
            _require(all(all(column in row for column in item["columns"]) for row in rows), "figure source column absent")
    _require({section["id"] for section in publication["sections"] if section["kind"] == "figure"} == {item["figure"] for item in bindings["figures"]}, "unbound figure")
    return {"check": "tables_to_publication_downloads_claims_figures", "status": "passed",
            "public_cells": count, "download_cells": download_cells, "claims": len(bindings["claims"]),
            "figures": len(bindings["figures"]), "publication_sha256": sha256(stage / "publication.json"),
            "bindings_sha256": sha256(stage / "source-bindings.json"),
            "qualification": "Figure sources and exact raster bytes verified; independent visual QA remains separate."}


def reconciliation_receipt(stage: Path, checks: list[dict], *, sources: list[Path], outputs: list[Path]):
    stage = Path(stage)
    def inventory(paths):
        return [{"path": str(Path(path).resolve()), "bytes": Path(path).stat().st_size, "sha256": sha256(path)} for path in paths]
    receipt = {"schema_version": 1, "study_id": "21_ema_cloud_trend_follow_opportunity", "run_id": stage.name,
               "status": "passed" if all(item["status"] == "passed" for item in checks) else "qualified",
               "checks": checks, "source_identities": inventory(sources), "output_identities": inventory(outputs),
               "checker_source": inventory([Path(__file__)]),
               "scope": "Independent scalar state/path calculations, ledger summaries and selected-source transfers; not native chart replay, feed certification or profitability."}
    (stage / "independent-reconciliation.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    return receipt


def reconcile_primary_bootstrap(outcomes: pd.DataFrame, score_path: Path, bootstrap_path: Path | None = None):
    """Independent event-weighted terminal means for all six H15 cells.

    Rebuild circular samples directly from sampled week indices, independently
    of the producer's multiplicity matrix and matrix multiplication.
    """
    weeks = list(pd.date_range("2018-01-01", "2020-12-28", freq="W-MON").strftime("%Y-%m-%d"))
    lookup = {week: i for i, week in enumerate(weeks)}
    primary = outcomes[(outcomes.horizon == 15) & (outcomes.status == "completed")]
    cohorts = []
    for (product, interval), group in primary.groupby(["product", "interval_minutes"]):
        sums = np.zeros(len(weeks))
        counts = np.zeros(len(weeks))
        for week, week_group in group.groupby("week"):
            sums[lookup[week]] = math.fsum(week_group.terminal_delta.tolist())
            counts[lookup[week]] = len(week_group)
        cohorts.append((product, interval, sums, counts))
    score = _raw_csv(score_path)
    boot = _raw_csv(bootstrap_path) if bootstrap_path and bootstrap_path.exists() else []
    checked = []
    for block in (4, 1, 8):
        rng = np.random.default_rng(20261010)
        starts = rng.integers(0, len(weeks), size=(10000, math.ceil(len(weeks) / block)))
        # Derive the full selected-week roster rather than producer weights.
        selected = np.concatenate([((starts + offset) % len(weeks))[:, :, None] for offset in range(block)], axis=2).reshape(10000, -1)[:, :len(weeks)]
        for product, interval, sums, counts in cohorts:
            numerators = sums[selected].sum(axis=1)
            denominators = counts[selected].sum(axis=1)
            valid = denominators > 0
            draws = (numerators[valid] / denominators[valid]).tolist()
            low, high = linear_quantile(draws, .025), linear_quantile(draws, .975)
            if block == 4:
                matches = [row for row in score if row["product"] == product and int(row["interval_minutes"]) == interval and row["direction"] == "All" and row["horizon"] == "15" and row["unit"] == "points" and row["support"] == "all"]
                _require(len(matches) == 1, "primary bootstrap summary row unique")
                _cell(matches[0]["ci95_low"], low, "independent 4wk primary low")
                _cell(matches[0]["ci95_high"], high, "independent 4wk primary high")
            if boot:
                matches = [row for row in boot if row["kind"] == "cohort" and row["product"] == product and int(float(row["interval_minutes"])) == interval and row["direction"] == "All" and int(float(row["horizon"])) == 15 and row["unit"] == "points" and row["metric"] == "terminal_delta" and row["weighting"] == "event" and row["block_weeks"] == str(block)]
                _require(len(matches) == 1, "primary bootstrap evidence row unique")
                _cell(matches[0]["ci_low"], low, "independent primary low")
                _cell(matches[0]["ci_high"], high, "independent primary high")
                _cell(matches[0]["undefined_draws"], int((~valid).sum()), "undefined bootstrap draws")
            checked.append({"product": product, "interval_minutes": int(interval), "block_weeks": block,
                            "ci_low": low, "ci_high": high, "undefined_draws": int((~valid).sum())})
    return {"check": "independent_primary_terminal_bootstrap", "status": "passed",
            "resamples": 10000, "seed": 20261010, "cells": checked}


def reconcile_examples(outcomes: pd.DataFrame, technical: pd.DataFrame, table_path: Path):
    """Independently reselect the five frozen cases in each development cell."""
    rows = _raw_csv(table_path)
    _require(len(rows) == 30, "exact thirty example-class rows required")
    checked = 0
    for product in ("ES", "GC", "NQ"):
        for interval in (3, 5):
            cohort = outcomes[(outcomes["product"] == product) & (outcomes.interval_minutes == interval) & (outcomes.horizon == 15)]
            complete = cohort[cohort.status == "completed"]
            candidates = technical[(technical["product"] == product) & (technical.interval_minutes == interval) & technical.technical_candidate & ~technical.accepted]
            for kind in ("typical", "high_adverse", "high_favorable", "rejected", "partial"):
                chosen = None
                pool = complete.to_dict("records")
                if kind in ("typical", "high_adverse", "high_favorable") and pool:
                    median = linear_quantile([row["terminal_delta"] for row in pool], .5)
                    def rank(row):
                        score = abs(row["terminal_delta"] - median) if kind == "typical" else -row["mae"] if kind == "high_adverse" else -row["mfe"]
                        return score, pd.Timestamp(row["timestamp"]), str(row["event_id"])
                    chosen = min(pool, key=rank)
                elif kind == "rejected" and len(candidates):
                    chosen = min(candidates.to_dict("records"), key=lambda row: (pd.Timestamp(row["timestamp"]), int(row["signal_idx"])))
                elif kind == "partial":
                    pool = cohort[cohort.status == "censored"].to_dict("records")
                    if pool:
                        chosen = min(pool, key=lambda row: (pd.Timestamp(row["timestamp"]), str(row["event_id"])))
                matches = [row for row in rows if row["product"] == product and int(row["interval_minutes"]) == interval and row["example_class"] == kind]
                _require(len(matches) == 1, "unique example cell/class required")
                actual = matches[0]
                _equal(actual["selection_status"], "selected" if chosen is not None else "unavailable", "example availability")
                if chosen is not None:
                    _equal(pd.Timestamp(actual["timestamp"]), pd.Timestamp(chosen["timestamp"]), "deterministic example timestamp")
                    _cell(actual["signal_idx"], chosen["signal_idx"], "deterministic example ordinal")
                    _equal(actual["event_id"] or None, chosen.get("event_id"), "deterministic example ID")
                    if kind != "rejected":
                        for key in METRICS:
                            _cell(actual[key], chosen[key], f"example saved {key}")
                checked += 1
    return {"check": "independent_deterministic_example_selection", "status": "passed", "classes": checked}


def reconcile_example_paths(technical, examples, paths):
    """Every illustrated candle must be an exact saved technical-roster candle."""
    checked = 0
    for example in examples.to_dict("records"):
        if example["selection_status"] != "selected":
            continue
        index = int(example["signal_idx"])
        expected = technical.iloc[max(0, index - 10):index + 16].copy()
        years = pd.to_datetime(expected.timestamp, utc=True).dt.tz_convert(NY).dt.year
        expected = expected[years.between(2018, 2020)]
        plotted = paths[paths.selection_id == example["selection_id"]].sort_values("relative_slot")
        _require(len(expected) == len(plotted), "illustrated path dropped or fabricated scheduled candles")
        for original, candle in zip(expected.to_dict("records"), plotted.to_dict("records")):
            _equal(int(candle["relative_slot"]), int(original["signal_idx"]) - index, "example relative slot")
            for key in ("timestamp", "available_at", "open", "high", "low", "close", "ema20", "ema50", "usable"):
                _equal(candle[key], original[key], f"saved illustration candle {key}")
            _equal(candle["contract_id"], original["contract"], "illustration contract lineage")
            checked += 1
    return {"check": "independent_saved_example_path_candles", "status": "passed", "candles": checked}


def reconcile_coverage(technical, native_five, table_path):
    """Annual quality counts and mapped decision readiness, including warmup."""
    _require(len(technical) > 0, "empty technical coverage roster")
    products = technical["product"].unique().tolist()
    intervals = technical["interval_minutes"].unique().tolist()
    _require(len(products) == len(intervals) == 1, "coverage checker requires one cell")
    product, interval = str(products[0]), int(intervals[0])
    rows = [row for row in _raw_csv(table_path)
            if row["product"] == product and int(row["interval_minutes"]) == interval]
    local_year = pd.to_datetime(technical.timestamp, utc=True).dt.tz_convert(NY).dt.year
    native_year = pd.to_datetime(native_five.timestamp, utc=True).dt.tz_convert(NY).dt.year
    years = sorted(int(year) for year in local_year[local_year.between(2017, 2020)].unique())
    _require(sorted(int(row["year"]) for row in rows) == years,
             "coverage annual support is incomplete or duplicated")
    checked = 0
    annual = []
    for row in rows:
        year = int(row["year"])
        group = technical[local_year == year]
        eligible = group.usable.astype(bool) & group.feature_valid.astype(bool)
        ready = int(eligible.sum())
        expected = {"scheduled_slots": len(group), "usable_slots": int(group.usable.sum()),
                    "missing_slots": int(group.quality_reason.fillna("").str.contains("missing_source_minutes", regex=False).sum()),
                    "empty_slots": int((group.source_count == 0).sum()),
                    "mixed_slots": int((group.contract_count > 1).sum()),
                    "calendar_invalid_slots": int((~group.calendar_valid).sum()),
                    "expected_source_minutes": int(group.expected_count.sum()),
                    "observed_source_minutes": int(group.source_count.sum()),
                    "known_closures_before": int(group.known_closure_before.sum())}
        if 2018 <= year <= 2020:
            expected.update(feature_ready_slots=ready, mapped_ready_slots=ready,
                            ready_share=ready / len(group) if len(group) else None,
                            ready_sessions=int(group.loc[eligible, "session"].nunique()))
            _require(row.get("split") == "development", "development coverage split differs")
        else:
            native = native_five[native_year == year]
            expected.update(feature_ready_slots=int(native.feature_valid.sum()) if interval == 5 else None,
                            mapped_ready_slots=None, ready_share=None, ready_sessions=None)
            _require(row.get("split") == "warmup_only", "warmup coverage split differs")
        for key, value in expected.items():
            _require(key in row, "missing coverage field: " + key)
            _cell(row[key], value, f"independent coverage {product}/{interval}/{year}/{key}")
            checked += 1
        annual.append({"year": year, "scheduled_slots": len(group), "eligible_slots": ready,
                       "ready_sessions": expected["ready_sessions"],
                       "warmup_readiness_undefined": year == 2017 and interval == 3})
    return {"check": "independent_saved_roster_coverage_quality", "status": "passed",
            "numeric_cells": checked, "annual_support": annual}


def verify_bundle(stage: Path) -> dict:
    """Read explicitly pinned ledgers one product/candle cell at a time."""
    import os
    import tomllib
    stage = Path(stage).resolve()
    workspace = Path(__file__).resolve().parents[3]
    config_path = workspace / "config/paths.local.toml"
    config = tomllib.loads(config_path.read_text()) if config_path.exists() else {}
    configured_root = os.environ.get("ABACUS_PUBLICATION_ROOT", config.get("paths", {}).get("publication_root"))
    _require(isinstance(configured_root, str) and bool(configured_root.strip()), "explicit publication storage configuration required")
    publication_root = Path(configured_root).expanduser()
    if not publication_root.is_absolute():
        publication_root = workspace / publication_root
    records = json.loads((stage / "events.manifest.json").read_text())["records"]
    sources = [stage / "events.manifest.json", stage / "inputs.lock.json", stage / "config.json"]
    checks, event_frames, outcome_frames, technical_flow_frames = [], [], [], []
    def read_record(record):
        path = Path(record["path"])
        if not path.is_absolute():
            path = publication_root / path
        _require(path.stat().st_size == record["bytes"] and sha256(path) == record["sha256"], "explicit ledger bytes changed")
        frame = pd.read_parquet(path)
        expected_count = record.get("row_count", record.get("rows"))
        if expected_count is not None:
            _require(len(frame) == expected_count, "ledger row count changed")
        sources.append(path)
        return frame
    lock = json.loads((stage / "inputs.lock.json").read_text())
    delivery_path = Path(lock["delivery"]["path"])
    if not delivery_path.is_absolute():
        delivery_path = publication_root / delivery_path
    _require(sha256(delivery_path) == lock["delivery"]["sha256"], "native5m manifest changed")
    delivery = json.loads(delivery_path.read_text())
    sources.append(delivery_path)
    example_path = stage / "tables/selected-example-paths.parquet"
    example_table = stage / "tables/S1-T06_examples.csv"
    illustrated = pd.read_parquet(example_path)
    saved_examples = pd.read_csv(example_table)
    for product in ("ES", "GC", "NQ"):
        native_record = next(record for record in delivery["output_files"] if record["product"] == product and int(record["interval_minutes"]) == 5)
        native_five = read_record(native_record)
        for interval in (3, 5):
            cell_records = {record["role"]: record for record in records if record["product"] == product and record["interval_minutes"] == interval}
            technical = read_record(cell_records["technical"])
            events = read_record(cell_records["events"])
            outcomes = read_record(cell_records["outcomes"])
            # Technical retains the exact mapped bars, so reading the bars file
            # separately only verifies its byte pin and equality on scored columns.
            bars_record = cell_records["bars"]
            bars_path = Path(bars_record["path"])
            _require(sha256(bars_path) == bars_record["sha256"] and bars_path.stat().st_size == bars_record["bytes"], "saved mapped bars changed")
            sources.append(bars_path)
            mapped_bars = pd.read_parquet(bars_path, columns=["product", "interval_minutes", "timestamp", "available_at", "contract", "open", "high", "low", "close", "usable", "feature_valid", "ema20", "ema50", "atr14", "session", "quality_reason", "known_closure_before"])
            for column in mapped_bars:
                _require(mapped_bars[column].equals(technical[column]), f"mapped/technical column mismatch: {column}")
            checks.append(reconcile_mapping(technical, native_five))
            checks.append(reconcile_coverage(technical, native_five, stage / "tables/S1-T00_coverage.csv"))
            checks.append(reconcile_signals(technical, events))
            checks.append(reconcile_outcomes(technical, events, outcomes))
            examples = saved_examples[(saved_examples["product"] == product) & (saved_examples.interval_minutes == interval)]
            checks.append(reconcile_example_paths(technical, examples, illustrated))
            technical_flow_frames.append(technical[["product", "interval_minutes", "timestamp", "side", "usable", "feature_valid", "technical_candidate", "setup_candidate", "accepted", "session", "suppression_reason", "signal_idx", "event_id"]].copy())
            event_frames.append(events[[column for column in ("event_id", "product", "interval_minutes", "timestamp", "signal_idx", "reference_price", "side", "contract") if column in events]].copy())
            outcome_frames.append(outcomes)
            del technical, mapped_bars, events, outcomes
        del native_five
    from .reporting import TABLES
    tables = {key: stage / "tables" / filename for key, filename in TABLES.items()}
    combined = pd.concat(outcome_frames, ignore_index=True)
    flow_technical = pd.concat(technical_flow_frames, ignore_index=True)
    checks.append(reconcile_tables(combined, tables, flow_technical))
    local = pd.to_datetime(flow_technical.timestamp, utc=True).dt.tz_convert(NY)
    checks.append(reconcile_examples(combined, flow_technical[local.dt.year.between(2018, 2020)], example_table))
    checks.append(reconcile_primary_bootstrap(combined, tables["S1-T02"], stage / "tables/S1-bootstrap.csv"))
    checks.append(verify_publication(stage))
    sources.extend(tables.values())
    sources.extend([example_path, stage / "tables/S1-bootstrap.csv", stage / "tables/S1-comparisons.csv"])
    outputs = [stage / path for path in ("publication.json", "source-bindings.json", "report.md", "report.html", "advice.md")]
    return reconciliation_receipt(stage, checks, sources=sources, outputs=outputs)
