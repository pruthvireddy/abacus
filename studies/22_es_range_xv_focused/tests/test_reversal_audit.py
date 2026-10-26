"""Independent reversal verification examples; synthetic inputs only."""
from __future__ import annotations

import csv
from contextlib import redirect_stdout
import hashlib
import io
import json
from datetime import date, datetime, timedelta
from decimal import Decimal
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from dataclasses import replace


STUDY = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("study22_reversal_audit", STUDY / "reversal_audit.py")
audit = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = audit
spec.loader.exec_module(audit)


def bars(signs, *, start="2025-01-02 09:29:59", session="2025-01-02"):
    initial = datetime.fromisoformat(start)
    result = []
    for index, sign in enumerate(signs):
        stamp = initial + timedelta(seconds=index)
        opening = Decimal("100")
        closing = opening + Decimal(sign)
        result.append(audit.IndependentBar(index + 1, stamp, date.fromisoformat(session), opening,
                                          max(opening, closing), min(opening, closing), closing,
                                          stamp + timedelta(seconds=1), "next_bar_start_proxy"))
    return result


def save_inputs(directory: Path, observed: list, *, same_second=False):
    enhanced, original = directory / "enhanced.csv", directory / "source.csv"
    with enhanced.open("w", newline="") as enhanced_handle, original.open("w", newline="") as original_handle:
        writer = csv.DictWriter(enhanced_handle, delimiter=";", fieldnames=audit.INPUT_COLUMNS)
        writer.writeheader()
        raw_writer = csv.writer(original_handle, delimiter=";")
        for index, item in enumerate(observed):
            stamp = observed[0].start if same_second else item.start
            terminal = index + 1 == len(observed)
            same_session = not terminal and item.session == observed[index + 1].session
            completed = not terminal and same_session
            next_stamp = stamp if same_second else observed[index + 1].start if completed else None
            source_stamp = stamp.strftime("%Y-%d-%m %H:%M:%S")
            prices = [str(price) for price in (item.opening, item.high, item.low, item.closing)]
            raw_writer.writerow([source_stamp, *prices])
            writer.writerow({"source_row": index + 1, "source_timestamp": source_stamp,
                             "bar_start_timestamp": stamp.isoformat(sep=" "),
                             "bar_completion_timestamp_proxy": next_stamp.isoformat(sep=" ") if completed else "",
                             "bar_duration_seconds_proxy": (next_stamp - stamp).total_seconds() if completed else "",
                             "completion_proxy_status": ("next_bar_start_same_second" if same_second else "next_bar_start_proxy") if completed else "unavailable_export_end" if terminal else "unavailable_session_boundary",
                             "session_date_proxy": item.session.isoformat(),
                             **dict(zip(("open", "high", "low", "close"), prices))})
    return enhanced, original


