"""Independent original→copied→displayed Phase3 publication check.

Only saved artifacts are read. This standard-library verifier never imports the
web exporter or any numerical producer. Every publication attempt retains its
own checker snapshot and result; completed runs and reports are never changed.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime,timezone
import hashlib
import json
import math
import re
from pathlib import Path,PurePosixPath
import shutil
import sys
import xml.etree.ElementTree as ET

TEXT_COLUMNS={"policy","mode","control","year","session","side","leg","anchor","feature","bucket","contact_group","event","period","original_session","event_session","add_session","scenario","dimension","trade_id","episode_id","contract","time","timestamp","available_at","decision_at","entry_time","exit_time","annual_drawdown_path","status","event_at"}
BOOLEAN_COLUMNS={"qualifies","financing_enforced","source_candle_excluded","not_trade_return","partial_year","usable","feature_valid"}


def need(condition,message):
    if not condition:raise ValueError(message)


def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda:stream.read(1024*1024),b""):h.update(block)
    return h.hexdigest()


def ordinary(root,relative):
    need(isinstance(relative,str),"relative artifact string")
    path=PurePosixPath(relative)
    need(isinstance(relative,str) and relative and not path.is_absolute() and str(path)==relative and all(x not in (".","..","") for x in relative.split("/")) and "\\" not in relative,"unsafe relative artifact")
    current=Path(root)
    need(current.is_dir() and not current.is_symlink(),"ordinary artifact root")
    for part in path.parts:
        current=current/part
        need(not current.is_symlink(),"symlinked artifact")
    need(current.is_file(),"missing ordinary artifact "+relative)
    return current


def json_file(path):
    def unique(pairs):
        result={}
        for key,value in pairs:
            need(key not in result,"duplicate JSON key")
            result[key]=value
        return result
    return json.loads(Path(path).read_text(),object_pairs_hook=unique,parse_constant=lambda value:(_ for _ in ()).throw(ValueError("nonfinite JSON")))


def table(path):
    with Path(path).open(newline="") as stream:
        reader=csv.DictReader(stream,strict=True)
        headers=reader.fieldnames or []
        need(headers and len(set(headers))==len(headers),"unique CSV columns")
        rows=list(reader)
    need(all(None not in row and all(value is not None for value in row.values()) for row in rows),"malformed CSV row")
    return headers,rows


def scalar(raw,kind):
    if kind=="null":
        need(raw=="" or raw is None,"declared null source")
        return None
    if raw=="" or raw is None:return None
    if kind in ("string","text"):
        need(isinstance(raw,str),"text source type")
        return raw
    if kind in ("boolean","bool"):
        if type(raw) is bool:return raw
        need(raw in ("true","false","True","False"),"boolean source type")
        return raw.lower()=="true"
    need(kind in ("number","integer","int","float"),"declared scalar kind")
    need(type(raw) is not bool,"boolean cannot be numeric source")
    need(type(raw) in (str,int,float),"numeric source scalar type")
    if type(raw) is int:return raw
    value=float(raw)
    need(math.isfinite(value),"finite numeric source")
    if kind in ("integer","int"):
        need(value.is_integer(),"integral source")
        return int(value)
    return value


def same(actual,expected,context):
    if expected is None or type(expected) in (str,bool):
        need(type(actual) is type(expected) and actual==expected,"scalar transfer "+context)
    else:
        need(type(actual) in (int,float) and math.isfinite(actual) and actual==expected,"numeric transfer "+context)


def saved_column(column,raw,kind):
    if column in TEXT_COLUMNS:need(kind in ("string","text","null"),"saved cohort/text column type")
    if column in BOOLEAN_COLUMNS:need(kind in ("boolean","bool","null"),"saved boolean column type")
    return scalar(raw,kind)


def pointer(value,path):
    need(isinstance(path,str) and (not path or path.startswith("/")),"explicit JSON pointer")
    if not path:return value
    for token in path[1:].split("/"):
        need(not re.search(r"~(?![01])",token),"valid JSON pointer escape")
        key=token.replace("~1","/").replace("~0","~")
        if isinstance(value,list):
            need(key.isdigit() and (key=="0" or not key.startswith("0")) and int(key)<len(value),"saved JSON array pointer")
            value=value[int(key)]
        else:
            need(isinstance(value,dict) and key in value,"saved JSON object pointer")
            value=value[key]
    return value


class Projection:
    def __init__(self,stage,publication,source_map):
        self.stage=stage;self.publication=publication;self.pins={};self.tables={};self.original={}
        self.source_cells=0
        need(source_map["schema_version"]=="study23.phase3-web-source-cells/v1" and source_map["source_row_base"]==0,"source map schema/base")
        for record in source_map["source_artifacts"]:
            path=record["path"]
            need(path not in self.pins,"duplicate copied source")
            copy=ordinary(publication,path);original=ordinary(stage,record["original_stage_source_path"])
            need(digest(copy)==record["sha256"] and digest(original)==record["original_source_sha256"],"source byte pin "+path)
            if record["kind"]=="csv":
                headers,rows=table(copy);original_headers,original_rows=table(original)
                columns=record["columns"];indices=record["selected_source_rows"]
                need(record["source_row_base"]==0 and columns==headers and all(x in original_headers for x in columns),"copied column identity")
                need(indices==sorted(set(indices)) and all(type(i) is int and 0<=i<len(original_rows) for i in indices),"ordered exact copied rows")
                selectors=record.get("selectors",{})
                need(all(key in original_headers for key in selectors),"source selectors use saved columns")
                selected=[i for i,row in enumerate(original_rows) if all(row[key] in expected if isinstance(expected,list) else row[key]==expected for key,expected in selectors.items())]
                need(indices==selected,"copied selection is exact declared selector")
                need(len(rows)==len(indices),"copied row count")
                for copied,index in zip(rows,indices):
                    need(copied=={key:original_rows[index][key] for key in columns},"copied saved CSV strings "+path)
                    self.source_cells+=len(columns)
                self.tables[path]=(headers,rows)
                self.original[path]=(original_headers,original_rows)
            elif record["kind"] in ("json","text"):
                need(copy.read_bytes()==original.read_bytes(),"copied JSON/text exact bytes")
                if record["kind"]=="json":json_file(copy)
            else:raise ValueError("unregistered copied source kind")
            self.pins[path]=record

    def cell(self,binding):
        path=binding["source_artifact"]
        need(path in self.pins,"unbound source artifact")
        record=self.pins[path]
        need(binding["original_stage_source_path"]==record["original_stage_source_path"],"binding original artifact")
        kind=binding["value_type"]
        if "source_pointer" in binding:
            need(record["kind"]=="json" and binding["source_pointer"]==binding["original_source_pointer"],"exact original JSON pointer")
            original=pointer(json_file(ordinary(self.stage,record["original_stage_source_path"])),binding["original_source_pointer"])
            copy=pointer(json_file(ordinary(self.publication,path)),binding["source_pointer"])
            same(copy,original,"copied JSON scalar")
            allowed={type(None):{"null"},str:{"string","text"},bool:{"boolean","bool"},int:{"number","integer","int","float"},float:{"number","integer","int","float"}}
            need(type(original) in allowed and kind in allowed[type(original)],"exact typed JSON scalar")
            return scalar(copy,kind)
        need(record["kind"]=="csv","CSV binding kind")
        _,rows=self.tables[path]
        i=binding["source_row"];column=binding["source_column"]
        need(type(i) is int and 0<=i<len(rows) and column in rows[i],"copied source cell")
        need(binding["original_source_row"]==record["selected_source_rows"][i] and binding["original_source_column"]==column,"binding original cell identity")
        need((rows[i][column]=="")== (kind=="null"),"exact declared CSV null type")
        return saved_column(column,rows[i][column],kind)


def display_cells(report,source_map,projection):
    expected={}
    row_lineage={}
    for section in report["sections"]:
        if section["kind"]=="table":
            columns=[x["key"] for x in section["columns"]]
            need(len(columns)==len(set(columns)),"unique display columns")
            for i,row in enumerate(section["rows"]):
                need(set(row)==set(columns),"display cells equal declared columns")
                for key,value in row.items():expected[(section["id"],"row",i,key)]=value
            for selector in section.get("rowFilters",[]):
                need(selector["key"] in columns,"filter uses display column")
                if "defaultValue" in selector:need(any(row[selector["key"]]==selector["defaultValue"] for row in section["rows"]),"saved default filter value")
        elif section["kind"]=="metrics":
            for i,item in enumerate(section["items"]):expected[(section["id"],"metric",i)]=item["value"]
    observed=set()
    for binding in source_map["bindings"]:
        target=(binding["section"],"metric",binding["metric_index"]) if "metric_index" in binding else (binding["section"],"row",binding["row_index"],binding["key"])
        need(target in expected and target not in observed,"unique displayed cell binding")
        same(expected[target],projection.cell(binding),str(target))
        if "row_index" in binding and "source_row" in binding:
            row_target=(binding["section"],binding["row_index"])
            lineage=(binding["source_artifact"],binding["source_row"])
            need(row_lineage.setdefault(row_target,lineage)==lineage,"display row belongs to one exact saved cohort")
        observed.add(target)
    need(observed==set(expected),"all displayed cells explicitly bound")
    return len(observed)


def table_assertions(report,source_map,projection):
    sections={s["id"]:s for s in report["sections"] if s["kind"]=="table"}
    observed=set();checked=0
    for assertion in source_map.get("table_assertions",[]):
        section=assertion["section"]
        need(section in sections and section not in observed,"unique declared table semantics")
        observed.add(section);display=sections[section]
        artifact=assertion["source_artifact"]
        need(artifact in projection.tables,"table assertion exact copied CSV source")
        columns=assertion["columns"]
        need([c["key"] for c in columns]==[c["key"] for c in display["columns"]],"table assertion ordered display columns")
        bindings=[b for b in source_map["bindings"] if b["section"]==section]
        indexed={c["key"]:c["source_column"] for c in columns}
        need(all(b.get("source_column")==indexed.get(b.get("key")) for b in bindings),"every row uses its declared saved column")
        for expected,actual in zip(columns,display["columns"]):
            need(indexed.get(expected["key"])==expected["source_column"],"table assertion full saved column identity")
            for key in ("label","format","unit","precision"):
                need(actual.get(key)==expected.get(key),"table assertion label/unit/format "+key)
            checked+=1
        filters=assertion.get("filters",[])
        need(len(filters)==len(display.get("rowFilters",[])),"table assertion complete saved filters")
        for expected,actual in zip(filters,display.get("rowFilters",[])):
            need(indexed.get(expected["key"])==expected["source_column"],"filter saved column identity")
            need(actual=={k:v for k,v in expected.items() if k!="source_column"},"filter exact anchor label/default")
        if "cohort_anchor_column" in assertion:
            _,rows=projection.tables[artifact]
            need(all(row[assertion["cohort_anchor_column"]]==assertion["cohort_anchor_value"] for row in rows),"explicit saved cohort anchor")
        need(all(b["source_artifact"]==artifact for b in source_map["bindings"] if b["section"]==section),"table asserted source identity")
    expected={b["section"] for b in source_map["bindings"] if "row_index" in b and projection.pins[b["source_artifact"]]["kind"]=="csv"}
    need(observed==expected,"all copied-CSV tables have explicit units/labels/cohort anchor assertions")
    return checked


def downloads(report,source_map,projection):
    maps={x["id"]:x for x in source_map.get("downloads",[])}
    need(len(maps)==len(source_map.get("downloads",[])),"unique download map")
    cells=0
    for selected in report.get("downloads",[]):
        mapping=maps.pop(selected["id"])
        path=ordinary(projection.publication,selected["path"])
        need(digest(path)==selected["sha256"]==mapping["sha256"],"download bytes")
        need(mapping.get("path")==selected["path"],"download exact declared path")
        for context in ("units","population","scope"):
            need(isinstance(selected.get(context),str) and selected[context]==mapping.get(context),"download declared "+context)
        source=mapping["source_artifact"];record=projection.pins[source]
        need(selected["source"]["runId"]==report["source"]["runId"] and selected["source"]["artifact"]==source,"download run/source")
        need(selected["source"]["sha256"]==mapping["source_sha256"]==record["sha256"],"download copied source hash")
        need(mapping["original_stage_source_path"]==record["original_stage_source_path"] and mapping["original_source_sha256"]==record["original_source_sha256"],"download original source")
        columns,rows=table(path)
        need(columns==selected["columns"]==mapping["columns"] and len(rows)==selected["rowCount"],"download exact columns/count")
        indices=mapping["source_rows"]
        need(indices==sorted(set(indices)) and len(indices)==len(rows),"download ordered copied rows")
        need(all(type(i) is int and 0<=i<len(projection.tables[source][1]) for i in indices),"download valid copied rows")
        need(mapping["original_source_rows"]==[record["selected_source_rows"][i] for i in indices],"download original rows")
        _,source_rows=projection.tables[source]
        types=mapping.get("column_types")
        need(isinstance(types,dict) and set(types)==set(columns),"download complete declared column types")
        for column,kinds in types.items():
            need(isinstance(kinds,list) and kinds==sorted(set(kinds)) and kinds and set(kinds)<={"null","string","boolean","number"},"download valid column type set")
            nonnull=[kind for kind in kinds if kind!="null"]
            need(len(nonnull)<=1,"download single typed nonnull column")
            observed=set()
            for i in indices:
                raw=source_rows[i][column];kind="null" if raw=="" else nonnull[0] if nonnull else "null"
                saved_column(column,raw,kind);observed.add(kind)
            need(observed==set(kinds),"download exact observed nullable type set")
        for row,i in zip(rows,indices):
            need(row=={key:source_rows[i][key] for key in columns},"download saved strings")
            cells+=len(columns)
    need(not maps,"no undeclared download maps")
    return cells


def compare_condition(condition,projection):
    left=projection.cell(condition)
    right=projection.cell(condition["other_source"]) if "other_source" in condition else condition.get("value")
    operator=condition["operator"]
    if operator=="eq":same(left,right,"claim conditional equality");return
    if operator=="ne":
        numeric=type(left) in (int,float) and type(right) in (int,float)
        need(left!=right if numeric else type(left) is not type(right) or left!=right,"claim conditional inequality");return
    need(operator in ("gt","ge","lt","le") and left is not None and right is not None,"ordered claim condition values")
    need(type(left) is not bool and type(right) is not bool,"ordered conditions are not boolean arithmetic")
    need(type(left)==type(right) or type(left) in (int,float) and type(right) in (int,float),"claim comparable types")
    valid={"gt":left>right,"ge":left>=right,"lt":left<right,"le":left<=right}[operator]
    need(valid,"claim directional condition")


def format_token(value,display):
    style=display.get("style","number")
    if value is None:
        return display.get("null_text","Unavailable")
    if style=="verbatim":
        return str(value).lower() if type(value) is bool else str(value)
    need(style in ("number","percent","dollars") and type(value) in (int,float) and math.isfinite(value),"claim numeric token style")
    precision=display.get("precision",0)
    need(type(precision) is int and 0<=precision<=8,"bounded claim token precision")
    number=value*100 if style=="percent" else value
    token=format(number,("," if display.get("grouping",False) else "")+"."+str(precision)+"f")
    if style=="percent":token+="%"
    return display.get("prefix","")+token+display.get("suffix","")


def claims(report,source_map,projection):
    sections={x["id"]:x for x in report["sections"]}
    count=0;ids=set()
    for claim in source_map.get("claims",[]):
        need(claim["id"] not in ids,"unique narrative claim");ids.add(claim["id"])
        target=claim.get("target",{})
        section=target.get("section",claim.get("section"))
        field=target.get("field","body")
        displayed=report.get(field) if section is None else sections[section].get(field)
        need(isinstance(displayed,str) and claim["text"] in displayed,"claim exact displayed text")
        need(claim.get("sources") or claim.get("authored") is True,"claim explicit sources or authored qualification")
        for source in claim.get("sources",[]):
            if "source_column" in source or "source_pointer" in source:
                value=projection.cell(source)
                if "saved_value" in source:same(source["saved_value"],value,"claim saved value")
                if "display" in source:
                    token=format_token(value,source["display"])
                    pattern=r"(?<![\d,.])"+re.escape(token)+r"(?![\d,]|\.\d)" if type(value) in (int,float) else r"(?<!\w)"+re.escape(token)+r"(?!\w)"
                    need(re.search(pattern,claim["text"]) is not None,"claim exact formatted source token")
                count+=1
            else:
                need(source["source_artifact"] in projection.pins,"claim source pin")
                count+=1
        for condition in claim.get("conditions",[]):
            compare_condition(condition,projection);count+=1
        need(claim.get("authored") is True or claim.get("conditions") or any("display" in s for s in claim.get("sources",[])),"empirical claim has checked source tokens or conditions")
    return count


def timestamp(value):
    need(isinstance(value,str),"saved timestamp string")
    try:parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError:raise ValueError("valid saved ISO timestamp") from None
    need(parsed.tzinfo is not None,"timestamp explicit timezone")
    return parsed.astimezone(timezone.utc).timestamp()


def timing_assertions(source_map,projection):
    ids=set()
    for assertion in source_map.get("timing_assertions",[]):
        need(assertion["id"] not in ids,"unique timing assertion");ids.add(assertion["id"])
        left,right=projection.cell(assertion["left"]),projection.cell(assertion["right"])
        if left is None or right is None:
            need(assertion.get("allow_unknown") is True and "unknown_binding" in assertion,"unavailable causal timing remains explicitly unknown")
            same(projection.cell(assertion["unknown_binding"]),assertion.get("unknown_value",True),"unknown timing evidence")
            continue
        ltime,rtime=timestamp(left),timestamp(right)
        operator=assertion["operator"]
        need(operator in ("lt","le","eq","ge","gt"),"declared timing relation")
        need({"lt":ltime<rtime,"le":ltime<=rtime,"eq":ltime==rtime,"ge":ltime>=rtime,"gt":ltime>rtime}[operator],"causal available/full-candle/action timing relation")
    return len(ids)


def figures(report,source_map,projection):
    records=source_map.get("figures",[])
    ids=set();source_cells=0
    for record in records:
        figure_id=record["section"]
        need(figure_id not in ids,"unique figure source record");ids.add(figure_id)
        svg=ordinary(projection.publication,record["svg_path"])
        need(digest(svg)==record["svg_sha256"],"SVG bytes")
        tree=ET.parse(svg).getroot()
        image=ordinary(projection.publication,record["path"])
        need(image.read_bytes().startswith(b"\x89PNG\r\n\x1a\n") and digest(image)==record["image_sha256"],"rendered PNG bytes")
        need(all(n.tag.split("}")[-1] not in ("script","foreignObject") and all(not key.endswith("href") or value.startswith("#") for key,value in n.attrib.items()) for n in tree.iter()),"self-contained retained SVG")
        kind=record["kind"]
        need(kind in ("illustrative","saved-values","empirical-example"),"qualified figure kind")
        if kind=="illustrative":
            need("Illustrative" in "".join(tree.itertext()) or record.get("authored") is True,"authored guide qualification")
            pin=projection.pins[record["source_artifact"]]
            need(record["source_sha256"]==pin["sha256"],"illustrative protocol pin")
            continue
        source=record["source_artifact"];pin=projection.pins[source]
        need(record["source_sha256"]==pin["sha256"],"figure copied source")
        need(record.get("plot_encoding"),"explicit plotted transformation")
        if record["plot_encoding"]["kind"]=="cloud-path-v1":
            selected=record["selection_artifact"]
            need(selected in projection.pins and projection.pins[selected]["kind"]=="json" and record["selection_sha256"]==projection.pins[selected]["sha256"],"empirical selected-case source byte pin")
            selection=json_file(ordinary(projection.publication,selected))
            need(selection["schema_version"]=="study23.phase3-balanced-examples/v1" and selection["run_id"]==projection.stage.name,"empirical selected-case source schema/run")
            panels=record["plot_encoding"]["panels"]
            need(panels and len({p["policy"] for p in panels})==1,"one declared empirical policy per balanced figure")
            expected=["/cases/"+str(i) for i,c in enumerate(selection["cases"]) if c["policy"]==panels[0]["policy"]]
            need(record["selection_case_pointers"]==expected and len(panels)==len(expected),"complete balanced saved-case figure roster")
            for panel,case_pointer in zip(panels,expected):
                case=pointer(selection,case_pointer)
                need(panel["id"]=="case-"+case["id"],"empirical exact selected case identity")
                need(all(b["source_artifact"]==selected and b["source_pointer"]==case_pointer+"/"+key for key,b in panel["case_bindings"].items()),"empirical identity pointers belong to selected case")
        _,rows=projection.tables[source]
        plotted_rows=set()
        for point in record["plotted_values"]:
            i=point["source_row"]
            need(i not in plotted_rows,"unique plotted original row");plotted_rows.add(i)
            need(type(i) is int and 0<=i<len(rows) and point["original_source_row"]==pin["selected_source_rows"][i],"plot original row")
            for key,value in point["values"].items():
                kind="null" if value is None else "boolean" if type(value) is bool else "string" if type(value) is str else "number"
                same(value,saved_column(key,rows[i][key],kind),"plotted saved value")
                source_cells+=1
        source_cells+=verify_geometry(record,tree,projection) or 0
    displayed={section["id"]:section["path"] for section in report["sections"] if section["kind"]=="figure"}
    need(ids==set(displayed) and all(displayed[r["section"]]==r["path"] for r in records),"all and only displayed figures mapped")
    return len(records),source_cells


def verify_cloud_path(record,tree,projection):
    encoding=record["plot_encoding"];nodes=list(tree.iter())
    need(encoding["coordinate_precision"]==6 and [float(tree.attrib["width"]),float(tree.attrib["height"])]==encoding["canvas"],"cloud-path canvas and precision")
    panels=encoding["panels"];panel_ids=set();cells=0
    for panel in panels:
        panel_id=panel["id"];need(panel_id not in panel_ids,"unique empirical panel");panel_ids.add(panel_id)
        need({"episode_id","contract","policy","mode"}<=set(panel.get("case_bindings",{})) and {"role","trade_role","leg"}&set(panel["case_bindings"]) and panel.get("timing_assertion_ids"),"empirical identity/mode/leg and causal timing provenance")
        for field,binding in panel["case_bindings"].items():
            same(panel[field],projection.cell(binding),"empirical exact identity "+field)
        timing_ids={a["id"] for a in record["timing_assertions"]}
        need(set(panel["timing_assertion_ids"])<=timing_ids,"empirical declared timing assertions")
        timing_assertions({"timing_assertions":record["timing_assertions"]},projection)
        box=panel["plot_box"];xd,yd=panel["x_domain"],panel["y_domain"]
        need(len(xd)==2 and len(yd)==2 and xd[0]<xd[1] and yd[0]<yd[1],"empirical finite positive domains")
        need(all(type(v) in (int,float) and math.isfinite(v) for v in [*xd,*yd,*box.values()]),"empirical finite coordinate domain")
        relevant=[n for n in nodes if n.attrib.get("data-panel")==panel_id]
        expected_nodes=set();series_ids=set();series_nodes={};series_segments={}
        for series in panel["series"]:
            id=series["id"];need(id not in series_ids,"unique empirical series");series_ids.add(id)
            artifact=series["source_artifact"];pin=projection.pins[artifact]
            need(pin["kind"]=="csv" and series["source_sha256"]==pin["sha256"],"empirical exact saved series source")
            _,rows=projection.tables[artifact];indices=series["source_rows"]
            need(indices and indices==sorted(set(indices)) and all(type(i) is int and 0<=i<len(rows) for i in indices),"empirical ordered selected rows")
            need(series["original_source_rows"]==[pin["selected_source_rows"][i] for i in indices],"empirical original source rows")
            xkey,ykey=series["x_column"],series["y_column"]
            need(xkey in pin["columns"] and ykey in pin["columns"],"empirical saved time/value columns")
            selectors=series.get("row_selectors",{})
            need(all(key in pin["columns"] for key in selectors),"empirical selectors use saved columns")
            identities={series[key]:panel[field] for key,field in (("contract_column","contract"),("episode_column","episode_id")) if key in series}
            eligible=[i for i,row in enumerate(rows) if all(row[key] in value if isinstance(value,list) else row[key]==value for key,value in selectors.items()) and all(row[key]==value for key,value in identities.items()) and xd[0]<=timestamp(row[xkey])<=xd[1]]
            need(indices==eligible,"complete empirical case/window row selection preserves unknown spans")
            if "contract_column" in series:
                need(all(rows[i][series["contract_column"]]==panel["contract"] for i in indices),"empirical same-contract trace")
            if "episode_column" in series:
                need(all(rows[i][series["episode_column"]]==panel["episode_id"] for i in indices),"empirical same-episode trace")
            validity=[series["validity_column"]] if "validity_column" in series else []
            validity+=series.get("validity_columns",[])
            need(len(set(validity))==len(validity) and all(key in pin["columns"] for key in validity),"empirical explicit saved availability predicates")
            if ykey in {"ema20","ema50"} and "feature_valid" in projection.original[artifact][0]:need({"usable","feature_valid"}<=set(validity),"unavailable computed cloud features remain gated")
            drawable=[]
            for i in indices:
                row=rows[i];value=scalar(row[ykey],"number")
                usable=all(scalar(row[key],"boolean") is True for key in validity)
                if value is not None and usable:
                    when=timestamp(row[xkey]);need(xd[0]<=when<=xd[1] and yd[0]<=value<=yd[1],"empirical coordinates contain saved value")
                    if "availability_column" in series:need(timestamp(row[series["availability_column"]])<=when,"cloud value not drawn before availability")
                    drawable.append(i)
                cells+=1
            segments=series["segments"]
            need([i for segment in segments for i in segment]==drawable,"empirical null/unknown points never plotted as zero")
            positions={i:j for j,i in enumerate(indices)}
            for segment in segments:
                need(segment and all(positions[b]==positions[a]+1 for a,b in zip(segment,segment[1:])),"empirical series breaks across unavailable spans")
            actual=[n for n in relevant if n.tag.endswith("polyline") and n.attrib.get("data-series")==id]
            indexed={int(n.attrib["data-segment"]):n for n in actual}
            need(len(indexed)==len(actual)==len(segments) and set(indexed)==set(range(len(segments))),"empirical exact saved segments")
            for segment_id,segment in enumerate(segments):
                expected_nodes.add((id,str(segment_id)))
                xy=points(indexed[segment_id].attrib["points"])
                need(len(xy)==len(segment),"empirical plotted point cardinality")
                for (x,y),i in zip(xy,segment):
                    coordinate(x,linear(timestamp(rows[i][xkey]),xd,[box["left"],box["right"]]),"cloud-series x")
                    coordinate(y,linear(float(rows[i][ykey]),yd,[box["bottom"],box["top"]]),"cloud-series y")
            series_nodes[id]=indexed;series_segments[id]=segments
        all_lines={(n.attrib.get("data-series"),n.attrib.get("data-segment")) for n in relevant if n.tag.endswith("polyline")}
        need(all_lines==expected_nodes,"no unbound empirical line series")
        band_ids=set()
        for band in panel.get("bands",[]):
            need(band["id"] not in band_ids,"unique saved cloud band");band_ids.add(band["id"])
            upper,lower=band["upper_series"],band["lower_series"]
            need(upper in series_nodes and lower in series_nodes and series_segments[upper]==series_segments[lower],"cloud band aligned known series")
            matched=[n for n in relevant if n.tag.endswith("polygon") and n.attrib.get("data-cloud-band")==band["id"]]
            indexed={int(n.attrib["data-segment"]):n for n in matched}
            need(len(indexed)==len(matched)==len(series_segments[upper]),"cloud band preserves unknown segment breaks")
            for index in range(len(series_segments[upper])):
                expected=points(series_nodes[upper][index].attrib["points"])+list(reversed(points(series_nodes[lower][index].attrib["points"])))
                actual=points(indexed[index].attrib["points"]);need(len(actual)==len(expected),"cloud band exact saved point count")
                for (x,y),(ex,ey) in zip(actual,expected):coordinate(x,ex,"cloud-band x");coordinate(y,ey,"cloud-band y")
        need({n.attrib.get("data-cloud-band") for n in relevant if n.tag.endswith("polygon")}==band_ids,"no unbound empirical cloud polygon")
        for marker in panel.get("markers",[]):
            when,price=projection.cell(marker["time_binding"]),projection.cell(marker["price_binding"])
            same(marker["time"],when,"empirical marker saved clock");same(marker["price"],price,"empirical marker saved price")
            matched=[n for n in relevant if n.attrib.get("data-marker")==marker["id"]]
            need(len(matched)==1 and price is not None,"one bound empirical marker")
            need(xd[0]<=timestamp(when)<=xd[1] and yd[0]<=price<=yd[1],"empirical marker within observed display domain")
            coordinate(matched[0].attrib["cx"],linear(timestamp(when),xd,[box["left"],box["right"]]),"cloud-marker x")
            coordinate(matched[0].attrib["cy"],linear(price,yd,[box["bottom"],box["top"]]),"cloud-marker y")
        need({n.attrib["data-marker"] for n in relevant if "data-marker" in n.attrib}=={m["id"] for m in panel.get("markers",[])},"no unbound empirical marker")
        for level in panel.get("levels",[]):
            price,start,end=projection.cell(level["price_binding"]),projection.cell(level["start_binding"]),projection.cell(level["end_binding"])
            same(level["price"],price,"empirical frozen price level")
            same(level["start_time"],start,"empirical level start");same(level["end_time"],end,"empirical level end")
            matched=[n for n in relevant if n.attrib.get("data-level")==level["id"]]
            need(len(matched)==1 and price is not None,"one bound empirical price level")
            need(xd[0]<=timestamp(start)<=timestamp(end)<=xd[1] and yd[0]<=price<=yd[1],"empirical frozen level within display domain")
            for key,expected in dict(x1=linear(timestamp(start),xd,[box["left"],box["right"]]),x2=linear(timestamp(end),xd,[box["left"],box["right"]]),y1=linear(price,yd,[box["bottom"],box["top"]]),y2=linear(price,yd,[box["bottom"],box["top"]])).items():coordinate(matched[0].attrib[key],expected,"cloud-level "+key)
        need({n.attrib["data-level"] for n in relevant if "data-level" in n.attrib}=={l["id"] for l in panel.get("levels",[])},"no unbound empirical price level")
        for annotation in panel.get("annotations",[]):
            value=projection.cell(annotation["source_binding"]);token=format_token(value,annotation["display"])
            matched=[n for n in relevant if n.tag.endswith("text") and n.attrib.get("data-annotation")==annotation["id"]]
            need(len(matched)==1 and "".join(matched[0].itertext())==annotation.get("prefix","")+token+annotation.get("suffix",""),"exact own-panel saved annotation")
    need(all(n.attrib["data-panel"] in panel_ids for n in nodes if "data-panel" in n.attrib),"no undeclared empirical panel geometry")
    return cells


def coordinate(actual,expected,context):
    need(math.isclose(float(actual),float(expected),rel_tol=0,abs_tol=.0000011),"SVG coordinate "+context)


def points(value):
    return [tuple(float(x) for x in pair.split(",")) for pair in value.split()]


def linear(value,domain,range):
    return range[0]+(float(value)-domain[0])*(range[1]-range[0])/(domain[1]-domain[0])


def verify_geometry(record,tree,projection):
    encoding=record["plot_encoding"];kind=encoding["kind"]
    if kind=="cloud-path-v1":return verify_cloud_path(record,tree,projection)
    nodes=list(tree.iter());text="\n".join("".join(n.itertext()) for n in nodes if n.tag.endswith("text"))
    need(encoding["coordinate_precision"]==6,"explicit coordinate rounding")
    need([float(tree.attrib["width"]),float(tree.attrib["height"])]==encoding["canvas"],"SVG canvas")
    plotted=record["plotted_values"]
    if kind in ("bars-v1","line-v1"):
        column=encoding["value_column"];vals=[x["values"][column] for x in plotted]
        numeric=[v for v in vals if v is not None]
        low,high=min([0,*numeric]),max([0,*numeric])
        if low==high:low,high=-1,1
        span=high-low
        low-=span*(.1 if kind=="bars-v1" else .08);high+=span*(.15 if kind=="bars-v1" else .12)
        same(encoding["y_domain"][0],low,"plot domain low");same(encoding["y_domain"][1],high,"plot domain high")
        box=encoding["plot_box"];yrange=[box["bottom"],box["top"]]
        need(encoding["y_range"]==yrange,"plot y range")
        if kind=="bars-v1":
            step=(box["right"]-box["left"])/len(vals)
            centers=[box["left"]+step*(i+.5) for i in range(len(vals))]
            width=min(65,step*.68)
            for actual,expected in zip(encoding["x_centers"],centers):coordinate(actual,expected,"bar center")
            coordinate(encoding["bar_width"],width,"bar width")
            rects={int(n.attrib["data-source-row"]):n for n in nodes if "data-source-row" in n.attrib}
            need(set(rects)=={x["source_row"] for x in plotted if x["values"][column] is not None},"non-null plotted rectangles only")
            zero=linear(0,[low,high],yrange)
            for i,point in enumerate(plotted):
                value=point["values"][column]
                label=" / ".join(encoding.get("label_map",{}).get(str(point["values"][key]),str(point["values"][key])) for key in encoding["label_columns"])
                need("".join(label.split()) in "".join(text.split()),"saved chart category label after explicit SVG wrapping")
                if value is None:
                    need("Not available" in text,"null chart annotation");continue
                rect=rects[point["source_row"]];end=linear(value,[low,high],yrange)
                for key,expected in dict(x=centers[i]-width/2,y=min(zero,end),width=width,height=abs(end-zero)).items():coordinate(rect.attrib[key],expected,key)
                p=encoding["label_precision"]
                rendered=f"{value*100:,.{p}f}%" if encoding["label_format"]=="percent" else f"{value:,.{p}f}"
                need(rendered in text,"saved chart numeric label")
        else:
            poly=[n for n in nodes if n.attrib.get("data-series")==column]
            need(len(poly)==1 and all(v is not None for v in vals),"one saved non-null line")
            actual=points(poly[0].attrib["points"])
            need(len(actual)==len(vals),"line saved point cardinality")
            xs=[box["left"]+(box["right"]-box["left"])*i/max(1,len(vals)-1) for i in range(len(vals))]
            for i,(x,y) in enumerate(actual):coordinate(x,xs[i],"line x");coordinate(y,linear(vals[i],[low,high],yrange),"line y")
    elif kind=="heatmap-v1":
        xkey,ykey,column=encoding["x_key"],encoding["y_key"],encoding["value_column"]
        xs=list(dict.fromkeys(p["values"][xkey] for p in plotted));ys=list(dict.fromkeys(p["values"][ykey] for p in plotted))
        need(encoding["x_categories"]==xs and encoding["y_categories"]==ys,"heatmap exact ordered categories")
        need(len({(p["values"][xkey],p["values"][ykey]) for p in plotted})==len(plotted),"heatmap unique source coordinates")
        scale=max([abs(p["values"][column]) for p in plotted if p["values"][column] is not None]+[1])
        same(encoding["absolute_color_scale"],scale,"heatmap absolute color scale")
        need(encoding["origin"]==[210,180] and encoding["positive_color"]=="#2f756b" and encoding["negative_color"]=="#a96245" and encoding["null_color"]=="#e4e8e2","heatmap declared colors/origin")
        need(encoding["opacity_offset"]==.25 and encoding["opacity_multiplier"]==.75 and encoding["label_precision"]==0,"heatmap opacity and precision contract")
        width,height=950/len(xs),530/len(ys)
        coordinate(encoding["cell_size"][0],width,"heatmap width");coordinate(encoding["cell_size"][1],height,"heatmap height")
        rects={int(n.attrib["data-source-row"]):n for n in nodes if "data-source-row" in n.attrib}
        need(set(rects)=={p["source_row"] for p in plotted},"heatmap all saved cells including nulls")
        for p in plotted:
            values=p["values"];value=values[column];rect=rects[p["source_row"]]
            x,y=210+xs.index(values[xkey])*width,180+ys.index(values[ykey])*height
            for key,expected in dict(x=x,y=y,width=width,height=height).items():coordinate(rect.attrib[key],expected,"heatmap "+key)
            expectedcolor="#e4e8e2" if value is None else "#2f756b" if value>=0 else "#a96245"
            need(rect.attrib["fill"]==expectedcolor,"heatmap saved sign color")
            coordinate(rect.attrib["fill-opacity"],1 if value is None else .25+.75*abs(value)/scale,"heatmap opacity")
            label="Unavailable" if value is None else f"{value:,.0f}"
            labels=[n for n in nodes if n.tag.endswith("text") and abs(float(n.attrib.get("x",-1))-(x+width/2))<.001 and abs(float(n.attrib.get("y",-1))-(y+height/2+6))<.001]
            need(len(labels)==1 and "".join(labels[0].itertext())==label,"heatmap exact saved label at source cell")
        need(all(str(v) in text for v in (*xs,*ys)),"heatmap category labels")
    elif kind=="grouped-bars-v1":
        series=encoding["series"];need(series==["opportunities","signals","fills"],"grouped causal count series")
        box=encoding["plot_box"];need(box==dict(left=80,right=1185,top=180,bottom=620),"grouped declared plot box")
        maximum=max([p["values"][key] for p in plotted for key in series if p["values"][key] is not None]+[1]);scale=maximum*1.18
        need(encoding["y_domain"]==[0,scale],"grouped count scale")
        step=(box["right"]-box["left"])/len(plotted);width=min(25,step*.22)
        coordinate(encoding["group_step"],step,"group step");coordinate(encoding["bar_width"],width,"group width")
        need(encoding["series_spacing"]==1.2 and encoding["colors"]==dict(opportunities="#8f62bb",signals="#49899d",fills="#246b61"),"grouped declared spacing/colors")
        rects={(int(n.attrib["data-source-row"]),n.attrib["data-series"]):n for n in nodes if "data-source-row" in n.attrib}
        need(set(rects)=={(p["source_row"],key) for p in plotted for key in series if p["values"][key] is not None},"grouped exact non-null rectangles")
        for i,p in enumerate(plotted):
            center=box["left"]+(i+.5)*step
            label=encoding["label_map"][p["values"][encoding["label_key"]]]
            need("".join(label.split()) in "".join(text.split()),"grouped category annotation")
            for j,key in enumerate(series):
                value=p["values"][key]
                if value is None:continue
                require_value=value>=0 and float(value).is_integer()
                need(require_value,"grouped saved nonnegative integer count")
                rect=rects[(p["source_row"],key)];height=value*(box["bottom"]-box["top"])/scale
                for attr,expected in dict(x=center+(j-1)*width*1.2-width/2,y=box["bottom"]-height,width=width,height=height).items():coordinate(rect.attrib[attr],expected,"grouped "+attr)
                need(rect.attrib["fill"]==encoding["colors"][key],"grouped series color")
                need(f"{int(value):,}" in text,"grouped saved count label")
    elif kind=="empirical-close-v1":
        artifact=record["selection_artifact"];pin=projection.pins[artifact]
        need(record["selection_sha256"]==pin["sha256"],"empirical selection hash")
        selection=json_file(ordinary(projection.publication,artifact));_,rows=projection.tables[record["source_artifact"]]
        covered=[]
        for panel in encoding["panels"]:
            case=pointer(selection,panel["selection_pointer"]);index=panel["example_index"]
            need(panel["selection_pointer"]==f"/{index}" and panel["rule"]==case["rule"],"exact empirical selection rule")
            need(panel["example_id"]==case["policy"]+":"+case["side"]+":"+case["outcome"] and panel["contract"]==case["trade"]["contract"] and panel["trade_id"]==case["trade"]["trade_id"],"empirical identity")
            need(panel["trade_role"]==case.get("trade_role","actual_candidate"),"no-fill baseline versus candidate role")
            indices=panel["source_rows"];covered+=indices
            need(indices==[i for i,row in enumerate(rows) if row["trade_id"]==panel["trade_id"]],"exact empirical selected minute rows")
            if "observed_span_source_rows" in panel:
                need(panel["observed_span_source_rows"]==[indices[0],indices[-1]],"empirical observed span distinct from holding time")
            for annotation in panel.get("annotation_sources",[]):
                same(annotation["saved_value"],pointer(selection,annotation["source_pointer"]),"empirical exact saved annotation")
            def seconds(value):return datetime.fromisoformat(value.replace("Z","+00:00")).timestamp()
            first,last=seconds(rows[indices[0]]["timestamp"]),seconds(rows[indices[-1]]["timestamp"])
            need(panel["x_domain"]==[first,last],"empirical time domain")
            box=panel["plot_box"];xd=[first,max(first+1,last)];xr=[box["left"],box["right"]]
            numeric=[float(rows[i][key]) for i in indices for key in ("low","high")]+[case[key] for key in ("range_high","range_low","midpoint")]+[case["trade"][key] for key in ("entry_price","exit_price","initial_stop","reset_stop") if case["trade"].get(key) is not None]
            low,high=min(numeric),max(numeric);span=high-low or 1;domain=[low-span*.08,high+span*.08];yr=[box["bottom"],box["top"]]
            same(panel["y_domain"][0],domain[0],"empirical domain");same(panel["y_domain"][1],domain[1],"empirical domain")
            relevant=[n for n in nodes if n.attrib.get("data-example-index")==str(index)]
            poly=[n for n in relevant if n.tag.endswith("polyline")]
            need(len(poly)==1,"one empirical close series")
            xy=points(poly[0].attrib["points"]);need(len(xy)==len(indices),"empirical close count")
            for (x,y),i in zip(xy,indices):coordinate(x,linear(seconds(rows[i]["timestamp"]),xd,xr),"empirical x");coordinate(y,linear(float(rows[i]["close"]),domain,yr),"empirical close y")
            for level in panel["levels"]:
                value=pointer(selection,level["source_pointer"]);same(level["value"],value,"empirical range/stop source")
                isstop="start_time" in level
                line=[n for n in relevant if n.attrib.get("data-stop" if isstop else "data-level")==level["label"]]
                need(len(line)==1,"empirical range/stop line")
                x1=linear(seconds(level["start_time"]),xd,xr) if isstop else box["left"]
                x2=linear(seconds(level["end_time"]),xd,xr) if isstop else box["right"]
                for key,expected in dict(x1=x1,x2=x2,y1=linear(value,domain,yr),y2=linear(value,domain,yr)).items():coordinate(line[0].attrib[key],expected,"empirical "+key)
            for mark in panel["markers"]:
                when=pointer(selection,mark["time_pointer"]);price=pointer(selection,mark["price_pointer"])
                same(mark["time"],when,"empirical marker time");same(mark["price"],price,"empirical marker price")
                circle=[n for n in relevant if n.attrib.get("data-marker")==mark["label"]];need(len(circle)==1,"empirical marker")
                coordinate(circle[0].attrib["cx"],linear(seconds(when),xd,xr),"marker x");coordinate(circle[0].attrib["cy"],linear(price,domain,yr),"marker y")
            if "annotation_sources" in panel:
                # Source-linked annotations are checked at their own panel's
                # text positions, preventing another panel from masking them.
                top=box["top"]-90;left=box["left"]
                def panel_text(offset):
                    selectedtext=[n for n in nodes if n.tag.endswith("text") and abs(float(n.attrib.get("x",-1))-left)<.001 and abs(float(n.attrib.get("y",-1))-(top+offset))<.001]
                    need(len(selectedtext)==1,"one empirical annotation at own panel")
                    return "".join(selectedtext[0].itertext())
                need(panel_text(378)==f'H {case["range_high"]:,.1f} | M {case["midpoint"]:,.1f} | L {case["range_low"]:,.1f} — GC prices',"empirical numeric H/M/L labels")
                stop=lambda key:"Unavailable" if case["trade"].get(key) is None else f'{case["trade"][key]:,.1f}'
                need(panel_text(402)==f'Initial stop {stop("initial_stop")} | reset stop {stop("reset_stop")}',"empirical numeric stop annotations")
                need(panel_text(426)==f'Observed path {rows[indices[0]]["timestamp"][11:16]}–{rows[indices[-1]]["timestamp"][11:16]} UTC; {case["trade"]["exit_reason"]} exit',"empirical observed window annotation")
                clocklabel=lambda value:"Unavailable" if value is None else value[11:16]+" UTC"
                expected=f'Signal {clocklabel(case["policy_ledger"].get("signal_available_at"))} → actual fill {clocklabel(case["trade"]["entry_time"])}' if case["outcome"] in {"win","loss"} else f'Alternative: known no fill; shown baseline fill {clocklabel(case["trade"]["entry_time"])}'
                need(panel_text(450)==expected,"empirical actual signal/fill versus known no-fill")
                status=case["policy_ledger"].get("baseline_position_status_at_signal");loss=case["policy_ledger"].get("baseline_loss_known_at_signal")
                need(panel_text(474)==f'Comparator baseline at signal: {status or "Unavailable"}; loss known: {str(loss).lower() if loss is not None else "Unavailable"}',"empirical causal baseline status/loss-known")
        need(sorted(covered)==sorted(x["source_row"] for x in plotted),"all empirical plotted rows covered")
    else:raise ValueError("unregistered explicit plot encoding")


def verify_native_generation(stage,publication):
    generation=json_file(ordinary(publication,"publication-generation.json"))
    need(generation["run_id"]==stage.name and generation["publication_id"]==publication.name,"native generation run/publication identity")
    need(generation["producer_version"]=="study23.phase3-publication/v1","native Phase3 producer version")
    need(generation["publication_sha256"]==generation["report_sha256"]==digest(ordinary(publication,"publication.json")),"native exact report bytes")
    need(generation["source_map_sha256"]==digest(ordinary(publication,"source-map.json")),"native exact source-map bytes")
    result=generation["native_result"]
    need(result["returncode"]==0 and result["status"]=="passed","native publisher dry-run passed")
    command=generation["command"]
    workspace=Path(__file__).resolve().parents[2]
    need(len(command)==5 and Path(command[1]).resolve()==workspace/"apps/narada/scripts/publish.mjs" and command[2]=="--report" and Path(command[3]).resolve()==publication.resolve()/"publication.json" and command[4]=="--dry-run","exact native publisher script/report/dry-run command")
    paths=[]
    for name in ("stdout","stderr"):
        path=ordinary(publication,result[name+"_path"])
        need(digest(path)==result[name+"_sha256"],"native retained "+name+" byte pin")
        paths.append(result[name+"_path"])
    stdout=json_file(ordinary(publication,result["stdout_path"]))
    need(stdout==dict(id=publication.name,status="ready",dryRun=True),"native ready report/dry-run output")
    need(generation["renderer"]["node"].startswith("v24."),"native/render Node24 environment")
    return {"status":"passed","paths":["publication-generation.json",*paths],"command":command}


def verify_one(stage,publication,*,native=True):
    report=json_file(ordinary(publication,"publication.json"))
    source_map=json_file(ordinary(publication,"source-map.json"))
    need(source_map["run_id"]==report["source"]["runId"]==stage.name,"publication source run identity")
    need(source_map["publication_id"]==report["id"]==publication.name,"immutable publication identity")
    projection=Projection(stage,publication,source_map)
    result={"run_id":stage.name,"publication_id":report["id"],"copied_source_artifacts":len(projection.pins),"original_to_copy_cells":projection.source_cells,"displayed_cells":display_cells(report,source_map,projection),"table_semantic_columns":table_assertions(report,source_map,projection),"download_cells":downloads(report,source_map,projection),"claim_source_cells":claims(report,source_map,projection),"timing_assertions":timing_assertions(source_map,projection)}
    result["figures"],result["figure_saved_cells"]=figures(report,source_map,projection)
    paths=["publication.json","source-map.json",*[r["path"] for r in source_map["source_artifacts"]],*[r["path"] for r in source_map["downloads"]],*[r[key] for r in source_map["figures"] for key in ("path","svg_path")]]
    if native:
        result["native_contract"]=verify_native_generation(stage,publication)
        paths.extend(result["native_contract"]["paths"])
    result.update(status="passed",source_map_sha256=digest(publication/"source-map.json"),publication_sha256=digest(publication/"publication.json"),artifacts=[dict(path=path,bytes=ordinary(publication,path).stat().st_size,sha256=digest(ordinary(publication,path))) for path in sorted(set(paths))])
    return result


def verify_final_manifest(stage,publication,result):
    """Reconcile final inventories after per-report verification was retained.

    The receipt is an output of the manifest, so this check runs after the
    initial source-cell check and manifest finalization. It never modifies the
    per-report receipt or the immutable selected report bytes.
    """
    mapping=json_file(ordinary(publication,"source-map.json"))
    manifest=json_file(ordinary(publication,"publication-manifest.json"))
    need(manifest["publication_id"]==publication.name and manifest["source_run_id"]==stage.name and manifest["study_id"]=="23_gc_overnight_breakout_15m","final manifest identity")
    prefix="runs/23_gc_overnight_breakout_15m/"+stage.name+"/publications/"+publication.name+"/"
    sets={}
    for group in ("source_artifacts","outputs"):
        indexed={}
        for pin in manifest[group]:
            need(pin["path"].startswith(prefix),"final manifest future publication locator")
            relative=pin["path"][len(prefix):]
            need(relative not in indexed,"unique final manifest inventory")
            indexed[relative]=pin["sha256"]
            need(digest(ordinary(publication,relative))==pin["sha256"],"final manifest selected byte pin")
        sets[group]=indexed
    copied={r["path"]:r["sha256"] for r in mapping["source_artifacts"]}
    need(sets["source_artifacts"]==copied,"all and only selected copied sources in final manifest")
    files={str(p.relative_to(publication)) for p in publication.rglob("*") if p.is_file() and p.name!="publication-manifest.json"}
    need(set(sets["outputs"])==files,"complete final publication output inventory")
    need({"publication.json","source-map.json","publication-verification.json"}<=files,"final manifest contains independent verification output")
    prior=json_file(ordinary(publication,"publication-verification.json"))
    need(prior["schema_version"]=="study23.phase3-publication-independent/v1" and prior["status"]=="passed" and prior["run_id"]==stage.name and prior["publication_id"]==publication.name,"passing exact per-publication independent receipt schema/identity")
    need(prior["checker_sha256"]==result["checker_sha256"],"per-publication exact checker identity")
    need(prior["publication_sha256"]==result["publication_sha256"] and prior["source_map_sha256"]==result["source_map_sha256"],"per-publication verification exact source/report bytes")
    need(len(prior["artifacts"])==len({pin["path"] for pin in prior["artifacts"]}) and prior["artifacts"]==result["artifacts"],"complete exact initial publication artifact pins")
    for pin in prior["artifacts"]:
        path=ordinary(publication,pin["path"])
        need(path.stat().st_size==pin["bytes"] and digest(path)==pin["sha256"],"initial verified artifact unchanged")
    result["publication_manifest_sha256"]=digest(publication/"publication-manifest.json")
    result["final_manifest_source_pins"]=len(copied)
    result["final_manifest_output_pins"]=len(files)
    for path in ("publication-manifest.json","publication-verification.json"):
        source=ordinary(publication,path)
        if not any(pin["path"]==path for pin in result["artifacts"]):result["artifacts"].append(dict(path=path,bytes=source.stat().st_size,sha256=digest(source)))
    return result


def retain_final_receipt(stage,output,receipt,*,final):
    """Retain the attempt and create the canonical final receipt only once.

    The canonical receipt comes after all per-publication manifests and pins
    those manifests. It is deliberately absent from their output inventories
    and never contains a self hash.
    """
    raw=json.dumps(receipt,indent=2,allow_nan=False)+"\n"
    (output/"receipt.json").write_text(raw)
    if final:
        with (stage/"publication-verification.json").open("x") as stream:stream.write(raw)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage",type=Path,required=True)
    parser.add_argument("--attempt",required=True)
    parser.add_argument("--expected-count",type=int,default=19,help="exact explicitly planned report count, default19")
    parser.add_argument("--finalize-from",help="stage-relative passing initial transfer receipt; final inventory mode writes no per-report files")
    args=parser.parse_args();stage=args.stage.resolve()
    workspace=Path(__file__).resolve().parents[2]
    need(stage.is_relative_to(workspace/"work/23_gc_overnight_breakout_15m"),"new owning work stage only")
    need(args.attempt.replace("-","").replace("_","").isalnum(),"plain new attempt name")
    output=stage/"verification"/("publication-independent-"+args.attempt)
    output.mkdir(parents=True,exist_ok=False)
    snapshot=output/Path(__file__).name;shutil.copyfile(__file__,snapshot)
    tests=Path(__file__).parent/"tests/test_phase3_publication_verifier.py"
    testcopy=output/tests.name;shutil.copyfile(tests,testcopy)
    receipt={"schema_version":"study23.phase3-independent-publication/v1","run_id":stage.name,"attempt":args.attempt,"command":sys.argv,"checker_sha256":digest(snapshot),"source_snapshot":str(snapshot.relative_to(stage)),"source_snapshots":[dict(path=str(p.relative_to(stage)),bytes=p.stat().st_size,sha256=digest(p)) for p in (snapshot,testcopy)],"started_at":datetime.now(timezone.utc).isoformat()}
    try:
        need(not args.finalize_from or not (stage/"publication-verification.json").exists(),"fresh canonical final receipt only")
        roots=sorted((stage/"publications").iterdir())
        need(1<=args.expected_count<=96 and len(roots)==args.expected_count and all(x.is_dir() and not x.is_symlink() for x in roots),"exact explicitly planned report directories")
        receipt["publications"]=[verify_one(stage,path) for path in roots]
        receipt["artifacts"]=[]
        if args.finalize_from:
            initial_path=ordinary(stage,args.finalize_from);initial=json_file(initial_path)
            need(initial["schema_version"]==receipt["schema_version"] and initial["run_id"]==stage.name and initial["checker_sha256"]==receipt["checker_sha256"] and initial["status"]=="passed" and {p["publication_id"] for p in initial["publications"]}=={p.name for p in roots},"passing exact initial transfer prerequisite/checker source identity")
            for pin in initial["artifacts"]:
                source=ordinary(stage,pin["path"])
                need(source.stat().st_size==pin["bytes"] and digest(source)==pin["sha256"],"initial transferred bytes unchanged")
            receipt["initial_transfer_receipt"]=dict(path=args.finalize_from,bytes=initial_path.stat().st_size,sha256=digest(initial_path))
            receipt["artifacts"].append(receipt["initial_transfer_receipt"])
        for result,root in zip(receipt["publications"],roots):
            result["schema_version"]="study23.phase3-publication-independent/v1"
            result["checker_sha256"]=receipt["checker_sha256"]
            target=root/"publication-verification.json"
            if args.finalize_from:
                verify_final_manifest(stage,root,result)
            else:
                with target.open("x") as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write("\n")
            receipt["artifacts"].extend(dict(pin,path=str(root.relative_to(stage))+"/"+pin["path"]) for pin in result["artifacts"])
            target_path=str(target.relative_to(stage))
            if not any(pin["path"]==target_path for pin in receipt["artifacts"]):receipt["artifacts"].append(dict(path=target_path,bytes=target.stat().st_size,sha256=digest(target)))
        receipt.update(status="passed",finished_at=datetime.now(timezone.utc).isoformat(),scope="original saved bytes/cells → exact cohort-row copies → display/download/narrative/causal-time/retained-vector identity; native dry-run records and final inventories",limits=["Statistical validity uses the independent scientific receipt; no research producer imported or statistics recomputed.","Native contract commands/results are independently reconciled from hash-pinned executed producer logs, not rerun by this checker.","Table units/labels/anchor declarations are checked against explicit source-map assertions; scientific definitions remain the frozen protocol and independent scientific verifier's scope.","Raster appearance and hosted rendering need separate root visual/browser review."])
    except Exception as error:
        receipt.update(status="failed",error=type(error).__name__+": "+str(error),finished_at=datetime.now(timezone.utc).isoformat())
        (output/"receipt.json").write_text(json.dumps(receipt,indent=2,allow_nan=False)+"\n")
        raise
    retain_final_receipt(stage,output,receipt,final=bool(args.finalize_from))
    print(json.dumps(dict(status=receipt["status"],publications=len(receipt["publications"]),displayed_cells=sum(p["displayed_cells"] for p in receipt["publications"]),receipt=str(output/"receipt.json"),canonical_receipt=str(stage/"publication-verification.json") if args.finalize_from else None),allow_nan=False))


if __name__=="__main__":main()
