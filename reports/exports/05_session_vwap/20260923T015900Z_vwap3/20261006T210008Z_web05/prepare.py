"""Select and serialize saved evidence only; never import or execute study code."""
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
RUN = ROOT / "runs/05_session_vwap/20260923T015900Z_vwap3"
PUBLICATION_ID = "session-vwap-vwap3-20261006-web05"
BINDINGS = []
CLAIMS = []


def read_csv(name):
    with (RUN / "tables" / (name + ".csv")).open(newline="") as stream:
        return list(csv.DictReader(stream))


def select(rows, selector):
    matches = [r for r in rows if all(r[k] == v for k, v in selector.items())]
    assert len(matches) == 1, selector
    return matches[0]


def number(section, row_index, key, filename, selector, field, multiplier=1):
    row = select(read_csv(filename), selector)
    value = None if row[field] == "" else float(row[field]) * multiplier
    if value is not None and value.is_integer():
        value = int(value)
    BINDINGS.append({"section_id": section, "row": row_index, "key": key,
                     "source": f"{RUN.relative_to(ROOT)}/tables/{filename}.csv",
                     "selector": selector, "field": field, "multiplier": multiplier})
    return value


def text(id_, title, body, headings):
    CLAIMS.append({"section_id": id_, "source": f"{RUN.relative_to(ROOT)}/report.md",
                   "headings": headings, "operation": "abridge saved interpretation; preserve qualifications"})
    return {"id": id_, "title": title, "kind": "text", "body": body}


def column(key, label, format_=None, precision=0, unit=None):
    c = {"key": key, "label": label}
    if format_:
        c.update(format=format_, precision=precision)
    if unit:
        c["unit"] = unit
    return c


scorecards = read_csv("scorecards")
metrics = json.loads((RUN / "metrics.json").read_text())
names = {"B": "B · Return after departure", "A": "A · First outside-2σ fade", "C": "C · First VWAP retest bounce"}
primary = []
metric_items = []
for index, candidate in enumerate(["B", "A", "C"]):
    selector = {"strategy": candidate, "product": "ALL"}
    saved = select(scorecards, selector)
    metric = next(m for m in metrics if m["id"] == saved["metric_id"])
    assert metric["estimate"] == float(saved["rate"])
    assert metric["denominator"] == int(saved["evaluable"])
    assert metric["numerator"] == int(saved["successes"])
    assert metric["ci_95"] == [float(saved["ci_low"]), float(saved["ci_high"])]
    row = {"candidate": names[candidate], "horizon": "Window end" if candidate == "B" else "30 minutes"}
    for key, field in [("events", "events"), ("evaluable", "evaluable"), ("successes", "successes"),
                       ("rate", "rate"), ("ciLow", "ci_low"), ("ciHigh", "ci_high")]:
        row[key] = number("primary-scorecard", index, key, "scorecards", selector, field)
    primary.append(row)
    note = (f"{row['successes']:,} / {row['evaluable']:,} evaluable events. "
            f"{row['horizon']}; 95% shared-session-date interval "
            f"{row['ciLow']:.1%}–{row['ciHigh']:.1%}. "
            + ("Frozen VWAP contact; deadline-dependent." if candidate == "B" else "Favorable-first at equal 0.5σ barriers; not a trade win rate."))
    metric_items.append({"label": names[candidate], "value": metric["estimate"], "format": "percent", "precision": 1, "note": note})
    BINDINGS.append({"section_id": "key-rates", "item": index, "source": f"{RUN.relative_to(ROOT)}/metrics.json",
                     "metric_id": metric["id"], "field": "estimate", "multiplier": 1,
                     "note_sources": ["numerator", "denominator", "horizon", "ci_95"]})

outcomes = []
for index, candidate in enumerate(["A", "C"]):
    row = {"candidate": names[candidate]}
    for key, field in [("evaluable", "evaluable"), ("favorable", "favorable"), ("adverse", "adverse"),
                       ("neither", "neither"), ("ambiguous", "ambiguous")]:
        row[key] = number("barrier-counts", index, key, "scorecards", {"strategy": candidate, "product": "ALL"}, field)
    outcomes.append(row)