class InputAuditTests(unittest.TestCase):
    def test_all_source_rows_and_raw_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            enhanced, original = save_inputs(Path(directory).resolve(), bars([-1, 1, 1, -1]))
            observed = list(audit.read_bars(enhanced, raw_path=original))
            self.assertEqual([row.row for row in observed], [1, 2, 3, 4])
            self.assertEqual([row.direction for row in observed], ["bearish", "bullish", "bullish", "bearish"])
            self.assertIsNone(observed[-1].completion)
            original.write_text(original.read_text().replace("100;101;100;101", "100;102;100;101", 1))
            with self.assertRaisesRegex(ValueError, "original/enhanced row"):
                list(audit.read_bars(enhanced, raw_path=original))

    def test_adjacent_proxy_tamper_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            enhanced, _ = save_inputs(Path(directory).resolve(), bars([-1, 1, 1]))
            content = enhanced.read_text().replace("2025-01-02 09:30:00;1.0", "2025-01-02 09:30:00;2.0", 1)
            enhanced.write_text(content)
            with self.assertRaisesRegex(ValueError, "duration differs"):
                list(audit.read_bars(enhanced))

    def test_original_count_tamper_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            enhanced, original = save_inputs(Path(directory).resolve(), bars([-1, 1]))
            original.write_text(original.read_text() + original.read_text().splitlines()[0] + "\n")
            with self.assertRaisesRegex(ValueError, "row count"):
                list(audit.read_bars(enhanced, raw_path=original))

    def test_same_second_duplicates_retained_and_loader_diagnostics_reproduced(self):
        with tempfile.TemporaryDirectory() as directory:
            enhanced, original = save_inputs(Path(directory).resolve(), bars([1, 1, -1]), same_second=True)
            totals = {}
            observed = list(audit.observe_inputs(audit.read_bars(enhanced, raw_path=original), set(), totals))
            self.assertEqual(len(observed), 3)
            self.assertEqual(totals["input_rows"], 3)
            self.assertEqual(totals["primary_eligible_bars"], 2)
            self.assertEqual(totals["same_second_eligible_bars"], 2)
            self.assertEqual(totals["duplicate_adjacent_rows"], 1)
            self.assertEqual(totals["completion_status_counts"], {"next_bar_start_same_second": 2, "unavailable_export_end": 1})
            self.assertEqual(totals["barrier_counts"], {"completion_status:unavailable_export_end": 1})
            self.assertEqual(totals["duplicate_examples"], [{"source_row": 2, "previous_source_row": 1, "start_timestamp": "2025-01-02 09:29:59"}])

    def test_full_session_exclusion_overrides_completion_barrier(self):
        observed = bars([1, -1], session="2026-09-24", start="2026-09-24 10:00:00")
        totals = {}
        self.assertEqual(len(list(audit.observe_inputs(observed, {date(2026, 9, 24)}, totals))), 2)
        self.assertEqual(totals["primary_eligible_bars"], 0)
        self.assertEqual(totals["barrier_counts"], {"excluded_session": 2})
        self.assertEqual(totals["excluded_session_counts"], {"2026-09-24": 2})


class ComparisonAuditTests(unittest.TestCase):
    def test_nulls_are_distinct_from_false_and_decimal_equalities_exact(self):
        audit.compare_row({"known": False, "unknown": None, "price": Decimal("100.25")},
                          {"known": "False", "unknown": "", "price": "100.250"}, "example")
        with self.assertRaisesRegex(ValueError, "unknown"):
            audit.compare_row({"unknown": None}, {"unknown": "False"}, "example")
        with self.assertRaisesRegex(ValueError, "price"):
            audit.compare_row({"price": Decimal("100.25")}, {"price": "100.250000000001"}, "example")

    def test_saved_csv_all_row_counts_and_cell_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).resolve() / "saved.csv"
            path.write_text("count,probability,unknown\n3,0.75,\n")
            expected = [{"count": 3, "probability": .75, "unknown": None}]
            self.assertEqual(audit.compare_csv(expected, path), 1)
            path.write_text("count,probability,unknown\n3,0.75,\n3,0.75,\n")
            with self.assertRaisesRegex(ValueError, "row count"):
                audit.compare_csv(expected, path)

    def test_windows_are_completion_time_anchored_overlap_and_half_open(self):
        windows = [{"id": "asia", "start": "20:00", "end": "02:00"},
                   {"id": "asia_open", "start": "19:30", "end": "21:30"},
                   {"id": "ny", "start": "09:30", "end": "16:00"},
                   {"id": "ny_open", "start": "09:30", "end": "10:30"}]
        self.assertEqual(audit.window_ids(datetime(2025, 1, 2, 20), windows), ["all_hours", "asia", "asia_open"])
        self.assertEqual(audit.window_ids(datetime(2025, 1, 3, 2), windows), ["all_hours"])
        self.assertEqual(audit.window_ids(datetime(2025, 1, 2, 9, 30), windows), ["all_hours", "ny", "ny_open"])
        self.assertEqual(audit.window_ids(datetime(2025, 1, 2, 10, 30), windows), ["all_hours", "ny"])

    def test_symlink_and_traversal_paths_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            actual = root / "actual"
            actual.write_text("example")
            (root / "link").symlink_to(actual)
            with self.assertRaisesRegex(ValueError, "Symlinked"):
                audit.digest(root / "link")
            for name in ("../actual", "/actual", "x\\actual", "./actual", "x//actual"):
                with self.assertRaisesRegex(ValueError, "Unsafe"):
                    audit.located(root, name)


