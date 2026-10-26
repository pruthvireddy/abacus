"""Synthetic rejection tests for the independent Phase2 source-cell checker."""
import ast
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/"phase2_verify_publication.py"
spec=importlib.util.spec_from_file_location("phase2_independent_publication",SCRIPT)
check=importlib.util.module_from_spec(spec);spec.loader.exec_module(check)


def csv_write(path,rows):
    with path.open("w",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


class Phase2PublicationVerifierTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.stage=Path(self.tmp.name)
        (self.stage/"tables").mkdir()
        self.publication=self.stage/"publications/synthetic";self.publication.mkdir(parents=True)
        (self.publication/"tables").mkdir()
        self.original=self.stage/"tables/original.csv"
        self.copy=self.publication/"tables/copied.csv"
        self.rows=[dict(policy="other",value="99",unknown="False"),dict(policy="wanted",value="0",unknown="False"),dict(policy="wanted",value="",unknown="True")]
        csv_write(self.original,self.rows);csv_write(self.copy,self.rows[1:])
        self.record=dict(path="tables/copied.csv",sha256=check.digest(self.copy),kind="csv",original_stage_source_path="tables/original.csv",original_source_sha256=check.digest(self.original),source_row_base=0,selected_source_rows=[1,2],columns=list(self.rows[0]),selectors={"policy":"wanted"})
        self.map=dict(schema_version="study23.phase2-web-source-cells/v1",source_row_base=0,source_artifacts=[self.record],bindings=[],downloads=[])
        self.report=dict(source={"runId":"synthetic"},sections=[dict(id="table",kind="table",columns=[{"key":x} for x in self.rows[0]],rows=[dict(policy="wanted",value=0.,unknown=False),dict(policy="wanted",value=None,unknown=True)])],downloads=[])
        for i,row in enumerate(self.report["sections"][0]["rows"]):
            for key,value in row.items():
                kind="null" if value is None else "boolean" if type(value) is bool else "string" if type(value) is str else "number"
                self.map["bindings"].append(dict(section="table",row_index=i,key=key,source_artifact="tables/copied.csv",source_row=i,source_column=key,value_type=kind,original_stage_source_path="tables/original.csv",original_source_row=i+1,original_source_column=key))

    def projection(self):return check.Projection(self.stage,self.publication,self.map)

    def test_original_copied_display_zero_false_null_and_selected_rows(self):
        projection=self.projection()
        self.assertEqual(projection.source_cells,6)
        self.assertEqual(check.display_cells(self.report,self.map,projection),6)
        self.assertEqual(self.original.read_bytes(),(self.stage/"tables/original.csv").read_bytes())

    def test_copy_wrong_original_row_or_hidden_selector_omission_rejected(self):
        self.record["selected_source_rows"]=[0,2]
        with self.assertRaisesRegex(ValueError,"selection"):self.projection()
        self.record["selected_source_rows"]=[1]
        with self.assertRaisesRegex(ValueError,"selection"):self.projection()

    def test_display_null_is_not_false_or_zero(self):
        projection=self.projection()
        self.report["sections"][0]["rows"][1]["value"]=False
        with self.assertRaisesRegex(ValueError,"scalar transfer"):check.display_cells(self.report,self.map,projection)

    def test_unbound_cell_and_duplicate_binding_rejected(self):
        projection=self.projection()
        last=self.map["bindings"].pop()
        with self.assertRaisesRegex(ValueError,"all displayed"):check.display_cells(self.report,self.map,projection)
        self.map["bindings"].append(self.map["bindings"][0])
        with self.assertRaisesRegex(ValueError,"unique displayed"):check.display_cells(self.report,self.map,projection)

    def test_original_hash_and_binding_original_cell_cannot_be_relabelled(self):
        self.original.write_text(self.original.read_text().replace("99","98"))
        with self.assertRaisesRegex(ValueError,"byte pin"):self.projection()
        self.record["original_source_sha256"]=check.digest(self.original)
        projection=self.projection()
        self.map["bindings"][0]["original_source_row"]=0
        with self.assertRaisesRegex(ValueError,"original cell"):check.display_cells(self.report,self.map,projection)

    def test_json_pointer_duplicate_keys_and_type_preservation(self):
        data={"selected":None,"qualified":False,"count":0}
        original=self.stage/"selection.json";copy=self.publication/"selection.json"
        original.write_text(json.dumps(data));copy.write_bytes(original.read_bytes())
        self.map["source_artifacts"].append(dict(path="selection.json",kind="json",sha256=check.digest(copy),original_stage_source_path="selection.json",original_source_sha256=check.digest(original)))
        projection=self.projection()
        base=dict(source_artifact="selection.json",original_stage_source_path="selection.json")
        self.assertIsNone(projection.cell(dict(base,source_pointer="/selected",original_source_pointer="/selected",value_type="null")))
        self.assertIs(projection.cell(dict(base,source_pointer="/qualified",original_source_pointer="/qualified",value_type="boolean")),False)
        self.assertEqual(projection.cell(dict(base,source_pointer="/count",original_source_pointer="/count",value_type="number")),0)
        original.write_text('{"a":1,"a":2}')
        with self.assertRaisesRegex(ValueError,"duplicate JSON"):check.json_file(original)

    def test_download_original_rows_exact_strings_and_columns(self):
        projection=self.projection()
        (self.publication/"downloads").mkdir()
        path=self.publication/"downloads/selected.csv";csv_write(path,self.rows[1:])
        record=dict(id="selected",source_artifact="tables/copied.csv",source_sha256=self.record["sha256"],sha256=check.digest(path),columns=list(self.rows[0]),source_rows=[0,1],original_stage_source_path="tables/original.csv",original_source_sha256=self.record["original_source_sha256"],original_source_rows=[1,2])
        self.map["downloads"]=[record]
        self.report["downloads"]=[dict(id="selected",path="downloads/selected.csv",sha256=record["sha256"],columns=record["columns"],rowCount=2,source=dict(runId="synthetic",artifact="tables/copied.csv",sha256=self.record["sha256"]))]
        self.assertEqual(check.downloads(self.report,self.map,projection),6)
        record["original_source_rows"]=[0,1]
        with self.assertRaisesRegex(ValueError,"original rows"):check.downloads(self.report,self.map,projection)

    def test_paths_nonfinite_and_producer_imports_rejected(self):
        for path in ("../outside","/absolute","tables//copied.csv"):
            with self.assertRaises(ValueError):check.ordinary(self.publication,path)
        (self.publication/"linked").symlink_to(self.publication/"tables",target_is_directory=True)
        with self.assertRaisesRegex(ValueError,"symlink"):check.ordinary(self.publication,"linked/copied.csv")
        with self.assertRaisesRegex(ValueError,"finite"):check.scalar("NaN","number")
        imports=[node.module for node in ast.walk(ast.parse(SCRIPT.read_text())) if isinstance(node,ast.ImportFrom)]
        imports.extend(alias.name for node in ast.walk(ast.parse(SCRIPT.read_text())) if isinstance(node,ast.Import) for alias in node.names)
        self.assertFalse(any("engine" in name or "metrics" in name or "publish_web" in name for name in imports))


if __name__=="__main__":unittest.main()
