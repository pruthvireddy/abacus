"""Record this new presentation revision; excludes the manifest's own hash."""
import hashlib
import json
import platform
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
mapping = json.loads((HERE / "source-map.json").read_text())


def identity(path):
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


app = ROOT / "apps/narada"
snapshot = HERE / "provenance/narada-source"
snapshot_files = []
for directory in ["src", "types", "contracts", "scripts", "tests"]:
    for source in sorted((app / directory).rglob("*")):
        if source.is_file():
            target = snapshot / source.relative_to(app)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            snapshot_files.append(identity(target))
for filename in ["package.json", "package-lock.json", "next.config.ts", "tsconfig.json", "eslint.config.mjs"]:
    source = app / filename
    target = snapshot / filename
    shutil.copyfile(source, target)
    snapshot_files.append(identity(target))
revision_relative = str(HERE.relative_to(ROOT))
publish_relative = "../../" + revision_relative + "/publication.json"
commands = [
    {"cwd": ".", "command": f"python3 {revision_relative}/prepare.py"},
]
if (HERE / "rasterize.mjs").exists():
    commands.append({"cwd": ".", "command": f"node {revision_relative}/rasterize.mjs"})
commands += [
    {"cwd": ".", "command": f"python3 {revision_relative}/verify-content.py"},
    {"cwd": "apps/narada", "command": f"npm run report:publish -- --report {publish_relative} --dry-run"},
    {"cwd": "apps/narada", "command": f"npm run report:publish -- --report {publish_relative}"},
]
commands += [{"cwd": "apps/narada", "command": command} for command in
             ["npm run verify", "npm test", "npm run lint", "npm run build", "npm run preview"]]
commands += [
    {"cwd": ".", "command": "node reports/exports/05_session_vwap/20260923T015900Z_vwap3/20261006T210008Z_web05/provenance/check-static.mjs"},
    {"cwd": ".", "command": "python3 scripts/check-agent-docs.py"},
    {"cwd": ".", "command": f"python3 {revision_relative}/finalize.py"},
]
checks = [
    {"name": "saved_evidence_transfer", "record": "content-verification.json"},
    {"name": "publisher_dry_run_and_staging", "result": "passed; ready then published through Narada publisher"},
    {"name": "application_and_documentation", "record": "application-verification.json"},
    {"name": "static_content_and_http", "record": "static-verification.json"},
    {"name": "desktop_mobile_browser", "record": "browser-verification.json"},
    {"name": "initial_tree_preservation", "record": "preservation-verification.json"},
    {"name": "semantic_and_visual_review", "record": "verification.md"},
]
id_ = mapping["publication_id"]
bundle_path = app / "public/publications" / id_ / "report.json"
bundle = json.loads(bundle_path.read_text())
staged = [identity(bundle_path)] + [identity(bundle_path.parent / a["path"]) for a in bundle["provenance"]["assets"]]
outputs = [identity(p) for p in sorted(HERE.rglob("*")) if p.is_file() and p != HERE / "manifest.json"]
manifest = {
    "study_id": mapping["study_id"], "source_run_id": mapping["source_run_id"], "revision_id": HERE.name,
    "publication_id": id_, "created_at_utc": "2026-10-06T21:00:08Z",
    "source_selection": "registered reference run" if mapping["study_id"].startswith("05") else mapping["source_selection"],
    "change": ("Selected quantitative presentation from frozen primary evidence; explicit horizons, denominators, exploratory baselines and faithful labeled raster."
               if mapping["study_id"].startswith("05") else "Abridged qualitative presentation from frozen source review; five exact frames and eight attributed claim rows; no scorecard."),
    "source_artifacts": mapping["source_artifacts"],
    "renderer": {"path": revision_relative + "/prepare.py", "sha256": identity(HERE / "prepare.py")["sha256"],
                 "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                 "format_version": "web-study-report-1.0", "narada_version": "0.1.0", "python": platform.python_version(),
                 "node": subprocess.check_output(["node", "--version"], text=True).strip(),
                 "npm": subprocess.check_output(["npm", "--version"], text=True).strip(),
                 "platform": platform.platform(), "uncommitted_renderer_identity": {
                     "snapshot": revision_relative + "/provenance/narada-source/", "files": snapshot_files,
                     "scope": "Exact Narada renderer/contracts/publisher/tests/config/locked dependency identity; no dependency installation or research source import."}},
    "render_command": commands[0], "exact_commands": commands,
    "presentation_changes": ["Shared six-stage reading order; selected saved content only", "Preserved adverse/uncertain evidence and original source attribution",
                             "Generic accessible table hint, first-column width, numeric no-wrap, viewport-bounded contents; no schema or route changes"],
    "checks": checks, "outputs": outputs,
    "staged_publication": {"source_sha256": bundle["provenance"]["sourceSha256"], "artifacts": staged,
                           "catalog_at_delivery": identity(app / "public/publications/index.json"),
                           "route": f"/reports/{id_}/", "static_html_at_delivery": identity(app / "out/reports" / id_ / "index.html")},
    "boundaries": {"research_reexecuted": False, "completed_run_modified": False, "schema_modified": False,
                   "study_metadata_modified": False, "deployed": False, "committed_or_pushed": False},
}
(HERE / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
print(f"Recorded {HERE.name}: {len(outputs)} output hashes; manifest excluded.")