baseline_rows = []
for barrier in ["half_sigma", "fixed_8_ticks"]:
    for split in ["ALL", "final"]:
        for candidate, control in [("A", "A_control"), ("C", "C_near")]:
            selector = {"product": "ALL", "barrier_definition": barrier, "split": split, "treated": candidate, "control": control}
            saved = select(read_csv("baselines"), selector)
            assert saved["claim_status"] == "exploratory; no simultaneous familywise interval"
            row = {"comparison": "A vs lesser 1–2σ departures" if candidate == "A" else "C vs near approaches",
                   "period": "All years" if split == "ALL" else "2025–2026 to Sep 18",
                   "barrier": "0.5σ" if barrier == "half_sigma" else "8 ticks"}
            for key, field, multiplier in [("matched", "matched_treated", 1), ("unmatched", "unmatched_treated", 1),
                                          ("treatedRate", "treated_rate_matched", 1), ("controlRate", "control_rate_weighted", 1),
                                          ("difference", "difference", 100), ("ciLow", "ci_low_conditional_overlap", 100),
                                          ("ciHigh", "ci_high_conditional_overlap", 100)]:
                row[key] = number("matched-baselines", len(baseline_rows), key, "baselines", selector, field, multiplier)
            baseline_rows.append(row)

coverage = []
for index, product in enumerate(["ES", "NQ", "GC"]):
    row = {"product": product}
    for key, field in [("candidate", "candidate_days"), ("included", "eligible_days"), ("excluded", "excluded_unique_days")]:
        row[key] = number("coverage-2026", index, key, "eligibility", {"product": product, "year": "2026"}, field)
    coverage.append(row)

