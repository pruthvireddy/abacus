from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from abacus_bhishma import databento_credentials


class DatabentoCredentialsTests(unittest.TestCase):
    @patch.object(databento_credentials.platform, "system", return_value="Darwin")
    @patch.object(databento_credentials.getpass, "getuser", return_value="test-user")
    @patch.object(databento_credentials.subprocess, "run")
    def test_load_returns_valid_key(self, run, _getuser, _system):
        fake_key = "db-" + ("1" * 29)
        run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=f"{fake_key}\n"
        )

        key = databento_credentials.load()

        self.assertEqual(key, fake_key)
        self.assertTrue(run.call_args.kwargs["capture_output"])

    @patch.object(databento_credentials.platform, "system", return_value="Darwin")
    @patch.object(databento_credentials.getpass, "getuser", return_value="test-user")
    @patch.object(databento_credentials.subprocess, "run")
    def test_load_rejects_invalid_key(self, run, _getuser, _system):
        run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="not-a-key\n"
        )

        with self.assertRaises(databento_credentials.DatabentoCredentialError):
            databento_credentials.load()


if __name__ == "__main__":
    unittest.main()