class ReversalReconstructionTests(unittest.TestCase):
    def events(self, observed):
        return list(audit.reconstruct_events(observed, 4, {date(2026, 9, 24)}))

    def test_reversal_excludes_itself_and_retains_unknown_prior_start(self):
        events = self.events(bars([-1, -1, 1, 1, 1, -1]))
        self.assertEqual([event["source_row"] for event in events], [3, 6])
        first, terminal = events
        self.assertEqual(first["follow_count"], 2)
        self.assertEqual(first["exact_follow_count"], 2)
        self.assertFalse(first["right_censored"])
        self.assertEqual(first["end_reason"], "reversal")
        self.assertEqual(first["prior_observed_length"], 2)
        self.assertIsNone(first["prior_exact_length"])
        self.assertEqual(audit.prior_bucket(first), "unknown_start")
        self.assertEqual(terminal["prior_exact_length"], 3)
        self.assertEqual(audit.prior_bucket(terminal), "3")
        self.assertIsNone(terminal["exact_follow_count"])
        self.assertIsNone(terminal["touch_25"])

    def test_doji_breaks_leg_and_cannot_be_reversal_or_predecessor(self):
        events = self.events(bars([0, -1, -1, 1, 1, 0, -1, 1]))
        self.assertEqual([event["source_row"] for event in events], [4, 8])
        self.assertEqual(events[0]["prior_exact_length"], 2)
        self.assertEqual(events[0]["follow_count"], 1)
        self.assertEqual(events[0]["end_reason"], "doji")
        self.assertTrue(events[0]["f1_known"])
        self.assertEqual(events[1]["prior_exact_length"], 1)

    def test_ineligible_barrier_preserves_successes_then_censors(self):
        observed = bars([-1, 1, 1, 1, -1])
        observed[3] = replace(observed[3], completion=None, status="unknown_completion")
        events = self.events(observed)
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event["follow_count"], 1)
        self.assertTrue(event["right_censored"])
        self.assertEqual(event["end_reason"], "completion_status:unknown_completion")
        cells = {}
        audit.collect_event(cells, event, [])
        cell = cells[(4, None, "all_hours", "bullish", "all")]
        self.assertEqual(cell["outcomes"][1]["success"], 1)
        self.assertEqual(cell["outcomes"][2]["unknown"], 1)
        self.assertEqual(cell["outcomes"][20]["failure"], 0)

    def test_completed_failure_makes_later_horizons_known_despite_barrier(self):
        observed = bars([-1, 1, 1, -1, -1])
        observed[4] = replace(observed[4], completion=None, status="unknown_completion")
        events = self.events(observed)
        cells = {}
        audit.collect_event(cells, events[0], [])
        cell = cells[(4, None, "all_hours", "bullish", "all")]
        self.assertEqual(cell["outcomes"][1]["success"], 1)
        self.assertEqual(cell["outcomes"][2]["failure"], 1)
        self.assertEqual(cell["outcomes"][20]["failure"], 1)
        self.assertEqual(cell["outcomes"][20]["unknown"], 0)

    def test_source_gap_and_session_boundary_never_stitch(self):
        observed = bars([-1, 1, 1])
        later = replace(observed[-1], row=5)
        event = self.events([*observed[:2], later])[0]
        self.assertEqual(event["follow_count"], 0)
        self.assertEqual(event["end_reason"], "source_row_gap")
        self.assertFalse(event["f1_known"])
        tomorrow = replace(observed[-1], session=date(2025, 1, 3), start=datetime(2025, 1, 2, 18), completion=datetime(2025, 1, 2, 18, 1))
        event = self.events([*observed[:2], tomorrow])[0]
        self.assertEqual(event["end_reason"], "session_boundary")
        self.assertEqual(event["follow_count"], 0)

    def test_duplicate_second_original_order_and_one_bar_prior_leg(self):
        observed = bars([-1, 1, -1, 1])
        observed = [replace(item, start=observed[0].start, completion=observed[0].start, status="next_bar_start_same_second") for item in observed]
        events = self.events(observed)
        self.assertEqual([event["source_row"] for event in events], [2, 3, 4])
        self.assertEqual(events[0]["follow_count"], 0)
        self.assertEqual(events[1]["prior_exact_length"], 1)
        self.assertEqual(events[1]["available_at"], events[0]["available_at"])

    def test_partial_final_session_has_no_events(self):
        self.assertEqual(self.events(bars([-1, 1, -1], start="2026-09-24 10:00:00", session="2026-09-24")), [])

    def test_bull_retrace_touches_inclusive_and_favorable_beyond_close_strict(self):
        observed = bars([-1, 4, 1, -1])
        observed[2] = replace(observed[2], opening=Decimal(102), high=Decimal(105), low=Decimal(102), closing=Decimal(105))
        event = self.events(observed)[0]
        self.assertEqual([event[f"retrace_price_{level}"] for level in audit.LEVELS], [Decimal(103), Decimal(102), Decimal(101), Decimal(100)])
        self.assertEqual([event[f"touch_{level}"] for level in audit.LEVELS], [True, True, False, False])
        self.assertTrue(event["favorable_beyond_close"])
        observed[2] = replace(observed[2], closing=Decimal(104))
        event = self.events(observed)[0]
        self.assertFalse(event["favorable_beyond_close"])
        self.assertTrue(event["favorable_same_colour"])

    def test_bear_retrace_is_mirrored(self):
        observed = bars([1, -4, -1, 1])
        observed[1] = replace(observed[1], opening=Decimal(104), high=Decimal(104), low=Decimal(100), closing=Decimal(100))
        observed[2] = replace(observed[2], opening=Decimal(102), high=Decimal(102), low=Decimal(99), closing=Decimal(99))
        event = self.events(observed)[0]
        self.assertEqual([event[f"retrace_price_{level}"] for level in audit.LEVELS], [Decimal(101), Decimal(102), Decimal(103), Decimal(104)])
        self.assertEqual([event[f"touch_{level}"] for level in audit.LEVELS], [True, True, False, False])
        self.assertTrue(event["favorable_beyond_close"])

    def test_gap_and_doji_can_be_beyond_close_without_colour_continuation(self):
        observed = bars([-1, 4, 0, -1])
        observed[2] = replace(observed[2], opening=Decimal(105), high=Decimal(106), low=Decimal(102), closing=Decimal(105))
        event = self.events(observed)[0]
        self.assertTrue(event["favorable_beyond_close"])
        self.assertFalse(event["favorable_same_colour"])
        self.assertEqual(event["follow_count"], 0)
        self.assertEqual(event["end_reason"], "doji")
        self.assertTrue(event["touch_50"])


