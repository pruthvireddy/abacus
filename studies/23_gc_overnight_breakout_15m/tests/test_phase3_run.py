import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from phase3_run import config_for_scenario,SCENARIOS,freeze_selection,sha,group_parent_events


class Phase3StageTests(unittest.TestCase):
    def test_saved_parent_event_schemas_join_by_exact_trade_identity(self):
        trades=[dict(trade_id="native:one:2018-01-03:1",broker_day="2018-01-03")]
        records=[dict(event="missing_expected_evidence",broker_day="2018-01-02"),
                 dict(event="entry",trade_id=trades[0]["trade_id"],time="2018-01-03T07:05:00Z"),
                 dict(event="stop_reset",trade_id=trades[0]["trade_id"],time="2018-01-03T07:15:00Z"),
                 dict(event="exit",trade_id=trades[0]["trade_id"],time="2018-01-03T17:00:00Z")]
        result=group_parent_events(records,trades)
        self.assertEqual(result["2018-01-03"],records[1:])
        self.assertEqual(result["2018-01-02"],[records[0]])
        self.assertNotIn("broker_day",records[1])
        for bad in (dict(event="exit",trade_id="other"),dict(event="exit",trade_id=trades[0]["trade_id"],broker_day="2018-01-04"),dict(event="exit")):
            with self.subTest(record=bad):
                with self.assertRaises(ValueError):group_parent_events([bad],trades)
    def test_each_sensitivity_carries_its_matching_parent_identity_and_costs(self):
        for name in SCENARIOS:
            with self.subTest(scenario=name):
                config=config_for_scenario(name)
                self.assertEqual(config.scenario,name)
                self.assertEqual(config.commission_per_side,SCENARIOS[name]["commission_per_side"])
                self.assertEqual(config.slippage_ticks,SCENARIOS[name]["slippage_ticks"])
                self.assertEqual(config.ordering,SCENARIOS[name]["ordering"])
                self.assertEqual(config.initial_capital,10000)

    def test_selection_requires_same_run_freeze_and_verified_candidate_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            stage=Path(directory).resolve()/"synthetic";stage.mkdir()
            (stage/"execution-freeze.json").write_text("{}")
            (stage/"config.json").write_text("{}")
            candidate=stage/"selection-candidate.json";candidate.write_text(json.dumps(dict(later_outcomes_opened=False)))
            receipt=dict(status="passed",phase="dev-validation",run_id="another",execution_freeze_sha256=sha(stage/"execution-freeze.json"),artifacts=[dict(path=candidate.name,sha256=sha(candidate),bytes=candidate.stat().st_size)])
            verification=stage/"verification.json";verification.write_text(json.dumps(receipt))
            with patch("phase3_run.assert_freeze",return_value={}):
                with self.assertRaisesRegex(ValueError,"another frozen run"):freeze_selection(stage,verification)
                receipt["run_id"]=stage.name;verification.write_text(json.dumps(receipt))
                candidate.write_text(json.dumps(dict(later_outcomes_opened=False,retuned=True)))
                with self.assertRaisesRegex(ValueError,"candidate bytes"):freeze_selection(stage,verification)
                self.assertFalse((stage/"selection.json").exists())

    def test_later_evidence_prevents_backdated_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            stage=Path(directory).resolve()/"synthetic";stage.mkdir()
            (stage/"execution-freeze.json").write_text("{}")
            (stage/"phases/later").mkdir(parents=True)
            receipt=dict(status="passed",phase="dev-validation",run_id=stage.name,execution_freeze_sha256=sha(stage/"execution-freeze.json"))
            path=stage/"verification.json";path.write_text(json.dumps(receipt))
            with patch("phase3_run.assert_freeze",return_value={}):
                with self.assertRaisesRegex(ValueError,"later outcomes already"):freeze_selection(stage,path)


if __name__=="__main__":unittest.main()
