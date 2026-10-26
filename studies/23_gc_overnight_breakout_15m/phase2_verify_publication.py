"""Independent original→copied→displayed Phase2 publication check.

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
from pathlib import Path,PurePosixPath
import shutil
import sys
import xml.etree.ElementTree as ET


def need(condition,message):
    if not condition:raise ValueError(message)


def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda:stream.read(1024*1024),b""):h.update(block)
    return h.hexdigest()


def ordinary(root,relative):
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
        need(type(actual) in (int,float) and math.isfinite(actual) and math.isclose(actual,expected,rel_tol=1e-12,abs_tol=1e-9),"numeric transfer "+context)


def pointer(value,path):
    need(isinstance(path,str) and (not path or path.startswith("/")),"explicit JSON pointer")
    if not path:return value
    for token in path[1:].split("/"):
        key=token.replace("~1","/").replace("~0","~")
        value=value[int(key)] if isinstance(value,list) else value[key]
    return value


class Projection:
    def __init__(self,stage,publication,source_map):
        self.stage=stage;self.publication=publication;self.pins={};self.tables={};self.original={}
        self.source_cells=0
        need(source_map["schema_version"]=="study23.phase2-web-source-cells/v1" and source_map["source_row_base"]==0,"source map schema/base")
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
            return scalar(copy,kind)
        need(record["kind"]=="csv","CSV binding kind")
        _,rows=self.tables[path]
        i=binding["source_row"];column=binding["source_column"]
        need(type(i) is int and 0<=i<len(rows) and column in rows[i],"copied source cell")
        need(binding["original_source_row"]==record["selected_source_rows"][i] and binding["original_source_column"]==column,"binding original cell identity")
        return scalar(rows[i][column],kind)


def display_cells(report,source_map,projection):
    expected={}
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
        observed.add(target)
    need(observed==set(expected),"all displayed cells explicitly bound")
    return len(observed)


def downloads(report,source_map,projection):
    maps={x["id"]:x for x in source_map.get("downloads",[])}
    need(len(maps)==len(source_map.get("downloads",[])),"unique download map")
    cells=0
    for selected in report.get("downloads",[]):
        mapping=maps.pop(selected["id"])
        path=ordinary(projection.publication,selected["path"])
        need(digest(path)==selected["sha256"]==mapping["sha256"],"download bytes")
        source=mapping["source_artifact"];record=projection.pins[source]
        need(selected["source"]["runId"]==report["source"]["runId"] and selected["source"]["artifact"]==source,"download run/source")
        need(selected["source"]["sha256"]==mapping["source_sha256"]==record["sha256"],"download copied source hash")
        need(mapping["original_stage_source_path"]==record["original_stage_source_path"] and mapping["original_source_sha256"]==record["original_source_sha256"],"download original source")
        columns,rows=table(path)
        need(columns==selected["columns"]==mapping["columns"] and len(rows)==selected["rowCount"],"download exact columns/count")
        indices=mapping["source_rows"]
        need(indices==sorted(set(indices)) and len(indices)==len(rows),"download ordered copied rows")
        need(mapping["original_source_rows"]==[record["selected_source_rows"][i] for i in indices],"download original rows")
        _,source_rows=projection.tables[source]
        for row,i in zip(rows,indices):
            need(row=={key:source_rows[i][key] for key in columns},"download saved strings")
            cells+=len(columns)
    need(not maps,"no undeclared download maps")
    return cells


def claims(report,source_map,projection):
    sections={x["id"]:x for x in report["sections"]}
    count=0
    for claim in source_map.get("claims",[]):
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
                count+=1
            else:
                need(source["source_artifact"] in projection.pins,"claim source pin")
                count+=1
    return count


def figures(report,source_map,projection):
    records=source_map.get("figures",[])
    ids=set();source_cells=0
    for record in records:
        figure_id=record["section"]
        need(figure_id not in ids,"unique figure source record");ids.add(figure_id)
        svg=ordinary(projection.publication,record["svg_path"])
        need(digest(svg)==record["svg_sha256"],"SVG bytes")
        tree=ET.parse(svg).getroot()
        need(digest(ordinary(projection.publication,record["path"]))==record["image_sha256"],"rendered image bytes")
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
        _,rows=projection.tables[source]
        for point in record["plotted_values"]:
            i=point["source_row"]
            need(type(i) is int and 0<=i<len(rows) and point["original_source_row"]==pin["selected_source_rows"][i],"plot original row")
            for key,value in point["values"].items():
                kind="null" if value is None else "boolean" if type(value) is bool else "string" if type(value) is str else "number"
                same(value,scalar(rows[i][key],kind),"plotted saved value")
                source_cells+=1
        verify_geometry(record,tree,projection)
    displayed={section["id"]:section["path"] for section in report["sections"] if section["kind"]=="figure"}
    need(ids==set(displayed) and all(displayed[r["section"]]==r["path"] for r in records),"all and only displayed figures mapped")
    return len(records),source_cells


def coordinate(actual,expected,context):
    need(math.isclose(float(actual),float(expected),rel_tol=0,abs_tol=.0000011),"SVG coordinate "+context)


def points(value):
    return [tuple(float(x) for x in pair.split(",")) for pair in value.split()]


def linear(value,domain,range):
    return range[0]+(float(value)-domain[0])*(range[1]-range[0])/(domain[1]-domain[0])


def verify_geometry(record,tree,projection):
    encoding=record["plot_encoding"];kind=encoding["kind"]
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


def verify_one(stage,publication):
    report=json_file(ordinary(publication,"publication.json"))
    source_map=json_file(ordinary(publication,"source-map.json"))
    need(source_map["run_id"]==report["source"]["runId"]==stage.name,"publication source run identity")
    need(source_map["publication_id"]==report["id"]==publication.name,"immutable publication identity")
    projection=Projection(stage,publication,source_map)
    result={"publication_id":report["id"],"copied_source_artifacts":len(projection.pins),"original_to_copy_cells":projection.source_cells,"displayed_cells":display_cells(report,source_map,projection),"download_cells":downloads(report,source_map,projection),"claim_source_cells":claims(report,source_map,projection)}
    result["figures"],result["figure_saved_cells"]=figures(report,source_map,projection)
    paths=["publication.json","source-map.json",*[r["path"] for r in source_map["source_artifacts"]],*[r["path"] for r in source_map["downloads"]],*[r[key] for r in source_map["figures"] for key in ("path","svg_path")]]
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
    need(prior["status"]=="passed" and prior["publication_id"]==publication.name,"passing per-publication independent receipt")
    need(prior["publication_sha256"]==result["publication_sha256"] and prior["source_map_sha256"]==result["source_map_sha256"],"per-publication verification exact source/report bytes")
    for pin in prior["artifacts"]:
        path=ordinary(publication,pin["path"])
        need(path.stat().st_size==pin["bytes"] and digest(path)==pin["sha256"],"initial verified artifact unchanged")
    result["publication_manifest_sha256"]=digest(publication/"publication-manifest.json")
    result["final_manifest_source_pins"]=len(copied)
    result["final_manifest_output_pins"]=len(files)
    for path in ("publication-manifest.json","publication-verification.json","publication-generation.json"):
        source=ordinary(publication,path)
        result["artifacts"].append(dict(path=path,bytes=source.stat().st_size,sha256=digest(source)))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage",type=Path,required=True)
    parser.add_argument("--attempt",required=True)
    parser.add_argument("--finalize-from",help="stage-relative passing initial transfer receipt; final inventory mode writes no per-report files")
    args=parser.parse_args();stage=args.stage.resolve()
    workspace=Path(__file__).resolve().parents[2]
    need(stage.is_relative_to(workspace/"work/23_gc_overnight_breakout_15m"),"new owning work stage only")
    need(args.attempt.replace("-","").replace("_","").isalnum(),"plain new attempt name")
    output=stage/"verification"/("publication-independent-"+args.attempt)
    output.mkdir(parents=True,exist_ok=False)
    snapshot=output/Path(__file__).name;shutil.copyfile(__file__,snapshot)
    tests=Path(__file__).parent/"tests/test_phase2_publication_verifier.py"
    testcopy=output/tests.name;shutil.copyfile(tests,testcopy)
    receipt={"schema_version":"study23.phase2-independent-publication/v1","attempt":args.attempt,"command":sys.argv,"checker_sha256":digest(snapshot),"source_snapshot":str(snapshot.relative_to(stage)),"source_snapshots":[dict(path=str(p.relative_to(stage)),bytes=p.stat().st_size,sha256=digest(p)) for p in (snapshot,testcopy)],"started_at":datetime.now(timezone.utc).isoformat()}
    try:
        roots=sorted((stage/"publications").iterdir())
        need(len(roots)==23 and all(x.is_dir() and not x.is_symlink() for x in roots),"exactly23 explicit report directories")
        receipt["publications"]=[verify_one(stage,path) for path in roots]
        receipt["artifacts"]=[]
        if args.finalize_from:
            initial_path=ordinary(stage,args.finalize_from);initial=json_file(initial_path)
            need(initial["status"]=="passed" and {p["publication_id"] for p in initial["publications"]}=={p.name for p in roots},"passing exact23 initial transfer prerequisite")
            for pin in initial["artifacts"]:
                source=ordinary(stage,pin["path"])
                need(source.stat().st_size==pin["bytes"] and digest(source)==pin["sha256"],"initial transferred bytes unchanged")
            receipt["initial_transfer_receipt"]=dict(path=args.finalize_from,bytes=initial_path.stat().st_size,sha256=digest(initial_path))
            receipt["artifacts"].append(receipt["initial_transfer_receipt"])
        for result,root in zip(receipt["publications"],roots):
            result["schema_version"]="study23.phase2-publication-independent/v1"
            result["checker_sha256"]=receipt["checker_sha256"]
            target=root/"publication-verification.json"
            if args.finalize_from:
                verify_final_manifest(stage,root,result)
            else:
                with target.open("x") as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write("\n")
            receipt["artifacts"].extend(dict(pin,path=str(root.relative_to(stage))+"/"+pin["path"]) for pin in result["artifacts"])
            receipt["artifacts"].append(dict(path=str(target.relative_to(stage)),bytes=target.stat().st_size,sha256=digest(target)))
        receipt.update(status="passed",finished_at=datetime.now(timezone.utc).isoformat(),scope="original saved bytes/cells → selected copied bytes/cells → display/download/plot-array identity",limits=["Statistical validity uses the independent scientific receipt.","Raster appearance and hosted rendering need separate visual/browser review."])
    except Exception as error:
        receipt.update(status="failed",error=type(error).__name__+": "+str(error),finished_at=datetime.now(timezone.utc).isoformat())
        (output/"receipt.json").write_text(json.dumps(receipt,indent=2,allow_nan=False)+"\n")
        raise
    (output/"receipt.json").write_text(json.dumps(receipt,indent=2,allow_nan=False)+"\n")
    print(json.dumps(receipt,indent=2,allow_nan=False))


if __name__=="__main__":main()
