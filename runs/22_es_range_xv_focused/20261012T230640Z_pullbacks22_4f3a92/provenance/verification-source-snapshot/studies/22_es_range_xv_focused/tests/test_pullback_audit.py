"""Independent A→one B→R verification examples; synthetic inputs only."""
from __future__ import annotations

import csv
from contextlib import redirect_stdout
import hashlib
import io
import json
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from dataclasses import replace


STUDY = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("study22_pullback_audit", STUDY / "pullback_audit.py")
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
            source_stamp = stamp.replace(tzinfo=ZoneInfo("America/New_York")).astimezone(timezone(timedelta(hours=-4))).strftime("%Y-%d-%m %H:%M:%S")
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


class PullbackReconstructionTests(unittest.TestCase):
    def events(self, observed):
        return list(audit.reconstruct_events(observed, 4, {date(2026, 9, 24)}))

    def test_known_A_three_B_one_R_follow_two(self):
        event = self.events(bars([0, -1, -1, -1, 1, -1, -1, -1, 0]))[0]
        self.assertEqual(event['source_row'], 6)
        self.assertEqual(event['direction'], 'bearish')
        self.assertEqual(event['earlier_start_source_row'], 2)
        self.assertEqual(event['earlier_end_source_row'], 4)
        self.assertEqual(event['pullback_source_row'], 5)
        self.assertEqual(event['previous_source_row'], 5)
        self.assertTrue(event['earlier_start_known'])
        self.assertEqual(event['earlier_exact_length'], 3)
        self.assertEqual(event['earlier_observed_length'], 3)
        self.assertEqual(event['follow_count'], 2)
        self.assertEqual(event['exact_follow_count'], 2)
        self.assertEqual(event['end_reason'], 'doji')
        self.assertEqual(audit.earlier_bucket(event), '3')

    def test_unknown_A_start_is_not_exact_size(self):
        event = self.events(bars([1, 1, 1, -1, 1, 1, 1, -1]))[0]
        self.assertEqual(event['source_row'], 5)
        self.assertFalse(event['earlier_start_known'])
        self.assertIsNone(event['earlier_exact_length'])
        self.assertEqual(event['earlier_observed_length'], 3)
        self.assertEqual(audit.earlier_bucket(event), 'unknown_start')

    def test_two_opposite_B_candles_are_not_a_one_candle_pullback(self):
        self.assertEqual(self.events(bars([0, 1, 1, -1, -1, 1, 1, 0])), [])

    def test_doji_breaks_A_B_R_contiguity(self):
        self.assertEqual(self.events(bars([1, 1, 0, -1, 1, 0])), [])
        self.assertEqual(self.events(bars([1, -1, 0, 1, 1, 0])), [])
        self.assertEqual(self.events(bars([1, 0, 1, 1, 0])), [])

    def test_each_alternation_is_selected_in_source_order(self):
        events = self.events(bars([1, -1, 1, -1, 1, -1]))
        self.assertEqual([e['source_row'] for e in events], [3, 4, 5, 6])
        self.assertEqual([e['earlier_exact_length'] for e in events], [None, 1, 1, 1])
        self.assertEqual([e['follow_count'] for e in events], [0, 0, 0, 0])
        self.assertTrue(events[-1]['right_censored'])

    def test_same_second_rows_and_duplicates_retain_original_order(self):
        observed = bars([1, 1, -1, 1, 1, -1])
        observed = [replace(item, start=observed[0].start, completion=observed[0].start,
                            status='next_bar_start_same_second') for item in observed]
        events = self.events(observed)
        self.assertEqual([e['source_row'] for e in events], [4])
        self.assertEqual(events[0]['follow_count'], 1)
        self.assertEqual(events[0]['available_at'], observed[0].start)

    def test_ineligible_barrier_before_R_prevents_selection(self):
        observed = bars([1, -1, 1])
        observed[1] = replace(observed[1], completion=None, status='unknown_completion')
        self.assertEqual(self.events(observed), [])

    def test_ineligible_barrier_after_R_keeps_known_success_then_unknown(self):
        observed = bars([0, -1, 1, -1, -1, -1, 1])
        observed[5] = replace(observed[5], completion=None, status='unknown_completion')
        event = self.events(observed)[0]
        self.assertEqual(event['source_row'], 4)
        self.assertEqual(event['follow_count'], 1)
        self.assertTrue(event['right_censored'])
        cells = {}
        audit.collect_event(cells, event, [])
        c = cells[(4, None, 'all_hours', 'bearish', '1')]
        self.assertEqual(c['outcomes'][1]['success'], 1)
        self.assertEqual(c['outcomes'][2]['unknown'], 1)
        self.assertEqual(c['outcomes'][20]['failure'], 0)

    def test_missing_F1_is_unknown_not_failure(self):
        event = self.events(bars([0, 1, -1, 1]))[0]
        self.assertFalse(event['f1_known'])
        self.assertIsNone(event['touch_50'])
        cells = {}
        audit.collect_event(cells, event, [])
        row = audit.expected_tables(cells, {}, [4], [2025], [])['retracement'][0]
        self.assertEqual(row['valid_f1_count'], 0)
        self.assertIsNone(row['touch_probability'])

    def test_source_gap_and_session_boundary_never_stitch(self):
        observed = bars([1, -1, 1])
        self.assertEqual(self.events([*observed[:2], replace(observed[2], row=5)]), [])
        tomorrow = replace(observed[2], session=date(2025, 1, 3), start=datetime(2025, 1, 2, 18),
                           completion=datetime(2025, 1, 2, 18, 1))
        self.assertEqual(self.events([*observed[:2], tomorrow]), [])

    def test_partial_final_session_is_fully_excluded(self):
        self.assertEqual(self.events(bars([1, -1, 1, 1], start='2026-09-24 10:00:00', session='2026-09-24')), [])

    def test_inclusive_bull_retracement_and_strict_close(self):
        observed = bars([0, 1, -1, 4, 1, 0])
        observed[4] = replace(observed[4], opening=Decimal(102), high=Decimal(105),
                              low=Decimal(102), closing=Decimal(105))
        event = self.events(observed)[0]
        self.assertEqual([event[f'retrace_price_{p}'] for p in audit.LEVELS],
                         [Decimal(103), Decimal(102), Decimal(101), Decimal(100)])
        self.assertEqual([event[f'touch_{p}'] for p in audit.LEVELS], [True, True, False, False])
        self.assertTrue(event['favorable_beyond_close'])
        observed[4] = replace(observed[4], closing=Decimal(104))
        self.assertFalse(self.events(observed)[0]['favorable_beyond_close'])

    def test_bear_retracement_is_mirrored(self):
        observed = bars([0, -1, 1, -4, -1, 0])
        observed[3] = replace(observed[3], opening=Decimal(104), high=Decimal(104), low=Decimal(100), closing=Decimal(100))
        observed[4] = replace(observed[4], opening=Decimal(102), high=Decimal(102), low=Decimal(99), closing=Decimal(99))
        event = self.events(observed)[0]
        self.assertEqual([event[f'retrace_price_{p}'] for p in audit.LEVELS],
                         [Decimal(101), Decimal(102), Decimal(103), Decimal(104)])
        self.assertEqual([event[f'touch_{p}'] for p in audit.LEVELS], [True, True, False, False])
        self.assertTrue(event['favorable_beyond_close'])

    def test_all_groups_conserve_disjoint_cohorts_directions_and_years(self):
        cells = {}
        events = self.events(bars([0, 1, 1, -1, 1, 1, -1, -1, 1, -1, 0]))
        for event in events:
            audit.collect_event(cells, event, [])
        audit.verify_group_conservation(cells)
        rows = audit.expected_tables(cells, {}, [4], [2025], [])['continuation']
        all_cell = next(r for r in rows if r['direction']=='all' and r['earlier_leg_bucket']=='all' and r['n']==1 and r['year'] is None)
        self.assertEqual(all_cell['event_count'], len(events))
        self.assertEqual(all_cell['event_count'], all_cell['success_count']+all_cell['failure_count']+all_cell['unknown_count'])
        cells[(4, None, 'all_hours', 'all', 'all')]['events'] += 1
        with self.assertRaisesRegex(ValueError, 'conservation'):
            audit.verify_group_conservation(cells)

    def test_bucket_boundaries_10_15_20_and_longer(self):
        for length, bucket in [(1,'1'), (10,'10'), (11,'11-15'), (15,'11-15'), (16,'16-20'), (20,'16-20'), (21,'21+')]:
            event = self.events(bars([0]+[1]*length+[-1,1,0]))[0]
            self.assertEqual(audit.earlier_bucket(event), bucket)

    def test_year_and_window_use_R_completion_proxy(self):
        windows = [{'id':'ny_open','start':'09:30','end':'10:30'}]
        observed = bars([0, 1, -1, 1, 0], start='2025-01-02 09:29:56')
        event = self.events(observed)[0]
        self.assertEqual(event['start_timestamp'].time().isoformat(),'09:29:59')
        self.assertEqual(event['available_at'].time().isoformat(),'09:30:00')
        cells = {}
        audit.collect_event(cells, event, windows)
        self.assertIn((4,2025,'ny_open','bullish','1'), cells)
        summary = audit.expected_tables(cells, {}, [4], [2025], windows)['summary'][0]
        self.assertEqual(summary['event_membership_anchor'], 'setup_R_completion_timestamp_proxy')

    def test_wrong_declared_clock_transform_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            enhanced, original = save_inputs(Path(directory).resolve(), bars([1,-1,1]))
            # Shift derived wall time consistently while retaining valid shape.
            enhanced.write_text(enhanced.read_text().replace('09:29:59', '08:29:59'))
            with self.assertRaisesRegex(ValueError, 'clock normalization'):
                list(audit.read_bars(enhanced, raw_path=original))


