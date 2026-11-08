#!/usr/bin/env python3
"""Prepare and seal a verified, private Daily Map navigation bundle.

The retained source reader stays in its explicit work stage. This utility saves
only navigation, inventories, the supplied report and verification records, and
producer/environment snapshots in a fresh completed run. It never crawls sources,
rebuilds the reader, modifies a dataset or replaces an existing bundle/run.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shlex
import shutil
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit, urlunsplit


STUDY_ID = "27_verniman_method_knowledge"
SCHEMA = "daily-map-source-review-1"
ROOT = Path(__file__).resolve().parents[2]
NAVIGATION = Path("knowledge-base/daily-map")
MARKDOWN_LINK = re.compile(r"(?P<prefix>!?\[[^\]\n]*\]\()(?P<target><[^>]+>|[^)\s]+)(?P<suffix>\))")


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def identity(path: Path, *, relative_to: Path) -> dict:
    raw = path.read_bytes()
    return {"path": path.relative_to(relative_to).as_posix(), "bytes": len(raw), "sha256": digest(raw)}


def bounded(root: Path, relative: str) -> Path:
    candidate = root / relative
    result = candidate.resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError(f"path leaves declared root: {relative}")
    # A copied symlink would obscure which input bytes the bundle retained.
    for parent in [candidate, *candidate.parents]:
        if parent == root.parent:
            break
        if parent.is_symlink():
            raise ValueError(f"symlink is not a declared regular artifact: {candidate}")
    return result


def locations(stage: Path, root: Path) -> tuple[Path, Path, Path, Path]:
    root = root.resolve()
    original = stage if stage.is_absolute() else root / stage
    stage = original.resolve()
    if original.is_symlink() or stage.parent != root / "work" / STUDY_ID or not stage.is_dir():
        raise ValueError("stage must be an existing regular work/<study>/<run> directory")
    return root, stage, stage / "completed-bundle", root / "runs" / STUDY_ID / stage.name


def checked_record(root: Path, record: dict) -> bytes:
    path = bounded(root, record["path"])
    raw = path.read_bytes()
    if len(raw) != record["bytes"] or digest(raw) != record["sha256"]:
        raise ValueError(f"artifact identity mismatch: {path}")
    return raw


def verify_payload(stage: Path) -> tuple[dict, dict, dict]:
    capture_raw = (stage / "capture-manifest.json").read_bytes()
    capture = json.loads(capture_raw)
    inventory = json.loads((stage / "archive/archive-manifest.json").read_bytes())
    verification = json.loads((stage / "verification.json").read_text())
    if verification.get("status") != "passed":
        raise ValueError("verification.json must explicitly record status passed before preparation/sealing")
    if capture.get("run_id") != stage.name:
        raise ValueError("capture run identity differs from stage directory")
    if digest(capture_raw) != inventory["source_capture_manifest_sha256"]:
        raise ValueError("source capture manifest changed after reader construction")
    archive = stage / "archive"
    listed = {item["path"] for item in inventory["files"]}
    actual = {p.relative_to(archive).as_posix() for p in archive.rglob("*") if p.is_file()} - {"archive-manifest.json"}
    if listed != actual or len(listed) != len(inventory["files"]):
        raise ValueError("reader inventory differs from retained payload files")
    for item in inventory["files"]:
        checked_record(archive, item)
    return capture, inventory, verification


def local_parts(value: str):
    value = html.unescape(value)
    parts = urlsplit(value)
    return None if parts.scheme or parts.netloc or not parts.path else parts


def rewritten_markdown(raw: str, source: Path, destination: Path, archive: Path, final: Path, notes: set[Path]) -> str:
    def replace(match):
        target = match["target"]
        angular = target.startswith("<") and target.endswith(">")
        parts = local_parts(target[1:-1] if angular else target)
        if parts is None:
            return match[0]
        original = (source.parent / unquote(parts.path)).resolve()
        if not original.is_relative_to(archive) or not original.is_file():
            raise ValueError(f"source navigation link leaves reader or is missing: {source}: {target}")
        future = final / NAVIGATION / original.relative_to(archive) if original in notes else original
        link = urlunsplit(("", "", Path(os.path.relpath(future, destination.parent)).as_posix(), parts.query, parts.fragment))
        if angular:
            link = "<" + link + ">"
        return match["prefix"] + link + match["suffix"]
    return MARKDOWN_LINK.sub(replace, raw)


def rewritten_report_html(raw: str, archive: Path, final: Path) -> str:
    def replace(match):
        parts = local_parts(match["target"])
        if parts is None:
            return match[0]
        original = (archive / unquote(parts.path)).resolve()
        if not original.is_relative_to(archive) or not original.is_file():
            raise ValueError(f"reader index links outside retained payload: {match['target']}")
        value = urlunsplit(("", "", Path(os.path.relpath(original, final)).as_posix(), parts.query, parts.fragment))
        return match["prefix"] + html.escape(value, quote=True) + match["suffix"]
    return re.sub(r'(?P<prefix>\b(?:href|src)=")(?P<target>[^"<>]+)(?P<suffix>")', replace, raw)


class HtmlLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        self.links.extend(value for name, value in attrs if name in {"href", "src"} and value)


def validate_links(files: dict[str, bytes], root: Path, final: Path) -> dict:
    counts = {"markdown_links": 0, "html_links": 0}
    for relative, raw in files.items():
        path = Path(relative)
        if path.suffix == ".md":
            links = [m["target"].strip("<>") for m in MARKDOWN_LINK.finditer(raw.decode())]
            counter = "markdown_links"
        elif path.suffix == ".html":
            parser = HtmlLinks()
            parser.feed(raw.decode())
            links, counter = parser.links, "html_links"
        else:
            continue
        future = final / path
        for link in links:
            parts = local_parts(link)
            if parts is None:
                continue
            target = (future.parent / unquote(parts.path)).resolve()
            if not target.is_relative_to(root):
                raise ValueError(f"final reference leaves workspace: {relative}: {link}")
            if target.is_relative_to(final):
                exists = target.relative_to(final).as_posix() in files
            else:
                exists = target.is_file()
            if not exists:
                raise ValueError(f"missing intended final reference: {relative}: {link}")
            counts[counter] += 1
    return {"status": "passed", **counts}


def prepare(stage: Path, *, root: Path = ROOT) -> dict:
    root, stage, bundle, final = locations(stage, root)
    if bundle.exists() or final.exists():
        raise FileExistsError("refusing an existing completed-bundle or completed run")
    capture, payload, verification = verify_payload(stage)
    archive = stage / "archive"
    files = {}
    for name, destination in [("capture-manifest.json", "capture-manifest.json"),
                              ("archive/archive-manifest.json", "payload-inventory.json"),
                              ("archive/metrics.json", "metrics.json"),
                              ("archive/coverage.csv", "tables/coverage.csv"),
                              ("archive-report.md", "report.md")]:
        files[destination] = (stage / name).read_bytes()
    provenance = stage / "provenance"
    if not provenance.is_dir():
        raise ValueError("stage/provenance must contain frozen producer/environment identities")
    for source in sorted(provenance.rglob("*")):
        if source.is_file():
            bounded(provenance, source.relative_to(provenance).as_posix())
            files[(Path("provenance") / source.relative_to(provenance)).as_posix()] = source.read_bytes()
    files["provenance/producer/seal_daily_maps.py"] = Path(__file__).read_bytes()
    protocol = root / "studies" / STUDY_ID / "daily-map-plan.md"
    files["plan.md"] = protocol.read_bytes()
    metadata = root / "studies" / STUDY_ID / "study.json"
    if metadata.is_file():
        files["study.json"] = metadata.read_bytes()
    notes = {p.resolve() for p in archive.rglob("*.md")}
    for source in sorted(notes):
        relative = NAVIGATION / source.relative_to(archive)
        files[relative.as_posix()] = rewritten_markdown(source.read_text(), source, final / relative, archive, final, notes).encode()
    files["report.html"] = rewritten_report_html((archive / "index.html").read_text(), archive, final).encode()
    reader_link = Path(os.path.relpath(archive / "index.html", final)).as_posix()
    files["README.md"] = ("# Verniman Daily Map archive\n\n[Read the archive report](report.md), "
                          "[browse dates](knowledge-base/daily-map/README.md), or "
                          f"[open the offline reader]({reader_link}).\n\n"
                          "Completed source-preservation snapshot. Retain the matching ignored work stage; "
                          "its source bytes are not disposable cache.\n").encode()
    stage_path = stage.relative_to(root).as_posix()
    archive_path = archive.relative_to(root).as_posix()
    config = {"scope": "private_source_archive", "start_date": capture["start_date"], "end_date": capture["end_date"],
              "user_timezone": "America/New_York", "sort": "descending", "grouping": "year/month/day",
              "statistics_computed": False, "dataset_releases_modified": False, "public_deployment": False,
              "retained_stage": stage_path, "archive_path": archive_path,
              "date_policy": capture.get("date_policy"),
              "image_policy": "Original compressed bytes; content hashes; explicitly qualified inline fallback"}
    files["config.json"] = encoded(config)
    files["inputs.lock.json"] = encoded({"schema_version": "daily-map-inputs-1", "retained_source_manifests": capture.get("retained_inputs", []),
                                        "source_capture_manifest": "capture-manifest.json", "payload_inventory": "payload-inventory.json",
                                        "retained_stage": stage_path, "historical_availability_verified": False})
    source_command = capture.get("command", [])
    verified_commands = verification.get("commands", [])
    if not isinstance(verified_commands, list) or not all(isinstance(value, str) for value in verified_commands):
        raise ValueError("verification commands must be a list of exact command strings")
    commands = list(dict.fromkeys([
        shlex.join([sys.executable, *source_command]) if source_command else "Capture command retained in capture-manifest.json.",
        *verified_commands,
        shlex.join([sys.executable, str(Path(__file__).relative_to(ROOT)), "--stage", stage_path, "--prepare"]),
        shlex.join([sys.executable, str(Path(__file__).relative_to(ROOT)), "--stage", stage_path, "--seal"]),
    ]))
    files["commands.txt"] = ("\n".join(commands) + "\n").encode()
    checks = {**verification, "bundle_preparation": {"status": "passed", "payload_files_verified": len(payload["files"]),
                                                     "navigation_checks": "Resolved against intended final run locations."}}
    files["checks.json"] = encoded(checks)
    links = validate_links(files, root, final)
    checks["bundle_preparation"].update(links)
    files["checks.json"] = encoded(checks)
    artifacts = [{"path": path, "bytes": len(raw), "sha256": digest(raw)} for path, raw in sorted(files.items())]
    producer_ids = [item for item in artifacts if item["path"].startswith("provenance/") and item["path"].endswith(".py")]
    input_ids = [identity(stage / name, relative_to=stage) for name in
                 ["capture-manifest.json", "archive/archive-manifest.json", "archive-report.md", "verification.json"]]
    manifest = {"schema_version": SCHEMA, "study_id": STUDY_ID, "run_id": stage.name,
                "prepared_at": datetime.now(timezone.utc).isoformat(),
                "scope": "Daily Map private source-preservation snapshot", "stage": stage_path,
                "retained_payload": archive_path, "payload_inventory_sha256": digest(files["payload-inventory.json"]),
                "source_capture_manifest_sha256": digest(files["capture-manifest.json"]),
                "prepared_inputs": input_ids, "producers": producer_ids,
                "code_and_environment": "provenance/ frozen source and environment snapshots",
                "checks": "checks.json", "commands": "commands.txt", "scientific_validation": False,
                "public_deployment": False, "artifacts": artifacts}
    files["manifest.json"] = encoded(manifest)
    bundle.mkdir()
    for relative, raw in sorted(files.items()):
        destination = bounded(bundle, relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as stream:
            stream.write(raw)
    result = validate_prepared(stage, root=root)
    return {"status": "prepared", "bundle": bundle.relative_to(root).as_posix(), **result}


def validate_prepared(stage: Path, *, root: Path = ROOT) -> dict:
    root, stage, bundle, final = locations(stage, root)
    _, payload, verification = verify_payload(stage)
    manifest = json.loads((bundle / "manifest.json").read_text())
    if manifest.get("study_id") != STUDY_ID or manifest.get("run_id") != stage.name:
        raise ValueError("prepared study/run identity differs from requested stage")
    if manifest.get("schema_version") != SCHEMA:
        raise ValueError("unexpected prepared bundle schema")
    for item in manifest["prepared_inputs"]:
        checked_record(stage, item)
    artifacts = manifest["artifacts"]
    listed = {item["path"] for item in artifacts}
    actual = {p.relative_to(bundle).as_posix() for p in bundle.rglob("*") if p.is_file()} - {"manifest.json"}
    if listed != actual or len(listed) != len(artifacts):
        raise ValueError("prepared artifact inventory differs from files")
    files = {item["path"]: checked_record(bundle, item) for item in artifacts}
    if digest(files["capture-manifest.json"]) != manifest["source_capture_manifest_sha256"]:
        raise ValueError("prepared capture-manifest identity mismatch")
    if digest(files["payload-inventory.json"]) != manifest["payload_inventory_sha256"]:
        raise ValueError("prepared payload inventory identity mismatch")
    if json.loads(files["checks.json"]).get("status") != "passed" or verification.get("status") != "passed":
        raise ValueError("prepared source verification is not passing")
    links = validate_links(files, root, final)
    return {"artifacts": len(artifacts), "payload_files_verified": len(payload["files"]),
            "portable_links_checked": links["markdown_links"] + links["html_links"],
            "bundle_bytes": sum(item["bytes"] for item in artifacts)}


def seal(stage: Path, *, root: Path = ROOT) -> dict:
    root, stage, bundle, final = locations(stage, root)
    if final.exists():
        raise FileExistsError(f"refusing to replace completed run: {final}")
    result = validate_prepared(stage, root=root)
    final.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(bundle, final)
    manifest = json.loads((final / "manifest.json").read_text())
    for record in manifest["artifacts"]:
        checked_record(final, record)
    return {"status": "sealed", "run": final.relative_to(root).as_posix(), **result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--prepare", action="store_true", help="Prepare a fresh candidate after source verification")
    action.add_argument("--seal", action="store_true", help="Verify and copy a prepared candidate into a fresh immutable run")
    args = parser.parse_args()
    try:
        result = prepare(args.stage) if args.prepare else seal(args.stage)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"{type(exc).__name__}: {exc}\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