b = select(scorecards, {"strategy": "B", "product": "ALL"})
sections = [
    text("question", "Three questions about session VWAP",
         "Does price return after a meaningful departure, favor a fade after an extreme close, or bounce after its first causal retest? This report presents the three primary questions executed under protocol 1.0.0 on the pinned Session-Anchored VWAP 1.0.0 release, for ES, NQ and GC through September 18, 2026.\n\n"
         "Evidence status: price-path statistics; fills and execution costs remain unmodeled. The broader study also has exploratory A/C context and partial re-entry evidence in a separate run. Those findings are outside this publication. Cross acceptance/retests and outside-band continuation remain proposed.",
         ["Three-candidate scorecard", "Limitations and research advice"]),
    text("findings", "Frequent returns do not establish an executable edge",
         "Return after departure is frequent by the observation window's end, but that deadline varies across views. It does not describe a common short holding period or guarantee an attainable fill.\n\n"
         "At the primary barrier, outside-2σ fades and first retest bounces both have more adverse-first than favorable-first outcomes. The pooled fade contrast against lesser departures is small and reverses under the fixed eight-tick comparison. Retest bounces have no stable incremental advantage over near approaches. Neither candidate has a demonstrated incremental edge.",
         ["Return time and movement", "Favorable, adverse, timeout, and ambiguous outcomes", "Baseline comparisons"]),
    {"id": "key-rates", "title": "Primary outcomes at a glance", "kind": "metrics", "items": metric_items},
    text("denominators", "Read the denominators before comparing the rates",
         f"The scorecard pools {int(b['eligible_windows']):,} overlapping product × date × timeframe × anchor/window views from {int(b['sessions']):,} distinct product-sessions. Seven anchor/window views and two timeframes share price paths; they are not independent opportunities. The 95% percentile intervals resample shared session dates, keeping correlated views and products together.\n\n"
         "B measures frozen VWAP contact by window end. A and C measure favorable first passage before an equal adverse barrier within 30 elapsed minutes. Their evaluable denominators require a complete horizon; events too late for that horizon remain in event counts. Ambiguous and neither-barrier outcomes remain in the evaluable denominator. Do not compare these three rates as a profitability ranking.",
         ["Three-candidate scorecard", "Coverage and sample construction", "Frequency and denominators", "Favorable, adverse, timeout, and ambiguous outcomes"]),
    {"id": "primary-scorecard", "title": "Selected primary scorecard", "kind": "table",
     "columns": [column("candidate", "Candidate"), column("horizon", "Deadline"), column("events", "Events", "number"),
                 column("evaluable", "Evaluable", "number"), column("successes", "Primary successes", "number"),
                 column("rate", "Rate", "percent", 1), column("ciLow", "95% low", "percent", 1), column("ciHigh", "95% high", "percent", 1)], "rows": primary},
    text("barrier-definition", "What favorable, adverse and ambiguous mean",
         "A fades toward VWAP after the first fresh completed close outside 2σ in a rearmed excursion. C follows the departure's side after its first qualified retest. Both use distance equal to 0.5 × signal-time sigma, rounded upward to whole ticks and frozen at the signal.\n\n"
         "Favorable and adverse mean which equal-distance barrier is reached first after the next unadjusted one-minute open. Neither means no barrier within 30 minutes. If both opposing extremes cross within one one-minute bar and their order is unresolved, the outcome is ambiguous. A gap at a one-minute open can determine first passage. These are movement observations, not modeled stops, targets or fills.",
         ["Exact setup definitions", "Favorable, adverse, timeout, and ambiguous outcomes"]),
    {"id": "barrier-figure", "title": "The competing outcomes", "kind": "figure", "path": "figures/barrier-outcomes.png",
     "alt": "Stacked bars for outside-2σ fades and first VWAP retest bounces. Adverse-first portions are slightly larger than favorable-first; neither and ambiguous remain visible. Exact counts follow in the table.",
     "caption": "Saved primary A/C barrier illustration, faithfully rasterized with extra right margin for the existing denominator labels. Green: favorable first; red: adverse first; gray: neither; purple: ambiguous. Each bar uses its own evaluable denominator at equal 0.5σ barriers over 30 minutes. No uncertainty bands are shown; the scorecard carries the saved intervals."},
    {"id": "barrier-counts", "title": "All four classes remain in the denominator", "kind": "table",
     "columns": [column("candidate", "Candidate")] + [column(k, label, "number") for k, label in
                 [("evaluable", "Evaluable"), ("favorable", "Favorable first"), ("adverse", "Adverse first"), ("neither", "Neither"), ("ambiguous", "Ambiguous")]], "rows": outcomes},
    text("baseline-context", "Matched comparisons are exploratory",
         "A is compared with fresh lesser 1–2σ departures; C with near approaches that stay outside the causal one-tick touch zone. Matching uses product, timeframe, anchor/window, direction, hour, anchor age and observable sigma bins learned from development. Control rates are weighted to matched treated events. The A populations still have disjoint starting-distance support.\n\n"
         "All contrasts below are exploratory. Their 95% shared-date bootstrap intervals are conditional on observed matching overlap and weights; no simultaneous familywise interval was supplied. The difference is treated minus weighted control, in percentage points. A negative value favors the control. Fixed eight-tick results demonstrate barrier dependence, rather than selecting a preferred setting.",
         ["Baseline comparisons"]),
    {"id": "matched-baselines", "title": "Selected matched baselines and contrary evidence", "kind": "table",
     "columns": [column("comparison", "Comparison"), column("period", "Period"), column("barrier", "Symmetric barrier"),
                 column("matched", "Matched treated", "number"), column("unmatched", "Unmatched treated", "number"),
                 column("treatedRate", "Treated rate", "percent", 1), column("controlRate", "Weighted control", "percent", 1),
                 column("difference", "Difference", "number", 2, "pp"), column("ciLow", "95% low", "number", 2, "pp"), column("ciHigh", "95% high", "number", 2, "pp")], "rows": baseline_rows},
    text("methods", "Definitions, timing and reference prices",
         "B selects the first mature close in each view at least max(1σ, four ticks) from VWAP. Its frozen contact target is departure-time VWAP ± one tick. No departure is retained as a separate view state; a nonreturn remains a failure by the named deadline. Evolving VWAP contact is a distinct outcome and is not used for the headline rate.\n\n"
         "A uses a true published 2σ exit after a valid consecutive comparison, rather than treating an already-outside state as a fresh exit. It rearms after a completed close within inclusive ±1σ. C requires a meaningful departure, ten elapsed minutes of completed same-side closes, and the first causal touch of the open-known VWAP zone. An unqualified first contact consumes the departure. The touching bar's extremes do not count as post-signal movement.\n\n"
         "Anchors must be active, finite and have positive sigma after 30 minutes of accumulation. Signal information is available only at exclusive bar close. Paths begin at the following unadjusted one-minute open as an idealized reference; source gaps, contract rolls and session/window boundaries are not bridged. All session clocks follow America/New_York. Sigma is volume-weighted dispersion, not a normal-distribution containment guarantee.",
         ["Exact setup definitions", "Return time and movement"]),
    text("coverage", "Coverage is retrospective and product-specific",
         "The pinned sample is discontinuous and differs by product. Eligibility selects complete product-days retrospectively; it is not an observable entry-time filter. The following saved 2026 rows illustrate candidate versus included days through September 18. Excluded unique days are distinct days; underlying exclusion reasons can overlap and must not be added as a total.\n\n"
         "Development ends in 2023, validation covers 2024, and final evaluation starts in 2025. These are chronological labels; the final outcomes are not certified previously unseen. Two agreeing timeframes remain correlated views of the same history.",
         ["Coverage and sample construction", "Calendar and chronological stability"]),
    {"id": "coverage-2026", "title": "2026 eligibility example · through September 18", "kind": "table",
     "columns": [column("product", "Product"), column("candidate", "Candidate days", "number"),
                 column("included", "Included days", "number"), column("excluded", "Excluded unique days", "number")], "rows": coverage},
    text("limitations", "What the evidence leaves open",
         "No net trading conclusion follows from a return or barrier rate. Commission, spread/slippage, latency, order type, position size, overlap handling, touched-level fills and gap behavior remain unspecified. Full-horizon MFE/MAE may occur after a first barrier and cannot be assumed capturable by a stopped policy.\n\n"
         "A long window-end return rate is horizon dependent. Conditional waiting time among returners is not expected waiting time for all departures. Source one-minute bars cannot resolve intraminute ordering; ambiguity remains part of the outcome. Prespecified warm-up and barrier sensitivity tables are saved descriptions, not optimized settings. Broad segmentation and controls remain exploratory.",
         ["Return time and movement", "Limitations and research advice"]),
    text("sources", "Source and publication provenance",
         "Study 05 · Session-anchored VWAP. Source run 20260923T015900Z_vwap3 is the registered research reference; executed protocol 1.0.0, pinned feature release 1.0.0. Primary metric IDs: b.all.primary, a.all.primary, c.all.primary. Supporting saved evidence: primary scorecards, matched baselines and the eligibility audit.\n\n"
         "The source run records input reconciliation, denominator checks and deterministic example review. This publication checks transfer of saved values and figure identity; it does not repeat research execution or independently establish an edge. Presentation revision 20261006T210008Z_web05 uses web-study-report-1.0. The publication record below identifies this selected report and raster asset.",
         ["Saved evidence", "Coverage and sample construction"]),
]
report = {"schemaVersion": "1.0", "id": PUBLICATION_ID, "title": "Session VWAP: returns, fades and first retests",
          "summary": "ES, NQ and GC price-path evidence shows frequent return by window end, while extreme fades and first retest bounces do not demonstrate stable incremental advantage. These observations do not establish net profitability.",
          "publishedAt": "2026-10-06T21:00:08Z", "source": {"producer": "sahadeva", "runId": RUN.name}, "sections": sections}
