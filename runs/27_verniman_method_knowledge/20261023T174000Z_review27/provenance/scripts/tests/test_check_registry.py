"""Standard-library registry validation and bounded current-owner coverage."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("check_registry_tested", Path(__file__).resolve().parents[1] / "check_registry.py")
registry_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(registry_module)
RUNNER_SPEC = importlib.util.spec_from_file_location("workspace_checks_registry_tested", Path(__file__).resolve().parents[1] / "workspace_checks.py")
runner_module = importlib.util.module_from_spec(RUNNER_SPEC)
RUNNER_SPEC.loader.exec_module(runner_module)
REPOSITORY = Path(__file__).resolve().parents[2]


def fixture(root):
    for relative in ("README.md", "src/main.py", "scripts/check-agent-docs.py"):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Fixture\n" if relative.endswith(".md") else "# source fixture\n")
    (root / "tests").mkdir()
    return {
        "schema_version": 1, "default_profile": "default",
        "profiles": {
            "default": {"description": "First check", "checks": ["first"]},
            "all": {"description": "Reverse profile references", "checks": ["second", "first"]},
        },
        "owners": {"workspace": {
            "kind": "workspace", "path": ".", "description": "Fixture workspace",
            "guides": ["README.md"], "read_first": ["README.md"],
            "entry_points": ["src/main.py"], "preservation": ["Keep retained evidence unchanged."],
        }},
        "checks": [
            {"id": "first", "owner": "workspace", "kind": "command", "description": "First command",
             "cwd": ".", "argv": ["{python}", "scripts/check-agent-docs.py"], "env": {},
             "prerequisites": [], "scope": ["Fixture only"]},
            {"id": "second", "owner": "workspace", "kind": "unittest", "description": "Second suite",
             "cwd": ".", "runtime": "standard-library",
             "unittest": {"start_dir": "tests", "pattern": "test*.py", "optimize": False},
             "env": {}, "prerequisites": [], "scope": ["Fixture only"]},
        ],
    }


def save(root, value):
    path = root / "config/workspace-checks.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(value))
    return path


def tree(root):
    return {str(path.relative_to(root)): path.read_bytes() if path.is_file() else None
            for path in root.rglob("*")}


class RegistryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.registry = fixture(self.root)

    def invalid(self, mutate, message):
        value = copy.deepcopy(self.registry)
        mutate(value)
        with self.assertRaisesRegex(registry_module.RegistryError, message):
            registry_module.validate_registry(self.root, value)

    def test_valid_registry_load_selection_context_are_read_only(self):
        save(self.root, self.registry)
        before = tree(self.root)
        value = registry_module.load_registry(self.root)
        self.assertEqual(value, self.registry)
        self.assertEqual(registry_module.maintained_guides(value), ("README.md",))
        self.assertEqual([check["id"] for check in registry_module.select_checks(value)], ["first"])
        self.assertEqual(registry_module.owner_for_context(value, "workspace")["read_first"], ["README.md"])
        self.assertEqual(tree(self.root), before)

    def test_supported_version_and_top_level_records(self):
        for version in (0, 2, "1", True, None):
            with self.subTest(version=version):
                self.invalid(lambda r: r.update(schema_version=version), "unsupported schema_version")
        self.invalid(lambda r: r.update(extra="workflow"), "unknown fields")
        self.invalid(lambda r: r.pop("checks"), "missing fields")
        for field in ("owners", "profiles", "checks"):
            self.invalid(lambda r: r.update({field: {}}), "nonempty")

    def test_duplicate_check_ids_and_duplicate_json_keys(self):
        self.invalid(lambda r: r["checks"].append(copy.deepcopy(r["checks"][0])), "duplicate check ID")
        path = save(self.root, self.registry)
        path.write_text('{"schema_version":1,"schema_version":1}')
        with self.assertRaisesRegex(registry_module.RegistryError, "duplicate JSON key"):
            registry_module.load_registry(self.root)

    def test_invalid_identifiers_unknown_references_and_incomplete_records(self):
        self.invalid(lambda r: r["checks"][0].update(id="bad id"), "invalid ID")
        self.invalid(lambda r: r["checks"][0].update(owner="unknown"), "unknown owner")
        self.invalid(lambda r: r["profiles"]["default"]["checks"].append("unknown"), "unknown check IDs")
        self.invalid(lambda r: r.update(default_profile="unknown"), "unknown default_profile")
        self.invalid(lambda r: r["owners"]["workspace"].update(related_checks=["unknown"]), "unknown related checks")
        self.invalid(lambda r: r["checks"][0].pop("scope"), "missing fields")
        self.invalid(lambda r: r["checks"][0].update(kind="workflow"), "unsupported check kind")
        for malformed in ([], None, 3):
            self.invalid(lambda r: r["checks"][0].update(owner=malformed), "unknown owner")
            self.invalid(lambda r: r["owners"]["workspace"].update(kind=malformed), "unsupported owner kind")

    def test_command_argv_and_placeholder_validation(self):
        for arguments in ([], "python scripts/test.py", [""], [" "], [4], ["{private_config}"]):
            with self.subTest(arguments=arguments):
                self.invalid(lambda r: r["checks"][0].update(argv=arguments), "argv")
        for argument in ("{root!r}", "{root:20}", "{root", "{root.__class__}"):
            self.invalid(lambda r: r["checks"][0].update(argv=[argument]), "placeholder")

    def test_cwd_and_context_paths_are_bounded_and_existing(self):
        for path in ("../outside", "/tmp", "src/../tests", "src//main.py", "src\\main.py", "C:/private", "src/./main.py"):
            with self.subTest(path=path):
                self.invalid(lambda r: r["checks"][0].update(cwd=path), "bounded")
        self.invalid(lambda r: r["checks"][0].update(cwd="missing"), "missing directory")
        self.invalid(lambda r: r["owners"]["workspace"].update(entry_points=["missing.py"]), "missing context path")
        with tempfile.TemporaryDirectory() as outside:
            (self.root / "escape").symlink_to(Path(outside), target_is_directory=True)
            self.invalid(lambda r: r["checks"][0].update(cwd="escape"), "escapes repository")

    def test_missing_duplicate_escaping_and_historical_guides(self):
        self.invalid(lambda r: r["owners"]["workspace"].update(guides=["missing.md"]), "missing file")
        self.invalid(lambda r: r["owners"]["workspace"].update(guides=["../README.md"]), "bounded")
        self.invalid(lambda r: r["owners"]["workspace"].update(guides=["README.md", "README.md"]), "duplicate")
        def duplicate_owner(r):
            r["owners"]["second"] = copy.deepcopy(r["owners"]["workspace"])
        self.invalid(duplicate_owner, "duplicate guide declaration")
        for relative in ("legacy/study/README.md", "runs/study/report.md", "reports/exports/study/README.md",
                         "apps/narada/releases/release/README.md", "apps/narada/out/README.md"):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# Historical\n")
            self.invalid(lambda r: r["owners"]["workspace"].update(guides=[relative]), "historical/generated")
        with tempfile.TemporaryDirectory() as outside:
            source = Path(outside) / "README.md"
            source.write_text("# Outside\n")
            (self.root / "outside.md").symlink_to(source)
            self.invalid(lambda r: r["owners"]["workspace"].update(guides=["outside.md"]), "escapes repository")

    def test_child_environment_overrides_are_strings_and_narrow_substitutions(self):
        self.registry["checks"][0]["env"] = {"PYTHONPATH": "{root}/src", "EMPTY": ""}
        registry_module.validate_registry(self.root, self.registry)
        for environment in ({"HOME": "elsewhere"}, {"CODEX_HOME": "elsewhere"}, {"BAD-NAME": "x"}, {"PYTHONPATH": 3},
                            {"PYTHONPATH": "{python}"}, {"PYTHONPATH": "a\nb"}):
            self.invalid(lambda r: r["checks"][0].update(env=environment), "environment|placeholder")

    def test_prerequisite_schema_does_not_require_tool_or_input_presence_on_load(self):
        self.registry["checks"][0]["prerequisites"] = [
            {"kind": "file", "path": "absent.data", "description": "Retained prerequisite"},
            {"kind": "directory", "path": "absent-dependencies", "description": "Installed dependencies"},
            {"kind": "executable", "name": "not-installed", "description": "Tool"},
            {"kind": "node-major", "major": 24, "description": "Node version"},
            {"kind": "argument", "name": "preview_origin", "description": "Explicit preview"},
            {"kind": "note", "description": "Configured input resolver runs only in child"},
        ]
        registry_module.validate_registry(self.root, self.registry)
        for prerequisite in ({"kind": "probe", "description": "x"}, {"kind": "file", "path": "../outside", "description": "x"},
                             {"kind": "node-major", "major": True, "description": "x"},
                             {"kind": "argument", "name": "private_config", "description": "x"},
                             {"kind": "executable", "name": "/usr/bin/python", "description": "x"}, {"kind": []}):
            self.invalid(lambda r: r["checks"][0].update(prerequisites=[prerequisite]), "prerequisites")

    def test_unittest_selection_schema(self):
        for update in ({"start_dir": "missing"}, {"pattern": "tests/test*.py"}, {"optimize": 1},
                       {"names": []}, {"names": ["test_module.Test.test", "test_module.Test.test"]},
                       {"names": ["../test_module.py"]}):
            self.invalid(lambda r: r["checks"][1]["unittest"].update(update), "missing directory|pattern|optimize|names")
        self.invalid(lambda r: r["checks"][1].update(runtime=[]), "unsupported unittest runtime")
        self.invalid(lambda r: r["checks"][1].update(argv=["python"]), "unknown fields")

    def test_profile_selection_is_stable_deduplicated_and_rejects_empty_unknown(self):
        registry_module.validate_registry(self.root, self.registry)
        result = registry_module.select_checks(self.registry, profiles=("all", "default", "all"), checks=("second", "second"))
        self.assertEqual([record["id"] for record in result], ["first", "second"])
        for arguments in ({"profiles": ["unknown"]}, {"checks": ["unknown"]}, {"use_default": False}):
            with self.assertRaisesRegex(registry_module.RegistryError, "unknown|empty"):
                registry_module.select_checks(self.registry, **arguments)
        self.invalid(lambda r: r["profiles"]["default"].update(checks=[]), "nonempty")
        self.invalid(lambda r: r["profiles"]["default"].update(checks=["first", "first"]), "duplicate")
        with self.assertRaisesRegex(registry_module.RegistryError, "unknown context"):
            registry_module.owner_for_context(self.registry, "unregistered")


class StudyCoverageTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.registry = fixture(self.root)

    def study(self, number="18", *, suite=True, plan=True, pine=False):
        identity = number + "_fixture"
        relative = "studies/" + identity
        directory = self.root / relative
        directory.mkdir(parents=True)
        guides = [relative + "/README.md"]
        if plan:
            guides.append(relative + "/plan.md")
        if pine:
            guides.append(relative + "/pine/README.md")
        for relative_guide in guides:
            path = self.root / relative_guide
            path.parent.mkdir(exist_ok=True)
            path.write_text("# Study fixture\n")
        owner = {"kind": "study", "path": relative, "study_id": identity, "description": "Study fixture",
                 "guides": guides, "read_first": guides, "entry_points": [relative + "/README.md"],
                 "preservation": ["Preserve research definitions"]}
        if not plan:
            owner["plan_absence_reason"] = "Historical adapter; no current plan"
        if not suite:
            owner["no_suite_reason"] = "No local Python suite"
        self.registry["owners"]["study-" + number] = owner
        if suite:
            (directory / "tests").mkdir()
            check = copy.deepcopy(self.registry["checks"][1])
            check.update(id="study-" + number, owner="study-" + number)
            check["unittest"]["start_dir"] = relative + "/tests"
            self.registry["checks"].append(check)
        return owner

    def test_study18_without_metadata_and_historical_absent_plan_are_explicit(self):
        self.study()
        self.study("01", suite=False, plan=False)
        registry_module.validate_registry(self.root, self.registry)
        self.assertFalse((self.root / "studies/18_fixture/study.json").exists())
        self.assertEqual(registry_module.coverage_errors(self.root, self.registry), [])
        self.assertEqual(registry_module.owner_for_context(self.registry, "18_fixture")["id"], "study-18")

    def test_unregistered_study_and_unregistered_suite_are_detected_without_execution(self):
        owner = self.study()
        self.registry["checks"].pop()
        self.assertIn("unregistered active study test directory: studies/18_fixture/tests", registry_module.coverage_errors(self.root, self.registry))
        self.registry["owners"].pop("study-18")
        self.assertIn("unregistered current study owner: studies/18_fixture", registry_module.coverage_errors(self.root, self.registry))
        self.assertEqual(owner["study_id"], "18_fixture")

    def test_wrong_suite_owner_and_missing_guide_inventory_are_detected(self):
        owner = self.study(pine=True)
        self.registry["checks"][-1]["owner"] = "workspace"
        owner["guides"].remove("studies/18_fixture/pine/README.md")
        errors = registry_module.coverage_errors(self.root, self.registry)
        self.assertIn("unregistered active study test directory: studies/18_fixture/tests", errors)
        self.assertIn("unregistered maintained study guide: studies/18_fixture/pine/README.md", errors)

    def test_absence_reasons_must_match_actual_current_directories(self):
        absent = self.study("01", suite=False, plan=False)
        present = self.study()
        absent.pop("plan_absence_reason")
        absent.pop("no_suite_reason")
        present.update(plan_absence_reason="obsolete", no_suite_reason="obsolete")
        errors = registry_module.coverage_errors(self.root, self.registry)
        self.assertTrue(any("missing explicit absent-plan" in error for error in errors))
        self.assertTrue(any("missing explicit no-suite" in error for error in errors))
        self.assertTrue(any("obsolete absent-plan" in error for error in errors))
        self.assertTrue(any("obsolete no-suite" in error for error in errors))

    def test_historical_markdown_and_arbitrary_link_targets_are_not_crawled(self):
        self.study()
        for relative in ("runs/18_fixture/run/README.md", "reports/exports/18_fixture/revision/README.md",
                         "legacy/study/README.md", "studies/18_fixture/provenance/README.md"):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("[broken](never-created.md)\n")
        self.assertEqual(registry_module.coverage_errors(self.root, self.registry), [])


class ActualRegistryTests(unittest.TestCase):
    def test_opening_pivot_cloud_has_bounded_owned_synthetic_suite(self):
        registry = registry_module.load_registry(REPOSITORY)
        owner = registry_module.owner_for_context(registry, "study-26")
        base = "studies/26_es_opening_pivot_cloud"
        self.assertEqual(owner["path"], base)
        self.assertTrue({base + "/" + name for name in
                         ("README.md", "plan.md", "protocol-1.0.0.md", "inputs.lock.json", "study.yaml", "notes.md")}
                        .issubset(owner["read_first"]))
        checks = registry_module.select_checks(registry, checks=["study-26"], use_default=False)
        self.assertEqual(len(checks), 1)
        check = checks[0]
        self.assertEqual(check["owner"], "study-26")
        self.assertEqual(check["runtime"], "locked-python")
        self.assertEqual(check["unittest"], {"start_dir": base + "/tests", "pattern": "test*.py", "optimize": False})
        self.assertIn("study-26", registry["profiles"]["studies"]["checks"])
        self.assertNotIn("study-26", [c["id"] for c in registry_module.select_checks(registry)])

    def test_focused_bhishma_profiles_have_exact_owned_locked_selections(self):
        registry = registry_module.load_registry(REPOSITORY)
        expected = {
            "bhishma-loaders": [
                ("bhishma-feature-loaders", "bhishma", "test_feature_loaders.py", False),
                ("bhishma-vp-hvn-loader", "bhishma", "test_vp_hvn_loader.py", False),
                ("bhishma-loader-imports", "bhishma", "test_loader_import_boundaries.py", False),
                ("bhishma-manifest-loaders", "bhishma", "test_manifest_selected_loaders.py", False),
                ("study-14-consumer-imports", "study-14", "test_consumer_imports.py", False),
            ],
            "bhishma-safety": [
                ("bhishma-continuous-safety", "bhishma", "test_continuous_publication_safety.py", False),
                ("bhishma-feature-safety", "bhishma", "test_feature_publication_safety.py", False),
                ("bhishma-continuous-safety-optimized", "bhishma", "test_continuous_publication_safety.py", True),
                ("bhishma-feature-safety-optimized", "bhishma", "test_feature_publication_safety.py", True),
                ("bhishma-provenance", "bhishma", "test_provenance.py", False),
                ("bhishma-publication-provenance", "bhishma", "test_publication_provenance.py", False),
                ("bhishma-calendar", "bhishma", "test_calendar.py", False),
            ],
        }
        selected_ids = set()
        for profile, records in expected.items():
            checks = registry_module.select_checks(registry, profiles=[profile])
            self.assertEqual([(check["id"], check["owner"], check["unittest"]["pattern"],
                               check["unittest"]["optimize"]) for check in checks], records)
            for check in checks:
                with self.subTest(profile=profile, check=check["id"]):
                    selected_ids.add(check["id"])
                    self.assertEqual(check["kind"], "unittest")
                    self.assertEqual(check["runtime"], "locked-python")
                    self.assertEqual(check["cwd"], ".")
                    self.assertEqual(check["env"], {})
                    self.assertEqual([(item["kind"], item.get("name", item.get("path")))
                                      for item in check["prerequisites"]],
                                     [("executable", "uv"), ("directory", ".venv")])
                    self.assertNotIn("*", check["unittest"]["pattern"])
                    self.assertNotIn(check["unittest"]["pattern"],
                                     {"test_runtime_prerequisites.py", "test_vp_hvn.py",
                                      "test_continuous_phase1.py", "test_continuous_phase2.py"})
                    expected_dir = ("studies/14_asia_session_vp_levels/tests" if check["owner"] == "study-14"
                                    else "packages/bhishma/tests")
                    self.assertEqual(check["unittest"]["start_dir"], expected_dir)
                    # Each explicit suite becomes its own child command and result file;
                    # Study 14 never enters Bhishma's discovery/import namespace.
                    result_path = "/tmp/" + check["id"] + ".json"
                    command = runner_module.build_command(check, REPOSITORY, result_path=result_path)
                    self.assertEqual(command[:5], [str(REPOSITORY / "scripts/uv"), "run", "--locked", "--no-sync", "python"])
                    self.assertEqual("-O" in command, check["unittest"]["optimize"])
                    self.assertEqual(command[-1], result_path)
                    child_spec = json.loads(command[command.index("--spec") + 1])
                    self.assertEqual(child_spec["start_dir"], str(REPOSITORY / expected_dir))
                    self.assertEqual(child_spec["pattern"], check["unittest"]["pattern"])
        default = registry_module.select_checks(registry)
        self.assertEqual([check["id"] for check in default],
                         ["agent-docs", "bhishma", "sahadeva", "legacy-01", "legacy-02", "vwap-doctor"])
        self.assertFalse(selected_ids & {check["id"] for check in default})
        full = next(check for check in registry["checks"] if check["id"] == "bhishma")
        self.assertEqual(full["unittest"], {"start_dir": "packages/bhishma/tests", "pattern": "test*.py", "optimize": False})
        self.assertEqual([item.get("name") for item in full["prerequisites"] if item["kind"] == "executable"],
                         ["uv", "clang++", "ruby"])

    def test_bhishma_and_study14_context_names_concrete_task_sources_and_tests(self):
        registry = registry_module.load_registry(REPOSITORY)
        package = registry_module.owner_for_context(registry, "bhishma")
        self.assertTrue({"requests/README.md", "config/paths.example.toml"}.issubset(package["read_first"]))
        package_sources = {"publication_safety.py", "continuous_phase1.py", "continuous_phase2.py",
                           "vp_hvn_release.py", "daily_context.py", "gc_ema_bands.py", "derived_ohlcv_5m.py",
                           "session_anchored_vwap.py", "provenance.py", "calendar.py", "paths.py", "feature_loader.py", "continuous_loader.py",
                           "vp_hvn_loader.py", "manifest_selection.py", "vp_hvn.py", "vp_hvn_native.cpp"}
        self.assertTrue({"packages/bhishma/src/abacus_bhishma/" + path for path in package_sources}
                        .issubset(package["entry_points"]))
        for profile in ("bhishma-loaders", "bhishma-safety"):
            for check in registry_module.select_checks(registry, profiles=[profile]):
                if check["owner"] == "bhishma":
                    self.assertIn(check["unittest"]["start_dir"] + "/" + check["unittest"]["pattern"], package["entry_points"])
        self.assertIn("study-14-consumer-imports", package["related_checks"])
        study = registry_module.owner_for_context(registry, "study-14")
        consumers = {"src/preparation.py", "src/study_run.py", "src/previous_day_run.py", "seal.py",
                     "verify_previous_day_run.py", "feature_audit.py", "src/evidence.py", "tests/test_consumer_imports.py"}
        self.assertTrue({"studies/14_asia_session_vp_levels/" + path for path in consumers}
                        .issubset(study["entry_points"]))
        self.assertIn("packages/bhishma/src/abacus_bhishma/vp_hvn_loader.py", study["entry_points"])
        self.assertIn("packages/bhishma/src/abacus_bhishma/provenance.py", study["entry_points"])

    def test_study_evidence_guards_have_exact_selections_and_separate_locked_children(self):
        registry = registry_module.load_registry(REPOSITORY)
        expected = [
            ("numerical-record-guards", "test_numerical_test_record.py", False),
            ("numerical-record-guards-optimized", "test_numerical_test_record.py", True),
            ("study-execution-guards", "study_provenance_guards.py", False),
            ("study-execution-guards-optimized", "study_provenance_guards.py", True),
        ]
        checks = registry_module.select_checks(registry, profiles=["study-evidence"])
        self.assertEqual([(check["id"], check["unittest"]["pattern"], check["unittest"]["optimize"])
                          for check in checks], expected)
        guard_ids = {check["id"] for check in registry_module.select_checks(registry, profiles=["guards"])}
        self.assertTrue({check["id"] for check in checks}.issubset(guard_ids))
        for check in checks:
            with self.subTest(check=check["id"]):
                self.assertEqual(check["owner"], "workspace")
                self.assertEqual(check["runtime"], "locked-python")
                self.assertEqual(check["kind"], "unittest")
                self.assertEqual(check["unittest"]["start_dir"], "scripts/tests")
                self.assertNotIn("*", check["unittest"]["pattern"])
                self.assertEqual(check["cwd"], ".")
                self.assertEqual(check["env"], {})
                self.assertEqual([(p["kind"], p.get("name", p.get("path"))) for p in check["prerequisites"]],
                                 [("executable", "uv"), ("directory", ".venv")])
                result = "/tmp/" + check["id"] + ".json"
                command = runner_module.build_command(check, REPOSITORY, result_path=result)
                self.assertEqual(command[:5], [str(REPOSITORY / "scripts/uv"), "run", "--locked", "--no-sync", "python"])
                self.assertEqual("-O" in command, check["unittest"]["optimize"])
                self.assertEqual(command[-1], result)
        default = registry_module.select_checks(registry)
        self.assertEqual([c["id"] for c in default],
                         ["agent-docs", "bhishma", "sahadeva", "legacy-01", "legacy-02", "vwap-doctor"])
        self.assertFalse({c["id"] for c in checks} & {c["id"] for c in default})

    def test_study_record_context_does_not_register_research_or_record_creation(self):
        registry = registry_module.load_registry(REPOSITORY)
        for number in ("08", "09", "10", "12", "13"):
            owner = registry_module.owner_for_context(registry, "study-" + number)
            self.assertIn("scripts/record-numerical-tests.py", owner["entry_points"])
            self.assertIn("numerical-record-guards", owner["related_checks"])
            self.assertIn(owner["path"] + "/seal.py", owner["entry_points"])
            self.assertFalse(any("literal Ran" in rule for rule in owner["preservation"]))
            if number in ("12", "13"):
                self.assertIn("scripts/check-study-provenance.py", owner["entry_points"])
                self.assertIn("study-execution-guards", owner["related_checks"])
        package = registry_module.owner_for_context(registry, "sahadeva")
        self.assertIn("packages/sahadeva/src/abacus_sahadeva/presentation_revision.py", package["entry_points"])
        for check in registry["checks"]:
            if check["kind"] == "command":
                self.assertNotIn("scripts/record-numerical-tests.py", check["argv"])
                self.assertFalse(any(value.endswith("/seal.py") or value.endswith("/run.py")
                                     for value in check["argv"]))
        for number in ("08", "09", "10", "12", "13"):
            study = next(c for c in registry["checks"] if c["id"] == "study-" + number)
            self.assertEqual(study["unittest"]["pattern"], "test*.py")
            self.assertFalse(study["unittest"]["optimize"])

    def test_actual_default_order_environment_and_complete_active_study_coverage(self):
        registry = registry_module.load_registry(REPOSITORY)
        default = registry_module.select_checks(registry)
        self.assertEqual([record["id"] for record in default],
                         ["agent-docs", "bhishma", "sahadeva", "legacy-01", "legacy-02", "vwap-doctor"])
        for record, study in ((default[3], "01_reversal_follow_through"), (default[4], "02_followthrough_candle_adverse")):
            self.assertEqual(record["env"], {"PYTHONPATH": "{root}/legacy/sahadeva/analysis/" + study + "/src"})
        self.assertEqual(len(registry_module.select_checks(registry, profiles=["studies"])), 19)
        self.assertEqual(sum(owner["kind"] == "study" for owner in registry["owners"].values()), 27)
        self.assertEqual(len(registry_module.maintained_guides(registry)), 89)
        self.assertIn("docs/evidence-contract.md", registry_module.maintained_guides(registry))
        self.assertEqual(registry_module.coverage_errors(REPOSITORY, registry), [])
        self.assertEqual(registry_module.owner_for_context(registry, "18_fibonacci_memory")["id"], "study-18")

    def test_study25_import_and_per_future_context_preserves_research_and_default_gate(self):
        registry = registry_module.load_registry(REPOSITORY)
        owner = registry_module.owner_for_context(registry, "25_forex_news_ema")
        self.assertEqual(owner["id"], "study-25")
        self.assertEqual(owner["guides"], [
            "studies/25_forex_news_ema/README.md",
            "studies/25_forex_news_ema/plan.md",
            "studies/25_forex_news_ema/protocol-per-future-v2.md",
        ])
        for name in ("study.yaml", "inputs.lock.json", "notes.md", "protocol-per-future-v2.md",
                     "config-per-future-v2.json", "inputs-per-future-v2.lock.json"):
            self.assertIn("studies/25_forex_news_ema/" + name, owner["read_first"])
        for name in ("import_report.py", "per_future.py", "src/per_future_stats.py",
                     "per_future_report.py", "per_future_verify.py", "per_future_publication_verify.py",
                     "per_future_figures.py", "revise_attribution.py", "per_future_revision_verify.py", "tests"):
            self.assertIn("studies/25_forex_news_ema/" + name, owner["entry_points"])
        self.assertNotIn("no_suite_reason", owner)
        checks = [check for check in registry["checks"] if check["owner"] == "study-25"]
        self.assertEqual(len(checks), 1)
        self.assertEqual(checks[0]["id"], "study-25")
        self.assertEqual(checks[0]["runtime"], "locked-python")
        self.assertEqual(checks[0]["unittest"], {
            "start_dir": "studies/25_forex_news_ema/tests",
            "pattern": "test*.py",
            "optimize": False,
        })
        self.assertEqual(checks[0]["env"], {})
        self.assertIn("study-25", owner["related_checks"])
        self.assertIn("study-25", [check["id"] for check in
                                  registry_module.select_checks(registry, profiles=["studies"])])
        self.assertNotIn("study-25", [check["id"] for check in registry_module.select_checks(registry)])
        command = runner_module.build_command(checks[0], REPOSITORY, result_path="/tmp/study-25-result.json")
        self.assertEqual(command[:5], [str(REPOSITORY / "scripts/uv"), "run", "--locked",
                                       "--no-sync", "python"])
        child_spec = json.loads(command[command.index("--spec") + 1])
        self.assertEqual(child_spec["start_dir"], str(REPOSITORY / "studies/25_forex_news_ema/tests"))
        self.assertEqual(child_spec["pattern"], "test*.py")
        self.assertIn("No retained market-data reads", " ".join(checks[0]["scope"]))
        self.assertIn("does not rerun", " ".join(owner["preservation"]))
        self.assertEqual([check["id"] for check in registry_module.select_checks(registry)],
                         ["agent-docs", "bhishma", "sahadeva", "legacy-01", "legacy-02", "vwap-doctor"])

    def test_study24_source_review_context_has_no_numerical_suite(self):
        registry = registry_module.load_registry(REPOSITORY)
        owner = registry_module.owner_for_context(registry, "24_trader_assistant_manual")
        self.assertEqual(owner["id"], "study-24")
        self.assertEqual(owner["guides"], [
            "studies/24_trader_assistant_manual/README.md",
            "studies/24_trader_assistant_manual/plan.md",
        ])
        for name in ("study.yaml", "inputs.lock.json", "notes.md"):
            self.assertIn("studies/24_trader_assistant_manual/" + name, owner["read_first"])
        self.assertIn("no_suite_reason", owner)
        self.assertFalse(any(check["owner"] == "study-24" for check in registry["checks"]))
        self.assertNotIn("study-24", [check["id"] for check in
                                     registry_module.select_checks(registry, profiles=["studies"])])
        self.assertTrue({"documentation", "navigation-metadata", "research-index"}
                        .issubset(owner["related_checks"]))
        self.assertIn("unpinned", " ".join(owner["preservation"]))
        self.assertEqual([check["id"] for check in registry_module.select_checks(registry)],
                         ["agent-docs", "bhishma", "sahadeva", "legacy-01", "legacy-02", "vwap-doctor"])

    def test_study27_source_review_context_has_no_numerical_suite(self):
        registry = registry_module.load_registry(REPOSITORY)
        base = "studies/27_verniman_method_knowledge"
        owner = registry_module.owner_for_context(registry, "27_verniman_method_knowledge")
        self.assertEqual(owner["id"], "study-27")
        self.assertEqual(owner["path"], base)
        self.assertEqual(owner["guides"], [base + "/README.md", base + "/plan.md"])
        for name in ("README.md", "plan.md", "study.yaml", "inputs.lock.json", "notes.md"):
            self.assertIn(base + "/" + name, owner["read_first"])
        self.assertEqual(owner["entry_points"], [base + "/README.md", base + "/plan.md"])
        self.assertIn("no_suite_reason", owner)
        self.assertFalse(any(check["owner"] == "study-27" for check in registry["checks"]))
        self.assertNotIn("study-27", [check["id"] for check in
                                     registry_module.select_checks(registry, profiles=["studies"])])
        self.assertEqual(owner["related_checks"],
                         ["documentation", "navigation-metadata", "research-index"])
        self.assertIn("third-party", " ".join(owner["preservation"]))
        self.assertEqual([check["id"] for check in registry_module.select_checks(registry)],
                         ["agent-docs", "bhishma", "sahadeva", "legacy-01", "legacy-02", "vwap-doctor"])

    def test_study21_execution_context_has_owned_suite_without_changing_default(self):
        registry = registry_module.load_registry(REPOSITORY)
        owner = registry_module.owner_for_context(registry, "21_ema_cloud_trend_follow_opportunity")
        self.assertEqual(owner["id"], "study-21")
        self.assertIn("studies/21_ema_cloud_trend_follow_opportunity/run.py", owner["entry_points"])
        self.assertIn("studies/21_ema_cloud_trend_follow_opportunity/run_stage2.py", owner["entry_points"])
        self.assertIn("studies/21_ema_cloud_trend_follow_opportunity/protocol-stage2.md", owner["guides"])
        self.assertIn("studies/21_ema_cloud_trend_follow_opportunity/protocol-stage3.md", owner["guides"])
        self.assertIn("studies/21_ema_cloud_trend_follow_opportunity/run_stage3.py", owner["entry_points"])
        self.assertNotIn("no_suite_reason", owner)
        checks = [check for check in registry["checks"] if check["owner"] == "study-21"]
        self.assertEqual(len(checks), 1)
        self.assertEqual(checks[0]["unittest"]["start_dir"],
                         "studies/21_ema_cloud_trend_follow_opportunity/tests")
        study_path = REPOSITORY / owner["path"]
        self.assertTrue((study_path / "tests").is_dir())
        self.assertTrue((study_path / "run.py").is_file())
        self.assertEqual([check["id"] for check in registry_module.select_checks(registry)],
                         ["agent-docs", "bhishma", "sahadeva", "legacy-01", "legacy-02", "vwap-doctor"])

    def test_study22_trend_and_reversal_context_has_synthetic_owned_suite_without_changing_default(self):
        registry = registry_module.load_registry(REPOSITORY)
        owner = registry_module.owner_for_context(registry, "22_es_range_xv_focused")
        self.assertEqual(owner["id"], "study-22")
        self.assertEqual(owner["guides"], [
            "studies/22_es_range_xv_focused/README.md",
            "studies/22_es_range_xv_focused/plan.md",
            "studies/22_es_range_xv_focused/reversal-plan.md",
            "studies/22_es_range_xv_focused/pullback-plan.md",
        ])
        self.assertIn("studies/22_es_range_xv_focused/reversal-plan.md", owner["read_first"])
        self.assertIn("studies/22_es_range_xv_focused/pullback-plan.md", owner["read_first"])
        self.assertIn("studies/22_es_range_xv_focused/pullback_run.py", owner["entry_points"])
        self.assertIn("studies/22_es_range_xv_focused/pullback_audit.py", owner["entry_points"])
        self.assertIn("studies/22_es_range_xv_focused/run.py", owner["entry_points"])
        self.assertIn("studies/22_es_range_xv_focused/reversal_run.py", owner["entry_points"])
        self.assertIn("studies/22_es_range_xv_focused/reversal_audit.py", owner["entry_points"])
        self.assertIn("studies/22_es_range_xv_focused/src/timeframes.py", owner["entry_points"])
        self.assertIn("preceding-leg cohorts", " ".join(owner["preservation"]))
        self.assertIn("completed evidence", " ".join(owner["preservation"]))
        checks = [check for check in registry["checks"] if check["owner"] == "study-22"]
        self.assertEqual(len(checks), 1)
        check = checks[0]
        self.assertEqual(check["runtime"], "locked-python")
        self.assertEqual(check["unittest"], {
            "start_dir": "studies/22_es_range_xv_focused/tests",
            "pattern": "test*.py",
            "optimize": False,
        })
        self.assertEqual({item["kind"] for item in check["prerequisites"]}, {"executable", "directory"})
        self.assertIn("No real-data reads", " ".join(check["scope"]))
        self.assertIn("temporary synthetic inputs", " ".join(check["scope"]))
        self.assertIn("study-22", [record["id"] for record in registry_module.select_checks(registry, profiles=["studies"])])
        self.assertNotIn("study-22", [record["id"] for record in registry_module.select_checks(registry)])

    def test_study23_phases1_2_and3_context_has_owned_suite_without_changing_default(self):
        registry = registry_module.load_registry(REPOSITORY)
        owner = registry_module.owner_for_context(registry, "23_gc_overnight_breakout_15m")
        self.assertEqual(owner["id"], "study-23")
        self.assertEqual(owner["guides"], [
            "studies/23_gc_overnight_breakout_15m/README.md",
            "studies/23_gc_overnight_breakout_15m/plan.md",
            "studies/23_gc_overnight_breakout_15m/source-rules.md",
            "studies/23_gc_overnight_breakout_15m/protocol-phase1.md",
            "studies/23_gc_overnight_breakout_15m/protocol-phase2.md",
            "studies/23_gc_overnight_breakout_15m/protocol-phase3.md",
        ])
        self.assertIn("studies/23_gc_overnight_breakout_15m/study.yaml", owner["read_first"])
        self.assertIn("studies/23_gc_overnight_breakout_15m/inputs.lock.json", owner["read_first"])
        self.assertIn("studies/23_gc_overnight_breakout_15m/notes.md", owner["read_first"])
        self.assertIn("studies/23_gc_overnight_breakout_15m/metrics.py", owner["entry_points"])
        self.assertIn("studies/23_gc_overnight_breakout_15m/config-phase3.json", owner["read_first"])
        for source in ("phase3_inputs.py", "phase3_run.py", "phase3_execution.py", "phase3_metrics.py", "phase3_verify.py", "phase3_publish_web.py", "phase3_verify_publication.py", "phase3_seal.py"):
            self.assertIn("studies/23_gc_overnight_breakout_15m/" + source, owner["entry_points"])
        self.assertNotIn("no_suite_reason", owner)
        self.assertIn("Phase2", " ".join(owner["preservation"]))
        checks = [check for check in registry["checks"] if check["owner"] == "study-23"]
        self.assertEqual(len(checks), 1)
        self.assertEqual(checks[0]["unittest"]["start_dir"], "studies/23_gc_overnight_breakout_15m/tests")
        self.assertIn("study-23", [check["id"] for check in registry_module.select_checks(registry, profiles=["studies"])])
        self.assertNotIn("study-23", [check["id"] for check in registry_module.select_checks(registry)])
        self.assertEqual([check["id"] for check in registry_module.select_checks(registry)],
                         ["agent-docs", "bhishma", "sahadeva", "legacy-01", "legacy-02", "vwap-doctor"])

    def test_prerequisite_classifications_and_explicit_heavy_selections(self):
        registry = registry_module.load_registry(REPOSITORY)
        checks = {record["id"]: record for record in registry["checks"]}
        tools = {item.get("name") for item in checks["bhishma"]["prerequisites"] if item["kind"] == "executable"}
        self.assertTrue({"ruby", "clang++"}.issubset(tools))
        self.assertTrue(any("2023" in item["description"] for item in checks["study-06"]["prerequisites"]))
        self.assertTrue(any(item["kind"] == "file" and item["path"].endswith("generate.py") for item in checks["study-11"]["prerequisites"]))
        self.assertEqual(checks["workspace-utilities"]["runtime"], "standard-library")
        self.assertEqual(checks["workspace-utilities"]["prerequisites"], [])
        self.assertEqual(checks["export-guards"]["unittest"]["pattern"], checks["export-guards-optimized"]["unittest"]["pattern"])
        self.assertFalse(checks["export-guards"]["unittest"]["optimize"])
        self.assertTrue(checks["export-guards-optimized"]["unittest"]["optimize"])
        default_ids = {record["id"] for record in registry_module.select_checks(registry)}
        self.assertFalse({"narada-smoke-preview", "narada-audit-sources", "narada-build", "research-index"} & default_ids)
        self.assertEqual(checks["research-index"]["argv"][-1], "--check")
        for record in checks.values():
            if record["kind"] == "command":
                self.assertNotIn("release:prepare", record["argv"])
                self.assertNotIn("report:publish", record["argv"])

    def test_evidence_navigation_gates_remain_separate_and_context_is_explicit(self):
        registry = registry_module.load_registry(REPOSITORY)
        expected = {"metadata": ["navigation-metadata"],
                    "evidence-references": ["strategy-evidence-references"],
                    "navigation": ["research-index"]}
        for profile, identifiers in expected.items():
            self.assertEqual([check["id"] for check in registry_module.select_checks(registry, profiles=[profile])], identifiers)
        default = {check["id"] for check in registry_module.select_checks(registry)}
        self.assertFalse(default & {"navigation-metadata", "strategy-evidence-references", "evidence-contract-help"})
        checks = {check["id"]: check for check in registry["checks"]}
        self.assertEqual(checks["evidence-contract-help"]["argv"][-1], "--help")
        for owner in ("workspace", "sahadeva"):
            context = registry_module.owner_for_context(registry, owner)
            self.assertIn("docs/evidence-contract.md", context["read_first"])
            self.assertIn("scripts/check-evidence-bundle.py", context["entry_points"])
        self.assertEqual(registry["owners"]["study-18"]["kind"], "study")


if __name__ == "__main__":
    unittest.main()
