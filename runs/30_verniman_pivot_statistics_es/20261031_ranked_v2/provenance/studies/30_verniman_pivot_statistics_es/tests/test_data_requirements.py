"""Synthetic tests for price-blind exact-delivery acquisition requirements."""

from datetime import date
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data_requirements import (  # noqa: E402
    IDENTITY_COLUMNS, MASTER_COLUMNS, _expected_timestamp_ns,
    build_contract_windows, inspect_continuous_coverage,
    prior_nominal_full_sessions, session_bounds, session_calendar,
)


def coverage_row(day, contract="ESH2020", complete=True):
    return {"session_date": day, "full_contracts": [contract], "complete_nominal_roster": complete}


def candidate(day, contract="ESH2020", identifier="one"):
    return {"session_date": day, "full_contract": contract, "candidate_id": identifier}


class CalendarTests(unittest.TestCase):
    def test_prior_sessions_skip_weekend_and_existing_holiday_rules(self):
        prior, skipped = prior_nominal_full_sessions("2020-01-09")
        self.assertEqual(prior, ["2020-01-02", "2020-01-03", "2020-01-06", "2020-01-07", "2020-01-08"])
        prior, skipped = prior_nominal_full_sessions("2020-01-07")
        self.assertEqual(prior, ["2019-12-30", "2019-12-31", "2020-01-02", "2020-01-03", "2020-01-06"])
        self.assertIn("2020-01-01", [row["session_date"] for row in skipped])
        self.assertTrue(all(not row["exchange_calendar_certified"] for row in skipped))

    def test_dst_follows_new_york_not_fixed_utc_hours(self):
        before, _ = session_bounds("2026-03-06")
        after, end = session_bounds("2026-03-09")
        self.assertEqual(before.hour, 23)
        self.assertEqual(after.hour, 22)
        self.assertEqual(end.hour, 21)

    def test_historical_pause_and_uncertified_sessions(self):
        self.assertEqual(len(_expected_timestamp_ns(date(2021, 6, 25))), 1365)
        self.assertEqual(len(_expected_timestamp_ns(date(2021, 6, 28))), 1380)
        self.assertIsNone(session_calendar("2020-12-25")["expected_minutes"])
        self.assertEqual(_expected_timestamp_ns(date(2020, 12, 25)), set())


class ContractWindowTests(unittest.TestCase):
    def test_matching_delivery_requires_complete_warmup_and_target(self):
        prior, _ = prior_nominal_full_sessions("2020-01-09")
        retained = {"sessions": [coverage_row(day) for day in [*prior, "2020-01-09"]]}
        result = build_contract_windows([candidate("2020-01-09")], retained)
        row = result["candidate_requirements"][0]
        self.assertEqual(row["status"], "retained_identity_rosters_complete")
        self.assertFalse(row["feature_readiness_verified"])
        self.assertEqual(len(row["sessions"]), 6)
        self.assertFalse(result["contract_windows"][0]["requires_acquisition_or_review"])

    def test_mismatch_missing_and_incomplete_remain_distinct(self):
        prior, _ = prior_nominal_full_sessions("2020-01-09")
        rows = [coverage_row(day) for day in prior[:-1]]
        rows[0] = coverage_row(prior[0], "ESZ2019")
        rows[1] = coverage_row(prior[1], complete=False)
        result = build_contract_windows([candidate("2020-01-09")], {"sessions": rows})
        statuses = [row["retained_status"] for row in result["candidate_requirements"][0]["sessions"]]
        self.assertIn("selected_delivery_mismatch", statuses)
        self.assertIn("missing_retained_session", statuses)
        self.assertIn("retained_roster_incomplete_or_uncertified", statuses)

    def test_future_coverage_is_not_assumed_from_manifest_name(self):
        result = build_contract_windows([candidate("2026-10-30", "ESZ2026")],
                                        {"sessions": [coverage_row("2026-09-18", "ESZ2026")]})
        rows = result["candidate_requirements"][0]["sessions"]
        self.assertTrue(all(row["retained_status"] == "missing_retained_session" for row in rows))
        self.assertEqual(result["contract_windows"][0]["end_utc_exclusive"], "2026-10-30T21:00:00+00:00")

    def test_one_envelope_preserves_indicator_history_across_missing_pivot_dates(self):
        inputs = [candidate("2020-01-09", identifier="first"), candidate("2020-02-14", identifier="later")]
        result = build_contract_windows(inputs, {"sessions": []})
        self.assertEqual(len(result["contract_windows"]), 1)
        window = result["contract_windows"][0]
        self.assertEqual(window["candidate_ids"], ["first", "later"])
        self.assertIn("2020-01-27", window["required_session_dates"])
        self.assertIn("2020-01-20", window["missing_or_uncertified_session_dates"])
        self.assertIn("preceding", window["feature_readiness_requirement"])

    def test_deliveries_never_merge_or_infer_short_year(self):
        inputs = [candidate("2020-01-09"), candidate("2020-04-09", "ESM2020", "two"),
                  candidate("2020-01-10", "ESH20", "short"), candidate(None, "ESH2020", "undated")]
        result = build_contract_windows(inputs, {"sessions": []})
        self.assertEqual(len(result["contract_windows"]), 2)
        self.assertEqual(result["summary"]["candidate_status_counts"]["unresolved_candidate_identity"], 2)
        with self.assertRaises(ValueError):
            build_contract_windows([inputs[0]], {"sessions": []}, prior_full_sessions=4)

    def test_price_and_source_extra_fields_cannot_change_requirements(self):
        plain = candidate("2020-01-09")
        extra = {**plain, "pivot": 12345, "close": -999, "future_return": 10, "source_text": "ignore"}
        self.assertEqual(build_contract_windows([plain], {"sessions": []}),
                         build_contract_windows([extra], {"sessions": []}))