class IndependentEngineParityTests(unittest.TestCase):
    def test_exhaustive_short_sign_paths_match_separate_streaming_engine(self):
        # The verifier itself never imports numerical code. This test compares
        # two implementations on every 3^7 doji/bull/bear path.
        from itertools import product
        sys.path.insert(0, str(STUDY / 'src'))
        from pullbacks import extract_pullbacks, ledger_row
        from trends import Bar
        for signs in product((-1, 0, 1), repeat=7):
            observed = bars(signs)
            engine_bars = [Bar(4, b.row, b.start, b.completion, b.session,
                               b.opening, b.high, b.low, b.closing, b.status)
                           for b in observed]
            expected = list(audit.reconstruct_events(observed, 4, set()))
            actual = [ledger_row(e) for e in extract_pullbacks(engine_bars, 4)]
            self.assertEqual(len(expected), len(actual), signs)
            for a, b in zip(expected, actual):
                audit.compare_row(a, b, f'synthetic signs {signs}')


class FrozenProtocolGuardTests(unittest.TestCase):
    def settings(self):
        return json.loads((STUDY / 'pullback.yaml').read_text())

    def test_current_frozen_definitions_are_supported(self):
        windows, excluded = audit.validate_protocol(self.settings())
        self.assertEqual(len(windows), 7)
        self.assertEqual(excluded, {date(2026,9,24)})

    def test_changed_anchor_retracement_or_R_count_is_refused(self):
        for target, key, changed in [('reporting', 'event_membership_timestamp', 'R_open'),
                                     ('pullback_definition', 'touch', 'exclusive'),
                                     ('pullback_definition', 'n_excludes_reversal', False)]:
            settings = self.settings()
            settings[target][key] = changed
            with self.assertRaises(ValueError):
                audit.validate_protocol(settings)

    def test_changed_proxy_entry_stop_horizon_or_target_is_refused(self):
        for key, changed in [('entry', 'R.close'), ('nominal_price_buffer', '0.5'),
                             ('horizon_bars', 20), ('target_r', [1,3]), ('opening_cross','extrema first')]:
            settings = self.settings()
            settings['payoff_proxy_definition'][key] = changed
            with self.assertRaisesRegex(ValueError, 'payoff-proxy'):
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
        (self.study / "pullback_audit.py").write_bytes((STUDY / "pullback_audit.py").read_bytes())
        (self.study / "pullback.yaml").write_bytes((STUDY / "pullback.yaml").read_bytes())
        self.settings_path = self.stage / "config.json"
        self.settings_path.write_bytes((STUDY / "pullback.yaml").read_bytes())
        self.lock_path = self.stage / "inputs.lock.json"
        self.observed = [*bars([-1, 1], start="2019-11-01 10:00:00", session="2019-11-01"),
                         *bars([1, -1, 1, 1, -1], start="2025-01-02 10:00:00"),
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
        for name, destination, category in (("pullback_audit.py", f"provenance/source-snapshot/studies/{audit.STUDY_ID}/pullback_audit.py", execution_sources),
                                            ("pullback.yaml", "study.yaml", frozen_inputs),
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
        (self.study / "pullback_audit.py").write_text("# Changed verifier\n")
        with self.assertRaisesRegex(ValueError, "Frozen source/protocol"):
            audit.verify_frozen_stage(self.stage, self.settings_path, self.lock_path)

    def test_live_settings_instead_of_frozen_settings_are_refused(self):
        with self.assertRaisesRegex(ValueError, "frozen stage files"):
            audit.verify_frozen_stage(self.stage, self.study / "pullback.yaml", self.lock_path)

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
        cells, coverage, payoff_cells, diagnostics = {}, {}, {}, {}
        for setting in (4, 5, 6):
            enhanced = next(item for item in lock["files"] if item["role"] == "enhanced" and item["setting_ticks"] == setting)
            original = next(item for item in lock["files"] if item["role"] == "source" and item["setting_ticks"] == setting)
            totals = {}
            observed = list(audit.observe_inputs(audit.read_bars(self.root / enhanced["path"], raw_path=self.root / original["path"]), excluded, totals))
            payoff_results = []
            events = list(audit.reconstruct_events(observed, setting, excluded, payoff_sink=payoff_results.append))
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["follow_count"], 1)
            self.assertTrue(events[0]["right_censored"])
            self.save_rows(self.stage / "evidence" / f"pullbacks_{setting}t.csv", events)
            self.save_rows(self.stage / "evidence" / f"payoff_{setting}t.csv", payoff_results)
            for result in payoff_results:
                audit.collect_payoff(payoff_cells, result, windows)
            diagnostics[str(setting)] = totals
            for bar in observed:
                if audit.barrier(bar, excluded) is None:
                    audit.collect_coverage(coverage, bar, setting, windows)
            for event in events:
                audit.collect_event(cells, event, windows)
        expected = audit.expected_tables(cells, coverage, [4, 5, 6], list(range(2019, 2027)), windows)
        expected["payoff"] = audit.expected_payoff_tables(payoff_cells, [4,5,6], list(range(2019,2027)), windows)
        for name, rows in expected.items():
            path = self.stage / "tables" / ("coverage.csv" if name == "coverage" else f"pullback_{name}.csv")
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
        self.assertEqual(report["tables"]["payoff"]["rows"], 19440)
        self.assertTrue(all(source["reconstructed_payoffs"]==2 for source in report["sources"]))
        ledger = self.stage / "evidence/pullbacks_4t.csv"
        ledger.write_text(ledger.read_text().replace("next", "changed") + "\n")
        with self.assertRaisesRegex(ValueError, "differ from execution receipt"):
            audit.audit_stage(self.stage, self.stage / "evidence", self.root, self.settings_path, self.lock_path)

class IndependentPayoffTests(unittest.TestCase):
    def event(self, bullish=True):
        observed = bars([0,1,-1,1] if bullish else [0,-1,1,-1])
        return list(audit.reconstruct_events(observed,4,set()))[0]

    def path(self, length=10):
        template = bars([1])[0]
        return [replace(template, row=5+i, start=template.start+timedelta(seconds=4+i),
                        completion=template.completion+timedelta(seconds=4+i),
                        opening=Decimal(100), high=Decimal('100.5'), low=Decimal('99.5'), closing=Decimal('100.2'))
                for i in range(length)]

    def test_single_target_or_stop_touches_use_literal_payoff(self):
        event=self.event();path=self.path()
        path[0]=replace(path[0],high=Decimal('101.25'))
        result=audit.reconstruct_payoff(event,path,1,'export_end')
        self.assertEqual((result['status'],result['exit_reason'],result['payoff_lower_r']),('resolved','target_touch',Decimal(1)))
        path[0]=replace(path[0],high=Decimal('100.5'),low=Decimal('98.75'))
        result=audit.reconstruct_payoff(event,path,1,'export_end')
        self.assertEqual((result['exit_reason'],result['payoff_lower_r']),('stop_touch',Decimal(-1)))

    def test_same_bar_dual_touch_retains_order_bounds(self):
        path=self.path();path[0]=replace(path[0],high=Decimal('103'),low=Decimal('98'))
        result=audit.reconstruct_payoff(self.event(),path,2,'export_end')
        self.assertEqual(result['status'],'ambiguous')
        self.assertEqual(result['exit_reason'],'both_touch')
        self.assertEqual((result['payoff_lower_r'],result['payoff_upper_r']),(Decimal(-1),Decimal(2)))
        self.assertIsNone(result['exit_price'])

    def test_open_cross_has_precedence_even_if_both_extrema_cross(self):
        path=self.path();path[1]=replace(path[1],opening=Decimal(103),high=Decimal(104),low=Decimal(98))
        result=audit.reconstruct_payoff(self.event(),path,1,'export_end')
        self.assertEqual((result['status'],result['exit_reason']),('resolved','target_open_gap'))
        self.assertEqual(result['payoff_lower_r'],Decimal('2.4'))
        self.assertEqual(result['exit_available_at'],path[1].start)
        path[1]=replace(path[1],opening=Decimal(98),high=Decimal(104),low=Decimal(97))
        result=audit.reconstruct_payoff(self.event(),path,1,'export_end')
        self.assertEqual(result['exit_reason'],'stop_open_gap')
        self.assertEqual(result['payoff_lower_r'],Decimal('-1.6'))

    def test_horizon_mark_uses_tenth_physical_close(self):
        path=self.path();path[-1]=replace(path[-1],closing=Decimal('100.4'))
        result=audit.reconstruct_payoff(self.event(),path,2,'export_end')
        self.assertEqual((result['status'],result['bars_observed'],result['exit_source_row']),('marked',10,14))
        self.assertEqual(result['payoff_lower_r'],Decimal('.32'))
        self.assertEqual(result['exit_available_at'],path[-1].completion)

    def test_barrier_before_ten_is_unknown_with_observed_risk_and_entry(self):
        result=audit.reconstruct_payoff(self.event(),self.path(9),1,'session_boundary')
        self.assertEqual((result['status'],result['exit_reason'],result['bars_observed']),('unknown','session_boundary',9))
        self.assertEqual(result['risk_points'],Decimal('1.25'))
        self.assertIsNone(result['payoff_lower_r'])

    def test_no_F1_retains_unknown_entry_separately(self):
        result=audit.reconstruct_payoff(self.event(),[],1,'session_boundary')
        self.assertEqual((result['status'],result['exit_reason']),('unknown','f1_unavailable'))
        self.assertIsNone(result['entry_price'])
        self.assertEqual(result['stop_price'],Decimal('98.75'))

    def test_nonpositive_entry_to_stop_risk_is_invalid_not_unknown(self):
        path=self.path();path[0]=replace(path[0],opening=Decimal('98.5'),low=Decimal(98))
        result=audit.reconstruct_payoff(self.event(),path,1,'export_end')
        self.assertEqual((result['status'],result['exit_reason'],result['bars_observed']),('invalid','nonpositive_entry_to_stop_risk',0))
        self.assertEqual(result['risk_points'],Decimal('-.25'))
        self.assertIsNone(result['target_price'])

    def test_bearish_path_is_mirrored(self):
        path=self.path();path[0]=replace(path[0],low=Decimal('98.75'))
        result=audit.reconstruct_payoff(self.event(False),path,1,'export_end')
        self.assertEqual(result['stop_price'],Decimal('101.25'))
        self.assertEqual(result['target_price'],Decimal('98.75'))
        self.assertEqual(result['payoff_lower_r'],Decimal(1))

    def test_proxy_does_not_stop_at_opposite_or_doji_candle(self):
        path=self.path();path[0]=replace(path[0],closing=Decimal('99.8'))
        path[1]=replace(path[1],closing=Decimal(100))
        path[2]=replace(path[2],high=Decimal('101.25'))
        result=audit.reconstruct_payoff(self.event(),path,1,'export_end')
        self.assertEqual((result['exit_reason'],result['bars_observed']),('target_touch',3))

    def test_group_bounds_denominators_and_conservation(self):
        event=self.event();event_cells={};audit.collect_event(event_cells,event,[])
        payoffs={}
        for target in (1,2):
            path=self.path();path[0]=replace(path[0],high=Decimal(103),low=Decimal(98))
            result=audit.reconstruct_payoff(event,path,target,'export_end')
            audit.collect_payoff(payoffs,result,[])
        audit.verify_payoff_conservation(payoffs,event_cells)
        rows=audit.expected_payoff_tables(payoffs,[4],[2025],[])
        row=next(r for r in rows if r['year'] is None and r['direction']=='bullish' and r['earlier_leg_bucket']=='all' and r['target_multiple']==2)
        self.assertEqual((row['win_rate_lower'],row['win_rate_upper']),(0,1))
        self.assertEqual((row['mean_lower_r'],row['mean_upper_r']),(-1,2))
        payoffs[(4,None,'all_hours','bullish','all',2)]['events']+=1
        with self.assertRaisesRegex(ValueError,'conservation'):
            audit.verify_payoff_conservation(payoffs,event_cells)

    def test_independent_proxy_matches_streaming_engine_on_seeded_paths(self):
        import random
        sys.path.insert(0,str(STUDY/'src'))
        from pullbacks import extract_pullbacks
        from pullback_payoff import evaluate_payoffs,payoff_ledger_row
        from trends import Bar
        rng=random.Random(221004)
        for bullish in (True,False):
            for _ in range(50):
                observed=bars([0,1,-1,1] if bullish else [0,-1,1,-1])
                for i in range(12):
                    opening=Decimal(rng.randrange(96,105))+Decimal(rng.randrange(4))/4
                    closing=opening+Decimal(rng.choice((-1,0,1)))/4
                    high=max(opening,closing)+Decimal(rng.randrange(8))/4
                    low=min(opening,closing)-Decimal(rng.randrange(8))/4
                    stamp=observed[0].start+timedelta(seconds=4+i)
                    observed.append(audit.IndependentBar(5+i,stamp,observed[0].session,opening,high,low,closing,
                                                         stamp+timedelta(seconds=1),'next_bar_start_proxy'))
                engine_bars=[Bar(4,b.row,b.start,b.completion,b.session,b.opening,b.high,b.low,b.closing,b.status) for b in observed]
                engine_events=list(extract_pullbacks(engine_bars,4))
                actual=[payoff_ledger_row(result) for result in evaluate_payoffs(engine_events,engine_bars,4)]
                expected=[]
                list(audit.reconstruct_events(observed,4,set(),payoff_sink=expected.append))
                self.assertEqual(len(expected),len(actual))
                for e,a in zip(expected,actual):audit.compare_row(e,a,'seeded independent payoff parity')


if __name__ == '__main__':
    unittest.main()
