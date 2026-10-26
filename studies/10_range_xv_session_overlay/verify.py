"""Independent arithmetic checks against the three immutable source runs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.stats import ALL_SEGMENTS, SEGMENTS, named_window, segment
from run import CHARTS, IDEAS, checked_inputs


def integers_equal(a, b) -> bool:
    return int(round(a)) == int(round(b))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, type=Path)
    args = parser.parse_args()
    stage = args.stage.resolve()
    root = Path(__file__).resolve().parents[2]
    lock = json.loads((stage / "inputs.lock.json").read_text())
    audit = json.loads((stage / "audit.json").read_text())
    checked = checked_inputs(root, lock)
    assert [(x["path"], x["sha256"]) for x in checked] == [
        (x["path"], x["sha256"]) for x in audit["verified_inputs"]]
    tables = stage / "tables"
    s07 = pd.read_csv(tables / "07_summary.csv")
    p07 = pd.read_csv(tables / "07_period.csv")
    s08 = pd.read_csv(tables / "08_summary.csv")
    p08 = pd.read_csv(tables / "08_period.csv")
    b08 = pd.read_csv(tables / "08_prior_bin.csv")
    s09 = pd.read_csv(tables / "09_summary.csv")
    p09 = pd.read_csv(tables / "09_period.csv")
    o09 = pd.read_csv(tables / "09_opportunity.csv")
    age09 = pd.read_csv(tables / "09_age_two.csv")
    assert (len(s07), len(p07), len(s08), len(p08), len(b08), len(s09), len(p09), len(o09), len(age09)) == (
        36, 81, 56, 126, 168, 56, 126, 336, 56)
    assert set(s07.segment) == set(s08.segment) == set(s09.segment) == set(ALL_SEGMENTS)
    assert int(s07.standout.sum()) == audit["screens"]["study07"]["standouts"]
    assert int(s08.standout.sum()) == audit["screens"]["study08"]["standouts"]
    assert int(s09.standout.sum()) == audit["screens"]["study09"]["standouts"]

    base07 = root / lock["source_runs"]["07"]
    original07 = pd.read_csv(base07 / "tables" / "primary_summary.csv")
    for product in ("ES", "GC", "NQ"):
        events = pd.read_parquet(base07 / f"events_{product}.parquet",
                                 columns=["idea", "cohort", "session_date", "signal_index",
                                          "return_ticks", "traded"])
        corrected = next(x for x in lock["files"] if x["role"] == f"study07_normalized_{product}")
        bars = pd.read_csv(root / corrected["path"], sep=";", usecols=[
            "source_row", "bar_completion_timestamp_proxy", "session_date_proxy"])
        for trace in audit["study07_clock_mapping"][product]["trace"]:
            bar = bars.iloc[trace["signal_index"]]
            assert int(bar.source_row) == trace["signal_index"] + 1
            assert bar.session_date_proxy == trace["session_date"]
            assert bar.bar_completion_timestamp_proxy == trace["corrected_completion"]
            assert segment(bar.bar_completion_timestamp_proxy) == trace["segment"]
        assert len(events) == audit["study07_clock_mapping"][product]["events"]
        for idea, (candidate, control) in IDEAS.items():
            for cohort in (candidate, control):
                part = events.loc[events.idea.eq(idea) & events.cohort.eq(cohort)]
                old = original07.loc[original07["product"].eq(product) &
                    original07.idea.eq(idea) & original07.cohort.eq(cohort) &
                    original07.split.eq("all")].iloc[0]
                rows = s07.loc[s07["product"].eq(product) & s07.idea.eq(idea)]
                if cohort == candidate:
                    assert integers_equal(rows.denominator.sum(), len(part))
                    assert integers_equal(rows.candidate_trades.sum(), part.traded.sum())
                    assert abs(np.average(rows.candidate_gross_mean, weights=rows.denominator) -
                               old.mean_ticks) < 1e-5
                    assert abs(np.average(rows.estimate, weights=rows.denominator) -
                               old.mean_net_2_ticks) < 1e-5
                else:
                    assert integers_equal(rows.baseline_denominator.sum(), len(part))
                    assert integers_equal(rows.control_trades.sum(), part.traded.sum())
            for label in SEGMENTS:
                row = s07.loc[s07["product"].eq(product) & s07.idea.eq(idea) &
                              s07.segment.eq(label)].iloc[0]
                period = p07.loc[p07["product"].eq(product) & p07.idea.eq(idea) &
                                 p07.segment.eq(label)]
                assert len(period) == 3
                assert integers_equal(period.denominator.sum(), row.denominator)
                assert integers_equal(period.baseline_denominator.sum(), row.baseline_denominator)

    base08 = root / lock["source_runs"]["08"] / "tables"
    original08 = pd.read_csv(base08 / "lookup.csv")
    for product, setting in CHARTS:
        for direction in (-1, 1):
            rows = s08.loc[s08["product"].eq(product) & s08.setting.eq(setting) &
                            s08.direction.eq(direction)]
            assert len(rows) == 4
            for prior_bin in ("3-4", "5-7", "8+"):
                bins = b08.loc[b08["product"].eq(product) & b08.setting.eq(setting) &
                               b08.direction.eq(direction) & b08.prior_bin.eq(prior_bin)]
                original = original08.loc[original08["product"].eq(product) &
                    original08.setting.eq(setting) & original08.direction.eq(direction) &
                    original08.prior_bin.eq(prior_bin) & original08.metric.eq("p2")]
                assert len(bins) == 4 and len(original) == 5
                assert integers_equal(bins.denominator.sum(), original.denominator.sum())
                assert integers_equal(bins.numerator.sum(), original.numerator.sum())
                for label in ALL_SEGMENTS:
                    expected = original.loc[original.session_window.map(named_window).eq(label)]
                    actual = bins.loc[bins.segment.eq(label)].iloc[0]
                    assert integers_equal(actual.denominator, expected.denominator.sum())
                    assert integers_equal(actual.numerator, expected.numerator.sum())
            assert integers_equal(rows.denominator.sum(), b08.loc[
                b08["product"].eq(product) & b08.setting.eq(setting) &
                b08.direction.eq(direction)].denominator.sum())
            for label in SEGMENTS:
                row = rows.loc[rows.segment.eq(label)].iloc[0]
                part = p08.loc[p08["product"].eq(product) & p08.setting.eq(setting) &
                               p08.direction.eq(direction) & p08.segment.eq(label)]
                assert len(part) == 3
                assert integers_equal(row.denominator, part.denominator.sum())
                assert integers_equal(row.numerator, part.numerator.sum())

    base09 = root / lock["source_runs"]["09"] / "tables"
    original09 = pd.read_csv(base09 / "comparison.csv")
    original_age = pd.read_csv(base09 / "age2_comparison.csv")
    original_opportunities = pd.read_csv(base09 / "opportunity_window.csv")
    original_price = pd.read_csv(base09 / "price.csv")
    for product, setting in CHARTS:
        for direction in (-1, 1):
            identity = (s09["product"].eq(product) & s09.setting.eq(setting) &
                        s09.direction.eq(direction))
            rows = s09.loc[identity]
            assert len(rows) == 4
            original = original09.loc[original09["product"].eq(product) &
                original09.setting.eq(setting) & original09.direction.eq(direction) &
                original09.metric.eq("next2")]
            assert len(original) == 5
            for label in ALL_SEGMENTS:
                expected = original.loc[original.decision_window.map(named_window).eq(label)]
                actual = rows.loc[rows.segment.eq(label)].iloc[0]
                assert integers_equal(actual.denominator, expected.denominator.sum())
                assert integers_equal(actual.numerator, expected.numerator.sum())
                assert integers_equal(actual.ordinary_baseline_denominator,
                                      expected.baseline_denominator.sum())
                assert integers_equal(actual.ordinary_baseline_numerator,
                                      expected.baseline_numerator.sum())
                age_expected = original_age.loc[original_age["product"].eq(product) &
                    original_age.setting.eq(setting) & original_age.direction.eq(direction) &
                    original_age.metric.eq("next2") &
                    original_age.decision_window.map(named_window).eq(label)]
                age_actual = age09.loc[age09["product"].eq(product) &
                    age09.setting.eq(setting) & age09.direction.eq(direction) &
                    age09.segment.eq(label)].iloc[0]
                assert integers_equal(age_actual.denominator, age_expected.denominator.sum())
                assert integers_equal(age_actual.numerator, age_expected.numerator.sum())
                assert integers_equal(age_actual.baseline_denominator,
                                      age_expected.baseline_denominator.sum())
                assert integers_equal(age_actual.baseline_numerator,
                                      age_expected.baseline_numerator.sum())
                for metric, original_metric in (("c2_confirms", "c2_confirms"),
                    ("immediate_two_per_c1", "immediate_two_per_c1"),
                    ("wait_two_per_c1", "wait_two_per_c1")):
                    row = o09.loc[o09["product"].eq(product) & o09.setting.eq(setting) &
                        o09.direction.eq(direction) & o09.segment.eq(label) &
                        o09.metric.eq(metric)].iloc[0]
                    prior = original_opportunities.loc[original_opportunities["product"].eq(product) &
                        original_opportunities.setting.eq(setting) &
                        original_opportunities.direction.eq(direction) &
                        original_opportunities.metric.eq(original_metric) &
                        original_opportunities.c1_window.map(named_window).eq(label)]
                    assert integers_equal(row.denominator, prior.denominator.sum())
                    assert integers_equal(row.numerator, prior.numerator.sum())
            for metric, policy in (("immediate_mean_ticks", "immediate_per_c1"),
                                   ("wait_mean_ticks_per_c1", "wait_per_c1")):
                prices = o09.loc[o09["product"].eq(product) & o09.setting.eq(setting) &
                    o09.direction.eq(direction) & o09.metric.eq(metric)]
                prior = original_price.loc[original_price["product"].eq(product) &
                    original_price.setting.eq(setting) & original_price.direction.eq(direction) &
                    original_price.policy.eq(policy)].iloc[0]
                assert integers_equal(prices.denominator.sum(), prior.events)
                assert abs(np.average(prices.estimate, weights=prices.denominator) -
                           prior.mean_signed_ticks) < 1e-9
            for label in SEGMENTS:
                row = rows.loc[rows.segment.eq(label)].iloc[0]
                part = p09.loc[p09["product"].eq(product) & p09.setting.eq(setting) &
                               p09.direction.eq(direction) & p09.segment.eq(label)]
                assert len(part) == 3
                assert integers_equal(row.denominator, part.denominator.sum())
                assert integers_equal(row.ordinary_baseline_denominator,
                                      part.ordinary_baseline_denominator.sum())

    checks = {"status": "pass", "verified_input_files": len(checked),
              "study07_trace_count": sum(len(x["trace"]) for x in audit["study07_clock_mapping"].values()),
              "table_rows": audit["table_rows"], "screens": audit["screens"],
              "checks": ["all pinned sealed artifact and corrected-clock hashes",
                  "study 07 signal-row/session/clock traces and original whole-cohort payoff arithmetic",
                  "study 07 segment-to-period opportunity counts",
                  "study 08 prior-bin/window and segment/period count reconciliation",
                  "study 09 candidate/ordinary/age-two/window and common-C1 opportunity reconciliation",
                  "study 09 price means reconcile to sealed whole-chart means"]}
    (stage / "checks.json").write_text(json.dumps(checks, indent=2) + "\n")
    print(json.dumps({"status": "pass", "verified_inputs": len(checked),
                      "traces": checks["study07_trace_count"]}, indent=2))


if __name__ == "__main__":
    main()
