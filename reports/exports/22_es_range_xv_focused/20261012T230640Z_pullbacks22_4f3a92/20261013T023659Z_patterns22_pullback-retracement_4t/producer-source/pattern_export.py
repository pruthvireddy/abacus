"""Add schematic candle explanations to saved reports without recalculation.

Prepare fresh drafts, independently review them, then export unique presentation
revisions. Previous publication content, evidence bindings and CSV bytes survive
unchanged; only publication identity/time and additive explanation fields differ.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[2]
STUDY_ID = "22_es_range_xv_focused"
VERSION = "study22-candle-patterns/1.0"
ANALYSES = {
    "pullback-continuation": "pullback-continuation",
    "pullback-retracement": "pullback-retracement",
    "pullback-payoff": "pullback-payoff",
    "reversal-continuation": "reversal-continuation",
    "retracement-recovery": "reversal-retracement",
    "trend-length": "trend-length",
}
ILLUSTRATIVE = "Schematic candles in normalized illustrative units; not actual market bars or RXV geometry."


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode()


def record(path: Path) -> dict:
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": digest(path)}


def safe_file(locator: str) -> Path:
    if not locator or Path(locator).is_absolute() or any(p in ("", ".", "..") for p in locator.split("/")) or "\\" in locator:
        raise ValueError("Expected a contained workspace-relative locator")
    path = ROOT
    for part in locator.split("/"):
        path /= part
        if path.is_symlink():
            raise ValueError("Source symlinks are refused")
    if not path.is_file():
        raise ValueError(f"Source is not a regular file: {locator}")
    return path


def component(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", value):
        raise ValueError("Expected a single safe revision component")
    return value


def candle(cid, label, opening, close, low=None, high=None, role="context") -> dict:
    return {"id": cid, "label": label, "open": opening,
            "high": max(opening, close) + 2 if high is None else high,
            "low": min(opening, close) - 2 if low is None else low,
            "close": close, "role": role}


def span(start, end, label):
    return {"kind": "span", "startCandle": start, "endCandle": end, "label": label}


def level(start, end, price, label):
    return {"kind": "level", "startCandle": start, "endCandle": end, "price": price, "label": label}


def band(start, end, low, high, label):
    return {"kind": "band", "startCandle": start, "endCandle": end, "low": low, "high": high, "label": label}


def mirror(variant: dict) -> dict:
    result = deepcopy(variant)
    result["id"] = "bearish"
    result["title"] = result["title"].replace("Bullish", "Bearish")
    result["description"] = result["description"].replace("above", "below").replace("bullish", "bearish")
    for c in result["candles"]:
        c["open"], c["close"] = 100 - c["open"], 100 - c["close"]
        c["low"], c["high"] = 100 - c["high"], 100 - c["low"]
    for mark in result.get("marks", []):
        mark["label"] = mark["label"].replace("− 0.25", "+ 0.25")
        if mark["kind"] == "level":
            mark["price"] = 100 - mark["price"]
        elif mark["kind"] == "band":
            mark["low"], mark["high"] = 100 - mark["high"], 100 - mark["low"]
    return result


def pattern(pid, title, description, bull: dict, direction=None):
    variants = [bull, mirror(bull)]
    if direction == "bullish":
        variants = variants[:1]
    elif direction == "bearish":
        variants = variants[1:]
    return {"id": pid, "title": title, "description": description, "variants": variants}


def setup(pullback: bool, retracement=False):
    if pullback:
        candles = [candle("x", "Doji", 25, 25),
                   candle("a1", "A1", 25, 32), candle("a2", "A2", 32, 39),
                   candle("a3", "A3", 39, 46), candle("b", "B", 46, 40),
                   candle("r", "R", 40, 60 if retracement else 50, 37, 63 if retracement else 52, "signal")]
        marks = [span("a1", "a3", "Earlier A length = 3"), span("b", "b", "Exactly one opposite B")]
    else:
        candles = [candle("x", "X", 58, 68),
                   candle("p1", "P1", 68, 60), candle("p2", "P2", 60, 52),
                   candle("p3", "P3", 52, 40),
                   candle("r", "R", 40, 60 if retracement else 50, 37, 63 if retracement else 52, "signal")]
        marks = [span("p1", "p3", "Preceding opposite leg = 3")]
    return candles, marks


def continuation_patterns(pullback: bool) -> list[dict]:
    candles, marks = setup(pullback)
    candles += [candle("f1", "F1", 50, 58, 47, 60, "measured"),
                candle("f2", "F2", 58, 66, 56, 68, "measured"),
                candle("breaker", "End", 66, 59, 57, 68, "termination")]
    marks += [span("r", "r", "Signal R · excluded from n"), span("f1", "f2", "Measured followers · n = 2")]
    v = {"id": "bullish", "title": "Bullish continuation example", "description":
         "F1 and F2 continue after bullish R: success at n=2. The observed opposite breaker fails n=3 and every larger horizon. A boundary before classification would be unknown.",
         "candles": candles, "marks": marks}
    title = "Earlier A → one B → resumption R" if pullback else "Opposite leg → reversal R → followers"
    desc = "Measure uninterrupted same-colour followers after R. R is excluded from n. "
    desc += "The earlier length filter measures A before B; B is one candle and is also excluded." if pullback else "The length filter measures the opposite leg immediately before R."
    return [pattern("sequence", title, desc, v),
            pattern("continuation-bullish", "Bullish followers after R", desc, v, "bullish"),
            pattern("continuation-bearish", "Bearish followers after R", desc, v, "bearish")]


def retracement_variant(pullback: bool, depth: int | None):
    candles, marks = setup(pullback, True)
    touch_price = 40 if depth is None else 60 - depth * .2
    candles += [candle("f1", "F1", 60, 68, touch_price, 70, "measured")]
    marks += [band("r", "r", 40, 60, "R body · open to close"),
              level("r", "f1", 60, "R.close · close beyond this")]
    depths = (25, 50, 75, 100) if depth is None else (depth,)
    for percent in depths:
        marks.append(level("r", "f1", 60 - percent * .2,
                           "100% · R.open" if percent == 100 else f"{percent}% body touch"))
    marks.append(span("f1", "f1", "Only immediate completed F1"))
    return {"id": "bullish", "title": "Bullish touch and favorable close",
            "description": "One successful example: F1 touches the level and closes strictly above R.close. A touched F1 can instead close at or behind R.close. Equality counts for touch, not favorable close. OHLC does not identify intrabar order.",
            "candles": candles, "marks": marks}


def retracement_patterns(pullback: bool):
    desc = "Measure the immediate next candle F1 against R's body, from R.close toward R.open. The 100% level is R.open, not the outer wick."
    # Overview has four body levels; keeping all eight marks fits the generic bound.
    top = retracement_variant(pullback, None)
    if pullback:
        top["marks"] = [m for m in top["marks"] if m.get("label") != "Exactly one opposite B"]
    result = [pattern("sequence", "F1 body retracement and recovery", desc, top)]
    for depth in (25, 50, 75, 100):
        for direction in ("bullish", "bearish"):
            result.append(pattern(f"retracement-{depth}-{direction}", f"{depth}% body level · {direction}", desc,
                                  retracement_variant(pullback, depth), direction))
    return result


def trend_patterns():
    candles = [candle("x", "Doji", 25, 25),
               candle("t1", "T1", 25, 32, role="measured"),
               candle("t2", "T2", 32, 39, role="measured"),
               candle("t3", "T3", 39, 46, role="measured"),
               candle("breaker", "End", 46, 40, role="termination"),
               candle("u1", "U1", 40, 47, role="context"),
               candle("u2", "U2", 47, 54, role="context")]
    v = {"id": "bullish", "title": "Bullish exact trend · three candles",
         "description": "T1–T3 have an observed start and opposite breaker: exact length 3, breaker excluded. A boundary follows completed U1/U2 with no completed breaker: observed length ≥2, exact length unknown. A missing start also causes censoring.",
         "candles": candles, "marks": [span("t1", "t3", "Measured exact length = 3"), span("u1", "u2", "Boundary-limited · observed ≥ 2")]}
    desc = "Count the entire consecutive same-colour completed leg. Exact length requires an observed start and completed opposite/doji end."
    return [pattern("sequence", "Whole trend length · exact and censored", desc, v)]


def payoff_variant(target=None, ambiguity=False):
    candles = [candle("x", "Doji", 25, 25), candle("a1", "A1", 25, 32), candle("a2", "A2", 32, 39), candle("a3", "A3", 39, 46),
               candle("b", "B", 46, 42, 41, 48), candle("r", "R", 42, 50, 40, 52, "signal")]
    if ambiguity:
        candles += [candle("f1", "F1", 50, 52, 39, 72, "measured")]
        end = "f1"
        caption = "F1 opens inside the bracket, then its low and high cross both stop and target. The order is unknown: lower −1R, upper target R. No intrabar path is drawn."
    else:
        candles += [candle("f1", "F1", 50, 55, 48, 56, "measured"),
                    candle("c2", "C2", 55, 53, 51, 57, "measured"),
                    candle("c3", "C3", 53, 53, 50, 55, "measured"),
                    candle("c10", "C10", 55, 58, 53, 59, "measured")]
        end = "c10"
        caption = "The physical-bar horizon starts at F1 and includes opposite/doji candles. C4–C9 are omitted schematically. If no bracket resolves in ten completed bars, use C10.close; an earlier unresolved barrier is unknown."
    marks = [span("a1", "a3", "Earlier A length = 3"),
             level("f1", end, 50, "Entry reference · F1.open"),
             level("b", end, 39.75, "Stop · B/R adverse extreme − 0.25")]
    for multiple in ((1, 2) if target is None else (target,)):
        marks.append(level("f1", end, 50 + 10.25 * multiple, f"{multiple}R target · separate scenario"))
    marks.append(span("f1", end, "Measured physical-bar payoff path"))
    if not ambiguity:
        marks.append(band("f1", end, 39.75, 50, "Risk · entry-to-stop distance"))
    return {"id": "bullish", "title": "Bullish gross OHLC bracket proxy",
            "description": caption, "candles": candles, "marks": marks}


def payoff_patterns():
    desc = "F1.open is a reference, not a verified fill. Stop is min(B.low,R.low)−0.25 for bullish, max(B.high,R.high)+0.25 for bearish. Targets 1R/2R are separate scenarios."
    result = [pattern("sequence", "Reference entry, structural stop and payoff path", desc, payoff_variant())]
    for target in (1, 2):
        for direction in ("bullish", "bearish", "all"):
            result.append(pattern(f"payoff-{target}r-{direction}", f"{target}R target · gross OHLC proxy", desc,
                                  payoff_variant(target), None if direction == "all" else direction))
    result.append(pattern("ambiguity", "One candle can touch both boundaries",
                          "The candle's open is checked first. If open is inside and both extrema touch, keep lower/upper bounds rather than infer order.", payoff_variant(ambiguity=True)))
    return result


def strip_explanations(report: dict) -> dict:
    """Exact preservation identity: no old content may change under these fields."""
    result = deepcopy(report)
    for key in ("id", "publishedAt", "patterns", "patternOverviewId"):
        result.pop(key, None)
    for section in result["sections"]:
        section.pop("patternId", None)
        section.pop("patternFocus", None)
    return result


def enrich(report: dict, analysis: str, published_at: str) -> dict:
    if "patterns" in report or "patternOverviewId" in report or any("patternId" in s for s in report["sections"]):
        raise ValueError("Source already has explanatory patterns")
    result = deepcopy(report)
    result["id"] += "-patterns-r1"
    result["publishedAt"] = published_at
    result["patternOverviewId"] = "sequence"
    pullback = analysis.startswith("pullback-")
    if analysis == "trend-length":
        patterns = trend_patterns()
    elif analysis.endswith("continuation"):
        patterns = continuation_patterns(pullback)
    elif analysis.endswith("retracement"):
        patterns = retracement_patterns(pullback)
    elif analysis.endswith("payoff"):
        patterns = payoff_patterns()
    else:
        raise ValueError("Unsupported explicitly selected analysis")
    for p in patterns:
        p["description"] += " " + ILLUSTRATIVE
    result["patterns"] = patterns
    for s in result["sections"]:
        if s["kind"] not in ("table", "metrics"):
            continue
        sid = s["id"]
        direction = "bullish" if sid.endswith("bullish") else "bearish" if sid.endswith("bearish") else "all"
        pid = "sequence"
        if sid == "coverage":
            focus = "This section measures sample and coverage, rather than a pattern's success. Exact, censored or unavailable outcomes retain their saved definitions."
            if analysis == "trend-length":
                focus = "Coverage counts available observations; boundary-limited U candles remain censored."
        elif analysis == "trend-length":
            if sid.startswith(("tails", "survival")):
                focus = "Share of exact T legs reaching each length. Censored U legs are not short failures."
            elif sid.startswith("distribution") or sid == "histogram":
                focus = "Count exact T legs of each length; exclude the breaker and censored U legs."
            else:
                focus = "Length summarizes the whole exact T leg. Boundary-limited U legs are censored."
        elif analysis.endswith("continuation"):
            pid = "continuation-" + direction if direction != "all" else "sequence"
            if sid.startswith("counts"):
                focus = "This section shows setup, known-follow-up and unknown-outcome populations. It does not condition the sample on the two successful followers drawn in the schematic."
            else:
                horizon = re.fullmatch(r"n(\d+)-(\d+)-(?:bullish|bearish)", sid)
                reach = f"n={horizon[1]}–{horizon[2]}" if horizon else "each stated n"
                focus = f"Measure {reach} additional uninterrupted followers after R; R is excluded. The drawing illustrates F1/F2 only; the same rule extends to every stated horizon. Opposite/doji is failure; an unresolved boundary is unknown."
                if pullback:
                    focus += " Earlier trend length measures A before the single opposite B."
        elif analysis.endswith("retracement"):
            depth = re.fullmatch(r"depth-(25|50|75|100)-(bullish|bearish)", sid)
            if depth:
                pid = f"retracement-{depth[1]}-{depth[2]}"
                focus = f"Measure only F1 at the {depth[1]}% level from R.close toward R.open. Touch is inclusive; favorable close is strictly beyond R.close. Touch/known F1, joint/known F1 and favorable/touched F1 use different denominators."
            else:
                focus = "Measure immediate F1 body touches at each stated depth and its close beyond R.close. Joint rates use known F1; conditional recovery rates use touched F1. R.open is the 100% body level."
            if pullback:
                focus += " Earlier trend length measures A before B, not B or R."
        else:
            target = re.fullmatch(r"target-([12])r-(bullish|bearish|all)", sid)
            if target:
                pid = f"payoff-{target[1]}r-{target[2]}"
                focus = f"This section measures the separate {target[1]}R target scenario from F1.open, over at most ten physical completed bars. Opposite/doji bars still count. Stop/target ambiguity contributes bounds; costs and actual fills are unmodeled."
            else:
                pid = "ambiguity"
                focus = "Compare separate 1R and 2R target scenarios from F1.open over ten physical bars. Opening crosses take precedence; same-bar dual touches retain bounds. An unresolved barrier is unknown; a complete unresolved path exits at C10.close."
        s["patternId"] = pid
        s["patternFocus"] = focus
    if strip_explanations(result) != strip_explanations(report):
        raise ValueError("Existing content changed during presentation enrichment")
    return result


def validate_patterns(report):
    ids = {p["id"] for p in report["patterns"]}
    if len(ids) != len(report["patterns"]) or len(ids) > 12 or report["patternOverviewId"] not in ids:
        raise ValueError("Invalid pattern identity")
    for p in report["patterns"]:
        if len(p["description"]) > 600 or not 1 <= len(p["variants"]) <= 2:
            raise ValueError("Pattern exceeds bounded explanatory contract")
        for v in p["variants"]:
            cs = v["candles"]
            if not 1 <= len(cs) <= 12 or len(v.get("marks", [])) > 8 or len(v["description"]) > 600:
                raise ValueError("Variant exceeds bounded explanatory contract")
            candle_ids = {c["id"] for c in cs}
            if len(candle_ids) != len(cs):
                raise ValueError("Duplicate candle identity")
            for c in cs:
                if not 0 <= c["low"] <= min(c["open"], c["close"]) <= max(c["open"], c["close"]) <= c["high"] <= 100:
                    raise ValueError("Invalid schematic OHLC order")
                if len(c["label"]) > 20:
                    raise ValueError("Candle label is too long")
            for m in v.get("marks", []):
                if m["startCandle"] not in candle_ids or m["endCandle"] not in candle_ids or len(m["label"]) > 48:
                    raise ValueError("Invalid schematic mark")
                if m["kind"] == "level" and not 0 <= m["price"] <= 100:
                    raise ValueError("Invalid schematic level")
                if m["kind"] == "band" and not 0 <= m["low"] <= m["high"] <= 100:
                    raise ValueError("Invalid schematic band")
    for s in report["sections"]:
        if s["kind"] in ("table", "metrics") and (s.get("patternId") not in ids or len(s.get("patternFocus", "")) > 500):
            raise ValueError("Every quantitative section needs bounded resolved explanatory context")


def selections():
    catalog = json.loads(safe_file("apps/narada/content/studies.json").read_text())
    mapping = json.loads(safe_file("apps/narada/content/release-sources.json").read_text())
    study = next(s for s in catalog["studies"] if s["studyId"] == STUDY_ID)
    by_id = {p["publicationId"]: p["revision"] for p in mapping["publications"]}
    if {a["id"] for a in study["analyses"]} != set(ANALYSES):
        raise ValueError("Current study does not contain the six explicitly supported analyses")
    result = []
    for analysis in study["analyses"]:
        if [t["label"] for t in analysis["publicationTabs"]] != ["4 RXV", "5 RXV", "6 RXV"]:
            raise ValueError("Selected chart settings differ")
        for tab in analysis["publicationTabs"]:
            pid = tab["publicationId"]
            result.append({"analysis": ANALYSES[analysis["id"]], "analysisId": analysis["id"],
                           "setting": int(tab["label"][0]), "publicationId": pid,
                           "sourceRunId": tab["sourceRunId"], "revision": by_id[pid]})
    return catalog, mapping, result


def prepare(stage: Path, published_at: str):
    stage = stage.absolute()
    if stage.parent != ROOT / "work" / STUDY_ID or stage.exists() or stage.is_symlink():
        raise ValueError("Prepare requires a fresh direct child of the study work directory")
    dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("Presentation time must identify UTC")
    catalog, mapping, selected = selections()
    prepared = []
    sources = {}
    cache = {}
    def verify_pin(pin):
        path = safe_file(pin["path"])
        actual = cache.setdefault(pin["path"], digest(path))
        if actual != pin["sha256"]:
            raise ValueError(f"Retained source pin changed: {pin['path']}")
        sources[pin["path"]] = record(path)
    for item in selected:
        revision = ROOT / item["revision"]
        manifest_path = safe_file(item["revision"] + "/manifest.json")
        manifest = json.loads(manifest_path.read_text())
        if manifest["publication_id"] != item["publicationId"] or manifest["source_run_id"] != item["sourceRunId"] or manifest["study_id"] != STUDY_ID:
            raise ValueError("Selected revision attribution differs")
        sources[manifest_path.relative_to(ROOT).as_posix()] = record(manifest_path)
        for pin in [*manifest["source_artifacts"], *manifest["outputs"]]:
            verify_pin(pin)
        old = json.loads((revision / "publication.json").read_text())
        public = json.loads(safe_file(f"apps/narada/public/publications/{item['publicationId']}/report.json").read_text())["report"]
        if old != public or old["source"]["runId"] != item["sourceRunId"]:
            raise ValueError("Selected saved report differs from the public selection")
        new = enrich(old, item["analysis"], published_at)
        validate_patterns(new)
        copied = {"source-map.json": (revision / "source-map.json").read_bytes()}
        for download in old.get("downloads", []):
            copied[download["path"]] = (revision / download["path"]).read_bytes()
        copied["inherited-verification.json"] = (revision / "verification.json").read_bytes()
        prepared.append((item, old, new, copied))
    stage.mkdir(parents=True, exist_ok=False)
    settings = {"version": VERSION, "published_at": published_at, "publication_suffix": "-patterns-r1",
                "selected": selected, "change": "Add schematic candle-pattern explanations only; retain every prior section value, source binding and selected CSV byte.",
                "numerical_analysis_executed": False}
    (stage / "settings.json").write_bytes(json_bytes(settings))
    (stage / "catalog-selection.json").write_bytes(json_bytes(catalog))
    (stage / "release-source-selection.json").write_bytes(json_bytes(mapping))
    (stage / "producer-source").mkdir()
    shutil.copyfile(Path(__file__).resolve(), stage / "producer-source/pattern_export.py")
    shutil.copyfile(safe_file("apps/narada/contracts/report.schema.json"), stage / "producer-source/report.schema.json")
    transfers = []
    for item, old, new, copied in prepared:
        folder = stage / new["id"]
        folder.mkdir()
        (folder / "publication.json").write_bytes(json_bytes(new))
        for name, content in copied.items():
            target = folder / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        transfer = {**item, "newPublicationId": new["id"], "report": record(folder / "publication.json"),
                    "original_content_identity": hashlib.sha256(json_bytes(strip_explanations(old))).hexdigest(),
                    "retained_content_identity": hashlib.sha256(json_bytes(strip_explanations(new))).hexdigest(),
                    "table_rows_preserved": sum(len(s["rows"]) for s in old["sections"] if s["kind"] == "table"),
                    "quantitative_sections": sum(s["kind"] in ("table", "metrics") for s in old["sections"]),
                    "assets": [record(folder / n) for n in copied], "result": "passed"}
        transfers.append(transfer)
    verification = {"result": "passed", "scope": "Exact previous report content after removing only additive pattern fields and changed publication id/time; unchanged source-map and download bytes. Not research revalidation.",
                    "reports": transfers, "source_artifacts": list(sources.values()),
                    "outputs": [record(p) for p in sorted(stage.rglob("*")) if p.is_file()]}
    (stage / "transfer-verification.json").write_bytes(json_bytes(verification))
    return verification


def verify_review(review: Path, transfer: Path):
    receipt = json.loads(review.read_text())
    if receipt.get("result") != "passed":
        raise ValueError("A passing independent presentation receipt is required")
    expected = digest(transfer)
    direct = receipt.get("transfer_verification_sha256") == expected
    inventory = receipt.get("artifact_hashes", {})
    bound = isinstance(inventory, dict) and any(
        (name == "transfer-verification.json" or name.endswith("/transfer-verification.json")) and value == expected
        for name, value in inventory.items())
    if not (direct or bound):
        raise ValueError("Independent receipt must bind the exact draft transfer verification")


def export(stage: Path, revision_prefix: str, review: Path, semantics_review: Path):
    component(revision_prefix)
    stage = stage.absolute()
    review = review.absolute()
    semantics_review = semantics_review.absolute()
    if stage.parent != ROOT / "work" / STUDY_ID or stage.is_symlink():
        raise ValueError("Export requires a contained study presentation stage")
    verification = json.loads((stage / "transfer-verification.json").read_text())
    settings = json.loads((stage / "settings.json").read_text())
    if verification["result"] != "passed":
        raise ValueError("Passing exact-transfer and independent presentation receipts are required")
    verify_review(review, stage / "transfer-verification.json")
    verify_review(semantics_review, stage / "transfer-verification.json")
    for pin in [*verification["source_artifacts"], *verification["outputs"]]:
        if digest(safe_file(pin["path"])) != pin["sha256"]:
            raise ValueError("Draft/source changed after verification")
    destinations = []
    for item in settings["selected"]:
        target = ROOT / "reports/exports" / STUDY_ID / item["sourceRunId"] / f"{revision_prefix}_{item['analysisId']}_{item['setting']}t"
        if target.exists() or target.is_symlink():
            raise FileExistsError("Presentation revision overwrite refused")
        destinations.append((item, target))
    results = []
    for item, target in destinations:
        new_id = item["publicationId"] + "-patterns-r1"
        source = stage / new_id
        target.mkdir(parents=True, exist_ok=False)
        for p in sorted(source.rglob("*")):
            if p.is_file():
                out = target / p.relative_to(source)
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(p, out)
        for name in ("settings.json", "catalog-selection.json", "release-source-selection.json", "transfer-verification.json"):
            shutil.copyfile(stage / name, target / name)
        shutil.copytree(stage / "producer-source", target / "producer-source")
        shutil.copyfile(review, target / "independent-presentation-verification.json")
        shutil.copyfile(semantics_review, target / "pattern-semantics-verification.json")
        receipt = {"result": "passed", "scope": "Presentation-only exact transfer and independent schematic review; no market calculation or research revalidation.",
                   "transfer_verification_sha256": digest(target / "transfer-verification.json"),
                   "independent_presentation_sha256": digest(target / "independent-presentation-verification.json"),
                   "pattern_semantics_sha256": digest(target / "pattern-semantics-verification.json"),
                   "publication_sha256": digest(target / "publication.json")}
        (target / "verification.json").write_bytes(json_bytes(receipt))
        outputs = [record(p) for p in sorted(target.rglob("*")) if p.is_file()]
        sources = verification["source_artifacts"]
        manifest = {"study_id": STUDY_ID, "source_run_id": item["sourceRunId"], "revision_id": target.name,
                    "publication_id": new_id, "created_at_utc": datetime.now(timezone.utc).isoformat(),
                    "renderer_version": VERSION, "template_version": "Narada explanatory candles v1",
                    "verification_result": "passed",
                    "change": settings["change"], "numerical_analysis_executed": False,
                    "command": ["python", "studies/22_es_range_xv_focused/pattern_export.py", "export", "--stage", str(stage.relative_to(ROOT)), "--revision-prefix", revision_prefix, "--review", str(review.relative_to(ROOT)), "--semantics-review", str(semantics_review.relative_to(ROOT))],
                    "source_artifacts": sources, "outputs": outputs,
                    "checks": {"original_report_content": "exactly preserved", "selected_csvs": "byte-identical", "source_map": "byte-identical", "independent_presentation_review": "passed"}}
        (target / "manifest.json").write_bytes(json_bytes(manifest))
        results.append({"publicationId": new_id, "revision": target.relative_to(ROOT).as_posix(),
                        "analysisId": item["analysisId"], "setting": item["setting"], "sourceRunId": item["sourceRunId"], "previousPublicationId": item["publicationId"]})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--stage", type=Path, required=True)
    prep.add_argument("--published-at", required=True)
    final = sub.add_parser("export")
    final.add_argument("--stage", type=Path, required=True)
    final.add_argument("--revision-prefix", required=True)
    final.add_argument("--review", type=Path, required=True)
    final.add_argument("--semantics-review", type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.stage, args.published_at) if args.action == "prepare" else export(args.stage, args.revision_prefix, args.review, args.semantics_review)
    print(json.dumps(result if args.action == "export" else {"result": result["result"], "reports": len(result["reports"])}, indent=2))


if __name__ == "__main__":
    main()
