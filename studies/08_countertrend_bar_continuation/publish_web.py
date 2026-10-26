"""Presentation-only exporter for 08_countertrend_bar_continuation; no analytical imports."""

import argparse
import hashlib
import json
from pathlib import Path
import re

from abacus_sahadeva import presentation_revision, saved_evidence


SPEC = {
    "study_id": "08_countertrend_bar_continuation",
    "source_run_id": "20260924T132916Z_ctbars_v1",
    "publication_id": "08-countertrend-bar-continuation-20261006-web-r2",
    "title": "Countertrend reversals: bar persistence is not an edge",
    "summary": "Across seven ES/GC/NQ Range XV settings, the frozen two-more-bar screen finds no supported positive lift above its chart/direction/window baseline. Chart colour continuation is descriptive, not a payoff test.",
    "selection": "Registered reference",
    "reason": "Explicit registered reference; retain its executed scope and saved qualifications.",
    "sources": [
        "report.md",
        "config.json",
        "manifest.json",
        "inputs.lock.json",
        "metrics.json",
        "source-snapshot/plan.md"
    ],
    "sections": [
        {
            "kind": "text",
            "id": "question",
            "title": "Question and scope",
            "body": "After the first countertrend reversal C1, how often do the next two candles C2 and C3 continue its new direction? Seven chart settings span November 2019–September 2026, with incomplete paths excluded. The main prior-run cuts and clock windows are retained in the saved full screen; this concise table shows each chart/direction overall cohort.",
            "source": "report.md",
            "anchor": "Question and scope"
        },
        {
            "kind": "text",
            "id": "findings",
            "title": "Supported findings",
            "body": "No frozen primary comparison passes the positive familywise screen. A next-bar continuation can be common while two additional same-direction bars are much less common. Failures and dojis remain in eligible denominators; high bar-colour persistence does not establish profitable entry or exit.",
            "source": "report.md",
            "anchor": "Supported findings"
        },
        {
            "kind": "table",
            "id": "two-more",
            "title": "Two additional candles in the new direction",
            "file": "tables/overall.csv",
            "columns": [
                {
                    "column": {
                        "key": "product",
                        "label": "product"
                    },
                    "scale": 1
                },
                {
                    "column": {
                        "key": "setting",
                        "label": "Range XV setting",
                        "format": "number",
                        "precision": 0
                    },
                    "scale": 1
                },
                {
                    "column": {
                        "key": "direction",
                        "label": "Direction (1 bullish, −1 bearish)"
                    },
                    "scale": 1
                },
                {
                    "column": {
                        "key": "numerator",
                        "label": "Both candles succeed",
                        "format": "number",
                        "precision": 0
                    },
                    "scale": 1
                },
                {
                    "column": {
                        "key": "denominator",
                        "label": "Eligible C1 opportunities",
                        "format": "number",
                        "precision": 0
                    },
                    "scale": 1
                },
                {
                    "column": {
                        "key": "session_dates",
                        "label": "Session dates",
                        "format": "number",
                        "precision": 0
                    },
                    "scale": 1
                },
                {
                    "column": {
                        "key": "probability",
                        "label": "probability",
                        "format": "percent",
                        "precision": 1
                    },
                    "scale": 1
                },
                {
                    "column": {
                        "key": "ci_low",
                        "label": "95% low",
                        "format": "percent",
                        "precision": 1
                    },
                    "scale": 1
                },
                {
                    "column": {
                        "key": "ci_high",
                        "label": "95% high",
                        "format": "percent",
                        "precision": 1
                    },
                    "scale": 1
                }
            ],
            "where": {
                "metric": [
                    "p2"
                ]
            },
            "description": "Overall all-prior-run rows, both directions on all seven settings"
        },
        {
            "kind": "table",
            "id": "one-more",
            "title": "One additional candle: a different outcome",
            "file": "tables/overall.csv",
            "columns": [
                {
                    "column": {
                        "key": "product",
                        "label": "product"
                    },
                    "scale": 1
                },
                {
                    "column": {
                        "key": "setting",
                        "label": "setting",
                        "format": "number",
                        "precision": 0
                    },
                    "scale": 1
                },
                {
                    "column": {
                        "key": "direction",
                        "label": "Direction (1 bullish, −1 bearish)"
                    },
                    "scale": 1
                },
                {
                    "column": {
                        "key": "numerator",
                        "label": "C2 succeeds",
                        "format": "number",
                        "precision": 0
                    },
                    "scale": 1
                },
                {
                    "column": {
                        "key": "denominator",
                        "label": "Eligible C1 opportunities",
                        "format": "number",
                        "precision": 0
                    },
                    "scale": 1
                },
                {
                    "column": {
                        "key": "probability",
                        "label": "probability",
                        "format": "percent",
                        "precision": 1
                    },
                    "scale": 1
                },
                {
                    "column": {
                        "key": "ci_low",
                        "label": "95% low",
                        "format": "percent",
                        "precision": 1
                    },
                    "scale": 1
                },
                {
                    "column": {
                        "key": "ci_high",
                        "label": "95% high",
                        "format": "percent",
                        "precision": 1
                    },
                    "scale": 1
                }
            ],
            "where": {
                "metric": [
                    "p1"
                ]
            },
            "description": "All saved rows"
        },
        {
            "kind": "text",
            "id": "methods",
            "title": "Definitions and methods",
            "body": "C1 is the first non-doji reversal after an opposing run. Overall rows below use all eligible prior-run lengths, while the frozen main screen also imposes at least three prior bars and specified clock windows. p2 means both C2 and C3 close in C1 direction; p1 means C2 alone does. Dojis fail these colour tests. Strict eligibility requires original adjacent bars and next-bar-start completion proxies within the segment. Ratios use the displayed eligible opportunities, not sessions. Saved table intervals are 95% session-cluster bounds; primary inference separately uses a Bonferroni family over 210 comparisons against all-prior-run rates on the same chart, direction and clock window.",
            "source": "source-snapshot/plan.md",
            "anchor": "Definitions and methods"
        },
        {
            "kind": "text",
            "id": "limitations",
            "title": "Limitations and uncertainty",
            "body": "The seven settings share price streams and are correlated. Completeness and exceptional GC-day exclusions are retrospective; absent dates are not filled. Corrected inferred New York wall clocks remain inferred; completion and intrabar execution are unverified. This tests price-event bar behaviour without costs, fills, stops or net profitability.",
            "source": "report.md",
            "anchor": "Limitations and uncertainty"
        }
    ]
}

