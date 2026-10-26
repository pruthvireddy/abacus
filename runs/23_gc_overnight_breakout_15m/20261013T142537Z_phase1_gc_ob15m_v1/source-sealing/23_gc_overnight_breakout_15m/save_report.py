"""Render saved publication evidence locally; verify the day-disposition partition."""
import argparse
import csv
from datetime import datetime
import html
import json
from pathlib import Path
from zoneinfo import ZoneInfo

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
STUDY="23_gc_overnight_breakout_15m"


def owned_stage(stage,root=ROOT):
    stage,root=Path(stage).resolve(),Path(root).resolve()
    owner=root/"work"/STUDY
    if not stage.is_relative_to(owner) or stage==owner:
        raise ValueError("saved reports require an owning unique run stage")
    return stage


def verify_disposition(stage):
    with (stage/"tables/days.csv").open(newline="") as handle:
        days=list(csv.DictReader(handle))
    with (stage/"tables/day-disposition.csv").open(newline="") as handle:
        rows=list(csv.DictReader(handle))
    expected_years=["all",*(str(year)for year in range(2018,2027))]
    if [row["year"]for row in rows]!=expected_years:
        raise ValueError("exact complete day-disposition cohorts required")
    if len({day["broker_day"]for day in days})!=len(days):
        raise ValueError("duplicate broker day in saved roster")
    for day in days:
        if day["eligible"] not in ("True","False") or day["unknown_outcome"]not in ("True","False") or day["no_trade"]not in ("True","False"):
            raise ValueError("saved day boolean must remain explicit")
        completed,censored,accepted=(int(day[name])for name in ("completed_trades","censored_trades","accepted_breakouts"))
        if min(completed,censored,accepted)<0 or max(completed,censored,accepted)>1 or completed+censored!=accepted:
            raise ValueError("one accepted fill must have exactly one saved disposition")
        if day["eligible"]=="True":
            unknown=day["unknown_outcome"]=="True"
            no_trade=day["no_trade"]=="True"
            states=[completed==1,censored==1,no_trade,unknown and accepted==0]
            if sum(states)!=1 or (completed and unknown) or (censored and not unknown):
                raise ValueError("individual eligible day dispositions must be mutually exclusive")
        elif accepted:
            raise ValueError("quality-excluded day cannot acquire a primary fill")
    for row in rows:
        cohort=[d for d in days if row["year"]=="all" or
            str(datetime.fromisoformat(d["decision_available_at"]).astimezone(ZoneInfo("America/New_York")).year)==row["year"]]
        eligible=[d for d in cohort if d["eligible"]=="True"]
        values = {"eligible_days":len(eligible),
            "completed_fill_days":sum(int(d["completed_trades"]) for d in eligible),
            "censored_fill_days":sum(int(d["censored_trades"]) for d in eligible),
            "known_no_trade_days":sum(d["no_trade"]=="True" for d in eligible),
            "unobserved_first_fill_days":sum(d["unknown_outcome"]=="True" and int(d["accepted_breakouts"])==0 for d in eligible)}
        values["classification_total"]=sum(values[k] for k in ("completed_fill_days","censored_fill_days","known_no_trade_days","unobserved_first_fill_days"))
        values["excluded_calendar_days"]=sum(d["eligible"]=="False"for d in cohort)
        if values["classification_total"] != values["eligible_days"]:
            raise ValueError("day disposition is not a partition")
        for key,value in values.items():
            if int(row[key]) != value: raise ValueError("saved day disposition differs from saved day roster")
    outside=sum(str(datetime.fromisoformat(day["decision_available_at"]).astimezone(ZoneInfo("America/New_York")).year)not in expected_years for day in days)
    return {"result":"passed","rows":len(rows),"value_comparisons":len(rows)*7,
            "cohort_anchor":"New York calendar year of broker07:00 decision_available_at; trade performance still uses actual entry",
            "supporting_edge_roster_days_outside_2018_2026":outside,
            "scope":"Individual mutually exclusive saved-day states and complete annual/overall saved-roster partition, not a new execution model"}


