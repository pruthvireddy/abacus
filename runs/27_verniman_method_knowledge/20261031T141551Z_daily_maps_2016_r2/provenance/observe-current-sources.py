"""Record bounded current sitemap/known-live-page observations; no source-date inference."""
import gzip
import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

STAGE = Path(__file__).resolve().parents[1]
OUT = STAGE / "current-observations"
OUT.mkdir(exist_ok=False)
records = []


def stamp():
    return datetime.now(timezone.utc).isoformat()


def fetch(url, kind):
    if urllib.parse.urlsplit(url).hostname != "verniman.blogspot.com":
        raise ValueError("observation leaves source host")
    began = stamp()
    error = None
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "AbacusLocalSourceArchive/1.0"})
        response = urllib.request.urlopen(request, timeout=30)
    except urllib.error.HTTPError as failure:
        response = failure
        error = f"HTTP {failure.code}; current live probe, not an archive-adaptation failure"
    with response:
        raw = response.read()
        status, final, headers = response.code, response.url, dict(response.headers)
    packed = gzip.compress(raw, compresslevel=9, mtime=0)
    path = OUT / f"request-{len(records)+1:04d}.{kind}.gz"
    path.write_bytes(packed)
    record = {"url": url, "final_url": final, "http_status": status, "headers": headers,
              "request_started_at": began, "captured_at": stamp(), "error": error,
              "observation_kind": "current_sitemap" if kind == "xml" else "current_live_probe",
              "path": path.relative_to(STAGE).as_posix(), "bytes": len(packed),
              "sha256": hashlib.sha256(packed).hexdigest(),
              "uncompressed_bytes": len(raw), "uncompressed_sha256": hashlib.sha256(raw).hexdigest()}
    records.append(record)
    return raw


ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
index = ET.fromstring(fetch("https://verniman.blogspot.com/sitemap.xml", "xml"))
locators = []
for page in index.findall("s:sitemap", ns):
    raw = fetch(page.findtext("s:loc", namespaces=ns), "xml")
    locators.extend(item.findtext("s:loc", namespaces=ns) for item in ET.fromstring(raw))
manifest = STAGE / "capture-manifest.json"
capture = json.loads(manifest.read_text())
selected = {p["url"] for p in capture["posts"]}
for url in [capture["posts"][0]["url"], capture["posts"][-1]["url"]]:
    fetch(url, "html")
observation = {"observed_at": stamp(), "records": records, "sitemap_locator_count": len(locators),
               "selected_archived_urls_in_current_sitemap": sorted(selected & set(locators)),
               "scope": "Current observations only; retained archive source dates and capture clocks remain unchanged."}
output = STAGE / "provenance/current-source-observations.json"
output.write_text(json.dumps(observation, indent=2) + "\n")
raw = output.read_bytes()
capture["current_source_observations"] = {"path": output.relative_to(STAGE).as_posix(), "bytes": len(raw),
                                          "sha256": hashlib.sha256(raw).hexdigest()}
capture["sitemaps"] = [r for r in records if r["observation_kind"] == "current_sitemap"]
capture["attempts"].extend(records)
manifest.write_text(json.dumps(capture, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"current_observations": len(records), "sitemap_locators": len(locators),
                  "selected_urls_in_current_sitemap": observation["selected_archived_urls_in_current_sitemap"],
                  "probe_statuses": [r["http_status"] for r in records if r["observation_kind"] == "current_live_probe"]}))
