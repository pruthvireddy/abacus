"""Operation-specific native/Ruby prerequisites using disposable fixtures."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from abacus_bhishma import vp_hvn as vp
from abacus_bhishma.derived_ohlcv_5m import DeliveryError, _load_yaml_with_ruby


class NativePrerequisiteTests(unittest.TestCase):
    def setUp(self) -> None:
        native = patch.object(vp, "_native", None)
        native.start()
        self.addCleanup(native.stop)

    def test_missing_compiler_refuses_before_cache_mutation(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            sentinel = root / "retained.txt"
            sentinel.write_bytes(b"retained cache evidence\n")
            for cache in (root / "new-cache", root):
                with self.subTest(cache=cache.name), patch("shutil.which", return_value=None) as which:
                    before = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
                    with patch("subprocess.run") as run, patch("ctypes.CDLL") as load:
                        with self.assertRaisesRegex(RuntimeError, r"clang\+\+.*install.*PATH"):
                            vp.enable_native(cache)
                        run.assert_not_called()
                        load.assert_not_called()
                    which.assert_called_once_with("clang++")
                    self.assertEqual(
                        {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()},
                        before,
                    )
                    self.assertEqual(list(root.iterdir()), [sentinel])
                    self.assertIsNone(vp._native)

    def test_compilation_failure_is_the_original_hard_failure(self) -> None:
        failure = subprocess.CalledProcessError(1, ["clang++"], stderr=b"synthetic compiler failure")
        with TemporaryDirectory() as temporary, patch("shutil.which", return_value="/synthetic/clang++"):
            with patch("subprocess.run", side_effect=failure), patch("ctypes.CDLL") as load:
                with self.assertRaises(subprocess.CalledProcessError) as caught:
                    vp.enable_native(Path(temporary) / "cache")
                self.assertIs(caught.exception, failure)
                load.assert_not_called()
                self.assertIsNone(vp._native)

    def test_native_library_failure_is_the_original_hard_failure(self) -> None:
        failure = OSError("synthetic invalid native library")
        with TemporaryDirectory() as temporary, patch("shutil.which", return_value="/synthetic/clang++"):
            with patch("subprocess.run"), patch("ctypes.CDLL", side_effect=failure):
                with self.assertRaises(OSError) as caught:
                    vp.enable_native(Path(temporary) / "cache")
                self.assertIs(caught.exception, failure)
                self.assertIsNone(vp._native)

    def test_flags_source_cache_identity_and_provenance_are_preserved(self) -> None:
        source_hash = "b797cc3c96011422c6bdc0f7ff4989bff3319635d0c2cbf070ee889c5352857f"
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "vp_hvn_native.cpp"
            source.write_bytes(b"native fixture bytes\n")
            cache = root / "cache"
            target = cache / "vp_hvn_b797cc3c96011422.so"
            command = [
                "clang++", "-O2", "-std=c++17", "-shared", "-fPIC", "-ffp-contract=off",
                str(source), "-o", str(target),
            ]
            library = MagicMock()
            with patch.object(vp, "__file__", str(root / "vp_hvn.py")):
                with patch("shutil.which", return_value="/synthetic/clang++"):
                    with patch("subprocess.run") as run, patch("ctypes.CDLL", return_value=library) as load:
                        with patch("subprocess.check_output", return_value="synthetic compiler 1.0\nTarget: synthetic\n") as version:
                            self.assertEqual(
                                vp.enable_native(cache),
                                {"command": command, "source_sha256": source_hash, "compiler": "synthetic compiler 1.0"},
                            )
                        version.assert_called_once_with(["clang++", "--version"], text=True)
                    run.assert_called_once_with(command, check=True, capture_output=True)
                    load.assert_called_once_with(str(target))
            self.assertIs(vp._native, library)


class RubyPrerequisiteTests(unittest.TestCase):
    def test_missing_ruby_has_existing_actionable_error_and_preserves_input(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "request.yaml"
            raw = b"request:\n  id: synthetic\n"
            path.write_bytes(raw)
            with patch("shutil.which", return_value=None) as which, patch("subprocess.run") as run:
                with self.assertRaisesRegex(DeliveryError, "Ruby is required to parse the YAML request"):
                    _load_yaml_with_ruby(path)
                which.assert_called_once_with("ruby")
                run.assert_not_called()
            self.assertEqual(path.read_bytes(), raw)
            self.assertEqual(list(root.iterdir()), [path])

    def test_safe_parser_preserves_values_and_exact_raw_bytes(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "request.yaml"
            raw = b'request:\n  id: synthetic\nvalues: [1, true, null, "007"]\nnote: "preserve bytes" # retained\n'
            path.write_bytes(raw)
            values, retained = _load_yaml_with_ruby(path)
            self.assertEqual(
                values,
                {"request": {"id": "synthetic"}, "values": [1, True, None, "007"], "note": "preserve bytes"},
            )
            self.assertEqual(retained, raw)
            self.assertEqual(path.read_bytes(), raw)
            self.assertEqual(list(root.iterdir()), [path])

    def test_safe_parser_still_rejects_yaml_aliases(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "request.yaml"
            raw = b"value: &value [1, 2]\ncopy: *value\n"
            path.write_bytes(raw)
            with self.assertRaisesRegex(DeliveryError, "failed to parse request YAML"):
                _load_yaml_with_ruby(path)
            self.assertEqual(path.read_bytes(), raw)


if __name__ == "__main__":
    unittest.main()