def shown(value):
    return "Unavailable" if value is None else str(value)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage",type=Path,required=True)
    stage=owned_stage(parser.parse_args().stage)
    report=json.loads((stage/"publication.json").read_text())
    if report["source"]["runId"]!=stage.name:
        raise ValueError("saved report must retain its owning run identity")
    verification=verify_disposition(stage)
    for name in ("report.md","report.html","advice.md","day-disposition-verification.json"):
        if (stage/name).exists(): raise FileExistsError("saved reports require a fresh stage")
    markdown=["# "+report["title"],"",report["summary"],"", "Source run: `"+report["source"]["runId"]+"`. Executed protocol: `1.0.0`.",""]
    body=["<h1>"+html.escape(report["title"])+"</h1>","<p>"+html.escape(report["summary"])+"</p>"]
    for section in report["sections"]:
        title=section["title"]
        markdown += ["## "+title,""]
        body.append('<section id="'+section["id"]+'"><h2>'+html.escape(title)+"</h2>")
        if section["kind"]=="text":
            markdown += [section["body"],""]
            body += ["<p>"+html.escape(p)+"</p>" for p in section["body"].split("\n\n")]
        elif section["kind"]=="figure":
            markdown += [f'![{section["alt"]}]({section["path"]})',"",section.get("caption",""),""]
            body.append('<figure><img src="'+section["path"]+'" alt="'+html.escape(section["alt"],quote=True)+'"><figcaption>'+html.escape(section.get("caption",""))+"</figcaption></figure>")
        elif section["kind"]=="metrics":
            for item in section["items"]:
                text=item["label"]+": "+shown(item["value"])+(" "+item["unit"] if "unit" in item else "")
                markdown += ["- "+text]
                body.append("<p>"+html.escape(text)+"</p>")
            markdown += [""]
        elif section["kind"]=="table":
            columns=section["columns"]
            labels=[c["label"] for c in columns]
            markdown += [section.get("description",""),"", "| "+" | ".join(labels)+" |", "| "+" | ".join("---" for _ in labels)+" |"]
            body.append("<p>"+html.escape(section.get("description",""))+"</p><div class=table-scroll><table><thead><tr>"+"".join("<th>"+html.escape(v)+"</th>" for v in labels)+"</tr></thead><tbody>")
            for row in section["rows"]:
                values=[shown(row[c["key"]]) for c in columns]
                markdown.append("| "+" | ".join(v.replace("|","\\|") for v in values)+" |")
                body.append("<tr>"+"".join("<td>"+html.escape(v)+"</td>" for v in values)+"</tr>")
            body.append("</tbody></table></div>")
            markdown += [""]+section.get("notes",[])+[""]
            body += ["<p>"+html.escape(note)+"</p>" for note in section.get("notes",[])]
        body.append("</section>")
    markdown += ["## Selected downloads",""]
    body.append("<h2>Selected downloads</h2><ul>")
    for download in report["downloads"]:
        markdown += [f'- [{download["label"]}]({download["path"]}): {download["description"]}']
        body.append('<li><a href="'+download["path"]+'">'+html.escape(download["label"])+"</a>: "+html.escape(download["description"])+"</li>")
    body.append("</ul>")
    (stage/"report.md").write_text("\n".join(markdown)+"\n")
    (stage/"report.html").write_text('<!doctype html><html lang=en><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>'+html.escape(report["title"])+"</title><style>body{font:16px/1.6 system-ui;max-width:1100px;margin:auto;padding:24px;color:#24242b}img{max-width:100%;height:auto}table{border-collapse:collapse}td,th{border:1px solid #ddd;padding:8px;white-space:nowrap}.table-scroll{overflow-x:auto}section{margin:40px 0}</style><main>"+"\n".join(body)+"</main></html>\n")
    (stage/"day-disposition-verification.json").write_text(json.dumps(verification,indent=2)+"\n")
    (stage/"advice.md").write_text("""# Phase 1 interpretation — October 13, 2026

The fixed baseline's completed one-contract history is positive under the frozen assumed costs. This is conditional descriptive evidence on quality-qualified ranges and observable completed executions. The source $10,000 account submits no whole-GC orders. Its attainable return must not be inferred from the standardized ledger.

Annual performance is uneven: 2019 and 2023 are negative, and partial 2026 supplies more than half the historical net dollar total. London entries have stronger conditional results than Asia entries. New York and outside-session cohorts are sparse, and short-side expectancy remains uncertain. No session filter, alternate stop, midpoint entry or re-entry was selected.

Strict range completeness excludes substantial history. Later missing evidence remains unknown: censored accepted fills and unobserved first-fill opportunities are retained separately. Live vendor/mapping arrival timing, annual holiday certification, original raw reconstruction, tick ordering and native TradingView parity are not established. Closed-trade drawdown excludes floating equity. These limits constrain any trading claim.

Phase 2 should reuse this run's frozen baseline settings, pinned input identities, coverage roster, primary order/fill/trade ledgers and saved annual/session/side tables. All published baseline years are now exposed and cannot later be called untouched holdouts. Every midpoint/reclaim/interior entry, extra trade, re-entry and filter outcome remains uncomputed. A new instruction and frozen Phase 2 protocol are required before those calculations.
""")
    print(json.dumps(verification))


if __name__=="__main__": main()
