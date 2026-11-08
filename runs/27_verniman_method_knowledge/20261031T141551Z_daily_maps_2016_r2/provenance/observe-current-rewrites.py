"""Append exact observations of known surviving URLs; do not infer dates from them."""
import gzip
import hashlib
import importlib.util
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
stage = Path(__file__).resolve().parents[1]
root = Path(__file__).resolve().parents[4]
spec = importlib.util.spec_from_file_location("source_reader", root / "studies/27_verniman_method_knowledge/capture_daily_maps.py")
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)
manifest = stage / "capture-manifest.json"
capture = json.loads(manifest.read_text())
obs_path = stage / capture["current_source_observations"]["path"]
assert hashlib.sha256(obs_path.read_bytes()).hexdigest() == capture["current_source_observations"]["sha256"]
obs = json.loads(obs_path.read_text())
assert "current_rewrites" not in obs
rewrites = []
for url in obs["selected_archived_urls_in_current_sitemap"]:
    began = datetime.now(timezone.utc).isoformat()
    request = urllib.request.Request(url, headers={"User-Agent": "AbacusLocalSourceArchive/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read()
        status, final = response.status, response.url
    packed = gzip.compress(raw, compresslevel=9, mtime=0)
    target = stage / "current-observations" / f"request-{len(obs['records'])+1:04d}.html.gz"
    with target.open("xb") as output:
        output.write(packed)
    parsed = reader.Post(raw.decode("utf-8"))
    record = {"url": url, "final_url": final, "http_status": status, "error": None,
              "request_started_at": began, "captured_at": datetime.now(timezone.utc).isoformat(),
              "observation_kind": "current_educational_rewrite", "path": target.relative_to(stage).as_posix(),
              "bytes": len(packed), "sha256": hashlib.sha256(packed).hexdigest(),
              "uncompressed_bytes": len(raw), "uncompressed_sha256": hashlib.sha256(raw).hexdigest()}
    assert parsed.md is None
    rewrites.append({"url": url, "current_title": parsed.title.strip(), "current_outlook_month_day": None,
                     "qualification": "Current educational rewrite; no date inferred from old URL. Archived selected source remains unchanged."})
    obs["records"].append(record)
    capture["attempts"].append(record)
obs["current_rewrites"] = rewrites
obs_path.write_text(json.dumps(obs, indent=2) + "\n")
raw = obs_path.read_bytes()
capture["current_source_observations"].update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
manifest.write_text(json.dumps(capture, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"current_rewrites": rewrites}))
