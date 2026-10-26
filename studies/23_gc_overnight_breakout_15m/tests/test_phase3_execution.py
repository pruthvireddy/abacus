"""Synthetic caller/writer checks, without opening historical Phase3 outcomes."""
from copy import deepcopy
from dataclasses import replace
import gzip
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from phase3_execution import POLICY_MODES,LEDGERS,_write_stream,_previous_equity,execute_phase
from src.phase3_engine import Phase3Config
from test_phase3_engine import fixture


def rows(path):
    with gzip.open(path,"rt") as f:return [json.loads(line) for line in f]


class Phase3ExecutionTests(unittest.TestCase):
    def test_real_capital_skips_and_unfunded_diagnostic_kept_separate(self):
        day=fixture();eid=day.episode_id
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/"phase"
            result=_write_stream(folder,{"primary-one-tick":{eid:day}},
                {eid:dict(day.baseline_trade)},("primary-one-tick",),lambda _:Phase3Config())
            episodes=rows(folder/"episodes.jsonl.gz")
            self.assertEqual(len(episodes),len(POLICY_MODES))
            overlay=next(r for r in episodes if r["policy"]=="A20" and r["mode"]=="financed_overlay")
            diag=next(r for r in episodes if r["policy"]=="A20" and r["mode"]=="diagnostic_1plus1")
            self.assertEqual((overlay["original_fills"],overlay["signals"],overlay["add_fills"]),(0,0,0))
            self.assertEqual((diag["original_fills"],diag["signals"],diag["add_fills"]),(1,1,1))
            self.assertTrue(all((folder/(name+".jsonl.gz")).is_file() for name in LEDGERS))
            self.assertEqual(result["row_counts"]["monitoring"],len(rows(folder/"monitoring.jsonl.gz")))
            self.assertLess(result["row_counts"]["monitoring"],200)
            self.assertTrue(all(r["scenario"]=="primary-one-tick" for r in rows(folder/"monitoring.jsonl.gz")))
            self.assertGreater(result["row_counts"]["profiles"],2)
            with self.assertRaises(FileExistsError):
                _write_stream(folder,{"primary-one-tick":{eid:day}},{eid:day.baseline_trade},("primary-one-tick",),lambda _:Phase3Config())

    def test_fixed_roster_across_scenarios_refuses_silent_drop(self):
        day=fixture();eid=day.episode_id
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,"roster"):
                _write_stream(Path(tmp)/"p",{"primary-one-tick":{eid:day},"other":{}},
                    {eid:day.baseline_trade},("primary-one-tick","other"),lambda _:Phase3Config())

    def test_prior_unknown_account_state_remains_unknown_after_boundary(self):
        day=fixture();eid=day.episode_id
        seen=[]
        def fake(context,policy,cfg,*,mode,equity_start,**unused):
            seen.append(equity_start)
            return {"episode":{"episode_id":context.episode_id,"broker_day":context.broker_day,
                "policy":policy,"mode":mode,"scenario":cfg.scenario,"status":"unknown",
                "net_dollars":None,"ending_equity":None},
                **{name:[] for name in ("events","orders","trades","exposure","monitoring")}}
        with tempfile.TemporaryDirectory() as tmp,patch("phase3_execution.POLICY_MODES",(("A20","financed_overlay"),)),patch("phase3_execution.run_episode",fake):
            result=_write_stream(Path(tmp)/"p",{"primary-one-tick":{eid:day}},
                {eid:day.baseline_trade},("primary-one-tick",),lambda _:Phase3Config(),
                initial_equities={("primary-one-tick","A20","financed_overlay"):None})
            self.assertEqual(seen,[None])
            self.assertIsNone(result["account_end_states"][0]["equity"])

    def test_previous_equity_latest_per_separate_account_including_null(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"phases/dev-validation/episodes.jsonl.gz";p.parent.mkdir(parents=True)
            with gzip.open(p,"wt") as f:
                for r in ({"scenario":"primary-one-tick","policy":"A20","mode":"financed_overlay","ending_equity":10000},
                          {"scenario":"primary-one-tick","policy":"A20","mode":"financed_overlay","ending_equity":None},
                          {"scenario":"net-zero-ticks","policy":"A20","mode":"financed_overlay","ending_equity":10020}):
                    f.write(json.dumps(r)+"\n")
            state=_previous_equity(tmp)
            self.assertIsNone(state[("primary-one-tick","A20","financed_overlay")])
            self.assertEqual(state[("net-zero-ticks","A20","financed_overlay")],10020)

    def test_secondary_trace_retention_is_explicit_and_summary_computed(self):
        day=fixture();eid=day.episode_id
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"p"
            result=_write_stream(p,{"primary-one-tick":{eid:day},"secondary":{eid:day}},
                {eid:day.baseline_trade},("primary-one-tick","secondary"),
                lambda name:Phase3Config(scenario=name))
            secondary=[r for r in rows(p/"exposure.jsonl.gz") if r["scenario"]=="secondary"]
            self.assertTrue(secondary and all(r["trace_retention"]=="terminal_only" for r in secondary))
            self.assertTrue(all(r["scenario"]=="primary-one-tick" for r in rows(p/"monitoring.jsonl.gz")))
            self.assertLess(result["trace_counts"]["secondary"]["retained_exposure_rows"],result["trace_counts"]["secondary"]["computed_exposure_rows"])
            episodes=[r for r in rows(p/"episodes.jsonl.gz") if r["scenario"]=="secondary" and r["policy"]=="BASE" and r["mode"]=="parent_1"]
            self.assertGreater(episodes[0]["max_mtm_drawdown_dollars"],0)
            self.assertEqual(episodes[0]["exposure_trace_retention"],"terminal_only")

    def test_later_cannot_open_without_selection(self):
        with tempfile.TemporaryDirectory() as tmp,patch("phase3_run.assert_freeze",return_value={}):
            with self.assertRaises(FileNotFoundError):execute_phase(tmp,"later")
            self.assertFalse((Path(tmp)/"phases/later").exists())

    def test_known_saved_context_available_snapshot_and_no_trading_combination(self):
        day=fixture();eid=day.episode_id
        event={"episode_id":eid,"event_kind":"protected_touch","decision_at":"2018-01-03T04:15:00Z", "source_reference":"synthetic-saved-occurrence"}
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"p"
            _write_stream(p,{"primary-one-tick":{eid:day}},{eid:day.baseline_trade},("primary-one-tick",),lambda _:Phase3Config(),phase2_context=[event])
            context=rows(p/"phase2-context.jsonl.gz")
            self.assertEqual(len(context),1)
            self.assertEqual(context[0]["decision_at"],event["decision_at"])
            self.assertEqual(context[0]["snapshot"]["available_at"],event["decision_at"])
            self.assertEqual(context[0]["anchor"],"phase2_saved_event_context")
            self.assertFalse(any("phase2" in r["policy"].lower() for r in rows(p/"episodes.jsonl.gz")))


if __name__=="__main__":unittest.main()
