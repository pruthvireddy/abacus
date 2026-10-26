"""Synthetic boundary checks for the new presentation-only projection."""
import csv
import io
from pathlib import Path
import tempfile
import unittest

import session_revision as revision
import saved_projection_helper as saved


class ProjectionBoundaries(unittest.TestCase):
    def draft(self, rows):
        owner = tempfile.TemporaryDirectory()
        self.addCleanup(owner.cleanup)
        root = Path(owner.name)
        (root / "tables").mkdir()
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=["year", "session", "side", "count", "mean_delay_minutes_lower"])
        writer.writeheader()
        writer.writerows(rows)
        (root / "tables/source.csv").write_text(stream.getvalue())
        draft = saved.PublicationDraft(saved.SavedInputs(root), revision.RUN, revision.SPECS[0])
        artifact = draft.copy_table("tables/source.csv", "tables/copied.csv")
        return draft, artifact

    def selectors(self):
        return [("year", "Original year", "all"), ("session", "Original session", "all"), ("side", "Original side", "combined")]

    def test_alias_preserves_null_zero_and_original_column(self):
        draft, artifact = self.draft([{"year": "all", "session": "all", "side": "combined", "count": "0", "mean_delay_minutes_lower": ""}])
        keys = ["year", "session", "side", "count", "mean_delay_minutes_lower"]
        section = revision.table(draft, "saved", "Saved", artifact, keys, self.selectors())
        self.assertEqual(section["rows"][0]["c3"], 0)
        self.assertIsNone(section["rows"][0]["c4"])
        self.assertEqual(draft.bindings[4]["key"], "c4")
        self.assertEqual(draft.bindings[4]["source_column"], "mean_delay_minutes_lower")
        self.assertEqual(draft.bindings[4]["original_source_column"], "mean_delay_minutes_lower")
        self.assertEqual(draft.bindings[4]["original_source_row"], 0)
        self.assertEqual(section["rowFilters"][0]["key"], "c0")

    def test_saved_default_cannot_be_invented(self):
        draft, artifact = self.draft([{"year": "2018", "session": "all", "side": "combined", "count": "0", "mean_delay_minutes_lower": ""}])
        with self.assertRaisesRegex(ValueError, "default"):
            revision.table(draft, "saved", "Saved", artifact, ["year", "session", "side"], self.selectors())

    def test_table_bound_is_not_relaxed(self):
        row = {"year": "all", "session": "all", "side": "combined", "count": "0", "mean_delay_minutes_lower": ""}
        draft, artifact = self.draft([row] * 1501)
        with self.assertRaisesRegex(ValueError, "bounds"):
            revision.table(draft, "saved", "Saved", artifact, ["year", "session", "side"], self.selectors())

    def test_four_filters_are_refused(self):
        draft, artifact = self.draft([{"year": "all", "session": "all", "side": "combined", "count": "0", "mean_delay_minutes_lower": ""}])
        with self.assertRaisesRegex(ValueError, "three"):
            revision.table(draft, "saved", "Saved", artifact, ["year", "session", "side", "count"], self.selectors() + [("count", "Count", 0)])

    def test_missing_saved_column_is_refused(self):
        draft, artifact = self.draft([{"year": "all", "session": "all", "side": "combined", "count": "0", "mean_delay_minutes_lower": ""}])
        with self.assertRaisesRegex(ValueError, "selection"):
            revision.table(draft, "saved", "Saved", artifact, ["year", "session", "side", "invented"], self.selectors())


if __name__ == "__main__":
    unittest.main()
