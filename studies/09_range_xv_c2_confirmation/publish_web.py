"""Presentation-only exporter for 09_range_xv_c2_confirmation; no analytical imports."""

import argparse
import hashlib
import json
from pathlib import Path
import re

from abacus_sahadeva import presentation_revision, saved_evidence


SPEC = {
    "study_id": "09_range_xv_c2_confirmation",
    "source_run_id": "20260924T141810Z_c2confirm_v1",
    "publication_id": "09-range-xv-c2-confirmation-20261006-web",
    "title": "Second-candle confirmation: colour lift and price disagree",
    "summary": "Some confirmed cohorts beat ordinary two-bar baselines, but waiting does not improve signed chart-price means. Confirmed samples and original opportunities have different denominators.",
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
            "body": "Does waiting for C2 to confirm a countertrend C1 improve the next two-bar follow-through? This uses the corrected-prose reference run on seven Range XV chart settings. Primary C1 follows at least three opposing candles; confirmation is observed at C2 completion.",
            "source": "report.md",
            "anchor": "Question and scope"
        },
        {
            "kind": "text",
            "id": "findings",
            "title": "Supported findings",
            "body": "Selected GC and bearish NQ 10 cells show colour-rate improvement versus ordinary two-bar baselines. Yet the common-opportunity wait-minus-immediate price contrast is mostly negative and the saved wait means are negative throughout. The age-two follow-up is post-result exploratory and is excluded from this concise primary presentation.",
            "source": "report.md",
            "anchor": "Supported findings"
        },
        {
            "kind": "table",
            "id": "confirmed",
            "title": "Confirmed two-more-bar cohorts versus ordinary controls",
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
                        "label": "C3+C4 successes",
                        "format": "number",
                        "precision": 0
                    },
                    "scale": 1
                },
                {
                    "column": {
                        "key": "denominator",
                        "label": "Confirmed eligible n",
                        "format": "number",
                        "precision": 0
                    },
                    "scale": 1
                },
                {
                    "column": {
                        "key": "probability",
                        "label": "Confirmed rate",
                        "format": "percent",
                        "precision": 1
                    },
                    "scale": 1
                },
                {
                    "column": {
                        "key": "baseline_denominator",
                        "label": "Ordinary eligible n",
                        "format": "number",
                        "precision": 0
                    },
                    "scale": 1
                },
                {
                    "column": {
                        "key": "baseline_probability",
                        "label": "Ordinary rate",
                        "format": "percent",
                        "precision": 1
                    },
                    "scale": 1
                },
                {
                    "column": {
                        "key": "difference_pp",
                        "label": "Rate difference",
                        "format": "number",
                        "precision": 2,
                        "unit": "pp"
                    },
                    "scale": 1
                },
                {
                    "column": {
                        "key": "family_ci_low_pp",
                        "label": "Familywise low",
                        "format": "number",
                        "precision": 2,
                        "unit": "pp"
                    },
                    "scale": 1
                },
                {
                    "column": {
                        "key": "family_ci_high_pp",
                        "label": "Familywise high",
                        "format": "number",
                        "precision": 2,
                        "unit": "pp"
                    },
                    "scale": 1
                }
            ],
            "where": {
                "metric": [
                    "next2"
                ]
            },
            "description": "All saved rows"
        },
        {
            "kind": "table",
            "id": "common-opportunity",
            "title": "Policies on original C1 opportunities",
            "file": "tables/opportunity_overall.csv",
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
                        "key": "metric",
                        "label": "Policy outcome"
                    },
                    "scale": 1
                },
                {
                    "column": {
                        "key": "numerator",
                        "label": "numerator",
                        "format": "number",
                        "precision": 0
                    },
                    "scale": 1
                },
                {
                    "column": {
                        "key": "denominator",
                        "label": "Eligible C1 n",
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
                    "immediate_two_per_c1",
                    "wait_two_per_c1"
                ]
            },
            "description": "Both policies, all seven settings and directions; shifted horizon definitions retained"
        },
        {
            "kind": "table",
            "id": "price",
            "title": "Wait minus immediate: common-opportunity price contrast",
            "file": "tables/price_delta.csv",
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
                        "key": "events",
                        "label": "Eligible C1 n",
                        "format": "number",
                        "precision": 0
                    },
                    "scale": 1
                },
                {
                    "column": {
                        "key": "mean_signed_ticks",
                        "label": "Mean difference",
                        "format": "number",
                        "precision": 2,
                        "unit": "ticks"
                    },
                    "scale": 1
                },
                {
                    "column": {
                        "key": "mean_ci_low",
                        "label": "95% low",
                        "format": "number",
                        "precision": 2,
                        "unit": "ticks"
                    },
                    "scale": 1
                },
                {
                    "column": {
                        "key": "mean_ci_high",
                        "label": "95% high",
                        "format": "number",
                        "precision": 2,
                        "unit": "ticks"
                    },
                    "scale": 1
                }
            ],
            "where": {},
            "description": "All saved rows"
        },
        {
            "kind": "text",
            "id": "methods",
            "title": "Definitions and methods",
            "body": "Confirmed next2 requires C3 and C4 to close in C1 direction after C2 confirms. Its denominator is eligible confirmed C2 events. Ordinary controls begin after a same-direction B1/B2 pair, excluding main candidates. Common-opportunity immediate_two_per_c1 requires C2+C3; wait_two_per_c1 requires confirmation plus C3+C4. Thus these policies use shifted physical horizons. Nonconfirmation contributes zero signed price movement to the wait policy, not an observed trade loss. Price references use next-bar opens and fixed exits. Saved 95% intervals are session-cluster; the colour contrast table retains its familywise bounds in percentage points.",
            "source": "source-snapshot/plan.md",
            "anchor": "Definitions and methods"
        },
        {
            "kind": "text",
            "id": "limitations",
            "title": "Limitations and uncertainty",
            "body": "Bars with duplicate clocks or incomplete/boundary futures are excluded; inferred clocks and completion proxies do not verify live entry. Chart settings and screened cells are dependent. A fifty-percent colour benchmark is not a profitability baseline. Costs, spreads, fill latency and same-bar stop ordering are unverified. Waiting may condition on subsequent success rather than create an executable advantage.",
            "source": "report.md",
            "anchor": "Limitations and uncertainty"
        }
    ]
}