class GroupedReversalAuditTests(unittest.TestCase):
    def test_empty_groups_explicit_nulls_and_complete_dimensions(self):
        tables = audit.expected_tables({}, {}, [4], [2025], [])
        self.assertEqual(len(tables["summary"]), 2 * 3 * 15)
        self.assertEqual(len(tables["continuation"]), 2 * 3 * 15 * 20)
        self.assertEqual(len(tables["retracement"]), 2 * 3 * 15 * 4)
        self.assertTrue(all(row["probability"] is None for row in tables["continuation"]))
        self.assertTrue(all(row["joint_beyond_close_probability"] is None for row in tables["retracement"]))

    def test_prior_exact_bucket_endpoints_and_unknown_observed_lengths(self):
        for length, bucket in [(1, "1"), (10, "10"), (11, "11-15"), (15, "11-15"), (16, "16-20"), (20, "16-20"), (21, "21+")]:
            event = {"prior_start_known": True, "prior_exact_length": length, "prior_observed_length": length}
            self.assertEqual(audit.prior_bucket(event), bucket)
            event["prior_start_known"] = False
            self.assertEqual(audit.prior_bucket(event), "unknown_start")

    def test_completion_anchor_does_not_use_reversal_open_or_future_time(self):
        observed = bars([0, -1, 1, 1, -1], start="2025-01-02 09:29:57")
        event = list(audit.reconstruct_events(observed, 4, set()))[0]
        self.assertEqual(event["start_timestamp"], datetime(2025, 1, 2, 9, 29, 59))
        self.assertEqual(event["available_at"], datetime(2025, 1, 2, 9, 30))
        cells = {}
        windows = [{"id": "ny_open", "start": "09:30", "end": "10:30"}]
        audit.collect_event(cells, event, windows)
        self.assertIn((4, None, "ny_open", "bullish", "1"), cells)
        self.assertNotIn((4, None, "ny_open", "bearish", "all"), cells)

    def test_horizon_specific_known_denominators_and_conditional_retrace(self):
        first = list(audit.reconstruct_events(bars([0, -1, 4, 1, -1]), 4, set()))[0]
        first.update(f1_open=Decimal(102), f1_high=Decimal(105), f1_low=Decimal(102), f1_close=Decimal(105),
                     touch_25=True, touch_50=True, touch_75=False, touch_100=False,
                     favorable_beyond_close=True, favorable_same_colour=True)
        second = dict(first, right_censored=True, exact_follow_count=None, follow_count=1,
                      prior_start_known=False, prior_exact_length=None)
        cells = {}
        for event in (first, second):
            audit.collect_event(cells, event, [])
        tables = audit.expected_tables(cells, {}, [4], [2025], [])
        rows = [row for row in tables["continuation"] if row["year"] is None and row["direction"] == "bullish" and row["prior_leg_bucket"] == "all"]
        self.assertEqual((rows[0]["numerator"], rows[0]["denominator"], rows[0]["unknown_count"]), (2, 2, 0))
        self.assertEqual((rows[1]["numerator"], rows[1]["denominator"], rows[1]["unknown_count"]), (0, 1, 1))
        summary = [row for row in tables["summary"] if row["year"] is None and row["direction"] == "bullish"]
        self.assertEqual(summary[0]["event_count"], 2)
        self.assertEqual(sum(row["event_count"] for row in summary[1:]), 2)
        retraces = [row for row in tables["retracement"] if row["year"] is None and row["direction"] == "bullish" and row["prior_leg_bucket"] == "all"]
        self.assertEqual((retraces[1]["joint_beyond_close_numerator"], retraces[1]["joint_beyond_close_denominator"], retraces[1]["conditional_beyond_close_denominator"]), (2, 2, 2))
        self.assertEqual(retraces[3]["touch_count"], 0)
        self.assertIsNone(retraces[3]["conditional_beyond_close_probability"])

    def test_cohort_direction_and_year_conservation_rejects_tampered_counts(self):
        events = list(audit.reconstruct_events(bars([0, -1, 1, 1, -1]), 4, set()))
        cells = {}
        for event in events:
            audit.collect_event(cells, event, [])
        audit.verify_group_conservation(cells)
        cells[(4, None, "all_hours", "bullish", "1")]["events"] += 1
        with self.assertRaisesRegex(ValueError, "cohort conservation"):
            audit.verify_group_conservation(cells)


