import copy
import csv
from pathlib import Path
import tempfile
import unittest

from abacus_sahadeva.saved_evidence import project_table


class SavedEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "saved.csv"
        self.source = "runs/selected-study/saved-run/tables/saved.csv"

    def write_csv(self, columns, rows):
        with self.path.open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(columns)
            writer.writerows(rows)

    def project(self, columns, where=None, section="selected"):
        return project_table(self.path, columns=columns, where={} if where is None else where,
                             section=section, source=self.source)

    def test_and_predicates_preserve_source_rows_column_order_and_exact_bindings(self):
        self.write_csv(["metric", "cohort", "label", "rate"], [
            ["keep", "A", "first_row", ".125"],
            ["skip", "A", "unselected", ".9"],
            ["keep", "A", "third_row", ".3"],
            ["keep", "B", "other_cohort", ".4"],
        ])
        columns = [
            {"column": {"key": "rate", "label": "Rate", "format": "percent"}, "scale": 1},
            {"column": {"key": "label", "label": "Label"}, "scale": 10},
        ]
        where = {"metric": ["keep"], "cohort": ["A"]}
        before = self.path.read_bytes(), copy.deepcopy(columns), copy.deepcopy(where)
        rows, bindings = self.project(columns, where)
        self.assertEqual(rows, [{"rate": .125, "label": "first row"}, {"rate": .3, "label": "third row"}])
        self.assertEqual(list(rows[0]), ["rate", "label"])
        self.assertEqual(bindings, [
            {"section": "selected", "output_row": 0, "column": "rate", "source": self.source,
             "data_row_1_based": 1, "source_column": "rate", "source_raw": ".125", "scale": 1, "value": .125},
            {"section": "selected", "output_row": 0, "column": "label", "source": self.source,
             "data_row_1_based": 1, "source_column": "label", "source_raw": "first_row", "scale": 10, "value": "first row"},
            {"section": "selected", "output_row": 1, "column": "rate", "source": self.source,
             "data_row_1_based": 3, "source_column": "rate", "source_raw": ".3", "scale": 1, "value": .3},
            {"section": "selected", "output_row": 1, "column": "label", "source": self.source,
             "data_row_1_based": 3, "source_column": "label", "source_raw": "third_row", "scale": 10, "value": "third row"},
        ])
        self.assertEqual((self.path.read_bytes(), columns, where), before)

    def test_empty_predicates_select_all_in_saved_order_and_each_section_restarts_output_rows(self):
        self.write_csv(["label"], [["z_last"], ["a_first"], ["middle"]])
        columns = [{"column": {"key": "label"}, "scale": 1}]
        first, bindings = self.project(columns, section="first")
        second, other = self.project(columns, section="second")
        self.assertEqual(first, [{"label": "z last"}, {"label": "a first"}, {"label": "middle"}])
        self.assertEqual(second, first)
        self.assertEqual([b["data_row_1_based"] for b in bindings], [1, 2, 3])
        self.assertEqual([b["output_row"] for b in other], [0, 1, 2])
        self.assertEqual({b["section"] for b in other}, {"second"})

    def test_predicates_match_original_strings_without_conversion(self):
        self.write_csv(["code", "label"], [["004", "saved_first"], ["4", "saved_second"], ["True", "saved_third"]])
        columns = [{"column": {"key": "label"}, "scale": 1}]
        rows, bindings = self.project(columns, {"code": ["004", "True"]})
        self.assertEqual(rows, [{"label": "saved first"}, {"label": "saved third"}])
        self.assertEqual([b["data_row_1_based"] for b in bindings], [1, 3])

    def test_cell_conversions_preserve_null_bool_casing_identifiers_and_explicit_scales(self):
        keys = ["blank", "flag", "lower", "upper", "metric_id", "metric_id_departure",
                "metric_id_touch", "text", "numeric_text", "amount", "rate", "unformatted"]
        self.write_csv(keys, [
            ["", "True", "true", "TRUE", "metric_one", "depart_one", "touch_one", "some_text", "004", "1.25", ".125", "2_000"],
            ["", "False", "false", "FALSE", "metric_two", "depart_two", "touch_two", "other_text", "012", "-2", ".3", "3_000"],
        ])
        columns = [{"column": {"key": key}, "scale": 1} for key in keys]
        columns[0]["column"]["format"] = "number"
        columns[9] = {"column": {"key": "amount", "format": "number", "precision": 0}, "scale": 10}
        columns[10] = {"column": {"key": "rate", "format": "percent", "precision": 1}, "scale": 1}
        columns[11]["column"]["format"] = ""
        rows, _ = self.project(columns)
        self.assertEqual(rows, [
            {"blank": None, "flag": True, "lower": "true", "upper": "TRUE", "metric_id": "metric_one",
             "metric_id_departure": "depart_one", "metric_id_touch": "touch_one", "text": "some text",
             "numeric_text": "004", "amount": 12.5, "rate": .125, "unformatted": "2 000"},
            {"blank": None, "flag": False, "lower": "false", "upper": "FALSE", "metric_id": "metric_two",
             "metric_id_departure": "depart_two", "metric_id_touch": "touch_two", "text": "other text",
             "numeric_text": "012", "amount": -20.0, "rate": .3, "unformatted": "3 000"},
        ])

    def test_exactly_100_rows_are_allowed(self):
        self.write_csv(["value"], [[str(i)] for i in range(100)])
        rows, bindings = self.project([{"column": {"key": "value", "format": "number"}, "scale": 1}])
        self.assertEqual([r["value"] for r in rows], list(range(100)))
        self.assertEqual((bindings[-1]["output_row"], bindings[-1]["data_row_1_based"]), (99, 100))

    def test_zero_and_101_rows_fail_with_section_source_and_count_without_mutation(self):
        columns = [{"column": {"key": "value"}, "scale": 1}]
        for count in [0, 101]:
            with self.subTest(count=count):
                self.write_csv(["value"], [[str(i)] for i in range(count)])
                before = self.path.read_bytes()
                with self.assertRaisesRegex(ValueError, f"Section 'selected'.*saved.csv.*got {count}"):
                    self.project(columns)
                self.assertEqual(self.path.read_bytes(), before)
        self.write_csv(["value"], [["one"]])
        with self.assertRaisesRegex(ValueError, "got 0"):
            self.project(columns, {"value": ["absent"]})

    def test_nonfinite_and_invalid_numbers_include_source_cell_context(self):
        for raw, scale in [("NaN", 1), ("Infinity", 1), ("-Infinity", 1), ("1e308", 10), ("bad-number", 1)]:
            with self.subTest(raw=raw, scale=scale):
                self.write_csv(["value"], [[raw]])
                before = self.path.read_bytes()
                columns = [{"column": {"key": "value", "format": "number"}, "scale": scale}]
                with self.assertRaisesRegex(ValueError, "Section 'selected'.*saved.csv.*data row 1.*column 'value'"):
                    self.project(columns)
                self.assertEqual(self.path.read_bytes(), before)

    def test_missing_file_and_csv_columns_remain_explicit_failures(self):
        columns = [{"column": {"key": "value"}, "scale": 1}]
        with self.assertRaises(FileNotFoundError):
            self.project(columns)
        self.write_csv(["other"], [["saved"]])
        before = self.path.read_bytes()
        with self.assertRaisesRegex(KeyError, "value"):
            self.project(columns)
        with self.assertRaisesRegex(KeyError, "missing-predicate"):
            self.project([{"column": {"key": "other"}, "scale": 1}], {"missing-predicate": ["saved"]})
        self.assertEqual(self.path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
