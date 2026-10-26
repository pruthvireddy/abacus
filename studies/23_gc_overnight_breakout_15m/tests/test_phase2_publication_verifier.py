"""Synthetic rejection tests for the independent Phase2 source-cell checker."""
import ast
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

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

    def test_heatmap_sign_color_null_and_exact_rounded_cell_label(self):
        encoding=dict(kind="heatmap-v1",canvas=[1240,820],coordinate_precision=6,x_key="year",y_key="session",value_column="value",x_categories=["2024"],y_categories=["London"],origin=[210,180],cell_size=[950,530],absolute_color_scale=1,positive_color="#2f756b",negative_color="#a96245",null_color="#e4e8e2",opacity_offset=.25,opacity_multiplier=.75,label_precision=0)
        record=dict(plot_encoding=encoding,plotted_values=[dict(source_row=0,original_source_row=1,values=dict(year="2024",session="London",value=-1))])
        svg='<svg width="1240" height="820"><rect data-source-row="0" x="210" y="180" width="950" height="530" fill="#a96245" fill-opacity="1"/><text x="685" y="451">-1</text><text>2024 London</text></svg>'
        tree=ET.fromstring(svg);check.verify_geometry(record,tree,None)
        tree.find("rect").set("fill","#2f756b")
        with self.assertRaisesRegex(ValueError,"sign color"):check.verify_geometry(record,tree,None)
        tree=ET.fromstring(svg);tree.find("text").text="0"
        with self.assertRaisesRegex(ValueError,"saved label"):check.verify_geometry(record,tree,None)
        tree=ET.fromstring(svg);record["plotted_values"][0]["values"]["value"]=None
        tree.find("rect").set("fill","#e4e8e2");tree.find("text").text="Unavailable"
        check.verify_geometry(record,tree,None)

    def test_grouped_first_signal_counts_geometry_and_wrapped_policy_label(self):
        encoding=dict(kind="grouped-bars-v1",canvas=[1240,820],coordinate_precision=6,series=["opportunities","signals","fills"],label_key="policy",label_map={"p":"Friendly policy"},plot_box=dict(left=80,right=1185,top=180,bottom=620),y_domain=[0,118.],bar_width=25,group_step=1105,series_spacing=1.2,colors=dict(opportunities="#8f62bb",signals="#49899d",fills="#246b61"))
        record=dict(plot_encoding=encoding,plotted_values=[dict(source_row=0,original_source_row=1,values=dict(policy="p",opportunities=100,signals=80,fills=60))])
        parts=['<svg width="1240" height="820">']
        for index,(key,value) in enumerate((('opportunities',100),('signals',80),('fills',60))):
            height=value*440/118;x=632.5+(index-1)*30-12.5
            parts.append(f'<rect data-source-row="0" data-series="{key}" x="{x:.6f}" y="{620-height:.6f}" width="25" height="{height:.6f}" fill="{encoding["colors"][key]}"/><text>{value}</text>')
        parts.extend(['<text>Friendly</text><text>policy</text></svg>'])
        tree=ET.fromstring(''.join(parts));check.verify_geometry(record,tree,None)
        tree.findall('rect')[-1].set('height','1')
        with self.assertRaisesRegex(ValueError,"grouped height"):check.verify_geometry(record,tree,None)

    def test_final_manifest_includes_receipt_and_exact_all_selected_bytes(self):
        for name,value in (("publication.json",self.report),("source-map.json",self.map),("publication-generation.json",{"status":"prepared"})):
            (self.publication/name).write_text(json.dumps(value))
        result=dict(status="passed",publication_id=self.publication.name,publication_sha256=check.digest(self.publication/"publication.json"),source_map_sha256=check.digest(self.publication/"source-map.json"),artifacts=[dict(path="tables/copied.csv",bytes=self.copy.stat().st_size,sha256=check.digest(self.copy))])
        (self.publication/"publication-verification.json").write_text(json.dumps(result))
        prefix="runs/23_gc_overnight_breakout_15m/"+self.stage.name+"/publications/"+self.publication.name+"/"
        manifest=dict(study_id="23_gc_overnight_breakout_15m",source_run_id=self.stage.name,publication_id=self.publication.name,
                      source_artifacts=[dict(path=prefix+"tables/copied.csv",sha256=check.digest(self.copy))],
                      outputs=[dict(path=prefix+str(p.relative_to(self.publication)),sha256=check.digest(p)) for p in self.publication.rglob("*") if p.is_file()])
        target=self.publication/"publication-manifest.json";target.write_text(json.dumps(manifest))
        checked=check.verify_final_manifest(self.stage,self.publication,dict(result,artifacts=list(result["artifacts"])))
        self.assertEqual(checked["publication_manifest_sha256"],check.digest(target))
        self.assertEqual(checked["final_manifest_output_pins"],5)
        (self.publication/"unrecorded.txt").write_text("new selected source")
        with self.assertRaisesRegex(ValueError,"complete final"):check.verify_final_manifest(self.stage,self.publication,dict(result))
        (self.publication/"unrecorded.txt").unlink()
        manifest["outputs"]=[p for p in manifest["outputs"] if not p["path"].endswith("publication-verification.json")]
        target.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError,"complete final"):check.verify_final_manifest(self.stage,self.publication,dict(result))


if __name__=="__main__":unittest.main()