class FrozenProtocolGuardTests(unittest.TestCase):
    def settings(self):
        return json.loads((STUDY / "reversal.yaml").read_text())

    def test_supported_frozen_definition_is_accepted(self):
        windows, excluded = audit.validate_protocol(self.settings())
        self.assertEqual(len(windows), 7)
        self.assertEqual(excluded, {date(2026, 9, 24)})

    def test_changed_causal_anchor_and_touch_definition_are_refused(self):
        settings = self.settings()
        settings["reporting"]["event_membership_timestamp"] = "reversal_open_timestamp"
        with self.assertRaisesRegex(ValueError, "grouping"):
            audit.validate_protocol(settings)
        settings = self.settings()
        settings["reversal_definition"]["touch"] = "exclusive touch"
        with self.assertRaisesRegex(ValueError, "event/outcome"):
            audit.validate_protocol(settings)

    def test_reversal_included_in_horizon_or_missing_prior_bucket_are_refused(self):
        settings = self.settings()
        settings["reversal_definition"]["n_excludes_reversal"] = False
        with self.assertRaisesRegex(ValueError, "event/outcome"):
            audit.validate_protocol(settings)
        settings = self.settings()
        settings["reversal_definition"]["prior_leg_buckets"].remove("unknown_start")
        with self.assertRaisesRegex(ValueError, "event/outcome"):
            audit.validate_protocol(settings)