class RetainedCoverageTests(unittest.TestCase):
    def _fixture(self, root, *, timestamps=None, raw="ESH0", include_poison=True):
        import pyarrow as pa
        import pyarrow.parquet as pq
        day = date(2020, 1, 9)
        timestamps = sorted(_expected_timestamp_ns(day)) if timestamps is None else timestamps
        minute_path = Path("data/curated/continuous/1m/product=ES/roll=volume_lead_v1/variant=unadjusted/year=2020/part-000.parquet")
        master_path = Path("data/curated/instruments/roll=volume_lead_v1/instrument_master.parquet")
        (root / minute_path).parent.mkdir(parents=True)
        (root / master_path).parent.mkdir(parents=True)
        n = len(timestamps)
        table = {"ts_event": pa.array(timestamps, type=pa.timestamp("ns", tz="UTC")),
                 "session_date": [day] * n, "instrument_id": [7] * n,
                 "raw_symbol": [raw] * n, "roll_id": [4] * n}
        if include_poison:
            table.update(open=[-1.] * n, high=[-1.] * n, low=[-1.] * n, close=[-1.] * n, volume=[-1.] * n)
        pq.write_table(pa.table(table), root / minute_path)
        pq.write_table(pa.Table.from_pylist([{"product": "ES", "roll_id": 4, "instrument_id": 7,
                                            "raw_symbol": "ESH0", "maturity_year": 2020, "maturity_month": 3}]),
                       root / master_path)
        outputs = [{"path": str(p), "sha256": hashlib.sha256((root / p).read_bytes()).hexdigest()}
                   for p in [minute_path, master_path]]
        manifest = root / "manifest.json"
        manifest.write_text(json.dumps({"dataset": "volume_lead_unadjusted_v1", "adjusted": False,
                                        "output_files": outputs}))
        return hashlib.sha256(manifest.read_bytes()).hexdigest()

    def test_reads_identity_columns_only_and_resolves_decade_from_master(self):
        import pyarrow.parquet as pq
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            digest = self._fixture(root)
            original = pq.ParquetFile
            observed_columns = []

            class ObservedFile:
                def __init__(self, path):
                    self.file = original(path)

                def read(self, *, columns):
                    observed_columns.append(columns)
                    return self.file.read(columns=columns)

                def iter_batches(self, *, columns, batch_size):
                    observed_columns.append(columns)
                    yield from self.file.iter_batches(columns=columns, batch_size=batch_size)

            with patch.object(pq, "ParquetFile", ObservedFile):
                result = inspect_continuous_coverage(root, "manifest.json", digest,
                    start_date="2020-01-01", end_date="2020-02-01")
            row = result["sessions"][0]
            self.assertEqual(row["full_contracts"], ["ESH2020"])
            self.assertTrue(row["complete_nominal_roster"])
            self.assertEqual(observed_columns, [MASTER_COLUMNS, IDENTITY_COLUMNS])
            self.assertIn("OHLCV quality", " ".join(result["qualifications"]))

    def test_missing_duplicate_and_unknown_contract_are_not_complete(self):
        timestamps = sorted(_expected_timestamp_ns(date(2020, 1, 9)))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            digest = self._fixture(root, timestamps=timestamps[:-1] + [timestamps[0]])
            result = inspect_continuous_coverage(root, "manifest.json", digest,
                start_date="2020-01-01", end_date="2020-02-01")
            row = result["sessions"][0]
            self.assertFalse(row["complete_nominal_roster"])
            self.assertEqual(row["missing_expected_minutes"], 1)
            self.assertEqual(row["duplicate_minutes"], 1)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            digest = self._fixture(root, raw="ESM0")
            with self.assertRaisesRegex(ValueError, "disagrees with pinned master"):
                inspect_continuous_coverage(root, "manifest.json", digest,
                    start_date="2020-01-01", end_date="2020-02-01")

    def test_checksum_mismatch_refuses_inspection(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._fixture(root)
            with self.assertRaisesRegex(ValueError, "manifest checksum mismatch"):
                inspect_continuous_coverage(root, "manifest.json", "0" * 64,
                    start_date="2020-01-01", end_date="2020-02-01")


if __name__ == "__main__":
    unittest.main()
