"""Independent verifier regressions use synthetic bars and deliberate corruption."""
from copy import deepcopy
import csv
from datetime import timedelta
import importlib.util
from pathlib import Path
import tempfile
import unittest

from test_engine import engine, fixture, at

SPEC = importlib.util.spec_from_file_location("study30_independent_verifier", Path(__file__).resolve().parents[1] / "verify_saved.py")
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


def example():
    data = fixture(price_changes={"09:33": 102., "09:45": 98.},
                   ema_changes={"09:39": 101., "09:48": 99.})
    saved = engine.analyze_day(**data)
    return data, saved


def check(data, saved):
    return verifier.verify_day(saved, daily=saved["daily"][0], minutes=data["minutes"],
                               bars3=data["bars3"], bars5=data["bars5"])


class EventAndPathVerificationTests(unittest.TestCase):
    def test_independent_reconstruction_matches_synthetic_day(self):
        data, saved = example()
        result = check(data, saved)
        self.assertEqual(result["price_events"], 2)
        self.assertEqual(result["ema_events"], 2)
        self.assertEqual(result["snapshots"], 9)
        self.assertEqual(result["outcomes"], 30)

    def test_reconstruction_direct_vectors_and_equality(self):
        data = fixture(price_changes={"09:33": 100., "09:36": 102., "09:39": 100., "09:42": 98.},
                       ema_changes={"09:36": 100., "09:39": 101.})
        minutes, bars = map(verifier.series_records, (data["minutes"], data["bars3"]))
        result = verifier.reconstruct_events(data["session_date"], data["contract"], 100., minutes, bars)
        self.assertEqual([row["direction"] for row in result["price"]], [1, -1])
        self.assertEqual([row["observed_at"] for row in result["price"]], [at("09:36").astimezone(verifier.UTC).isoformat(), at("09:42").astimezone(verifier.UTC).isoformat()])
        self.assertEqual([row["direction"] for row in result["ema"]], [1])

    def test_changed_event_direction_or_omitted_event_is_rejected(self):
        data, saved = example()
        saved["price_events"][0]["direction"] = -1
        with self.assertRaisesRegex(ValueError, "direction"):
            check(data, saved)
        data, saved = example()
        saved["ema_events"].pop()
        with self.assertRaisesRegex(ValueError, "event count"):
            check(data, saved)

    def test_independent_exposure_and_crossing_rates(self):
        data, saved = example()
        self.assertEqual(saved["daily"][0]["price_observed_hours"], 6.5)
        self.assertEqual(saved["daily"][0]["ema_observed_hours"], 6.5)
        self.assertEqual(saved["daily"][0]["price_crosses_per_hour"], 2 / 6.5)
        check(data, saved)
        saved["daily"][0]["price_observed_hours"] = 7.
        with self.assertRaisesRegex(ValueError, "observed exposure"):
            check(data, saved)
        data, saved = example()
        saved["sections"][0]["ema_crosses_per_hour"] += 1.
        with self.assertRaisesRegex(ValueError, "exposure rate"):
            check(data, saved)

    def test_changed_confirmation_order_is_rejected(self):
        data, saved = example()
        saved["price_events"][0]["confirmation_at"] = at("09:45").astimezone(verifier.UTC).isoformat()
        with self.assertRaisesRegex(ValueError, "confirmation"):
            check(data, saved)

    def test_changed_mfe_and_false_for_censored_null_are_rejected(self):
        data, saved = example()
        saved["outcomes"][0]["favorable_excursion_points"] += 1
        with self.assertRaisesRegex(ValueError, "path favorable_excursion"):
            check(data, saved)
        data = fixture(price_changes={"15:45": 102.}, ema_changes={"15:45": 101.})
        saved = engine.analyze_day(**data)
        row = next(row for row in saved["outcomes"] if row["horizon"] == "30m")
        self.assertIsNone(row["favorable_reach_5"])
        row["favorable_reach_5"] = False
        with self.assertRaisesRegex(ValueError, "expected unknown/null"):
            check(data, saved)

    def test_changed_native_snapshot_and_delivery_are_rejected(self):
        data, saved = example()
        saved["snapshots"][0]["ema6"] = 123456.
        with self.assertRaisesRegex(ValueError, "snapshot native"):
            check(data, saved)
        data, saved = example()
        data["minutes"][0]["contract"] = "ESM2020"
        with self.assertRaisesRegex(ValueError, "wrong delivery"):
            check(data, saved)

    def test_changed_reference_context_and_retest_are_rejected(self):
        data, saved = example()
        saved["outcomes"][0]["cloud_order"] = "bearish"
        with self.assertRaisesRegex(ValueError, "reference-time cloud_order"):
            check(data, saved)
        data, saved = example()
        saved["ema_events"][0]["retest_found"] = True
        with self.assertRaisesRegex(ValueError, "retest"):
            check(data, saved)

    def test_crossing_snapshots_are_shared_and_link_native_information_time(self):
        data = fixture(price_changes={"09:33": 102.}, ema_changes={"09:33": 101.})
        saved = engine.analyze_day(**data)
        crossing = [row for row in saved["snapshots"] if row["snapshot_label"] == "crossing"]
        self.assertEqual(len(crossing), 1)
        self.assertEqual(saved["price_events"][0]["feature_snapshot_id"], saved["ema_events"][0]["feature_snapshot_id"])
        self.assertEqual(saved["price_events"][0]["confirmation_feature_snapshot_id"], crossing[0]["snapshot_id"])
        self.assertEqual(check(data, saved)["snapshots"], 6)

    def test_missing_or_duplicate_crossing_snapshot_is_rejected(self):
        data, saved = example()
        crossing = next(row for row in saved["snapshots"] if row["snapshot_label"] == "crossing")
        saved["snapshots"].remove(crossing)
        with self.assertRaisesRegex(ValueError, "crossing snapshot timestamp inventory"):
            check(data, saved)
        data, saved = example()
        crossing = deepcopy(next(row for row in saved["snapshots"] if row["snapshot_label"] == "crossing"))
        crossing["snapshot_id"] += ":duplicate"
        saved["snapshots"].append(crossing)
        with self.assertRaisesRegex(ValueError, "crossing snapshot timestamp inventory"):
            check(data, saved)

    def test_wrong_event_or_confirmation_snapshot_link_is_rejected(self):
        data, saved = example()
        crossing = [row for row in saved["snapshots"] if row["snapshot_label"] == "crossing"]
        saved["price_events"][0]["feature_snapshot_id"] = crossing[-1]["snapshot_id"]
        with self.assertRaisesRegex(ValueError, "event feature snapshot link time"):
            check(data, saved)
        data, saved = example()
        saved["price_events"][0]["confirmation_feature_snapshot_id"] = saved["price_events"][0]["feature_snapshot_id"]
        with self.assertRaisesRegex(ValueError, "confirmation feature snapshot link time"):
            check(data, saved)

    def test_crossing_raw_values_and_forming_native_timestamp_are_rejected(self):
        data, saved = example()
        crossing = next(row for row in saved["snapshots"] if row["snapshot_label"] == "crossing")
        crossing["ema20"] += 1.
        with self.assertRaisesRegex(ValueError, "snapshot native ema20"):
            check(data, saved)
        data, saved = example()
        crossing = next(row for row in saved["snapshots"] if row["snapshot_label"] == "crossing")
        crossing["cloud_source_at"] = (verifier.instant(crossing["snapshot_at"]) + timedelta(minutes=5)).isoformat()
        with self.assertRaisesRegex(ValueError, "asof native completion"):
            check(data, saved)

    def test_confirmation_outcome_links_confirmation_not_origin_features(self):
        data, saved = example()
        outcome = next(row for row in saved["outcomes"] if row["event_type"] == "ema_confirmation")
        event = next(row for row in saved["price_events"] if row["event_id"] == outcome["event_id"])
        self.assertNotEqual(event["feature_snapshot_id"], event["confirmation_feature_snapshot_id"])
        outcome["feature_snapshot_id"] = event["feature_snapshot_id"]
        with self.assertRaisesRegex(ValueError, "outcome reference-time feature snapshot link"):
            check(data, saved)

    def test_duplicate_horizon_or_wrong_forward_endpoint_is_rejected(self):
        data, saved = example()
        saved["outcomes"].append(deepcopy(saved["outcomes"][0]))
        with self.assertRaisesRegex(ValueError, "outcome horizon inventory"):
            check(data, saved)
        data, saved = example()
        saved["outcomes"][0]["endpoint_at"] = at("10:00").astimezone(verifier.UTC).isoformat()
        with self.assertRaisesRegex(ValueError, "horizon endpoint"):
            check(data, saved)

    def test_cross_section_confirmation_has_own_time_zero_section(self):
        data = fixture(price_changes={"10:30": 102.}, ema_changes={"10:33": 101.})
        saved = engine.analyze_day(**data)
        result = check(data, saved)
        self.assertGreater(result["outcomes"], 0)
        row = next(row for row in saved["outcomes"] if row["event_type"] == "ema_confirmation" and row["horizon"] == "section_end")
        self.assertEqual(row["section"], "new_york_am")
        row["section"] = "opening_range"
        with self.assertRaisesRegex(ValueError, "reference-time section"):
            check(data, saved)

    def test_hand_path_has_exact_post_event_minutes(self):
        observed = at("09:33").astimezone(verifier.UTC)
        rows = {
            observed - timedelta(minutes=1): {"usable": True, "high": 1000., "low": 1., "close": 100.},
            observed: {"usable": True, "high": 105., "low": 99., "close": 104.},
            observed + timedelta(minutes=1): {"usable": True, "high": 106., "low": 98., "close": 103.},
        }
        row = verifier.reconstruct_path(observed=observed, reference=100., direction=1,
            endpoint=observed + timedelta(minutes=2), day_end=at("16:00").astimezone(verifier.UTC), by_open=rows)
        self.assertEqual(row["displacement_points"], 3.)
        self.assertEqual(row["favorable_excursion_points"], 6.)
        self.assertEqual(row["adverse_excursion_points"], 2.)
        self.assertIs(row["favorable_reach_5"], True)


