"""Synthetic rejection tests for the independent Phase3 source-cell checker."""
import ast
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

SCRIPT=Path(__file__).resolve().parents[1]/"phase3_verify_publication.py"
spec=importlib.util.spec_from_file_location("phase3_independent_publication",SCRIPT)
check=importlib.util.module_from_spec(spec);spec.loader.exec_module(check)


def csv_write(path,rows):
    with path.open("w",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


class Phase3PublicationVerifierTests(unittest.TestCase):
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
        self.map=dict(schema_version="study23.phase3-web-source-cells/v1",source_row_base=0,source_artifacts=[self.record],bindings=[],downloads=[])
        self.report=dict(source={"runId":"synthetic"},sections=[dict(id="table",kind="table",columns=[{"key":x} for x in self.rows[0]],rows=[dict(policy="wanted",value=0.,unknown=False),dict(policy="wanted",value=None,unknown=True)])],downloads=[])
        for i,row in enumerate(self.report["sections"][0]["rows"]):
            for key,value in row.items():
                kind="null" if value is None else "boolean" if type(value) is bool else "string" if type(value) is str else "number"
                self.map["bindings"].append(dict(section="table",row_index=i,key=key,source_artifact="tables/copied.csv",source_row=i,source_column=key,value_type=kind,original_stage_source_path="tables/original.csv",original_source_row=i+1,original_source_column=key))

    def projection(self):return check.Projection(self.stage,self.publication,self.map)

    def json_source(self,data,name="case.json"):
        original=self.stage/name;copy=self.publication/name
        original.write_text(json.dumps(data));copy.write_bytes(original.read_bytes())
        self.map["source_artifacts"].append(dict(path=name,kind="json",sha256=check.digest(copy),original_stage_source_path=name,original_source_sha256=check.digest(original)))
        def binding(pointer,kind):
            return dict(source_artifact=name,original_stage_source_path=name,source_pointer=pointer,original_source_pointer=pointer,value_type=kind)
        return binding

    def test_original_copied_display_zero_false_null_and_selected_rows(self):
        projection=self.projection()
        self.assertEqual(projection.source_cells,6)
        self.assertEqual(check.display_cells(self.report,self.map,projection),6)
        self.assertEqual(self.original.read_bytes(),(self.stage/"tables/original.csv").read_bytes())

    def test_sub_micro_numeric_change_is_rejected_not_hidden_by_tolerance(self):
        projection=self.projection();self.report["sections"][0]["rows"][0]["value"]=1e-10
        with self.assertRaisesRegex(ValueError,"numeric transfer"):check.display_cells(self.report,self.map,projection)

    def test_valid_cell_from_wrong_cohort_is_rejected_even_with_same_numeric_value(self):
        self.rows[2]["value"]="0";csv_write(self.original,self.rows);csv_write(self.copy,self.rows[1:])
        self.record.update(sha256=check.digest(self.copy),original_source_sha256=check.digest(self.original))
        self.report["sections"][0]["rows"][1]["value"]=0
        self.map["bindings"][4]["value_type"]="number"
        firstvalue=self.map["bindings"][1];firstvalue.update(source_row=1,original_source_row=2)
        with self.assertRaisesRegex(ValueError,"saved cohort"):check.display_cells(self.report,self.map,self.projection())

    def test_extra_unknown_cell_requires_its_own_exact_source(self):
        self.report["sections"][0]["columns"].append({"key":"extra_unknown"})
        for row in self.report["sections"][0]["rows"]:row["extra_unknown"]=0
        with self.assertRaisesRegex(ValueError,"all displayed"):check.display_cells(self.report,self.map,self.projection())

    def test_table_unit_label_and_default_are_explicitly_asserted(self):
        cols=[dict(key=k,label=k,format="number",unit="USD") if k=="value" else dict(key=k,label=k) for k in self.rows[0]]
        section=self.report["sections"][0];section["columns"]=cols
        section["rowFilters"]=[dict(key="policy",label="Exact original policy",defaultValue="wanted")]
        self.map["table_assertions"]=[dict(section="table",source_artifact="tables/copied.csv",columns=[dict(c,source_column=c["key"]) for c in cols],filters=[dict(section["rowFilters"][0],source_column="policy")])]
        projection=self.projection();self.assertEqual(check.table_assertions(self.report,self.map,projection),3)
        section["columns"][1]["unit"]="GC points"
        with self.assertRaisesRegex(ValueError,"label/unit"):check.table_assertions(self.report,self.map,projection)
        section["columns"][1]["unit"]="USD";section["rowFilters"][0]["label"]="Actual add entry"
        with self.assertRaisesRegex(ValueError,"anchor label"):check.table_assertions(self.report,self.map,projection)

    def test_numeric_narrative_tokens_and_directional_condition_reconcile_saved_cells(self):
        binding=self.json_source({"mean":-12.5,"count":12,"rate":.25})
        text="Mean -12.50 USD; rate25.0%; support12."
        self.report["sections"].append(dict(id="claim",kind="text",body=text))
        self.map["claims"]=[dict(id="net",target=dict(section="claim",field="body"),text=text,authored=False,sources=[dict(binding("/mean","number"),display=dict(style="number",precision=2)),dict(binding("/rate","number"),display=dict(style="percent",precision=1)),dict(binding("/count","number"),display=dict(style="number"))],conditions=[dict(binding("/mean","number"),operator="lt",value=0)])]
        projection=self.projection();self.assertEqual(check.claims(self.report,self.map,projection),4)
        self.map["claims"][0]["conditions"][0]["operator"]="gt"
        with self.assertRaisesRegex(ValueError,"directional"):check.claims(self.report,self.map,projection)

    def test_numeric_token_cannot_match_substring_of_larger_number(self):
        binding=self.json_source({"count":12});text="Support312."
        self.report["sections"].append(dict(id="claim",kind="text",body=text))
        self.map["claims"]=[dict(id="count",target=dict(section="claim",field="body"),text=text,sources=[dict(binding("/count","number"),display=dict(style="number"))])]
        with self.assertRaisesRegex(ValueError,"formatted source token"):check.claims(self.report,self.map,self.projection())

    def test_future_cloud_binding_cannot_be_relabelled_available_at_contact(self):
        binding=self.json_source(dict(prior="2020-01-01T09:00:00Z",future="2020-01-01T09:05:00Z",contact="2020-01-01T09:00:00Z"))
        self.map["timing_assertions"]=[dict(id="prior-cloud",left=binding("/prior","string"),operator="le",right=binding("/contact","string"))]
        projection=self.projection();self.assertEqual(check.timing_assertions(self.map,projection),1)
        self.map["timing_assertions"][0]["left"]=binding("/future","string")
        with self.assertRaisesRegex(ValueError,"causal available"):check.timing_assertions(self.map,projection)

    def test_unavailable_time_is_not_known_false_or_zero(self):
        binding=self.json_source(dict(available=None,contact="2020-01-01T09:00:00Z",unknown=True,known=False))
        assertion=dict(id="unknown-cloud",left=binding("/available","null"),operator="le",right=binding("/contact","string"))
        self.map["timing_assertions"]=[assertion];projection=self.projection()
        with self.assertRaisesRegex(ValueError,"explicitly unknown"):check.timing_assertions(self.map,projection)
        assertion.update(allow_unknown=True,unknown_binding=binding("/unknown","boolean"))
        self.assertEqual(check.timing_assertions(self.map,projection),1)
        assertion["unknown_binding"]=binding("/known","boolean")
        with self.assertRaisesRegex(ValueError,"unknown timing evidence"):check.timing_assertions(self.map,projection)

    def test_naive_timestamp_and_invalid_pointer_escape_are_refused(self):
        with self.assertRaisesRegex(ValueError,"explicit timezone"):check.timestamp("2020-01-01T09:00:00")
        with self.assertRaisesRegex(ValueError,"pointer escape"):check.pointer({"bad~2":"x"},"/bad~2")

    def test_json_numeric_string_is_not_silently_changed_to_number(self):
        binding=self.json_source({"year":"2020"})
        with self.assertRaisesRegex(ValueError,"typed JSON"):self.projection().cell(binding("/year","number"))
        self.assertEqual(self.projection().cell(binding("/year","string")),"2020")

    def test_csv_empty_cell_requires_null_type_and_large_json_integer_is_exact(self):
        self.map["bindings"][4]["value_type"]="number"
        with self.assertRaisesRegex(ValueError,"declared CSV null type"):check.display_cells(self.report,self.map,self.projection())
        binding=self.json_source({"integer":10**16+1})
        self.assertEqual(self.projection().cell(binding("/integer","number")),10**16+1)

    def test_wrong_saved_anchor_is_refused(self):
        cols=[dict(key=k,label=k) for k in self.rows[0]]
        self.report["sections"][0]["columns"]=cols
        assertion=dict(section="table",source_artifact="tables/copied.csv",columns=[dict(c,source_column=c["key"]) for c in cols],filters=[],cohort_anchor_column="policy",cohort_anchor_value="wanted")
        self.map["table_assertions"]=[assertion];projection=self.projection()
        self.assertEqual(check.table_assertions(self.report,self.map,projection),3)
        assertion["cohort_anchor_value"]="different_actual_entry"
        with self.assertRaisesRegex(ValueError,"saved cohort anchor"):check.table_assertions(self.report,self.map,projection)

    def native_generation(self):
        (self.publication/"publication.json").write_text(json.dumps(self.report))
        (self.publication/"source-map.json").write_text(json.dumps(self.map))
        (self.publication/"native-stdout.log").write_text(json.dumps(dict(id=self.publication.name,status="ready",dryRun=True))+"\n")
        (self.publication/"native-stderr.log").write_text("")
        workspace=SCRIPT.resolve().parents[2]
        result=dict(returncode=0,status="passed",stdout_path="native-stdout.log",stdout_sha256=check.digest(self.publication/"native-stdout.log"),stderr_path="native-stderr.log",stderr_sha256=check.digest(self.publication/"native-stderr.log"))
        record=dict(run_id=self.stage.name,publication_id=self.publication.name,producer_version="study23.phase3-publication/v1",report_sha256=check.digest(self.publication/"publication.json"),publication_sha256=check.digest(self.publication/"publication.json"),source_map_sha256=check.digest(self.publication/"source-map.json"),native_result=result,renderer=dict(node="v24.18.0"),command=["/synthetic/node24",str(workspace/"apps/narada/scripts/publish.mjs"),"--report",str(self.publication/"publication.json"),"--dry-run"])
        (self.publication/"publication-generation.json").write_text(json.dumps(record))
        return record

    def test_native_record_requires_exact_executed_command_and_ready_output(self):
        record=self.native_generation();self.assertEqual(check.verify_native_generation(self.stage,self.publication)["status"],"passed")
        record["command"][1]=record["command"][1].replace("publish.mjs","publish-report.mjs")
        (self.publication/"publication-generation.json").write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError,"native publisher script"):check.verify_native_generation(self.stage,self.publication)

    def test_native_record_rejects_wrong_report_hash_and_fabricated_ready_identity(self):
        record=self.native_generation();record["report_sha256"]="0"*64
        (self.publication/"publication-generation.json").write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError,"report bytes"):check.verify_native_generation(self.stage,self.publication)
        record=self.native_generation();(self.publication/"native-stdout.log").write_text(json.dumps(dict(id="wrong",status="ready",dryRun=True)))
        record["native_result"]["stdout_sha256"]=check.digest(self.publication/"native-stdout.log")
        (self.publication/"publication-generation.json").write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError,"ready report"):check.verify_native_generation(self.stage,self.publication)

    def cloud_fixture(self):
        binding=self.json_source(dict(episode_id="episode-a",contract="SYNTHETIC",policy="A20",mode="diagnostic_1plus1",role="added_leg",prior="2020-01-01T09:00:00Z",contact="2020-01-01T09:00:00Z",signal="2020-01-01T09:05:00Z",action="2020-01-01T09:10:00Z",action_price=12,frozen_level=11))
        original=self.stage/"tables/bars.csv";copy=self.publication/"tables/bars.csv"
        rows=[dict(timestamp="2020-01-01T09:00:00Z",available_at="2020-01-01T09:00:00Z",close="10",ema20="11",ema50="12",usable="True",contract="SYNTHETIC",episode_id="episode-a"),dict(timestamp="2020-01-01T09:05:00Z",available_at="2020-01-01T09:05:00Z",close="11",ema20="",ema50="",usable="False",contract="SYNTHETIC",episode_id="episode-a"),dict(timestamp="2020-01-01T09:10:00Z",available_at="2020-01-01T09:10:00Z",close="12",ema20="13",ema50="14",usable="True",contract="SYNTHETIC",episode_id="episode-a")]
        csv_write(original,rows);copy.write_bytes(original.read_bytes())
        pin=dict(path="tables/bars.csv",kind="csv",sha256=check.digest(copy),original_stage_source_path="tables/bars.csv",original_source_sha256=check.digest(original),source_row_base=0,selected_source_rows=[0,1,2],columns=list(rows[0]),selectors={})
        self.map["source_artifacts"].append(pin);projection=self.projection()
        panel=dict(id="panel-a",episode_id="episode-a",contract="SYNTHETIC",policy="A20",mode="diagnostic_1plus1",role="added_leg",case_bindings={key:binding("/"+key,"string") for key in ("episode_id","contract","policy","mode","role")},timing_assertion_ids=["prior-before-contact","signal-before-action"],plot_box=dict(left=0,right=100,top=0,bottom=100),x_domain=[check.timestamp(rows[0]["timestamp"]),check.timestamp(rows[-1]["timestamp"])],y_domain=[0,20],series=[],markers=[dict(id="actual-action",time="2020-01-01T09:10:00Z",price=12,time_binding=binding("/action","string"),price_binding=binding("/action_price","number"))],levels=[dict(id="frozen-contact",price=11,start_time="2020-01-01T09:00:00Z",end_time="2020-01-01T09:05:00Z",price_binding=binding("/frozen_level","number"),start_binding=binding("/contact","string"),end_binding=binding("/signal","string"))],annotations=[dict(id="prior-level",source_binding=binding("/frozen_level","number"),display=dict(style="number",precision=1),prefix="Prior EMA20 ")])
        svg=['<svg width="100" height="100">']
        for key,segments,coords in [("close",[[0,1,2]],["0,50 50,45 100,40"]),("ema20",[[0],[2]],["0,45","100,35"]),("ema50",[[0],[2]],["0,40","100,30"])]:
            series=dict(id=key,source_artifact="tables/bars.csv",source_sha256=pin["sha256"],source_rows=[0,1,2],original_source_rows=[0,1,2],x_column="timestamp",y_column=key,segments=segments,contract_column="contract",episode_column="episode_id")
            if key.startswith("ema"):series.update(validity_column="usable",availability_column="available_at")
            panel["series"].append(series)
            svg.extend(f'<polyline data-panel="panel-a" data-series="{key}" data-segment="{i}" points="{xy}"/>' for i,xy in enumerate(coords))
        panel["bands"]=[dict(id="cloud",upper_series="ema20",lower_series="ema50")]
        svg+=['<polygon data-panel="panel-a" data-cloud-band="cloud" data-segment="0" points="0,45 0,40"/>','<polygon data-panel="panel-a" data-cloud-band="cloud" data-segment="1" points="100,35 100,30"/>','<circle data-panel="panel-a" data-marker="actual-action" cx="100" cy="40"/>','<line data-panel="panel-a" data-level="frozen-contact" x1="0" x2="50" y1="45" y2="45"/>','<text data-panel="panel-a" data-annotation="prior-level">Prior EMA20 11.0</text>','</svg>']
        record=dict(plot_encoding=dict(kind="cloud-path-v1",canvas=[100,100],coordinate_precision=6,panels=[panel]),timing_assertions=[dict(id="prior-before-contact",left=binding("/prior","string"),operator="le",right=binding("/contact","string")),dict(id="signal-before-action",left=binding("/signal","string"),operator="le",right=binding("/action","string"))])
        return record,ET.fromstring(''.join(svg)),projection

    def test_empirical_cloud_curves_markers_frozen_level_and_own_annotations_are_exact(self):
        record,tree,projection=self.cloud_fixture();self.assertEqual(check.verify_cloud_path(record,tree,projection),9)
        tree.find("circle").set("cx","99")
        with self.assertRaisesRegex(ValueError,"cloud-marker x"):check.verify_cloud_path(record,tree,projection)

    def test_missing_cloud_span_cannot_be_connected_or_plotted_as_zero(self):
        record,tree,projection=self.cloud_fixture()
        record["plot_encoding"]["panels"][0]["series"][1]["segments"]=[[0,1,2]]
        with self.assertRaisesRegex(ValueError,"null/unknown"):check.verify_cloud_path(record,tree,projection)
        record["plot_encoding"]["panels"][0]["series"][1]["segments"]=[[0,2]]
        with self.assertRaisesRegex(ValueError,"breaks across unavailable"):check.verify_cloud_path(record,tree,projection)

    def test_unknown_source_row_cannot_be_omitted_to_bridge_a_cloud_gap(self):
        record,tree,projection=self.cloud_fixture()
        series=record["plot_encoding"]["panels"][0]["series"][1]
        series.update(source_rows=[0,2],original_source_rows=[0,2],segments=[[0,2]])
        with self.assertRaisesRegex(ValueError,"complete empirical case/window"):check.verify_cloud_path(record,tree,projection)

    def test_unregistered_empirical_panel_geometry_is_rejected(self):
        record,tree,projection=self.cloud_fixture()
        ET.SubElement(tree,"circle",{"data-panel":"unmapped","cx":"0","cy":"0"})
        with self.assertRaisesRegex(ValueError,"undeclared empirical panel"):check.verify_cloud_path(record,tree,projection)

    def test_unbound_extra_series_and_wrong_mode_are_rejected(self):
        record,tree,projection=self.cloud_fixture();ET.SubElement(tree,"polyline",{"data-panel":"panel-a","data-series":"extra","data-segment":"0","points":"0,0"})
        with self.assertRaisesRegex(ValueError,"unbound empirical line"):check.verify_cloud_path(record,tree,projection)
        tree.remove(tree[-1]);record["plot_encoding"]["panels"][0]["mode"]="financed_overlay"
        with self.assertRaisesRegex(ValueError,"empirical exact identity mode"):check.verify_cloud_path(record,tree,projection)

    def test_cloud_band_and_frozen_annotation_geometry_mutations_are_rejected(self):
        record,tree,projection=self.cloud_fixture();original=ET.tostring(tree);tree.find("polygon").set("points","0,40 0,40")
        with self.assertRaisesRegex(ValueError,"cloud-band y"):check.verify_cloud_path(record,tree,projection)
        tree=ET.fromstring(original);tree.find("text").text="Prior EMA20 12.0"
        with self.assertRaisesRegex(ValueError,"own-panel saved annotation"):check.verify_cloud_path(record,tree,projection)

    def test_copy_wrong_original_row_or_hidden_selector_omission_rejected(self):
        self.record["selected_source_rows"]=[0,2]
        with self.assertRaisesRegex(ValueError,"selection"):self.projection()
        self.record["selected_source_rows"]=[1]
        with self.assertRaisesRegex(ValueError,"selection"):self.projection()

    def test_display_null_is_not_false_or_zero(self):
        projection=self.projection()
        self.report["sections"][0]["rows"][1]["value"]=False
        with self.assertRaisesRegex(ValueError,"scalar transfer"):check.display_cells(self.report,self.map,projection)

    def test_undefined_profit_factor_cannot_become_a_known_zero_metric(self):
        binding=self.json_source(dict(profit_factor=None,losses=0))
        self.report["sections"].append(dict(id="ratio",kind="metrics",items=[dict(label="No-loss profit factor",value=0)]))
        self.map["bindings"].append(dict(binding("/profit_factor","null"),section="ratio",metric_index=0))
        with self.assertRaisesRegex(ValueError,"scalar transfer"):check.display_cells(self.report,self.map,self.projection())

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
        record=dict(id="selected",path="downloads/selected.csv",units="Counts and flags",population="Synthetic selected cohort",scope="Exact cells",column_types=dict(policy=["string"],value=["null","number"],unknown=["boolean"]),source_artifact="tables/copied.csv",source_sha256=self.record["sha256"],sha256=check.digest(path),columns=list(self.rows[0]),source_rows=[0,1],original_stage_source_path="tables/original.csv",original_source_sha256=self.record["original_source_sha256"],original_source_rows=[1,2])
        self.map["downloads"]=[record]
        self.report["downloads"]=[dict(id="selected",path="downloads/selected.csv",units="Counts and flags",population="Synthetic selected cohort",scope="Exact cells",sha256=record["sha256"],columns=record["columns"],rowCount=2,source=dict(runId="synthetic",artifact="tables/copied.csv",sha256=self.record["sha256"]))]
        self.assertEqual(check.downloads(self.report,self.map,projection),6)
        record["units"]="USD"
        with self.assertRaisesRegex(ValueError,"declared units"):check.downloads(self.report,self.map,projection)
        record["units"]="Counts and flags";record["column_types"]["value"]=["number"]
        with self.assertRaisesRegex(ValueError,"nullable"):check.downloads(self.report,self.map,projection)
        record["column_types"]["value"]=["null","number"]
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
        result=dict(schema_version="study23.phase3-publication-independent/v1",checker_sha256="a"*64,status="passed",run_id=self.stage.name,publication_id=self.publication.name,publication_sha256=check.digest(self.publication/"publication.json"),source_map_sha256=check.digest(self.publication/"source-map.json"),artifacts=[dict(path="tables/copied.csv",bytes=self.copy.stat().st_size,sha256=check.digest(self.copy))])
        (self.publication/"publication-verification.json").write_text(json.dumps(result))
        prefix="runs/23_gc_overnight_breakout_15m/"+self.stage.name+"/publications/"+self.publication.name+"/"
        manifest=dict(study_id="23_gc_overnight_breakout_15m",source_run_id=self.stage.name,publication_id=self.publication.name,
                      source_artifacts=[dict(path=prefix+"tables/copied.csv",sha256=check.digest(self.copy))],
                      outputs=[dict(path=prefix+str(p.relative_to(self.publication)),sha256=check.digest(p)) for p in self.publication.rglob("*") if p.is_file()])
        target=self.publication/"publication-manifest.json";target.write_text(json.dumps(manifest))
        checked=check.verify_final_manifest(self.stage,self.publication,dict(result,artifacts=list(result["artifacts"])))
        self.assertEqual(checked["publication_manifest_sha256"],check.digest(target))
        self.assertEqual(checked["final_manifest_output_pins"],5)
        checked_result=dict(result,artifacts=list(result["artifacts"]))
        receipt=self.publication/"publication-verification.json"
        for field,wrong,error in (("schema_version","study23.phase2-publication-independent/v1","schema/identity"),("run_id","wrong-run","schema/identity"),("checker_sha256","b"*64,"checker identity")):
            changed=dict(result);changed[field]=wrong;receipt.write_text(json.dumps(changed))
            for pin in manifest["outputs"]:
                if pin["path"].endswith("publication-verification.json"):pin["sha256"]=check.digest(receipt)
            target.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,error):check.verify_final_manifest(self.stage,self.publication,checked_result)
        receipt.write_text(json.dumps(result))
        for pin in manifest["outputs"]:
            if pin["path"].endswith("publication-verification.json"):pin["sha256"]=check.digest(receipt)
        target.write_text(json.dumps(manifest))
        (self.publication/"unrecorded.txt").write_text("new selected source")
        with self.assertRaisesRegex(ValueError,"complete final"):check.verify_final_manifest(self.stage,self.publication,dict(result))
        (self.publication/"unrecorded.txt").unlink()
        manifest["outputs"]=[p for p in manifest["outputs"] if not p["path"].endswith("publication-verification.json")]
        target.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError,"complete final"):check.verify_final_manifest(self.stage,self.publication,dict(result))

    def test_final_receipt_is_byte_identical_append_only_and_non_circular(self):
        output=self.stage/"verification/attempt";output.mkdir(parents=True)
        receipt=dict(status="passed",run_id=self.stage.name,publications=[dict(publication_manifest_sha256="a"*64)])
        check.retain_final_receipt(self.stage,output,receipt,final=False)
        self.assertFalse((self.stage/"publication-verification.json").exists())
        check.retain_final_receipt(self.stage,output,receipt,final=True)
        self.assertEqual((output/"receipt.json").read_bytes(),(self.stage/"publication-verification.json").read_bytes())
        with self.assertRaises(FileExistsError):check.retain_final_receipt(self.stage,output,receipt,final=True)
        self.assertNotIn("sha256",check.json_file(self.stage/"publication-verification.json"))


if __name__=="__main__":unittest.main()
