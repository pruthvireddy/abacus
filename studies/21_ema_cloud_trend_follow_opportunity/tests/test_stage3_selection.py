import json
import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.stage3_selection import assess_candidates, select_nominees, validation_decisions, h15_support


def config():
    return json.loads((Path(__file__).resolve().parents[1] / "config-stage3.json").read_text())


def folds(phase="development", candidate_values=None):
    cfg = config()
    ids = [f["id"] for f in cfg["development_folds" if phase == "development" else "validation_folds"]]
    values = candidate_values or [2.] * len(ids)
    rows = []
    for gate, threshold in (("abs_2p4", 2.4), ("abs_3", 3.)):
        for fold, val in zip(ids + ["pooled"], values + [float(np.mean(values))]):
            rows.append(dict(product="ES", interval_minutes=3, touch_mode="fast", gate_id=gate,
                gate_family="absolute", gate_threshold=threshold, fold_id=fold,
                accepted=100 if fold != "pooled" else 400, scoring_accepted=100 if fold != "pooled" else 400,
                completed=100 if fold != "pooled" else 400, censored=0,
                contributing_sessions=20 if fold != "pooled" else 80,
                contributing_weeks=10 if fold != "pooled" else 40,
                mean_terminal_delta_atr=1. if gate == "abs_2p4" else val,
                mean_mfe_atr=2., mean_mae_atr=1.))
    return pd.DataFrame(rows)


