"""Study 22 presentation preservation and schematic semantics, no market rerun."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

WORKSPACE = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("study22_patterns", WORKSPACE / "studies/22_es_range_xv_focused/pattern_export.py")
exporter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(exporter)


def report(analysis, setting=4):
    sections = [{"id": "definition", "kind": "text", "title": "Definition", "body": "Original methods remain exact."},
                {"id": "coverage", "kind": "metrics", "title": "Sample", "items": [{"label": "Events", "value": 12}]}]
    if analysis == "trend-length":
        ids = ["overall", "histogram", "survival", "yearly-bullish", "tails-year-bearish"]
    elif analysis.endswith("continuation"):
        ids = ["overall-all", "n1-8-bullish", "n17-20-bearish", "counts-bullish"]
    elif analysis.endswith("retracement"):
        ids = ["overall"] + [f"depth-{n}-{d}" for n in (25, 50, 75, 100) for d in ("bullish", "bearish")]
    else:
        ids = ["overall-payoff"] + [f"target-{n}r-{d}" for n in (1, 2) for d in ("bullish", "bearish", "all")]
    for sid in ids:
        sections.append({"id": sid, "kind": "table", "title": sid,
                         "columns": [{"key": "value", "label": "Saved metric"}],
                         "rows": [{"value": None}, {"value": 0}, {"value": .123456}],
                         "notes": ["Exact retained notes"], "referenceIds": ["source"]})
    return {"schemaVersion": "1.1", "id": f"original-{analysis}-{setting}", "title": "Original title",
            "summary": "Saved study statistics", "publishedAt": "2026-10-12T23:00:00Z",
            "source": {"runId": "original_run", "artifact": "report.md"}, "sections": sections,
            "references": [{"id": "source", "sha256": "f" * 64}], "notes": ["Original limitations"],
            "downloads": [{"path": "downloads/evidence.csv", "sha256": "e" * 64}]}


class Study22PatternSemanticsTests(unittest.TestCase):
    def test_every_analysis_preserves_entire_prior_content_and_has_resolved_context(self):
        for analysis in exporter.ANALYSES.values():
            with self.subTest(analysis=analysis):
                old = report(analysis)
                new = exporter.enrich(old, analysis, "2026-10-13T02:36:59Z")
                exporter.validate_patterns(new)
                self.assertEqual(exporter.strip_explanations(new), exporter.strip_explanations(old))
                self.assertNotIn("patterns", old)
                self.assertEqual(new["source"], old["source"])
                self.assertTrue(all(s.get("patternFocus") for s in new["sections"] if s["kind"] in ("table", "metrics")))

    def test_continuation_measures_only_f1_f2_and_excludes_signal_b(self):
        for pullback in (True, False):
            v = exporter.continuation_patterns(pullback)[0]["variants"][0]
            measured = [c["id"] for c in v["candles"] if c["role"] == "measured"]
            self.assertEqual(measured, ["f1", "f2"])
            self.assertIn("fails n=3", v["description"])
            n17 = next(s for s in exporter.enrich(report("pullback-continuation"), "pullback-continuation", "2026-10-13T00:00:00Z")["sections"] if s["id"] == "n17-20-bearish")
            self.assertIn("n=17–20", n17["patternFocus"])
            self.assertIn("illustrates F1/F2 only", n17["patternFocus"])

    def test_all_body_depths_match_mirrored_r_close_to_open_and_strict_favorable_close(self):
        for pullback in (True, False):
            for p in exporter.retracement_patterns(pullback)[1:]:
                v = p["variants"][0]
                depth = int(p["id"].split("-")[1])
                cs = {c["id"]: c for c in v["candles"]}
                r, f1 = cs["r"], cs["f1"]
                expected = r["close"] + (r["open"] - r["close"]) * depth / 100
                touch = next(m for m in v["marks"] if m["kind"] == "level" and ("body touch" in m["label"] or "100%" in m["label"]))
                self.assertEqual(touch["price"], expected)
                if v["id"] == "bullish":
                    self.assertEqual(f1["low"], expected)
                    self.assertGreater(f1["close"], r["close"])
                else:
                    self.assertEqual(f1["high"], expected)
                    self.assertLess(f1["close"], r["close"])

    def test_payoff_stop_targets_and_physical_colour_breakers_are_semantically_exact(self):
        for p in exporter.payoff_patterns()[1:7]:
            multiple = int(p["id"].split("-")[1][0])
            for v in p["variants"]:
                cs = {c["id"]: c for c in v["candles"]}
                marks = v["marks"]
                stop = next(m["price"] for m in marks if m["kind"] == "level" and m["label"].startswith("Stop"))
                target = next(m["price"] for m in marks if m["kind"] == "level" and "target" in m["label"])
                entry = cs["f1"]["open"]
                if v["id"] == "bullish":
                    self.assertEqual(stop, min(cs["b"]["low"], cs["r"]["low"]) - .25)
                    self.assertEqual(target, entry + multiple * (entry - stop))
                else:
                    self.assertEqual(stop, max(cs["b"]["high"], cs["r"]["high"]) + .25)
                    self.assertEqual(target, entry - multiple * (stop - entry))
                self.assertEqual(cs["c2"]["role"], "measured")
                self.assertEqual(cs["c3"]["open"], cs["c3"]["close"])
                self.assertEqual(cs["c3"]["role"], "measured")

    def test_ambiguous_f1_opens_inside_bracket_and_touches_both_targets_and_stop(self):
        for v in exporter.payoff_patterns()[-1]["variants"]:
            f1 = next(c for c in v["candles"] if c["id"] == "f1")
            stop = next(m["price"] for m in v["marks"] if m["kind"] == "level" and m["label"].startswith("Stop"))
            targets = [m["price"] for m in v["marks"] if m["kind"] == "level" and "target" in m["label"]]
            for target in targets:
                self.assertLess(min(stop, target), f1["open"])
                self.assertLess(f1["open"], max(stop, target))
                self.assertLessEqual(f1["low"], min(stop, target))
                self.assertGreaterEqual(f1["high"], max(stop, target))
            self.assertIn("order is unknown", v["description"])

    def test_trend_exact_and_censored_examples_have_distinct_measurement_spans(self):
        for v in exporter.trend_patterns()[0]["variants"]:
            exact = next(m for m in v["marks"] if "exact length = 3" in m["label"])
            censored = next(m for m in v["marks"] if "observed ≥ 2" in m["label"])
            self.assertEqual((exact["startCandle"], exact["endCandle"]), ("t1", "t3"))
            self.assertEqual((censored["startCandle"], censored["endCandle"]), ("u1", "u2"))
            self.assertIn("exact length unknown", v["description"])

    def test_invalid_geometry_and_existing_patterns_are_refused(self):
        new = exporter.enrich(report("trend-length"), "trend-length", "2026-10-13T00:00:00Z")
        with self.assertRaises(ValueError):
            exporter.enrich(new, "trend-length", "2026-10-13T00:00:00Z")
        new["patterns"][0]["variants"][0]["candles"][0]["low"] = 99
        with self.assertRaises(ValueError):
            exporter.validate_patterns(new)


class Study22PatternLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stage = self.root / "work" / exporter.STUDY_ID / "new_stage"
        self.stage.parent.mkdir(parents=True)
        self.patch = patch.object(exporter, "ROOT", self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.selected = []
        schema = self.root / "apps/narada/contracts/report.schema.json"
        schema.parent.mkdir(parents=True)
        schema.write_text('{}\n')
        for analysis_id, analysis in exporter.ANALYSES.items():
            for setting in (4, 5, 6):
                old = report(analysis, setting)
                relative = f"reports/exports/{exporter.STUDY_ID}/original_run/prior_{analysis}_{setting}"
                source = self.root / relative
                source.mkdir(parents=True)
                (source / "publication.json").write_bytes(exporter.json_bytes(old))
                (source / "source-map.json").write_text('{"saved": "unchanged"}\n')
                (source / "verification.json").write_text('{"result":"passed"}\n')
                (source / "downloads").mkdir()
                (source / "downloads/evidence.csv").write_bytes(b'value\n\n0\n0.123456789\n')
                manifest = {"study_id": exporter.STUDY_ID, "source_run_id": "original_run", "publication_id": old["id"],
                            "source_artifacts": [], "outputs": [exporter.record(p) for p in source.rglob("*") if p.is_file()]}
                (source / "manifest.json").write_bytes(exporter.json_bytes(manifest))
                pub = self.root / f"apps/narada/public/publications/{old['id']}/report.json"
                pub.parent.mkdir(parents=True)
                pub.write_bytes(exporter.json_bytes({"report": old}))
                self.selected.append({"analysis": analysis, "analysisId": analysis_id, "setting": setting,
                                      "publicationId": old["id"], "sourceRunId": "original_run", "revision": relative})
        selection_patch = patch.object(exporter, "selections", return_value=({"selection": "saved"}, {"mapping": "saved"}, self.selected))
        selection_patch.start()
        self.addCleanup(selection_patch.stop)

    def prepare(self):
        return exporter.prepare(self.stage, "2026-10-13T02:36:59Z")

    def reviews(self):
        result = {"result": "passed", "artifact_hashes": {"transfer-verification.json": exporter.digest(self.stage / "transfer-verification.json")}}
        paths = [self.stage / "independent-verification.json", self.stage / "pattern-semantics-verification.json"]
        for p in paths:
            p.write_bytes(exporter.json_bytes(result))
        return paths

    def test_prepare_copy_and_finalize_preserve_all_assets_and_refuse_overwrite(self):
        verification = self.prepare()
        self.assertEqual(len(verification["reports"]), 18)
        for item in verification["reports"]:
            folder = self.stage / item["newPublicationId"]
            prior = self.root / item["revision"]
            self.assertEqual((folder / "downloads/evidence.csv").read_bytes(), (prior / "downloads/evidence.csv").read_bytes())
            self.assertEqual(item["original_content_identity"], item["retained_content_identity"])
        with self.assertRaises(ValueError):
            self.prepare()
        results = exporter.export(self.stage, "new_revision", *self.reviews())
        self.assertEqual(len(results), 18)
        for item in results:
            target = self.root / item["revision"]
            manifest = json.loads((target / "manifest.json").read_text())
            self.assertFalse(manifest["numerical_analysis_executed"])
            self.assertEqual(manifest["verification_result"], "passed")
            self.assertEqual((target / "downloads/evidence.csv").read_bytes(), b'value\n\n0\n0.123456789\n')
        with self.assertRaises(FileExistsError):
            exporter.export(self.stage, "new_revision", *self.reviews())

    def test_modified_draft_or_unbound_independent_receipt_refuses_finalization(self):
        self.prepare()
        paths = self.reviews()
        paths[0].write_bytes(exporter.json_bytes({"result": "passed", "artifact_hashes": {}}))
        with self.assertRaises(ValueError):
            exporter.export(self.stage, "new_revision", *paths)
        paths = self.reviews()
        target = self.stage / (self.selected[0]["publicationId"] + "-patterns-r1") / "source-map.json"
        target.write_text('changed')
        with self.assertRaises(ValueError):
            exporter.export(self.stage, "new_revision", *paths)

    def test_source_symlink_and_changed_pins_refused_before_creating_stage(self):
        source = self.root / self.selected[0]["revision"] / "source-map.json"
        original = source.read_bytes()
        source.write_text('changed')
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertFalse(self.stage.exists())
        source.write_bytes(original)
        source.unlink()
        source.symlink_to("verification.json")
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertFalse(self.stage.exists())


if __name__ == "__main__":
    unittest.main()
