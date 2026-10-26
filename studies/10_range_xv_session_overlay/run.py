"""Analyze fixed Asia/London/New York segments in sealed 07–09 event ledgers."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from src.stats import (ALL_SEGMENTS, SEGMENTS, difference, estimate,
                       family_interval, grouped, named_window, segment, supported)


CHARTS = (("ES", 4), ("ES", 5), ("ES", 6), ("GC", 6), ("GC", 10),
          ("NQ", 10), ("NQ", 20))
IDEAS = {"pullback": ("extreme_break", "unfiltered"),
         "exhaustion": ("wait_policy", "early_policy"),
         "quiet_breakout": ("quiet", "not_quiet")}
BLOCKS_07 = ("development", "validation", "final")
BLOCKS_LONG = ("early", "middle", "recent")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def checked_inputs(root: Path, lock: dict) -> list[dict]:
    verified = []
    for record in lock["files"]:
        path = (root / record["path"]).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            raise FileNotFoundError(record["path"])
        actual = sha256(path)
        if actual != record["sha256"]:
            raise ValueError(f"input hash differs: {record['path']}")
        verified.append({"role": record["role"], "path": record["path"],
                         "sha256": actual, "bytes": path.stat().st_size})
    return verified


def stage_07(root: Path, lock: dict, tables: Path) -> tuple[list[dict], list[dict], dict]:
    rows, periods = [], []
    mapping = {}
    root07 = root / lock["source_runs"]["07"]
    for product in ("ES", "GC", "NQ"):
        events = pd.read_parquet(root07 / f"events_{product}.parquet")
        record = next(x for x in lock["files"] if x["role"] == f"study07_normalized_{product}")
        bars = pd.read_csv(root / record["path"], sep=";", usecols=[
            "source_row", "source_timestamp", "bar_completion_timestamp_proxy",
            "completion_proxy_status", "session_date_proxy"])
        assert len(bars) == record["rows"]
        assert np.array_equal(bars.source_row.to_numpy(), np.arange(1, len(bars) + 1))
        index = events.signal_index.to_numpy(dtype=np.int64)
        assert ((index >= 0) & (index < len(bars))).all()
        matched = bars.iloc[index].reset_index(drop=True)
        assert np.array_equal(matched.source_row.to_numpy(), index + 1)
        assert np.array_equal(matched.session_date_proxy.to_numpy(), events.session_date.to_numpy())
        assert np.array_equal(matched.source_timestamp.str[-8:].to_numpy(),
                              events.signal_clock.to_numpy())
        assert matched.completion_proxy_status.eq("next_bar_start_proxy").all()
        events["segment"] = matched.bar_completion_timestamp_proxy.map(segment).to_numpy()
        mapping[product] = {"events": len(events),
                            "corrected_clock_hash": record["sha256"],
                            "segment_counts": events.segment.value_counts().to_dict(),
                            "trace": [
                                {"signal_index": int(events.signal_index.iloc[i]),
                                 "session_date": str(events.session_date.iloc[i]),
                                 "old_signal_clock": str(events.signal_clock.iloc[i]),
                                 "corrected_completion": str(matched.bar_completion_timestamp_proxy.iloc[i]),
                                 "segment": str(events.segment.iloc[i])}
                                for i in sorted(set((0, len(events) // 2, len(events) - 1)))]}
        events["net_ticks"] = (events.return_ticks - 2 * events.traded.astype(int)).astype(float)
        for idea, (candidate_name, control_name) in IDEAS.items():
            idea_events = events.loc[events.idea.eq(idea)]
            for label in ALL_SEGMENTS:
                seg = idea_events.loc[idea_events.segment.eq(label)]
                candidate = seg.loc[seg.cohort.eq(candidate_name)]
                control = seg.loc[seg.cohort.eq(control_name)]
                identity = {"product": product, "idea": idea, "segment": label,
                            "candidate": candidate_name, "control": control_name}
                ca = estimate(grouped(candidate, candidate.net_ticks))
                gross = estimate(grouped(candidate, candidate.return_ticks))
                control_net = estimate(grouped(control, control.net_ticks))
                delta = difference(grouped(candidate, candidate.net_ticks),
                                   grouped(control, control.net_ticks), scale=1, family=27)
                family_low, family_high = family_interval(ca, 27)
                rows.append({**identity, **ca, **delta,
                             "candidate_gross_mean": gross["estimate"],
                             "candidate_trades": int(candidate.traded.sum()),
                             "control_trades": int(control.traded.sum()),
                             "candidate_net_family_low": family_low,
                             "candidate_net_family_high": family_high,
                             "screened": label in SEGMENTS})
                if label not in SEGMENTS:
                    continue
                for block in BLOCKS_07:
                    cb = candidate.loc[candidate.split.eq(block)]
                    bb = control.loc[control.split.eq(block)]
                    part = estimate(grouped(cb, cb.net_ticks))
                    periods.append({**identity, "block": block, **part,
                                    **difference(grouped(cb, cb.net_ticks),
                                                 grouped(bb, bb.net_ticks), scale=1, family=27)})
        del events, bars
    return rows, periods, mapping


def stage_08(root: Path, lock: dict) -> tuple[list[dict], list[dict], list[dict]]:
    rows, periods, bins = [], [], []
    base = root / lock["source_runs"]["08"] / "tables"
    columns = ["session_date", "block", "source_row", "direction", "prior_run", "prior_bin",
               "session_window", "c1_completion", "primary_eligible", "gc_gap_excluded",
               "c2_c3_follow"]
    for product, setting in CHARTS:
        events = pd.read_parquet(base / f"events_{product}_{setting}.parquet", columns=columns)
        events = events.loc[events.primary_eligible & events.prior_run.ge(3) &
                            ~events.gc_gap_excluded].copy()
        events["segment"] = events.session_window.map(named_window)
        assert np.array_equal(events.segment.to_numpy(),
                              events.c1_completion.map(segment).to_numpy())
        for direction in (-1, 1):
            directed = events.loc[events.direction.eq(direction)]
            named = directed.loc[directed.segment.isin(SEGMENTS)]
            for label in ALL_SEGMENTS:
                selected = directed.loc[directed.segment.eq(label)]
                other = named.loc[~named.segment.eq(label)] if label in SEGMENTS else named.iloc[0:0]
                identity = {"product": product, "setting": setting,
                            "direction": direction, "segment": label}
                values = grouped(selected, selected.c2_c3_follow)
                row = estimate(values, scale=100, clamp_rate=True)
                contrast = difference(values, grouped(other, other.c2_c3_follow),
                                      scale=100, family=42)
                rows.append({**identity, **row, **contrast,
                             "screened": label in SEGMENTS})
                for prior_bin in ("3-4", "5-7", "8+"):
                    slice_ = selected.loc[selected.prior_bin.eq(prior_bin)]
                    bins.append({**identity, "prior_bin": prior_bin,
                                 **estimate(grouped(slice_, slice_.c2_c3_follow),
                                            scale=100, clamp_rate=True)})
                if label not in SEGMENTS:
                    continue
                for block in BLOCKS_LONG:
                    a = selected.loc[selected.block.eq(block)]
                    b = other.loc[other.block.eq(block)]
                    ga, gb = grouped(a, a.c2_c3_follow), grouped(b, b.c2_c3_follow)
                    periods.append({**identity, "block": block,
                                    **estimate(ga, scale=100, clamp_rate=True),
                                    **difference(ga, gb, scale=100, family=42)})
    return rows, periods, bins


def stage_09(root: Path, lock: dict) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    rows, periods, opportunities, age_two = [], [], [], []
    base = root / lock["source_runs"]["09"] / "tables"
    opportunity_cols = ["session_date", "block", "c1_source_row", "c2_source_row",
        "direction", "prior_run", "c1_window", "decision_window", "c1_completion",
        "c2_completion", "main_prior", "common_eligible", "gc_gap_excluded",
        "c2_follows", "immediate_two_success", "wait_two_success",
        "immediate_signed_ticks", "wait_signed_ticks"]
    ordinary_cols = ["session_date", "block", "b2_source_row", "direction", "pair_run_age",
                     "decision_window", "b2_completion", "two_success", "gc_gap_excluded"]
    for product, setting in CHARTS:
        main = pd.read_parquet(base / f"opportunities_{product}_{setting}.parquet",
                               columns=opportunity_cols)
        main = main.loc[main.main_prior & main.common_eligible & ~main.gc_gap_excluded].copy()
        baseline = pd.read_parquet(base / f"ordinary_{product}_{setting}.parquet",
                                   columns=ordinary_cols)
        baseline = baseline.loc[~baseline.gc_gap_excluded].copy()
        main["c1_segment"] = main.c1_window.map(named_window)
        main["c2_segment"] = main.decision_window.map(named_window)
        baseline["segment"] = baseline.decision_window.map(named_window)
        assert np.array_equal(main.c1_segment.to_numpy(), main.c1_completion.map(segment).to_numpy())
        assert np.array_equal(main.c2_segment.to_numpy(), main.c2_completion.map(segment).to_numpy())
        assert np.array_equal(baseline.segment.to_numpy(), baseline.b2_completion.map(segment).to_numpy())
        confirmed = main.loc[main.c2_follows]
        assert not np.intersect1d(confirmed.c2_source_row.to_numpy(),
                                  baseline.b2_source_row.to_numpy()).size
        for direction in (-1, 1):
            co = confirmed.loc[confirmed.direction.eq(direction)]
            bo = baseline.loc[baseline.direction.eq(direction)]
            mo = main.loc[main.direction.eq(direction)]
            named = co.loc[co.c2_segment.isin(SEGMENTS)]
            for label in ALL_SEGMENTS:
                c = co.loc[co.c2_segment.eq(label)]
                b = bo.loc[bo.segment.eq(label)]
                other = named.loc[~named.c2_segment.eq(label)] if label in SEGMENTS else named.iloc[0:0]
                identity = {"product": product, "setting": setting,
                            "direction": direction, "segment": label}
                gc, gb = grouped(c, c.wait_two_success), grouped(b, b.two_success)
                rows.append({**identity, **estimate(gc, scale=100, clamp_rate=True),
                             **{f"ordinary_{k}": v for k, v in difference(gc, gb, scale=100,
                                 family=42).items()},
                             **{f"other_{k}": v for k, v in difference(gc,
                                 grouped(other, other.wait_two_success), scale=100,
                                 family=42).items()},
                             "screened": label in SEGMENTS})
                age = b.loc[b.pair_run_age.eq(2)]
                age_two.append({**identity,
                    **estimate(gc, scale=100, clamp_rate=True),
                    **difference(gc, grouped(age, age.two_success), scale=100, family=42),
                    "status": "post_result_exploratory"})
                if label in SEGMENTS:
                    for block in BLOCKS_LONG:
                        cb = c.loc[c.block.eq(block)]
                        bb = b.loc[b.block.eq(block)]
                        ob = other.loc[other.block.eq(block)]
                        gcb = grouped(cb, cb.wait_two_success)
                        periods.append({**identity, "block": block,
                                        **estimate(gcb, scale=100, clamp_rate=True),
                                        **{f"ordinary_{k}": v for k, v in difference(gcb,
                                            grouped(bb, bb.two_success), scale=100,
                                            family=42).items()},
                                        **{f"other_{k}": v for k, v in difference(gcb,
                                            grouped(ob, ob.wait_two_success), scale=100,
                                            family=42).items()}})
                original = mo.loc[mo.c1_segment.eq(label)]
                wait_ticks = np.where(original.c2_follows,
                                      original.wait_signed_ticks.fillna(0), 0)
                metrics = {"c2_confirms": (original.c2_follows.to_numpy(), 100),
                           "immediate_two_per_c1": (original.immediate_two_success.to_numpy(), 100),
                           "wait_two_per_c1": (original.wait_two_success.to_numpy(), 100),
                           "immediate_mean_ticks": (original.immediate_signed_ticks.to_numpy(), 1),
                           "wait_mean_ticks_per_c1": (wait_ticks, 1),
                           "wait_minus_immediate_ticks":
                               (wait_ticks - original.immediate_signed_ticks.to_numpy(), 1)}
                for metric, (values, scale) in metrics.items():
                    opportunities.append({**identity, "metric": metric,
                        **estimate(grouped(original, values), scale=scale,
                                   clamp_rate=scale == 100)})
    return rows, periods, opportunities, age_two


def screen_tables(tables: Path) -> dict:
    definitions = {
        "study07": ("07_summary", "07_period", "difference", "family_ci_low"),
        "study08": ("08_summary", "08_period", "difference", "family_ci_low"),
        "study09": ("09_summary", "09_period", "ordinary_difference",
                    "ordinary_family_ci_low"),
    }
    result = {}
    for study, (summary_name, period_name, delta_col, lower_col) in definitions.items():
        summary = pd.read_csv(tables / f"{summary_name}.csv")
        period = pd.read_csv(tables / f"{period_name}.csv")
        identifiers = ["product", "segment"] + (["idea"] if study == "study07" else
                       ["setting", "direction"])
        consistency = []
        other_consistency = []
        for _, row in summary.iterrows():
            if not row.screened:
                consistency.append(False)
                other_consistency.append(False)
                continue
            part = period
            for key in identifiers:
                part = part.loc[part[key].eq(row[key])]
            consistency.append(len(part) == 3 and (part.session_dates >= 30).all() and
                               (part[delta_col] > 0).all())
            if study == "study09":
                other_consistency.append(len(part) == 3 and (part.session_dates >= 30).all() and
                                         (part.other_difference > 0).all())
            else:
                other_consistency.append(False)
        summary["supported"] = ((summary.denominator >= 300) &
                                (summary.session_dates >= 100) &
                                (summary.events_per_session >= 2))
        summary["three_block_positive"] = consistency
        if study == "study07":
            summary["standout"] = (summary.screened & summary.supported &
                summary.candidate_net_family_low.gt(0) & summary.family_ci_low.gt(0) &
                summary.three_block_positive)
        else:
            summary["standout"] = (summary.screened & summary.supported &
                summary[lower_col].gt(0) & summary.three_block_positive)
        if study == "study09":
            summary["other_three_block_positive"] = other_consistency
            summary["segment_specific"] = (summary.standout &
                summary.other_family_ci_low.gt(0) & summary.other_three_block_positive)
        summary.to_csv(tables / f"{summary_name}.csv", index=False)
        result[study] = {"screened": int(summary.screened.sum()),
                         "supported": int((summary.screened & summary.supported).sum()),
                         "standouts": int(summary.standout.sum())}
        if study == "study09":
            result[study]["segment_specific"] = int(summary.segment_specific.sum())
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, type=Path)
    args = parser.parse_args()
    study = Path(__file__).resolve().parent
    root = study.parents[1]
    stage = args.stage.resolve()
    if not stage.is_relative_to((root / "work" / study.name).resolve()) or stage.exists():
        raise ValueError("stage must be a new directory under this study's work/")
    lock = json.loads((study / "inputs.lock.json").read_text())
    verified = checked_inputs(root, lock)
    stage.mkdir(parents=True)
    tables = stage / "tables"
    tables.mkdir()
    (stage / "inputs.lock.json").write_text(json.dumps(lock, indent=2) + "\n")
    (stage / "config.json").write_text(json.dumps({"plan": (study / "plan.md").read_text(),
        "study_yaml": (study / "study.yaml").read_text()}, indent=2) + "\n")
    rows07, periods07, mapping = stage_07(root, lock, tables)
    rows08, periods08, bins08 = stage_08(root, lock)
    rows09, periods09, opportunities09, age_two09 = stage_09(root, lock)
    outputs = {"07_summary": rows07, "07_period": periods07,
               "08_summary": rows08, "08_period": periods08, "08_prior_bin": bins08,
               "09_summary": rows09, "09_period": periods09,
               "09_opportunity": opportunities09, "09_age_two": age_two09}
    for name, rows in outputs.items():
        pd.DataFrame(rows).to_csv(tables / f"{name}.csv", index=False)
    screens = screen_tables(tables)
    audit = {"executed_at_utc": datetime.now(timezone.utc).isoformat(),
             "verified_inputs": verified, "study07_clock_mapping": mapping,
             "table_rows": {name: len(rows) for name, rows in outputs.items()},
             "screens": screens}
    (stage / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(screens, indent=2))
    print(stage)


if __name__ == "__main__":
    main()