EXPECTED = {
    "runs/09_range_xv_c2_confirmation/20260924T141810Z_c2confirm_v1/report.md": "b7e945549a4f8ffe014b8491679746271d2f82b86d5072a248155a96e2c1bf32",
    "runs/09_range_xv_c2_confirmation/20260924T141810Z_c2confirm_v1/manifest.json": "bd44c0ed937f0c23065f9241f13c0467c87118d983bd5ec826eb7e288177c00b",
    "runs/09_range_xv_c2_confirmation/20260924T141810Z_c2confirm_v1/tables/price_delta.csv": "1f36555bc6c8aed8071990f6130c3585f0a27a4a603f9965f41547bfd66fc9ec",
    "runs/09_range_xv_c2_confirmation/20260924T141810Z_c2confirm_v1/inputs.lock.json": "54b28368ba02b9a74b367ba0d46cd6896127f081433dce2bcec1b7ebd6e42ae3",
    "runs/09_range_xv_c2_confirmation/20260924T141810Z_c2confirm_v1/source-snapshot/plan.md": "7d423c5480c70ca73ec7f2e1eb3302ef4af8d5c639c6f42ee92723c8fbc818ac",
    "runs/09_range_xv_c2_confirmation/20260924T141810Z_c2confirm_v1/tables/overall.csv": "797583e3cc00dcc4eefc060f11dce1b59d698ce87defcd1c3cafa7fb7ddc7952",
    "runs/09_range_xv_c2_confirmation/20260924T141810Z_c2confirm_v1/config.json": "db7529145b1cf240b0ffdaf89d9694e15240949675e27ab6d373db55df494dd5",
    "runs/09_range_xv_c2_confirmation/20260924T141810Z_c2confirm_v1/metrics.json": "4cbc75e3df28c5c75583b358730229d9764bdf11b947ae58859a34f7a35d582b",
    "runs/09_range_xv_c2_confirmation/20260924T141810Z_c2confirm_v1/tables/opportunity_overall.csv": "2dc4bb66eae151630a05fabfda82f086395d59b502bc73fb4da07d4ea0acf72f"
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
