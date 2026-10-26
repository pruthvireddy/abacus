"""Prepare immutable presentation revisions correcting the producer identity.

Only publication.id, publication.source.producer and source-map.publication_id
change. Statistics, prose, dates, chart inputs and asset bytes stay identical.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

SID = "25_forex_news_ema"
RUN = "20261017T193830Z_perfuture25_d2c74b"
SYMBOLS = ("6E", "6B", "6J", "6A", "6C", "6S")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)+"\n", encoding="utf-8")


def locations(root, symbol):
    old_id = f"forex-news-{symbol.lower()}-20261017-v2"
    new_id = old_id+"-r1"
    origin = root/"runs"/SID/RUN/"publications"/old_id
    revision_id = f"20261017T205500Z_attribution_{symbol.lower()}_r1"
    revision = root/"reports"/"exports"/SID/RUN/revision_id
    return old_id, new_id, origin, revision_id, revision


def selected_assets(report):
    return sorted({*[s["path"] for s in report["sections"] if s["kind"] == "figure"], *[d["path"] for d in report["downloads"]]})


def verify(root, symbol):
    old_id, new_id, origin, _, revision = locations(root, symbol)
    original, revised = load(origin/"publication.json"), load(revision/"publication.json")
    expected = copy.deepcopy(original)
    expected["id"], expected["source"]["producer"] = new_id, "sahadeva"
    require(revised == expected, "Publication changed beyond the two allowed attribution paths")
    require(original["id"] == old_id and original["source"]["runId"] == RUN, "Wrong original identity")
    original_map, revised_map = load(origin/"source-map.json"), load(revision/"source-map.json")
    expected_map = copy.deepcopy(original_map)
    expected_map["publication_id"] = new_id
    require(revised_map == expected_map, "Source map changed beyond publication identity")
    copied = [*selected_assets(original), "chart-spec.json", "figure-environment.json"]
    records = []
    for name in copied:
        require((origin/name).read_bytes() == (revision/name).read_bytes(), f"Copied bytes changed: {name}")
        records.append({"path": name, "sha256": sha(revision/name), "identical_to_source": True})
    inventory = load(revision/"provenance"/"source-inventory.json")
    for item in inventory:
        require(sha(root/item["path"]) == item["sha256"], "Pinned sealed source changed")
    require(sha(revision/"provenance"/"revise_attribution.py") == load(revision/"provenance"/"preparation.json")["producer_sha256"], "Frozen producer changed")
    return {"schema_version": "forex25-attribution-revision-checks/v1", "result": "passed", "status": "passed", "publication_id": new_id, "source_run_id": RUN,
            "publication_sha256": sha(revision/"publication.json"), "source_map_sha256": sha(revision/"source-map.json"),
            "allowed_report_changes": ["/id", "/source/producer"], "allowed_source_map_changes": ["/publication_id"],
            "checks": [{"name": "Report JSON equals sealed source except the two declared attribution paths", "passed": True},
                       {"name": "Source map equals sealed source except publication identity", "passed": True},
                       {"name": "All figures, downloads, chart inputs and figure environment are byte-identical", "passed": True},
                       {"name": "All retained source artifact pins and frozen revision producer agree", "passed": True}],
            "copied_files": records, "scope": "Metadata-only presentation integrity; no statistical, price, indicator or chart calculations were executed."}


def prepare(args):
    root = args.workspace_root.resolve()
    for symbol in SYMBOLS:
        old_id, new_id, origin, revision_id, revision = locations(root, symbol)
        require(not revision.exists(), f"Refusing to replace revision: {revision}")
        original = load(origin/"publication.json")
        old_manifest = load(origin/"publication-manifest.json")
        # Retain the exact revision producer and all consumed source identities
        # before writing any revised report or copied asset.
        provenance = revision/"provenance"
        provenance.mkdir(parents=True)
        shutil.copyfile(Path(__file__), provenance/"revise_attribution.py")
        sources = {item["path"]: item["sha256"] for item in old_manifest["source_artifacts"]}
        for path in [origin/"publication.json", origin/"source-map.json", origin/"publication-manifest.json", root/"runs"/SID/RUN/"manifest.json", *[origin/name for name in [*selected_assets(original), "chart-spec.json", "figure-environment.json"]]]:
            sources[path.relative_to(root).as_posix()] = sha(path)
        write(provenance/"source-inventory.json", [{"path": p, "sha256": digest} for p, digest in sorted(sources.items())])
        write(provenance/"preparation.json", {"schema_version": "forex25-attribution-preparation/v1", "study_id": SID, "source_run_id": RUN,
            "revision_id": revision_id, "original_publication_id": old_id, "publication_id": new_id, "producer_sha256": sha(provenance/"revise_attribution.py"),
            "command": [sys.executable, *sys.argv], "cwd": str(Path.cwd()), "python": sys.version,
            "changes": {"/id": new_id, "/source/producer": "sahadeva", "source-map.json/publication_id": new_id}, "numerical_results_changed": False})
        (revision/"README.md").write_text("# Producer attribution presentation revision\n\nThis metadata-only revision corrects the public producer token to `sahadeva`, as required by Narada's study-catalog attribution validator, and assigns a new immutable publication ID. The sealed run is unchanged. All statistics, report prose, dates, chart inputs, figures and selected CSV bytes retain their sealed source values. No research or chart calculation was run.\n\nThe source map changes only its publication identity. Frozen revision source and consumed source hashes were saved under provenance before revised output. verification.json records exact allowed-path and asset-byte comparisons; publisher and candidate-catalog receipts record their separate application gates.\n", encoding="utf-8")
        report = copy.deepcopy(original)
        report["id"], report["source"]["producer"] = new_id, "sahadeva"
        mapping = load(origin/"source-map.json")
        mapping["publication_id"] = new_id
        write(revision/"publication.json", report)
        write(revision/"source-map.json", mapping)
        for name in [*selected_assets(original), "chart-spec.json", "figure-environment.json"]:
            target = revision/name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(origin/name, target)
        write(revision/"verification.json", verify(root, symbol))
    validate_application(args)
    for symbol in SYMBOLS:
        _, new_id, _, revision_id, revision = locations(root, symbol)
        receipt = verify(root, symbol)
        receipt["checks"].extend([{"name": "Strict Narada publisher dry-run", "passed": True}, {"name": "Actual app study-catalog candidate with all six revised tabs", "passed": True}])
        write(revision/"verification.json", receipt)
        source_inventory = load(revision/"provenance"/"source-inventory.json")
        outputs = sorted(p for p in revision.rglob("*") if p.is_file() and p.name != "manifest.json")
        write(revision/"manifest.json", {"schema_version": "forex25-attribution-presentation/v1", "publication_id": new_id, "study_id": SID, "source_run_id": RUN,
            "revision_id": revision_id, "presentation_changes": "Only immutable publication identity and the canonical sahadeva producer token; all saved numerical content and asset bytes unchanged.",
            "source_artifacts": source_inventory, "outputs": [{"path": p.relative_to(root).as_posix(), "sha256": sha(p)} for p in outputs]})
    print(json.dumps({"status": "passed", "revisions": [{"publication_id": locations(root,s)[1], "path": locations(root,s)[4].relative_to(root).as_posix()} for s in SYMBOLS]}))


def validate_application(args):
    root = args.workspace_root.resolve()
    app = args.app.resolve()
    reports = []
    for symbol in SYMBOLS:
        _, new_id, _, _, revision = locations(root, symbol)
        command = [str(args.node), "scripts/publish.mjs", "--report", str(revision/"publication.json"), "--dry-run"]
        result = subprocess.run(command, cwd=app, capture_output=True, text=True)
        (revision/"publisher-dry-run.log").write_text(result.stdout+result.stderr, encoding="utf-8")
        require(result.returncode == 0, f"Publisher failed {new_id}; inspect {revision/'publisher-dry-run.log'}")
        write(revision/"publisher-verification.json", {"status": "passed", "result": "passed", "argv": command, "cwd": str(app), "exit_code": result.returncode, "publication_sha256": sha(revision/"publication.json")})
        reports.append(str(revision/"publication.json"))
    catalog = load(app/"content"/"studies.json")
    study = copy.deepcopy(next(s for s in catalog["studies"] if s["studyId"] == SID))
    study.pop("analyses", None)
    study.pop("phaseFamilies", None)
    study["featuredPublicationId"] = locations(root, "6E")[1]
    study["featuredSourceRunId"] = RUN
    study["publicationTabs"] = [{"publicationId": locations(root,s)[1], "sourceRunId": RUN, "label": s} for s in SYMBOLS]
    study["relatedPublications"] = [{"publicationId": "forex-news-ema-20261017-v1", "sourceRunId": "20261017T190030Z_import25_4b8a21", "relationship": "other-run", "label": "Earlier shared U.S. release sample"}]
    candidate = {"schemaVersion": catalog["schemaVersion"], "studies": [study]}
    old_report = root/"runs"/SID/"20261017T190030Z_import25_4b8a21"/"publication.json"
    reports.append(str(old_report))
    first_revision = locations(root, "6E")[4]
    write(first_revision/"catalog-candidate.json", candidate)
    js = "import fs from 'node:fs'; import {validateStudyCatalog} from './scripts/lib/studies.mjs'; const [catalog,...reports]=process.argv.slice(1); validateStudyCatalog(JSON.parse(fs.readFileSync(catalog)),reports.map(p=>JSON.parse(fs.readFileSync(p)))); console.log(JSON.stringify({status:'passed',result:'passed',scope:'Six revised contract tabs plus preserved earlier report; actual app validator',publications:reports.length}));"
    command = [str(args.node), "--input-type=module", "-e", js, str(first_revision/"catalog-candidate.json"), *reports]
    result = subprocess.run(command, cwd=app, capture_output=True, text=True)
    (first_revision/"catalog-validation.log").write_text(result.stdout+result.stderr, encoding="utf-8")
    require(result.returncode == 0, f"Candidate catalog failed; inspect {first_revision/'catalog-validation.log'}")
    for symbol in SYMBOLS:
        revision = locations(root, symbol)[4]
        if revision != first_revision:
            shutil.copyfile(first_revision/"catalog-candidate.json", revision/"catalog-candidate.json")
            shutil.copyfile(first_revision/"catalog-validation.log", revision/"catalog-validation.log")
        write(revision/"catalog-verification.json", {"status": "passed", "result": "passed", "argv": command, "cwd": str(app), "exit_code": 0,
            "candidate_sha256": sha(revision/"catalog-candidate.json"), "reports": [{"path": str(Path(p).relative_to(root)), "sha256": sha(Path(p))} for p in reports]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument("--app", type=Path, default=Path("apps/narada-per-future-staging"))
    parser.add_argument("--node", type=Path, default=Path("/Users/ppanati/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        for symbol in SYMBOLS:
            root = args.workspace_root.resolve()
            verify(root, symbol)
            revision = locations(root, symbol)[4]
            manifest = load(revision/"manifest.json")
            for output in manifest["outputs"]:
                require(sha(root/output["path"]) == output["sha256"], "Revision output pin changed")
        print(json.dumps({"status": "passed", "revisions": 6, "scope": "Exact allowed attribution changes, asset bytes, sealed-source hashes and output hashes"}))
    else:
        prepare(args)


if __name__ == "__main__":
    main()