class SelectionTest(unittest.TestCase):
    def test_equal_fold_score_not_pooled_mean_selects_frozen_objective(self):
        data = folds(candidate_values=[.5, 1.5, 1.5, 1.5])
        data.loc[data.gate_id.eq("abs_3") & data.fold_id.eq("pooled"), "mean_terminal_delta_atr"] = -100.
        assessment = assess_candidates(data, config(), phase="development")
        candidate = assessment.loc[assessment.gate_id.eq("abs_3")].iloc[0]
        self.assertEqual(candidate.selection_score, 1.25)
        self.assertEqual(candidate.overall_improvement, .25)
        self.assertTrue(candidate.eligible)
        self.assertEqual(select_nominees(assessment, config()).nominee_gate_id.iloc[0], "abs_3")

    def test_guard_boundaries_are_inclusive_and_strict_positive_is_not_tolerance(self):
        data = folds()
        candidate = data.gate_id.eq("abs_3")
        data.loc[candidate & data.fold_id.ne("pooled"), ["completed", "contributing_sessions"]] = [25, 10]
        data.loc[candidate & data.fold_id.eq("pooled"), ["completed", "contributing_sessions", "contributing_weeks", "mean_mfe_atr"]] = [200, 60, 20, 1.8]
        assessment = assess_candidates(data, config(), phase="development")
        row = assessment.loc[assessment.gate_id.eq("abs_3")].iloc[0]
        self.assertTrue(row.eligible)
        data.loc[candidate & data.fold_id.eq("pooled"), "contributing_weeks"] = 19
        self.assertIn("weeks", assess_candidates(data, config(), phase="development").loc[lambda x: x.gate_id.eq("abs_3"), "failed_guards"].iloc[0])
        data = folds(candidate_values=[1., 1., 1., 1.])
        self.assertFalse(assess_candidates(data, config(), phase="development").eligible.any())

    def test_any_undefined_comparison_fails_and_preserves_fallback(self):
        data = folds(); data.loc[data.gate_id.eq("abs_3") & data.fold_id.eq("2019H1"), "mean_terminal_delta_atr"] = np.nan
        assessment = assess_candidates(data, config(), phase="development")
        row = assessment.loc[assessment.gate_id.eq("abs_3")].iloc[0]
        self.assertFalse(row.guard_defined)
        choice = select_nominees(assessment, config()).iloc[0]
        self.assertTrue(choice.fallback)
        self.assertEqual((choice.nominee_gate_id, choice.nomination_status), ("abs_2p4", "no_eligible_improvement"))

    def test_ties_use_completed_family_threshold_then_id(self):
        base = assess_candidates(folds(), config(), phase="development").loc[lambda x: x.gate_id.eq("abs_3")].iloc[0].to_dict()
        candidates = [base | dict(gate_id="atr_0p1", gate_family="atr", gate_threshold=.1, completed=401),
                      base | dict(gate_id="abs_7p2", gate_threshold=7.2, completed=400, selection_score=2. + 5e-13),
                      base | dict(gate_id="abs_3p6", gate_threshold=3.6, completed=401),
                      base | dict(gate_id="abs_3", completed=401)]
        choice = select_nominees(pd.DataFrame(candidates), config()).iloc[0]
        self.assertEqual(choice.nominee_gate_id, "abs_3")
        candidates[0]["selection_score"] = 2. + 1e-10
        self.assertEqual(select_nominees(pd.DataFrame(candidates), config()).nominee_gate_id.iloc[0], "atr_0p1")

    def test_validation_uses_pooled_and_four_of_six_then_fixed_no_rescue(self):
        nominee = select_nominees(assess_candidates(folds(), config(), phase="development"), config())
        valid = folds("validation", [.5, .5, 2., 2., 2., 2.])
        assessment = assess_candidates(valid, config(), phase="validation")
        decisions = validation_decisions(assessment, nominee, config())
        self.assertEqual(decisions.selected_gate_id.iloc[0], "abs_3")
        valid.loc[valid.gate_id.eq("abs_3") & valid.fold_id.eq("pooled"), "mean_terminal_delta_atr"] = .9
        decisions = validation_decisions(assess_candidates(valid, config(), phase="validation"), nominee, config())
        self.assertEqual(decisions.selected_gate_id.iloc[0], "abs_2p4")
        self.assertEqual(decisions.validation_status.iloc[0], "fixed_fallback_validation_failed")

    def test_chained_near_ties_are_anchored_to_highest_score_independent_of_order(self):
        import itertools
        base = assess_candidates(folds(), config(), phase="development").loc[lambda x: x.gate_id.eq("abs_3")].iloc[0].to_dict()
        candidates = [base | dict(gate_id="abs_3", selection_score=1. + 1.8e-12, completed=200),
                      base | dict(gate_id="abs_3p6", selection_score=1. + .9e-12, completed=300),
                      base | dict(gate_id="abs_4p8", selection_score=1., completed=400)]
        for order in itertools.permutations(candidates):
            choice = select_nominees(pd.DataFrame(order), config()).iloc[0]
            self.assertEqual(choice.nominee_gate_id, "abs_3p6")
            self.assertEqual((choice.eligible_candidates, choice.tied_to_highest_count), (3, 2))

    def test_sparse_fold_fails_even_when_pooled_is_large(self):
        data = folds(); data.loc[data.gate_id.eq("abs_3") & data.fold_id.eq("2020H2"), "completed"] = 24
        assessment = assess_candidates(data, config(), phase="development")
        self.assertIn("fold_completed", assessment.loc[assessment.gate_id.eq("abs_3"), "failed_guards"].iloc[0])

    def test_duplicate_missing_baseline_fold_fails_instead_of_silent_mean(self):
        data = folds()
        with self.assertRaises(ValueError):
            assess_candidates(data.loc[~(data.gate_id.eq("abs_2p4") & data.fold_id.eq("2019H1"))], config(), phase="development")
        with self.assertRaises(ValueError):
            assess_candidates(pd.concat([data, data.iloc[:1]], ignore_index=True), config(), phase="development")

    def test_every_risk_and_retention_guard_fails_without_relaxation(self):
        changes = (("completed", 199, "completed"), ("contributing_sessions", 59, "sessions"),
            ("contributing_weeks", 19, "weeks"), ("mean_mae_atr", 1.00001, "mae"),
            ("mean_mfe_atr", 1.79999, "mfe"))
        for col, value, guard in changes:
            with self.subTest(guard=guard):
                data = folds()
                data.loc[data.gate_id.eq("abs_3") & data.fold_id.eq("pooled"), col] = value
                result = assess_candidates(data, config(), phase="development").loc[lambda x: x.gate_id.eq("abs_3")].iloc[0]
                self.assertFalse(result.eligible)
                self.assertIn(guard, result.failed_guards)
        data = folds()
        data.loc[data.gate_id.eq("abs_2p4") & data.fold_id.eq("pooled"), "completed"] = 2001
        self.assertFalse(assess_candidates(data, config(), phase="development").loc[lambda x: x.gate_id.eq("abs_3"), "guard_retention"].iloc[0])
        data = folds(candidate_values=[.9, .9, 2., 2.])
        self.assertFalse(assess_candidates(data, config(), phase="development").loc[lambda x: x.gate_id.eq("abs_3"), "guard_positive_folds"].iloc[0])

    def test_support_does_not_intersect_candidate_and_fixed_accepted_times(self):
        out = pd.DataFrame(dict(horizon=[15] * 4, score_eligible=[True, True, False, True], atr_support=[True, True, True, False],
            status=["completed"] * 4, session=["s1", "s2", "s3", "s4"], week=["w1", "w2", "w3", "w4"],
            terminal_delta_atr=[1., 3., 100., 100.], mfe_atr=[2., 4., 100., 100.], mae_atr=[1., 1., 100., 100.]))
        result = h15_support(out)
        self.assertEqual((result["accepted"], result["completed"], result["mean_terminal_delta_atr"]), (4, 2, 2.))


if __name__ == "__main__":
    unittest.main()
