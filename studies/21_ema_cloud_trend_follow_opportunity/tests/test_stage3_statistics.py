import sys
import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.stage3_statistics import (calendar_weights, weekly_sufficient, period_effects, grid_comparisons,
                                 neighborhoods, summaries, stability, _write_csv, produce_development, evaluate_period)
from src.stage3_masks import calendar_weeks, ScoringPeriod
from test_stage3_selection import config
from test_stage3_masks import roster, events
from test_stage3_outcomes import score
from test_stage3_outcomes import Authorization


def population():
    rows = []
    for gate, weeks, vals in (("abs_2p4", ["2024-01-01", "2024-01-08"], [1., 2.]),
                             ("abs_3", ["2024-01-01", "2024-01-15"], [3., 4.])):
        for j, (week, val) in enumerate(zip(weeks, vals)):
            rows.append(dict(product="ES", interval_minutes=3, touch_mode="fast", gate_id=gate,
                event_id=gate + str(j), horizon=15, score_eligible=True, atr_support=True, status="completed",
                side="Buy", week=week, session=week, mfe=val + 1, mae=.5, terminal_delta=val,
                mfe_atr=val + 1, mae_atr=.5, terminal_delta_atr=val))
    return pd.DataFrame(rows)


class StatisticsTest(unittest.TestCase):
    def test_weights_exact_independent_sample_indices_and_zero_weeks(self):
        weeks, actual = calendar_weights("2024-01-01", "2026-01-01", resamples=23, block_weeks=4)
        n = len(weeks)
        rng = np.random.default_rng(20261010)
        starts = rng.integers(0, n, (23, (n + 3) // 4))
        expected = np.zeros((23, n))
        for r in range(23):
            sampled = []
            for start in starts[r]:
                sampled.extend((int(start) + k) % n for k in range(4))
            for w in sampled[:n]:
                expected[r, w] += 1
        np.testing.assert_array_equal(actual, expected)
        self.assertTrue((actual.sum(axis=1) == 105).all())

    def test_whole_session_mean_then_trading_date_week(self):
        out = pd.DataFrame(dict(session=["2024-01-08", "2024-01-08", "2024-01-09"],
            week=["2024-01-01", "2024-01-08", "2024-01-08"], terminal_delta_atr=[2., 6., 10.]))
        weeks = calendar_weeks("2024-01-01", "2026-01-01")
        weekly, mean = weekly_sufficient(out, weeks, "terminal_delta", "atr", "session")
        self.assertEqual(mean, 7.)
        self.assertEqual((weekly.loc["2024-01-08", "sum"], weekly.loc["2024-01-08", "count"]), (14., 2))
        self.assertEqual(weekly.loc["2024-01-01", "count"], 0)
        outside = out.copy(); outside.loc[0, "session"] = "2023-12-25"
        with self.assertRaises(ValueError):
            weekly_sufficient(outside, weeks, "terminal_delta", "atr", "session")

    def test_paired_primary_exact_twelve_tails_and_independent_draws(self):
        cfg = config(); cfg["horizons"] = [15]; cfg["bootstrap"]["resamples"] = 100
        choices = pd.DataFrame([dict(product="ES", interval_minutes=3, touch_mode="fast", selected_gate_id="abs_3", fixed_gate_id="abs_2p4")])
        out = population()
        effects, sufficient = period_effects(out, choices, cfg, "final")
        primary = effects.loc[effects.interval_kind.eq("bonferroni12") & effects.block_weeks.eq(4)].iloc[0]
        self.assertEqual(primary.quantile_low, .05 / 24)
        self.assertEqual(primary.quantile_high, 1 - .05 / 24)
        weeks, weights = calendar_weights("2024-01-01", "2026-01-01", resamples=100)
        totals = []
        for gate in ("abs_3", "abs_2p4"):
            part = out.loc[out.gate_id.eq(gate)]
            vals, counts = np.zeros(len(weeks)), np.zeros(len(weeks))
            for event in part.to_dict("records"):
                idx = weeks.index(event["week"]); vals[idx] += event["terminal_delta_atr"]; counts[idx] += 1
            denom = weights @ counts
            totals.append(np.divide(weights @ vals, denom, out=np.full(100, np.nan), where=denom > 0))
        draws = totals[0] - totals[1]; finite = draws[np.isfinite(draws)]
        expected = np.quantile(finite, [.05 / 24, 1 - .05 / 24], method="linear")
        self.assertEqual((primary.ci_low, primary.ci_high), tuple(expected))
        self.assertEqual(primary.undefined_draws, 100 - len(finite))
        self.assertEqual(len(sufficient), 4 * len(weeks))

    def test_estimable_identity_fallback_zero_ci_undefined_is_null(self):
        cfg = config(); cfg["horizons"] = [15]; cfg["bootstrap"]["resamples"] = 40
        choices = pd.DataFrame([dict(product="ES", interval_minutes=3, touch_mode="fast", selected_gate_id="abs_2p4", fixed_gate_id="abs_2p4")])
        out = population(); effects, _ = period_effects(out, choices, cfg, "final")
        primary = effects.loc[effects.interval_kind.eq("bonferroni12")]
        self.assertTrue(primary.estimate.eq(0).all())
        self.assertTrue(primary.ci_low.eq(0).all() and primary.ci_high.eq(0).all())
        out["score_eligible"] = False
        effects, _ = period_effects(out, choices, cfg, "final")
        primary = effects.loc[effects.interval_kind.eq("bonferroni12")]
        self.assertTrue(primary.estimate.isna().all() and primary.ci_low.isna().all())
        self.assertTrue(primary.undefined_draws.eq(40).all())

    def test_common_atr_filter_is_after_acceptance_and_full_absolute_retained(self):
        bars = roster(6); ev = events(bars, [0, 1]); ev.loc[0, "entry_atr"] = 0.
        out = score(bars, ev, (1,))
        payload = dict(product="ES", interval_minutes=3, touch_mode="fast", gate=dict(gate_id="abs_2p4", family="absolute", threshold=2.4))
        table = summaries(out, payload, "development", [1])
        common = table.loc[table.direction.eq("All") & table.unit.eq("atr") & table.support.eq("common_atr_valid")].iloc[0]
        full = table.loc[table.direction.eq("All") & table.unit.eq("points") & table.support.eq("full_absolute")].iloc[0]
        self.assertEqual((common.accepted_total, common.evaluable, full.evaluable), (2, 1, 2))

    def test_neighbors_and_frontier_use_same_horizon_within_family(self):
        cfg = config()
        rows = []
        for gate, threshold, terminal, adverse, n in (("abs_2p4", 2.4, 1., 2., 100), ("abs_3", 3., 2., 1., 110), ("abs_3p6", 3.6, 3., 3., 20)):
            rows.append(dict(stage=3, period_id="development", product="ES", interval_minutes=3, touch_mode="fast", gate_id=gate,
                gate_family="absolute", gate_threshold=threshold, direction="All", horizon=15, unit="atr", support="common_atr_valid",
                evaluable=n, mean_terminal_delta=terminal, mean_mfe=3., mean_mae=adverse, row_id=gate))
        grid = grid_comparisons(pd.DataFrame(rows), cfg)
        result = neighborhoods(grid).set_index("gate_id")
        self.assertFalse(result.loc["abs_2p4", "pareto_frontier"])
        self.assertTrue(result.loc["abs_3", "pareto_frontier"])
        self.assertEqual(result.loc["abs_3", "previous_gate_id"], "abs_2p4")
        self.assertEqual(result.loc["abs_3", "next_gate_id"], "abs_3p6")
        self.assertFalse(result.loc["abs_3", "stable_positive_neighborhood"])

    def test_output_guard_rejects_overwrite_and_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            table = pd.DataFrame([dict(row_id="a", value=1.)])
            _write_csv(Path(tmp), "x.csv", table)
            with self.assertRaises(ValueError):
                _write_csv(Path(tmp), "x.csv", table)
            with self.assertRaises(ValueError):
                _write_csv(Path(tmp), "y.csv", pd.concat([table, table]))

    def test_frontier_compares_families_but_neighbors_stay_within_family(self):
        cfg = config()
        base = dict(stage=3, period_id="development", product="ES", interval_minutes=3, touch_mode="fast",
            direction="All", horizon=15, unit="atr", support="common_atr_valid", mean_mfe=3.)
        rows = [base | dict(gate_id="abs_2p4", gate_family="absolute", gate_threshold=2.4,
            evaluable=100, mean_terminal_delta=1., mean_mae=2., row_id="fixed"),
            base | dict(gate_id="atr_0p1", gate_family="atr", gate_threshold=.1,
            evaluable=110, mean_terminal_delta=2., mean_mae=1., row_id="atr")]
        table = neighborhoods(grid_comparisons(pd.DataFrame(rows), cfg)).set_index("gate_id")
        self.assertFalse(table.loc["abs_2p4", "pareto_frontier"])
        self.assertTrue(table.loc["atr_0p1", "pareto_frontier"])
        self.assertEqual(table.neighbor_count.tolist(), [0, 0])
        self.assertTrue(table.frontier_scope.eq("all_gate_families_same_cell_horizon").all())

    def test_volatility_cuts_use_common_input_roster_lower_ties_and_empty_bins(self):
        from src.engine import _strata
        cfg = config()
        bars = roster(8); bars["atr14"] = [1., 2., 2., 4., 5., 6., 6., 8.]
        tech = _strata(bars.copy()); tech["feature_valid"] = True
        ev = events(bars, [1, 5]); ev["entry_atr"] = [2., 6.]
        out = score(bars, ev, (15,))
        payload = dict(product="ES", interval_minutes=3, touch_mode="fast", bars=bars, technical=tech,
            events=ev, gate=dict(gate_id="abs_2p4", family="absolute", threshold=2.4))
        table = stability(out, payload, "development", cfg)
        bins = table.loc[table.period_kind.eq("volatility_bin")].set_index("period")
        self.assertEqual(bins.atr_q25.tolist(), [2.] * 5)
        self.assertEqual(bins.atr_q75.tolist(), [6.] * 5)
        self.assertEqual((bins.loc["Q1", "accepted"], bins.loc["Q3", "accepted"]), (1, 1))
        self.assertEqual(bins.scheduled_slots.sum(), 8)
        self.assertEqual(bins.eligible_atr_slots.sum(), 8)
        # Changing event outcomes cannot change input quartile thresholds.
        changed = out.copy(); changed["terminal_delta_atr"] = 999.
        pd.testing.assert_series_equal(stability(changed, payload, "development", cfg).atr_q50, table.atr_q50)
        payload["technical"]["atr14"] = 5.
        out["entry_atr"] = 5.
        collapsed = stability(out, payload, "development", cfg).loc[lambda x: x.period_kind.eq("volatility_bin")].set_index("period")
        self.assertEqual(collapsed.loc["Q1", "scheduled_slots"], 8)
        self.assertEqual(collapsed.loc["Q2", "scheduled_slots"], 0)
        self.assertTrue(np.isnan(collapsed.loc["Q2", "mean_terminal_delta"]))

    def test_disposable_development_pipeline_retains_all_masks_and_fallback(self):
        from src.engine import _strata
        cfg = config()
        cfg["products"], cfg["interval_minutes"], cfg["touch_modes"] = ["ES"], [3], ["fast"]
        cfg["horizons"] = [1, 15]
        cfg["absolute_gates"]["ES"], cfg["atr_gates"] = [2.4, 3.], []
        bars = roster()
        tech = _strata(bars.copy())
        tech["side"] = "Buy"
        tech["feature_valid"], tech["accepted"] = True, False
        tech["technical_candidate"], tech["setup_candidate"], tech["suppression_reason"] = False, False, "not_touch"
        tech.loc[101, ["accepted", "technical_candidate", "setup_candidate", "suppression_reason"]] = [True, True, True, "accepted"]
        auth = Authorization()
        auth.gates = (("ES", 3, "fast", "abs_2p4"), ("ES", 3, "fast", "abs_3"))
        payloads = [dict(product="ES", interval_minutes=3, touch_mode="fast", bars=bars, technical=tech,
            events=events(bars, [101]), gate=dict(gate_id=gate, family="absolute", threshold=t)) for gate, t in (("abs_2p4", 2.4), ("abs_3", 3.))]
        with tempfile.TemporaryDirectory() as tmp:
            receipt = produce_development(Path(tmp), cfg, iter(payloads), auth)
            self.assertEqual(len(receipt["records"]), 2)
            grid = pd.read_csv(Path(tmp) / "tables/S3-T11_development_grid.csv")
            self.assertEqual(len(grid), 4)
            choices = receipt["choices"]
            self.assertEqual(choices.nomination_status.iloc[0], "no_eligible_improvement")
            self.assertEqual(choices.selected_gate_id.iloc[0], "abs_2p4")
            masks = pd.read_csv(Path(tmp) / "tables/S3-T16_development_masks.csv")
            self.assertEqual(len(masks), 24)
            self.assertTrue((masks.accepted == masks.completed + masks.censored + masks.excluded).all())
            for record in receipt["records"]:
                self.assertFalse(Path(record["path"]).is_absolute())

    def test_reserved_choice_inventory_rejects_alternate_before_iterator(self):
        cfg = config()
        choices = pd.DataFrame([dict(product="ES", interval_minutes=3, touch_mode="fast", selected_gate_id="abs_3", final_gate_id="abs_3", fixed_gate_id="abs_2p4")])
        auth = Authorization("final", end="2026-01-01", start="2024-01-01")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "choice inventory"):
                evaluate_period(Path(tmp), cfg, choices, "final", auth, iter(()))

    def test_disposable_validation_fallback_manifest_uses_json_null(self):
        import json
        from src.engine import _strata
        cfg = config(); cfg["horizons"] = [15]; cfg["bootstrap"]["resamples"] = 25
        bars = roster()
        delta = pd.Timestamp("2021-01-01T05:00Z") - bars.timestamp.iloc[0]
        bars["timestamp"], bars["available_at"] = bars.timestamp + delta, bars.available_at + delta
        bars["session"] = "2021-01-01"
        ev = events(bars, [101]); ev["session"], ev["week"], ev["month"], ev["year"] = "2021-01-01", "2020-12-28", "2021-01", 2021
        tech = _strata(bars.copy()); tech["side"] = "Buy"
        tech["feature_valid"], tech["accepted"] = True, False
        tech["technical_candidate"], tech["setup_candidate"], tech["suppression_reason"] = False, False, "not_touch"
        payload = dict(product="ES", interval_minutes=3, touch_mode="fast", bars=bars, technical=tech,
            events=ev, gate=dict(gate_id="abs_2p4", family="absolute", threshold=2.4))
        choice = pd.DataFrame([dict(product="ES", interval_minutes=3, touch_mode="fast", selected_gate_id="abs_2p4",
            nominee_gate_id="abs_2p4", fixed_gate_id="abs_2p4", nomination_status="no_eligible_improvement",
            selection_score=np.nan, selection_improvement=np.nan, selected_gate_family="absolute", selected_gate_threshold=2.4)])
        auth = Authorization("validation", start="2021-01-01", end="2024-01-01")
        with tempfile.TemporaryDirectory() as tmp:
            result = evaluate_period(Path(tmp), cfg, choice, "validation", auth, iter([payload]))
            manifest = json.loads((Path(tmp) / "stage3-validation.manifest.json").read_text())
            self.assertIsNone(manifest["choices"][0]["selection_score"])
            self.assertEqual(manifest["choices"][0]["validation_improvement"], 0.)
            self.assertEqual(result["choices"].final_gate_id.iloc[0], "abs_2p4")
            self.assertEqual(result["choices"].validation_status.iloc[0], "fixed_fallback_no_eligible_nominee")
            effects = pd.read_csv(Path(tmp) / "tables/S3-T14_validation_effects.csv")
            ci = effects.loc[effects.interval_kind.eq("pointwise95")]
            self.assertTrue(ci.estimate.eq(0).all())
            self.assertFalse(effects.interval_kind.eq("bonferroni12").any())


if __name__ == "__main__":
    unittest.main()
