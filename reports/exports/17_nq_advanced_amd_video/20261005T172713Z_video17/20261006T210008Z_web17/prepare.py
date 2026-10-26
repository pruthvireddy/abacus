"""Abridge a frozen source review and copy five explicitly selected frames."""
import csv
import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
RUN = ROOT / "runs/17_nq_advanced_amd_video/20261005T172713Z_video17"
PUBLICATION_ID = "nq-amd-source-review-20261006-web17"
SOURCE = json.loads((RUN / "source.json").read_text())
CLAIM_MAP = []
FIGURE_MAP = []


def text(id_, title, body, headings, claim_ids):
    CLAIM_MAP.append({"section_id": id_, "source": str((RUN / "report.md").relative_to(ROOT)),
                      "headings": headings, "claim_ids": claim_ids, "operation": "abridge saved qualitative interpretation"})
    return {"id": id_, "title": title, "kind": "text", "body": body}


charts = {r["chart_id"]: r for r in csv.DictReader((RUN / "tables/charts.csv").open(newline=""))}
captures = {r["file"]: r for r in json.loads((RUN / "capture-log.json").read_text())}


def figure(chart_id, id_, title, alt):
    chart = charts[chart_id]
    source = RUN / chart["file"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == chart["sha256"]
    assert source.stat().st_size == int(chart["bytes"])
    assert captures[source.name]["seconds"] == int(chart["seconds"])
    shutil.copyfile(source, HERE / chart["file"])
    FIGURE_MAP.append({"section_id": id_, "chart_id": chart_id, "source": str(source.relative_to(ROOT)),
                       "output": chart["file"], "sha256": chart["sha256"], "operation": "exact byte copy; no crop, resize or recompression",
                       "timestamp_source": "tables/charts.csv + capture-log.json", "media_seconds": int(chart["seconds"])})
    return {"id": id_, "kind": "figure", "title": title, "path": chart["file"], "alt": alt,
            "caption": f"Tmac · {SOURCE['title']} · chart {chart_id}, media time {chart['timestamp']} ({chart['displayed_timeframe']}). "
                       f"{chart['visible_observation']} {chart['interpretive_limit']} Source: {chart['source_url']}"}


selected_claim_ids = ["C02", "C06", "C11", "C14", "C15", "C17", "C20", "C21"]
claims = {r["claim_id"]: r for r in csv.DictReader((RUN / "tables/claims.csv").open(newline=""))}
ledger = [{"claim": f"{id_} · {claims[id_]['claim_summary']}",
           "attribution": claims[id_]["attribution"].replace("_", " "),
           "status": claims[id_]["evidence_status"].replace("_", " "),
           "qualification": claims[id_]["qualification"]} for id_ in selected_claim_ids]

sections = [
    text("question", "A source review of the weekly-to-intraday decision process",
         f"What does {SOURCE['creator']}'s lesson teach about carrying a weekly view into local NQ decisions, and what do its selected examples actually establish? Source: {SOURCE['title']}, {SOURCE['url']}. YouTube displayed publication on {SOURCE['publication_date_as_displayed']}; the saved review accessed it on {SOURCE['access_date']}. The full {SOURCE['displayed_duration']} lesson was reviewed from 0:00 using English automatic captions and selected actual chart captures.\n\n"
         f"Evidence status: qualitative source review only. No independent trade verification or profitability test. The quarterly-candle regularity is unverified, and the all-time-high objective was not reached in the reviewed week. Visible chart labels identify {SOURCE['chart_period']['start']} through {SOURCE['chart_period']['end']}, a period distinct from the video's publication date.",
         ["Introduction", "Evidence and reproduction"], ["C06", "C17", "C21"]),
    text("findings", "Bias, confirmation and permission to abstain",
         "Saved reviewer interpretation: the lesson describes a hierarchy—form a conditional weekly view, identify the liquidity destination that would make it actionable, then wait for a suitable local entry sequence. Having a bullish view is distinct from having an acceptable long entry.\n\n"
         "AMD means accumulation, manipulation and distribution in the speaker's vocabulary. These labels describe his interpretation of visible price behavior; candles alone do not identify deliberate manipulation by a market participant. A sweep, reaction, break of structure and later order-block retest can describe overlapping parts of the same path. Their independence is not established.",
         ["What the framework means", "The sequence that carries across days", "What is demonstrated and what remains open"], ["C02", "C20"]),
    text("weekly-context", "The weekly thesis remains conditional",
         "Presenter interpretation: the preceding weekly-zone reaction supports a bullish view toward a higher liquidity objective. Local bearish sequences can be pullbacks within that larger thesis; this does not prove countertrend trades lack positive expectancy.\n\n"
         "Visible observation: the hourly capture shows the broader rebound and annotated continuation. The drawn path illustrates the speaker's thesis, not a calculated probability or an authenticated advance forecast.",
         ["What the framework means"], ["C02", "C03"]),
    figure("01", "weekly-figure", "Weekly context · 3:33",
           "Hourly NQ chart with a broader rebound, marked horizontal zones and a red sketched continuation path. Later chart bars are visible; the drawing is the presenter's thesis rather than a forecast distribution."),
    text("wednesday", "Wednesday: the information between two zones matters",
         "Presenter preference: the first zone can be an area of interest while an external low remains vulnerable. A subsequent reaction and break of structure supply the reason to prefer a later zone. This is not a rule to buy the second rectangle on a chart.\n\n"
         "Visible observation: the three-minute frame shows the first reaction, the marked structure break and subsequent zone. Saved reviewer inference: waiting trades earlier access for confirmation, with a risk of missing a move that never retests. The lesson does not estimate that tradeoff. The saved review also retains a weaker re-entry rejected on discretionary quality grounds; no numerical retest cutoff is supplied.",
         ["Wednesday explains why the second order block matters"], ["C11", "C12"]),
    figure("06", "wednesday-figure", "Reaction, structure break and later zone · 15:23",
           "Three-minute NQ chart showing a downswing into marked lower zones, a reaction and sharp upward expansion. Annotations distinguish the initial reaction from the later zone after structure changes."),
    text("thursday", "Thursday: a directional view can still produce no trade",
         "Presenter claim: overlapping accumulation, awkward transitions and an unclear destination left no sufficiently clean combination of structure and target. He says he took no positions.\n\n"
         "Visible observation: the five-minute chart contains overlapping swings and nearby competing structures. Saved reviewer interpretation: bullish context is permission to look for an entry, not an instruction to stay long. The reported abstention is not independently verified by an account ledger, and one rejected day does not provide the denominator of all skipped or failed setups.",
         ["Thursday demonstrates the no-trade state", "What is demonstrated and what remains open"], ["C14"]),
    figure("09", "thursday-figure", "The rejected profile · 20:08",
           "Five-minute NQ chart with overlapping swings, shaded zones and an earlier rise followed by a sharp decline. Competing nearby structures illustrate the presenter's no-trade discussion."),
    text("friday", "Friday: revise the thesis after the observed response",
         "Presenter explanation: he initially considers a range-bound day and a short from an upper area. The sharp upward response around what he calls NFP changes that view, leading him to look for a later long setup.\n\n"
         "Visible observation: the three-minute capture shows an upward expansion followed by substantial retracement and overlap. Saved reviewer interpretation: this is adaptation to an observed response, not demonstrated advance prediction of the news result. The event identity follows the speaker; this review did not independently reconstruct the release or its execution conditions.",
         ["Friday shows revision and a target shortfall"], ["C15"]),
    figure("11", "friday-figure", "Expansion, retracement and reassessment · 23:23",
           "Three-minute NQ chart with a sharp upward leg, a peak and substantial retracement into overlapping price action. Marked zones and channel lines remain as shown by the presenter."),
    text("shortfall", "Preserve the difference between objective and outcome",
         "Presenter acknowledgment: the all-time-high objective was not reached during the reviewed week. He describes nearer relative equal highs on the hourly chart as the actual terminal draw and proposes another attempt the following week.\n\n"
         "Visible observation: the hourly frame places the nearer draw below the broader objective. Saved reviewer interpretation: moving an unmet objective into a later week is a revised hypothesis, not evidence that the original timing was correct. The next-week scenario remains unevaluated in this source.",
         ["Friday shows revision and a target shortfall"], ["C17", "C18"]),
    figure("13", "shortfall-figure", "The unmet broader target · 24:48",
           "Hourly NQ chart with nearer marked highs around the week's upper price action and a broader horizontal objective above. The original target and the stopping point are distinct."),
    text("ledger-context", "Keep claims, observations and interpretation separate",
         "This selected claim ledger copies saved claims and qualifications. Presenter interpretation, reported decisions, historical assertions and reviewer cautions retain distinct attribution and evidence labels. It is not a statistical scorecard. Specialist terms and discretionary rules remain as limited by the source.",
         ["What is demonstrated and what remains open"], selected_claim_ids),
    {"id": "claim-ledger", "title": "Selected claims and their evidentiary limits", "kind": "table",
     "columns": [{"key": "claim", "label": "Saved claim"}, {"key": "attribution", "label": "Attribution"},
                 {"key": "status", "label": "Evidence status"}, {"key": "qualification", "label": "Qualification"}], "rows": ledger},
    text("methods", "How the source was reviewed",
         "The saved review covers the entire automatic English caption track and fourteen purposively selected actual player captures. This publication selects five unchanged frames to explain context, confirmation, abstention, reassessment and shortfall. Specialist auto-caption terminology can be uncertain; the caption export is not an independently audited transcript.\n\n"
         "Media timestamps identify moments in the lesson. Chart dates, replay cursor, screen-recording clock and publication time are separate. Several chart status bars show UTC+4; session names follow the speaker without assuming New York chart time. Original annotations and facecam remain. Approximate prices in these images are not executable data.\n\n"
         "The source and captions were inspected before the exploratory review protocol was written. The days and possible entries share one selected week's price path; they are not independent validation samples.",
         ["Introduction", "Evidence and reproduction", "What is demonstrated and what remains open"], ["C20", "C21"]),
    text("limitations", "What the examples do not verify",
         "The examples provide a coherent explanation of the presenter's decision hierarchy. They do not supply a hit rate, calibrated probability, net expectancy, complete trade log or superiority to a simpler trend-and-pullback rule. Speaker-reported point and R examples remain unaudited and are omitted from this presentation. Embedded clips do not independently authenticate original private-message timestamps or all contemporaneous forecasts.\n\n"
         "The quarterly assertion is unverified: an inside-range candle and a close inside a prior candle are different definitions, and the source supplies neither a precise complete count nor a fixed construction method. Swing choice, order-block boundaries, break-of-structure rules, invalidation, fill logic and costs remain underspecified. Thursday's abstention and Friday's revised objective remain part of the record. More examples from this already-reviewed week would not constitute out-of-sample evidence.",
         ["Monday establishes a candidate low", "What is demonstrated and what remains open", "How Abacus could test the ideas later"], ["C01", "C06", "C08", "C09", "C14", "C17", "C20", "C21"]),
    text("sources", "Source and publication provenance",
         f"Primary source: {SOURCE['creator']}, {SOURCE['title']}. Video identity: mmem9CI7vvw; {SOURCE['url']}. Publication and access dates recorded by the saved review: {SOURCE['publication_date_as_displayed']} and {SOURCE['access_date']}. Captions: English, automatically generated. Figure captions retain source URLs and actual media timestamps.\n\n"
         "Study 17 · NQ advanced AMD video source study. Source run 20261005T172713Z_video17, exploratory source-review protocol 1.0.0. It is explicitly selected for this presentation as the sole complete saved review of the lesson; the study has no registered research reference. The source run records capture, link and artifact-hash checks. This publication checks selected frame identity and faithful abridgment; no trade or profitability test was performed. Presentation revision 20261006T210008Z_web17 uses web-study-report-1.0.",
         ["Evidence and reproduction"], ["C21"]),
]
report = {"schemaVersion": "1.0", "id": PUBLICATION_ID,
          "title": "NQ advanced AMD: bias, confirmation and abstention",
          "summary": "A qualitative review of Tmac's weekly-to-intraday decision process, with selected charts showing confirmation, a no-trade day, reassessment and an unmet target. One reviewed week does not establish independently verified performance or profitability.",
          "publishedAt": "2026-10-06T21:00:08Z", "source": {"producer": "sahadeva", "runId": RUN.name}, "sections": sections}
source_names = ["report.md", "report.html", "source.json", "config.json", "provenance/study-source/plan.md", "inputs.lock.json", "manifest.json", "checks.json",
                "capture-log.json", "tables/coverage.csv", "tables/claims.csv", "tables/charts.csv", "provenance/acquisition.md"]
# The executed protocol is retained in the run's frozen study-source snapshot.
source_names += [charts[id_]["file"] for id_ in ["01", "06", "09", "11", "13"]]
artifacts = [{"path": str((RUN / name).relative_to(ROOT)), "sha256": hashlib.sha256((RUN / name).read_bytes()).hexdigest()} for name in source_names]
source_map = {"study_id": "17_nq_advanced_amd_video", "source_run_id": RUN.name, "revision_id": HERE.name, "publication_id": PUBLICATION_ID,
              "source_selection": "Sole complete saved review of the requested lesson; selected for publication without registering a research reference.",
              "source_artifacts": artifacts, "claims": CLAIM_MAP, "figures": FIGURE_MAP,
              "table": {"section_id": "claim-ledger", "source": str((RUN / "tables/claims.csv").relative_to(ROOT)), "claim_ids": selected_claim_ids,
                        "field_mapping": {"claim": ["claim_id", "claim_summary"], "attribution": ["attribution"], "status": ["evidence_status"], "qualification": ["qualification"]},
                        "operation": "exact field transfer; replace underscores with spaces in attribution/status labels"},
              "metadata": {"source": str((RUN / "source.json").relative_to(ROOT)), "fields": list(SOURCE)},
              "numeric_bindings": [], "limits": "No metrics, performance scorecard, invented chart, new market data or full transcript."}
for filename, data in [("publication.json", report), ("source-map.json", source_map)]:
    (HERE / filename).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
print(f"Prepared {PUBLICATION_ID}; five exact saved frame copies, eight attributed claims.")