EXPECTED = {
    "runs/08_countertrend_bar_continuation/20260924T132916Z_ctbars_v1/report.md": "f7b3132a1173fc9651dbd12a98500fda2b9d11288007935b1fcab234024b4c89",
    "runs/08_countertrend_bar_continuation/20260924T132916Z_ctbars_v1/manifest.json": "f6ca2f3042c3320bc5a44a324b4014e4138ad72d6e0ca68e8d587b1c4e9963bd",
    "runs/08_countertrend_bar_continuation/20260924T132916Z_ctbars_v1/inputs.lock.json": "54b28368ba02b9a74b367ba0d46cd6896127f081433dce2bcec1b7ebd6e42ae3",
    "runs/08_countertrend_bar_continuation/20260924T132916Z_ctbars_v1/source-snapshot/plan.md": "aae96bde07854cfec80e60c73d06a3bb2972ed024bd36781472f420def5dabff",
    "runs/08_countertrend_bar_continuation/20260924T132916Z_ctbars_v1/tables/overall.csv": "cd68e930ff507285d3fa2d67ccab8431b3afd704f8cadbb1bef1ea5e478c2588",
    "runs/08_countertrend_bar_continuation/20260924T132916Z_ctbars_v1/config.json": "9283a1fb480bb28a74997aae8ae48b79ea6a9412fa9b3a5988002f5bf4512737",
    "runs/08_countertrend_bar_continuation/20260924T132916Z_ctbars_v1/metrics.json": "c30d49cf5e3ace58c71a04ef9b9e629d9875ad2f734e0b7043914eb64984ac37"
}

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _claim(run, item):
    source = run / item["source"]
    headings = [
        line.lstrip("#").strip()
        for line in source.read_text().splitlines()
        if line.startswith("#")
    ]
    return {
        "section": item["id"],
        "source": str(source.relative_to(ROOT)),
        "heading_or_scope": {
            "scope": "Selected saved document; authored abridgment",
            "headings": headings,
        },
        "operation": (
            "Authored abridgment preserving the saved meaning; definitions and "
            "result numbers are not recomputed."
        ),
    }


def _table_section(run, item):
    source = run / item["file"]
    rows, bindings = saved_evidence.project_table(
        source,
        columns=item["columns"],
        where=item["where"],
        section=item["id"],
        source=str(source.relative_to(ROOT)),
    )
    section = {
        "kind": "table",
        "id": item["id"],
        "title": item["title"],
        "columns": [field["column"] for field in item["columns"]],
        "rows": rows,
    }
    return section, bindings


