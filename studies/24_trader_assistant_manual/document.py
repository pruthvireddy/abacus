"""Package an authored qualitative companion; never fetch or calculate market data."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone

STUDY = Path(__file__).resolve().parent
ROOT = STUDY.parents[1]
STUDY_ID = STUDY.name
SOURCE = "https://willyalgotrader.pro/strategy/manual/"


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def pin(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def argv_record(argv):
    return {"argv": argv, "cwd": str(ROOT)}


def render(report, destination):
    esc = html.escape
    references = {item["id"]: item for item in report["references"]}
    toc, sections, markdown = [], [], [f"# {report['title']}", report["summary"]]
    for section in report["sections"]:
        title = esc(section["title"])
        toc.append(f'<li><a href="#{section["id"]}">{title}</a></li>')
        markdown.append(f"## {section['title']}")
        if section["kind"] == "text":
            body = "".join(f"<p>{esc(paragraph)}</p>" for paragraph in section["body"].split("\n\n"))
            markdown.append(section["body"])
        else:
            body = f'<figure><a href="{section["path"]}"><img src="{section["path"]}" alt="{esc(section["alt"])}" width="1400" height="850" loading="lazy"></a><figcaption>{esc(section["caption"])}</figcaption></figure>'
            markdown.append(f"![{section['alt']}]({section['path']})\n\n{section['caption']}")
        for reference_id in section.get("referenceIds", []):
            reference = references[reference_id]
            body += f'<p class="source"><a href="{esc(reference["url"])}" target="_blank" rel="noopener noreferrer">{esc(reference["label"])} ↗</a></p>'
            markdown.append(f"[{reference['label']}]({reference['url']})")
        sections.append(f'<section id="{section["id"]}"><h2>{title}</h2>{body}</section>')
    notes = "".join(f"<p>{esc(note)}</p>" for note in report["notes"])
    markdown.extend(["## Review notes", *report["notes"]])
    document = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(report['title'])} · Abacus</title><style>
:root{{color-scheme:light;--ink:#193447;--muted:#546c79;--line:#dce6e6;--teal:#117d78}}*{{box-sizing:border-box}}html{{scroll-behavior:smooth;scroll-padding-top:24px}}body{{margin:0;background:#f7faf9;color:var(--ink);font:17px/1.65 system-ui,-apple-system,sans-serif}}a{{color:var(--teal);text-underline-offset:4px}}a:focus-visible{{outline:3px solid #e6a348;outline-offset:5px}}header{{max-width:1140px;margin:auto;padding:56px 28px 28px}}.brand{{font-size:13px;letter-spacing:.14em;font-weight:700}}h1{{font-size:clamp(30px,4vw,48px);line-height:1.15;margin:16px 0}}header p{{max-width:720px;color:var(--muted)}}.layout{{display:grid;grid-template-columns:245px minmax(0,1fr);gap:48px;max-width:1140px;margin:0 auto;padding:0 28px 64px}}nav{{position:sticky;top:20px;align-self:start;font-size:14px;border-top:1px solid var(--line);padding-top:15px}}nav ol{{list-style:none;padding:0}}nav li{{margin:8px 0}}nav a{{text-decoration:none}}main{{min-width:0}}section{{border-top:1px solid var(--line);padding:26px 0}}h2{{font-size:23px;margin:0 0 12px}}p{{margin:12px 0}}.source{{font-size:14px}}figure{{margin:16px 0}}img{{display:block;width:100%;height:auto;border:1px solid var(--line);border-radius:12px;background:white}}figcaption{{color:var(--muted);font-size:14px;margin-top:12px}}aside{{border-top:1px solid var(--line);font-size:14px;color:var(--muted);padding-top:20px}}@media(max-width:760px){{header{{padding:30px 20px 20px}}.layout{{display:block;padding:0 20px 40px}}nav{{position:static;margin-bottom:24px}}nav ol{{columns:2;column-gap:20px}}nav li{{break-inside:avoid}}}}@media(prefers-reduced-motion:reduce){{html{{scroll-behavior:auto}}}}@media print{{nav{{display:none}}.layout{{display:block}}header{{padding-top:0}}section{{break-inside:avoid}}body{{background:white}}}}
</style></head><body><header><span class="brand">ABACUS / READING LIBRARY</span><h1>{esc(report['title'])}</h1><p>{esc(report['summary'])}</p></header><div class="layout"><nav aria-label="Chapter contents"><strong>CONTENTS</strong><ol>{''.join(toc)}</ol></nav><main>{''.join(sections)}<aside aria-label="Review notes">{notes}</aside></main></div></body></html>'''
    (destination / "report.html").write_text(document, encoding="utf-8")
    (destination / "report.md").write_text("\n\n".join(markdown) + "\n", encoding="utf-8")


def prepare(stage, run_id, publication_id):
    if (stage / "publication.json").exists():
        raise SystemExit("Refusing to replace an existing prepared publication.")
    stage.mkdir(parents=True, exist_ok=True)
    authored = read_json(STUDY / "companion.json")
    references = [{"id": "manual", "kind": "external", "label": "Read the full manual", "title": "Original manual", "creator": "Willy Collins", "url": SOURCE, "accessedOn": "2026-10-13"}]
    for index in range(13):
        references.append({"id": "updates" if index == 0 else f"chapter-{index}", "kind": "external", "label": "Read original update" if index == 0 else f"Read original chapter {index:02}", "title": "Original manual", "creator": "Willy Collins", "url": f"{SOURCE}#ch-{index}", "accessedOn": "2026-10-13"})
    report = {"schemaVersion": "1.1", "id": publication_id, "title": authored["title"], "summary": authored["summary"], "publishedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "source": {"producer": "sahadeva", "runId": run_id}, "sections": authored["sections"], "references": references, "notes": authored["notes"]}
    for section in report["sections"]:
        if section["kind"] == "figure" and not (stage / section["path"]).is_file():
            raise SystemExit(f"Missing authored image: {section['path']}")
    write_json(stage / "publication.json", report)
    render(report, stage)
    for name in ["companion.json", "source-observations.json", "inputs.lock.json", "study.yaml", "plan.md"]:
        shutil.copyfile(STUDY / name, stage / name)
    source = stage / "source"
    source.mkdir()
    for name in ["document.py", "illustrate.py", "companion.json", "source-observations.json"]:
        shutil.copyfile(STUDY / name, source / name)
    shutil.copyfile(ROOT / "apps/narada/package-lock.json", stage / "package-lock.json")
    shutil.copyfile(ROOT / "uv.lock", stage / "uv.lock")
    status = subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True)
    (stage / "code-status.txt").write_text(status, encoding="utf-8")
    write_json(stage / "config.json", {"reviewed_on": "2026-10-13", "review_timezone": "America/New_York", "prepared_at": report["publishedAt"], "market_data_analysis": False, "source_reproduction": False, "source_bytes_retained": False, "publication_id": publication_id, "content_scope": "Concise authored chapter orientation, external references and original educational illustrations."})
    write_json(stage / "source-map.json", {"schema_version": "manual24-qualitative-source-map-1", "study_id": STUDY_ID, "run_id": run_id, "publication_id": publication_id, "authored_source": "companion.json", "sections": [{"id": section["id"], "source": "companion.json", "external_reference_ids": section.get("referenceIds", []), "kind": "original_illustration" if section["kind"] == "figure" else "authored_companion"} for section in report["sections"]], "limitations": "No empirical cells, fills or market statistics. Live manual bytes are unavailable and unpinned."})
    write_json(stage / "commands.json", [argv_record([sys.executable, *sys.argv])])
    print(f"Prepared {stage.relative_to(ROOT)}")


def finalize(stage, run_id):
    if (stage / "manifest.json").exists():
        raise SystemExit("Refusing to replace an existing finalized manifest.")
    report = read_json(stage / "publication.json")
    if report["source"]["runId"] != run_id:
        raise SystemExit("Run identity mismatch.")
    expected = {f"chapter-{index}" for index in range(1, 13)}
    actual = {section["id"] for section in report["sections"] if section["id"].startswith("chapter-")}
    if actual != expected or "updates" not in {section["id"] for section in report["sections"]}:
        raise SystemExit("Incomplete chapter/update coverage.")
    for section in report["sections"]:
        if section["kind"] == "figure":
            data = (stage / section["path"]).read_bytes()
            if not data.startswith(b"\x89PNG\r\n\x1a\n") or len(data) > 150 * 1024:
                raise SystemExit("Figure fails PNG/lightweight budget.")
    result = subprocess.run(["node", "scripts/publish.mjs", "--report", str(stage / "publication.json"), "--dry-run"], cwd=ROOT / "apps/narada", text=True, capture_output=True)
    (stage / "publisher-dry-run.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        raise SystemExit(result.stderr)
    write_json(stage / "publication-verification.json", {"schema_version": "manual24-publication-checks-1", "result": "passed", "scope": "Original local companion coverage, PNG budgets and Narada source contract dry run; not live source bytes or empirical validation.", "checks": [{"name": "chapter and update coverage", "passed": True}, {"name": "three original PNGs within 150 KiB each", "passed": True}, {"name": "Narada source contract dry run", "passed": True}], "publication_sha256": pin(stage / "publication.json")["sha256"], "source_map_sha256": pin(stage / "source-map.json")["sha256"]})
    commands = read_json(stage / "commands.json")
    commands.extend([argv_record([sys.executable, *sys.argv]), {"argv": result.args, "cwd": str(ROOT / "apps/narada")}])
    write_json(stage / "commands.json", commands)
    write_json(stage / "checks.json", [{"name": "companion publication verification", "status": "passed", "record": "publication-verification.json"}, {"name": "live source byte identity", "status": "not_run", "reason": "Full source text and source images were deliberately not retained; no source byte authentication."}, {"name": "market research", "status": "not_applicable", "reason": "Qualitative source orientation only; no market statistics or strategy implementation."}])
    locator = f"runs/{STUDY_ID}/{run_id}"
    names = ["publication.json", "source-map.json", "publication-verification.json", *[section["path"] for section in report["sections"] if section["kind"] == "figure"]]
    write_json(stage / "publication-manifest.json", {"study_id": STUDY_ID, "source_run_id": run_id, "publication_id": report["id"], "source_artifacts": [{"path": f"{locator}/companion.json", **pin(stage / "companion.json")}], "outputs": [{"path": f"{locator}/{name}", **pin(stage / name)} for name in names]})
    files = sorted(path for path in stage.rglob("*") if path.is_file() and path.name != "manifest.json")
    write_json(stage / "manifest.json", {"contract": "abacus.evidence/v1", "bundle_kind": "research", "study_id": STUDY_ID, "run_id": run_id, "inventory_scope": "declared_artifacts", "results": {"kind": "qualitative", "state": "not_computed", "artifacts": ["companion.json", "source-observations.json"], "reason": "Authored external-source reading companion; no market statistics were computed."}, "provenance": {"settings": "config.json", "input_lock": "inputs.lock.json", "exclusions": {"state": "not_applicable", "reason": "No numerical sample; copied full text and source screenshots excluded by scope."}, "commands": "commands.json", "checks": "checks.json", "environment_lock": "package-lock.json", "code": {"revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "dirty": bool((stage / "code-status.txt").read_text()), "status": "code-status.txt", "source_snapshot": {"paths": ["source/document.py", "source/illustrate.py", "source/companion.json", "source/source-observations.json"], "scope": "Exact authored companion, observation metadata and offline generation code. No full live-source snapshot or claim authentication."}}}, "artifacts": [{"path": path.relative_to(stage).as_posix(), **pin(path)} for path in files]})
    verify(stage)
    print("Finalized and verified declared authored artifacts.")


def verify(bundle):
    result = subprocess.run([sys.executable, str(ROOT / "scripts/check-evidence-bundle.py"), str(bundle)], cwd=ROOT)
    if result.returncode:
        raise SystemExit(result.returncode)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "finalize", "seal", "verify"])
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--publication-id", default="trader-assistant-manual-20261013-companion-v1")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.run_id):
        parser.error("run ID must be a single safe segment")
    stage = ROOT / "work" / STUDY_ID / args.run_id
    destination = ROOT / "runs" / STUDY_ID / args.run_id
    if args.command == "prepare":
        prepare(stage, args.run_id, args.publication_id)
    elif args.command == "finalize":
        finalize(stage, args.run_id)
    elif args.command == "verify":
        verify(destination if destination.exists() else stage)
    else:
        if destination.exists():
            raise SystemExit("Refusing to overwrite a sealed run.")
        verify(stage)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(stage, destination)
        verify(destination)
        print(f"Sealed {destination.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