source_names = ["report.md", "report.html", "config.json", "protocol-1.0.0.md", "metrics.json", "publication.json", "manifest.json",
                "inputs.lock.json", "events.manifest.json", "verification-results.json", "tables/scorecards.csv", "tables/baselines.csv",
                "tables/eligibility.csv", "tables/exclusions.csv", "figures/barrier-outcomes.svg", "figures/barrier-outcomes.png"]
artifacts = [{"path": str((RUN / name).relative_to(ROOT)), "sha256": hashlib.sha256((RUN / name).read_bytes()).hexdigest()} for name in source_names]
source_map = {"study_id": "05_session_vwap", "source_run_id": RUN.name, "revision_id": HERE.name, "publication_id": PUBLICATION_ID,
              "source_artifacts": artifacts, "numeric_bindings": BINDINGS, "claims": CLAIMS,
              "definitions": {"source": str((RUN / "protocol-1.0.0.md").relative_to(ROOT)), "sections": ["Population and time", "B", "A", "C", "Comparisons and uncertainty"]},
              "figure": {"section_id": "barrier-figure", "source": str((RUN / "figures/barrier-outcomes.svg").relative_to(ROOT)),
                         "output": "figures/barrier-outcomes.png", "operation": "librsvg rasterization; extend white canvas to 960px to preserve existing right-edge labels; 2× resolution; geometry unchanged"},
              "formatting": "Ratios retained; baseline ratio contrasts ×100 to percentage points; display rounding only. Metric notes generated from saved values, not separately retyped."}
for filename, data in [("publication.json", report), ("source-map.json", source_map)]:
    (HERE / filename).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
print(f"Prepared {PUBLICATION_ID}; {len(BINDINGS)} numerical bindings from saved evidence.")