class SummaryVerificationTests(unittest.TestCase):
    def test_direct_recurrence_cells_and_tamper_detection(self):
        ledgers = {"daily": [{"session_date": "2020-01-02", "price_crosses": 0},
                             {"session_date": "2020-01-03", "price_crosses": 2}], "sections": [], "outcomes": []}
        row = {"metric": "price_crosses", "period_kind": "overall", "period": "all", "section": "all",
               "denominator": 2, "unknown": 0, "numerator": 2, "estimate": 1., "zero_count": 1, "zero_share": .5}
        with tempfile.TemporaryDirectory() as temporary:
            stage = Path(temporary)
            (stage / "tables").mkdir()

            def save(value):
                with (stage / "tables/daily_summary.csv").open("w", newline="") as stream:
                    writer = csv.DictWriter(stream, fieldnames=value)
                    writer.writeheader()
                    writer.writerow(value)

            save(row)
            (stage / "tables/outcome_summary.csv").write_text("horizon,direction,section,condition\n")
            self.assertEqual(verifier.verify_summaries(stage, ledgers), 6)
            row["estimate"] = 2.
            save(row)
            with self.assertRaisesRegex(ValueError, "saved recurrence estimate"):
                verifier.verify_summaries(stage, ledgers)


if __name__ == "__main__":
    unittest.main()
