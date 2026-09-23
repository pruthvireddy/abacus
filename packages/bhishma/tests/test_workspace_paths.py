from __future__ import annotations

import argparse
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from abacus_bhishma.databento_cli import DEFAULT_ROLL_MAP, _output_path
from abacus_bhishma.paths import (
    PathConfigurationError,
    load_workspace_paths,
    resolve_publication_root,
)


class RelocatedWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        (self.root / "pyproject.toml").write_text('[tool.uv.workspace]\nmembers = []\n')
        (self.root / "config").mkdir()
        (self.root / "config/paths.local.toml").write_text(
            '[paths]\npublication_root = "storage"\nlegacy_research_root = "history"\n'
        )
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_nested_working_directory_finds_workspace_and_external_storage(self):
        nested = self.root / "packages/bhishma/src/abacus_bhishma"
        nested.mkdir(parents=True)
        prior = Path.cwd()
        self.addCleanup(os.chdir, prior)
        os.chdir(nested)
        paths = load_workspace_paths()
        self.assertEqual(paths.workspace_root, self.root)
        self.assertEqual(paths.publication_root, self.root / "storage")
        self.assertEqual(paths.legacy_research_root, self.root / "history")

    def test_explicit_publication_root_wins_over_environment_and_package_location(self):
        with patch.dict(os.environ, {"ABACUS_PUBLICATION_ROOT": str(self.root / "override")}):
            self.assertEqual(resolve_publication_root(self.root / "chosen"), self.root / "chosen")
            self.assertEqual(load_workspace_paths(self.root).publication_root, self.root / "override")

    def test_missing_config_never_defaults_to_code_or_current_directory(self):
        (self.root / "config/paths.local.toml").unlink()
        with self.assertRaisesRegex(PathConfigurationError, "publication_root"):
            load_workspace_paths(self.root)

    def test_databento_destination_is_resolved_at_execution_without_network(self):
        args = argparse.Namespace(output=None, root=self.root / "publication")
        self.assertEqual(_output_path(args, DEFAULT_ROLL_MAP), args.root / DEFAULT_ROLL_MAP)
        args.output = str(self.root / "explicit.json")
        self.assertEqual(_output_path(args, DEFAULT_ROLL_MAP), self.root / "explicit.json")


if __name__ == "__main__":
    unittest.main()
