"""Read-only review of saved r3 report artifacts; writes this review receipt only."""
from pathlib import Path
from html.parser import HTMLParser
from datetime import datetime, timezone
import csv
import hashlib
import importlib
import json
import struct
import sys

import pandas as pd

STAGE = Path(__file__).resolve().parents[2]
WORKSPACE = STAGE.parents[2]
sys.path.insert(0, str(WORKSPACE / "studies"))
reconcile = importlib.import_module("21_ema_cloud_trend_follow_opportunity.src.reconcile")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def identity(path):
    path = Path(path)
    return {"path": str(path.resolve()), "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


class Parsed(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables, self.images, self.links, self.text = [], [], [], []
        self.current = self.row = self.cell = None
        self.scrolls = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "table":
            self.current = []
        elif tag == "tr":
            self.row = []
        elif tag in ("th", "td"):
            self.cell = []
        elif tag == "img":
            self.images.append(attrs)
        elif tag == "a":
            self.links.append(attrs)
        elif tag == "div" and attrs.get("class") == "scroll" and attrs.get("tabindex") == "0":
            self.scrolls += 1

    def handle_data(self, data):
        self.text.append(data)
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("th", "td") and self.cell is not None:
            self.row.append("".join(self.cell))
            self.cell = None
        elif tag == "tr" and self.current is not None:
            self.current.append(self.row)
            self.row = None
        elif tag == "table":
            self.tables.append(self.current)
            self.current = None


publication = json.loads((STAGE / "publication.json").read_text())
bindings = json.loads((STAGE / "source-bindings.json").read_text())
checks = [reconcile.verify_publication(STAGE)]
parsed = Parsed()
parsed.feed((STAGE / "report.html").read_text())
tables = [s for s in publication["sections"] if s["kind"] == "table"]
figures = [s for s in publication["sections"] if s["kind"] == "figure"]
require(len(parsed.tables) == len(tables) == parsed.scrolls, "HTML table count or scroll containers differ")
cells = 0
for actual, source in zip(parsed.tables, tables):
    require(actual[0] == [c["label"] for c in source["columns"]], "HTML headers differ")
    expected = [["Not available" if row.get(c["key"]) is None else str(row[c["key"]])
                 for c in source["columns"]] for row in source["rows"]]
    require(actual[1:] == expected, "HTML cells differ from publication cells")
    cells += sum(map(len, expected))
require([(s["src"], s["alt"]) for s in parsed.images] == [(s["path"], s["alt"]) for s in figures], "HTML image declarations differ")
require(all((STAGE / s["src"]).is_file() for s in parsed.images), "HTML local image missing")
require(all((STAGE / a["href"]).is_file() for a in parsed.links), "HTML local evidence link missing")
html_text = " ".join(parsed.text)
markdown = (STAGE / "report.md").read_text()
require(all(all(p in markdown and p in html_text for p in s["body"].split("\n\n"))
            for s in publication["sections"] if s["kind"] == "text"), "HTML/Markdown narrative differs")
checks.append({"check": "offline_html_transfer", "status": "passed", "tables": len(tables),
               "table_cells": cells, "local_figures": len(figures), "local_evidence_links": len(parsed.links),
               "focusable_scroll_containers": parsed.scrolls})

with (STAGE / "tables/S1-T02_horizon_scorecard.csv").open(newline="") as handle:
    score = list(csv.DictReader(handle))
primary = [r for r in score if r["horizon"] == "15" and r["direction"] == "All" and r["support"] == "all" and r["unit"] == "points"]
require(len(primary) == 6, "primary cells missing")
require(all(float(r["ci95_low"]) <= 0 <= float(r["ci95_high"]) for r in primary), "primary zero-interval claim differs")
require(all(float(r["mean_mae"]) > float(r["mean_mfe"]) for r in primary), "primary MAE/MFE comparison differs")
atr = [r for r in score if r["horizon"] == "15" and r["direction"] == "All" and r["support"] == "all" and r["unit"] == "atr"]
require(len(atr) == 6 and all(int(r["normalization_missing"]) == 0 for r in atr), "primary ATR denominator requires further qualification")
checks.append({"check": "primary_descriptive_claims", "status": "passed", "cells": 6,
               "all_four_week_raw_primary_intervals_include_zero": True, "mean_mae_exceeds_mean_mfe_all_six": True,
               "primary_atr_normalization_missing": 0})

calendar = []
with (STAGE / "tables/S1-T05_calendar.csv").open(newline="") as handle:
    for row in csv.DictReader(handle):
        if row["horizon"] == "15" and row["direction"] == "All" and row["support"] == "all" and row["unit"] == "points":
            calendar.append(row)
for product in ("ES", "GC", "NQ"):
    for interval in ("3", "5"):
        rows = [r for r in calendar if r["product"] == product and r["interval_minutes"] == interval]
        weeks = [r for r in rows if r["period_kind"] == "week"]
        months = [r for r in rows if r["period_kind"] == "month"]
        require(len(weeks) == 157 and weeks[0]["period"] == "2018-01-01" and weeks[-1]["period"] == "2020-12-28", "corrected week roster differs")
        require(len(months) == 36 and months[0]["period"] == "2018-01" and months[-1]["period"] == "2020-12", "full month roster differs")
        require(all(r["mean_terminal_delta"] == "" for r in rows if int(r["completed"]) == 0), "undefined period replaced with zero")
checks.append({"check": "complete_calendar_and_null_displays", "status": "passed", "weeks_per_cell": 157,
               "months_per_cell": 36, "zero_completed_periods": sum(int(r["completed"]) == 0 for r in calendar)})

with (STAGE / "tables/S1-T06_examples.csv").open(newline="") as handle:
    examples = list(csv.DictReader(handle))
require(len(examples) == 30 and len({r["selection_id"] for r in examples}) == 30, "deterministic example roster differs")
paths = pd.read_parquet(STAGE / "tables/selected-example-paths.parquet")
require(pd.to_datetime(paths.timestamp, utc=True).dt.tz_convert("America/New_York").dt.year.between(2018, 2020).all(), "reserved illustration candles exposed")
checks.append({"check": "example_scope", "status": "passed", "selections": 30, "path_rows": len(paths),
               "only_ny_2018_2020": True})

figure_sizes = []
for figure in figures:
    path = STAGE / figure["path"]
    data = path.read_bytes()
    require(data[:8] == b"\x89PNG\r\n\x1a\n", "figure is not PNG")
    width, height = struct.unpack(">II", data[16:24])
    require(path.stat().st_size <= 2 * 1024 * 1024, "figure exceeds image budget")
    figure_sizes.append({"path": figure["path"], "width": width, "height": height, "bytes": path.stat().st_size})
require(sum(r["bytes"] for r in figure_sizes) <= 8 * 1024 * 1024 and (STAGE / "publication.json").stat().st_size <= 96 * 1024, "publication byte budget exceeded")
checks.append({"check": "visual_and_source_budget_review", "status": "passed", "figures": figure_sizes,
               "method": "Manual inspection of all six saved PNGs via view_image plus exact source bindings; no figure regenerated.",
               "findings": "Readable labels and axes; MAE/MFE share product scale; all years retained; undefined monthly means remain gaps; each illustration contains fixed example classes.",
               "browser_visual_qa": "Unavailable: iab browser not available and sandbox denied loopback server bind. HTML structure, all cells and local assets checked independently."})

source_rows = json.loads((STAGE / "provenance/source-inventory.json").read_text())["sources"]
owned = [r for r in source_rows if r["workspace_path"].endswith(("src/reporting.py", "src/reconcile.py", "tests/test_reporting.py", "tests/test_reconcile.py"))]
for row in owned:
    require(identity(WORKSPACE / row["workspace_path"])["sha256"] == row["sha256"] == identity(STAGE / row["snapshot_path"])["sha256"], "frozen report/check source drift")
checks.append({"check": "owned_source_identity", "status": "passed", "frozen_files": len(owned)})

selected = [STAGE / p for p in ("config.json", "protocol.md", "inputs.lock.json", "events.manifest.json", "evidence.manifest.json", "report.md", "report.html", "advice.md", "publication.json", "source-bindings.json", "figure-environment.json", "provenance/source-inventory.json")]
plan = STAGE / "plan.md"
frozen_plan = STAGE / "provenance/source/studies/21_ema_cloud_trend_follow_opportunity/plan.md"
if plan.is_file():
    require(identity(plan)["sha256"] == identity(frozen_plan)["sha256"], "run plan differs from frozen plan")
    selected.extend([plan, frozen_plan])
selected.extend(STAGE / s["path"] for s in figures)
selected.extend(STAGE / s["path"] for s in bindings["downloads"])
selected.extend(STAGE / r["source_artifact"] for r in bindings["cells"] + bindings["claims"])
selected.extend(STAGE / r["source_artifact"] for b in bindings["figures"] for r in b["sources"])
completion = STAGE / "provenance/reviews/coverage-adapter-completion.json"
verification_passed = completion.is_file() and json.loads(completion.read_text()).get("status") == "passed"
for name in ("coverage-adapter-before-execution.json", "coverage-adapter-completion.json", "presentation-correction.json"):
    path = STAGE / "provenance/reviews" / name
    if path.is_file():
        selected.append(path)
receipt = {"schema_version": 1, "study_id": "21_ema_cloud_trend_follow_opportunity", "run_id": STAGE.name,
           "reviewer": "Agent C independent actual report review", "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
           "status": "passed" if verification_passed else "presentation_passed_verification_pending", "checks": checks,
           "findings": [{"id": "R3-C01", "severity": "disclosed_verification_correction", "status": "resolved" if verification_passed else "full_adapter_check_pending",
                         "description": "Frozen pipeline populates T00 feature_ready_slots from mapped decision readiness, but frozen independent checker expected null for 3m. Original scientific verify stopped on ES/3/2018 actual 45541 versus expected null. Root corrected static coverage captions and retained a coverage-only independent verification adapter; canonical frozen sources and numerical artifacts remain unchanged.",
                         "affected": ["tables/S1-T00_coverage.csv:feature_ready_slots", "src/reconcile.py:573", "publication.json:coverage.description", "report.md:Input coverage and quality"],
                         "classification": "Checker/presentation semantics mismatch; no observed event/outcome formula or primary numerical claim defect.",
                         "resolution": "Final report/pub/HTML caption alignment is reviewed here. The separately pinned adapter checks mapped readiness, shares and sessions while rerunning all unchanged verification functions; its completion receipt determines the overall status."}],
           "scope_review": "2018–2020 only; no later-period result, fast branch, threshold search, selected hour, profitability, public staging or deployment. Calendar/feed timing qualifications are prominent; early sparse GC strata retained.",
           "interpretation_limit": "All-six interval and MAE/MFE statements refer to pooled raw H15 primary cells. They do not imply every direction/session/sensitivity or equal-active contrast is null.",
           "artifact_identities": [identity(p) for p in sorted(set(selected))], "review_script": identity(__file__),
           "source_mutations": False, "generated_report_mutations": False}
(STAGE / "provenance/reviews/report-review.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
print(json.dumps({"status": receipt["status"], "checks": len(checks), "review_receipt": str(STAGE / "provenance/reviews/report-review.json")}, indent=2))
