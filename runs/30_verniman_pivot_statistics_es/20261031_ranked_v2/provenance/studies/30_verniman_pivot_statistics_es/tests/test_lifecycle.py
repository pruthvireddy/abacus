"""Source-bound evidence refusal and retained-ledger tests; no market inputs."""
import gzip
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

STUDY = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("study30_lifecycle_tested", STUDY / "src/lifecycle.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FrozenEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.stage = self.root / "stage"
        self.stage.mkdir()
        (self.root / "scientific.py").write_text("# Synthetic source\n")
        (self.stage / "retained.py").write_text("# Synthetic source\n")
        (self.stage / "numerical-tests.log").write_text("Ran1test\nOK\n")
        module.dump(self.stage / "numerical-tests.json", {"status": "passed", "tests": 1,
                    "log_sha256": module.digest(self.stage / "numerical-tests.log")})
        module.dump(self.stage / "freeze.json", {"sources": [{"path": "scientific.py", "retained_path": "retained.py",
                    "sha256": module.digest(self.root / "scientific.py")}], "run_id": "synthetic"})

    def test_freeze_requires_unchanged_live_and_retained_source(self):
        with patch.object(module, "ROOT", self.root):
            self.assertEqual(module.assert_frozen(self.stage)["run_id"], "synthetic")
            (self.root / "scientific.py").write_text("# Changed source\n")
            with self.assertRaisesRegex(ValueError, "source/settings"):
                module.assert_frozen(self.stage)

    def test_missing_successful_tests_or_tampered_log_refused(self):
        with patch.object(module, "ROOT", self.root):
            (self.stage / "numerical-tests.log").write_text("fabricated\n")
            with self.assertRaisesRegex(ValueError, "numerical tests"):
                module.assert_frozen(self.stage)

    def test_ledger_preserves_null_false_zero_and_refuses_changed_bytes(self):
        ledger = {"rows": [{"unknown": None, "event": False, "count": 0}]}
        with gzip.open(self.stage / "ledgers.json.gz", "wt") as stream:
            json.dump(ledger, stream)
        module.dump(self.stage / "execution.json", {"ledger_sha256": module.digest(self.stage / "ledgers.json.gz")})
        self.assertEqual(module.read_ledgers(self.stage), ledger)
        with (self.stage / "ledgers.json.gz").open("ab") as stream:
            stream.write(b"changed")
        with self.assertRaisesRegex(ValueError, "ledger bytes"):
            module.read_ledgers(self.stage)

    def test_evidence_writes_refuse_existing_destinations(self):
        path = self.stage / "record.json"
        module.dump(path, {"status": "original"})
        with self.assertRaises(FileExistsError):
            module.dump(path, {"status": "replacement"})
        self.assertEqual(module.load(path), {"status": "original"})


if __name__ == "__main__":
    unittest.main()