class StagedAuditGuardTests(unittest.TestCase):
    """Positive/tamper checks of receipts, separate from the numerical examples."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.stage = self.root / "work" / audit.STUDY_ID / "20261012T000000Z_audit_synthetic"
        self.stage.mkdir(parents=True)
        self.study = self.root / "studies" / audit.STUDY_ID
        self.study.mkdir(parents=True)
        self.workspace_patch = patch.object(audit, "WORKSPACE", self.root)
        self.workspace_patch.start()
        self.addCleanup(self.workspace_patch.stop)
        (self.study / "reversal_audit.py").write_bytes((STUDY / "reversal_audit.py").read_bytes())
        (self.study / "reversal.yaml").write_bytes((STUDY / "reversal.yaml").read_bytes())
        self.settings_path = self.stage / "config.json"
        self.settings_path.write_bytes((STUDY / "reversal.yaml").read_bytes())
        self.lock_path = self.stage / "inputs.lock.json"
        self.observed = [*bars([-1, 1], start="2019-11-01 10:00:00", session="2019-11-01"),
                         *bars([-1, 1, 1, -1], start="2025-01-02 10:00:00"),
                         *bars([1], start="2026-09-24 10:00:00", session="2026-09-24")]
        self.observed = [replace(item, row=index + 1) for index, item in enumerate(self.observed)]
        files = []
        for setting in (4, 5, 6):
            directory = self.root / "data" / str(setting)
            directory.mkdir(parents=True)
            enhanced, original = save_inputs(directory, self.observed)
            for role, path in (("source", original), ("enhanced", enhanced)):
                files.append({"role": role, "setting_ticks": setting, "root_alias": "publication_root",
                              **self.record(path, self.root), "rows": len(self.observed),
                              "first_session_date_proxy": "2019-11-01", "last_session_date_proxy": "2026-09-24",
                              "session_dates_with_data": 3})
        manifest = self.root / "data" / "manifest.json"
        manifest.write_text("{}\n")
        clock = self.root / "docs" / "clock.json"
        clock.parent.mkdir()
        clock.write_text("{}\n")
        lock = {"study_id": audit.STUDY_ID, "files": files,
                "manifests": [{"role": "range_xv_export_manifest", "root_alias": "publication_root", **self.record(manifest, self.root)}],
                "clock_migration": {"root_alias": "workspace_root", **self.record(clock, self.root)}}
        self.save(self.study / "inputs.lock.json", lock)
        self.lock_path.write_bytes((self.study / "inputs.lock.json").read_bytes())
        execution_sources, frozen_inputs = [], []
        for name, destination, category in (("reversal_audit.py", f"provenance/source-snapshot/studies/{audit.STUDY_ID}/reversal_audit.py", execution_sources),
                                            ("reversal.yaml", "study.yaml", frozen_inputs),
                                            ("inputs.lock.json", "inputs.lock.json", frozen_inputs)):
            source = self.study / name
            retained = self.stage / destination
            retained.parent.mkdir(parents=True, exist_ok=True)
            if not retained.exists():
                retained.write_bytes(source.read_bytes())
            category.append({**self.record(source, self.root), "snapshot_path": destination})
        self.save(self.stage / "provenance/execution-start.json", {"study_id": audit.STUDY_ID, "run_id": self.stage.name,
                  "execution_sources": execution_sources, "frozen_inputs": frozen_inputs})

    @staticmethod
    def record(path, root):
        return {"path": path.relative_to(root).as_posix(), "sha256": audit.digest(path), "bytes": path.stat().st_size}

    @staticmethod
    def save(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + "\n")

    @staticmethod
    def save_rows(path, rows):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def test_frozen_verifier_and_settings_bytes_must_match(self):
        binding = audit.verify_frozen_stage(self.stage, self.settings_path, self.lock_path)
        self.assertEqual(binding["settings_sha256"], audit.digest(self.settings_path))
        (self.study / "reversal_audit.py").write_text("# Changed verifier\n")
        with self.assertRaisesRegex(ValueError, "Frozen source/protocol"):
            audit.verify_frozen_stage(self.stage, self.settings_path, self.lock_path)

    def test_live_settings_instead_of_frozen_settings_are_refused(self):
        with self.assertRaisesRegex(ValueError, "frozen stage files"):
            audit.verify_frozen_stage(self.stage, self.study / "reversal.yaml", self.lock_path)

    def test_retained_snapshot_tamper_is_refused(self):
        (self.stage / "study.yaml").write_text("{}\n")
        with self.assertRaisesRegex(ValueError, "Frozen source/protocol"):
            audit.verify_frozen_stage(self.stage, self.settings_path, self.lock_path)

    def test_all_input_pins_reject_raw_byte_drift(self):
        lock = json.loads(self.lock_path.read_text())
        self.assertEqual(len(audit.verify_input_pins(lock, self.root)), 8)
        source = next(item for item in lock["files"] if item["role"] == "source")
        (self.root / source["path"]).write_text("changed source\n")
        with self.assertRaisesRegex(ValueError, "Pinned input bytes changed"):
            audit.verify_input_pins(lock, self.root)

    def test_complete_synthetic_stage_and_changed_artifact_refusal(self):
        lock = json.loads(self.lock_path.read_text())
        windows, excluded = audit.validate_protocol(json.loads(self.settings_path.read_text()))
        cells, coverage, diagnostics = {}, {}, {}
        for setting in (4, 5, 6):
            enhanced = next(item for item in lock["files"] if item["role"] == "enhanced" and item["setting_ticks"] == setting)
            original = next(item for item in lock["files"] if item["role"] == "source" and item["setting_ticks"] == setting)
            totals = {}
            observed = list(audit.observe_inputs(audit.read_bars(self.root / enhanced["path"], raw_path=self.root / original["path"]), excluded, totals))
            events = list(audit.reconstruct_events(observed, setting, excluded))
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["follow_count"], 1)
            self.assertTrue(events[0]["right_censored"])
            self.save_rows(self.stage / "evidence" / f"reversals_{setting}t.csv", events)
            diagnostics[str(setting)] = totals
            for bar in observed:
                if audit.barrier(bar, excluded) is None:
                    audit.collect_coverage(coverage, bar, setting, windows)
            for event in events:
                audit.collect_event(cells, event, windows)
        expected = audit.expected_tables(cells, coverage, [4, 5, 6], list(range(2019, 2027)), windows)
        for name, rows in expected.items():
            path = self.stage / "tables" / ("coverage.csv" if name == "coverage" else f"reversal_{name}.csv")
            self.save_rows(path, rows)
        self.save(self.stage / "input-audit.json", {"schema_version": 1, "study_id": audit.STUDY_ID,
                  "run_id": self.stage.name, "settings": diagnostics})
        artifacts = [self.stage / "input-audit.json", *(self.stage / "tables").glob("*.csv"), *(self.stage / "evidence").glob("*.csv")]
        hashes = {path.relative_to(self.stage).as_posix(): audit.digest(path) for path in artifacts}
        self.save(self.stage / "provenance/execution-complete.json", {"result": "passed", "study_id": audit.STUDY_ID,
                  "run_id": self.stage.name, "artifact_hashes": hashes})
        with redirect_stdout(io.StringIO()):
            report = audit.audit_stage(self.stage, self.stage / "evidence", self.root, self.settings_path, self.lock_path)
        self.assertEqual(report["result"], "passed")
        self.assertEqual(report["tables"]["summary"]["rows"], 9720)
        self.assertEqual(report["tables"]["continuation"]["rows"], 194400)
        self.assertEqual(report["tables"]["retracement"]["rows"], 38880)
        ledger = self.stage / "evidence/reversals_4t.csv"
        ledger.write_text(ledger.read_text().replace("next", "changed") + "\n")
        with self.assertRaisesRegex(ValueError, "differ from execution receipt"):
            audit.audit_stage(self.stage, self.stage / "evidence", self.root, self.settings_path, self.lock_path)


if __name__ == "__main__":
    unittest.main()