def _pinned_sources(run, sources):
    artifacts = []
    for name in sorted(sources):
        source = run / name
        relative = str(source.relative_to(ROOT))
        actual = digest(source)
        if actual != EXPECTED[relative]:
            raise ValueError(f"Source hash mismatch: {relative}")
        artifacts.append({"path": relative, "sha256": actual})
    return artifacts


def prepare(revision):
    run = ROOT / "runs" / SPEC["study_id"] / SPEC["source_run_id"]
    bindings = []
    sections = []
    sources = set(SPEC["sources"])
    claims = []
    for item in SPEC["sections"]:
        if item["kind"] == "text":
            sections.append({key: item[key] for key in ["kind", "id", "title", "body"]})
            sources.add(item["source"])
            claims.append(_claim(run, item))
        else:
            sources.add(item["file"])
            section, table_bindings = _table_section(run, item)
            bindings.extend(table_bindings)
            sections.append(section)

    provenance = (
        f"Study {SPEC['study_id']}; source run {SPEC['source_run_id']}. "
        f"{SPEC['selection']}: {SPEC['reason']}\n\n"
        f"Presentation revision {revision}, web-study-report-1.0. Saved numerical "
        "tables are the authority; only selected rows and columns are presented. "
        "No new statistics or research execution. The publication record identifies "
        "this JSON and its selected assets."
    )
    sections.append({
        "kind": "text",
        "id": "sources-provenance",
        "title": "Source and presentation provenance",
        "body": provenance,
    })
    publication = {
        "schemaVersion": "1.0",
        "id": SPEC["publication_id"],
        "title": SPEC["title"],
        "summary": SPEC["summary"],
        "publishedAt": "2026-10-06T23:09:36Z",
        "source": {"producer": "sahadeva", "runId": SPEC["source_run_id"]},
        "sections": sections,
    }
    mapping = {
        "study_id": SPEC["study_id"],
        "source_run_id": SPEC["source_run_id"],
        "revision_id": revision,
        "sources": _pinned_sources(run, sources),
        "bindings": bindings,
        "claims": claims,
        "table_selections": [
            {
                "section": item["id"],
                "source": item["file"],
                "where": item["where"],
                "description": item["description"],
            }
            for item in SPEC["sections"]
            if item["kind"] == "table"
        ],
        "figures": [],
    }
    return publication, mapping


def _json_bytes(value):
    return (
        json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")


def _producer_sources():
    return [
        ("provenance/publish_web.py", Path(__file__).read_bytes()),
        ("provenance/saved_evidence.py", Path(saved_evidence.__file__).read_bytes()),
        ("provenance/presentation_revision.py", Path(presentation_revision.__file__).read_bytes()),
    ]


def _readme():
    return (
        f"# {SPEC['title']}\n\n"
        "[Publication](publication.json) · [Source map](source-map.json) · "
        "[Manifest](manifest.json) · [Verification](verification.json)\n\n"
        f"{SPEC['selection']}: {SPEC['reason']}\n\n"
        "Bounded table-first presentation. Full tables and research figures remain "
        "in the saved run. No new calculations. Reproduce into a fresh revision "
        "and use a fresh publication ID for changed content.\n"
    )


def _check_revision(output, publication, mapping):
    if json.loads((output / "publication.json").read_text()) != publication:
        raise ValueError(f"Publication mismatch: {output / 'publication.json'}")
    if json.loads((output / "source-map.json").read_text()) != mapping:
        raise ValueError(f"Source-map mismatch: {output / 'source-map.json'}")
    print(
        f"{SPEC['study_id']}: {len(mapping['bindings'])} "
        "saved-cell transfers and source hashes match."
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Presentation only: select pinned saved evidence; never execute research."
    )
    parser.add_argument("--revision", required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.revision):
        raise ValueError(f"Invalid revision identifier: {args.revision!r}")
    output = (
        ROOT / "reports/exports" / SPEC["study_id"] / SPEC["source_run_id"] / args.revision
    )
    publication, mapping = prepare(args.revision)
    if args.check:
        _check_revision(output, publication, mapping)
    else:
        publication_bytes = _json_bytes(publication)
        source_map_bytes = _json_bytes(mapping)
        producer_sources = _producer_sources()
        readme_text = _readme()
        presentation_revision.write_revision(
            output,
            publication_bytes=publication_bytes,
            source_map_bytes=source_map_bytes,
            readme_text=readme_text,
            producer_sources=producer_sources,
        )
        print(output.relative_to(ROOT))


if __name__ == "__main__":
    main()
