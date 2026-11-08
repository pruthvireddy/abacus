"""Offline regression for a malformed full-image link and observed inline fallback."""
import http.client
import importlib.util
import json
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

here = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("frozen_capture", here / "capture_daily_maps.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
failure = json.loads((here / "initial-attempt-failure.json").read_text())
image = {"url": failure["malformed_url"], "inline_url": failure["observed_inline_url"], "alt": ""}
with tempfile.TemporaryDirectory() as directory:
    capture = module.Capture(Path.cwd(), Path(directory) / "fixture", date(2024, 1, 1), date(2024, 12, 31),
                             seed="https://verniman.blogspot.com/2007/12/good-bye-2024.html", retained_manifests=[])
    with patch.object(module.urllib.request, "urlopen", side_effect=http.client.InvalidURL("malformed source URL")):
        record, data = capture.fetch(image["url"], "image")
    assert data is None and record["error"].startswith("InvalidURL:")
    assert capture.m["attempts"][-1]["url"] == image["url"]
    capture.saved_images[image["inline_url"]] = {"url": image["inline_url"], "path": "assets/fixture.jpg",
                                               "bytes": 1, "sha256": "fixture"}
    with patch.object(module.urllib.request, "urlopen", side_effect=http.client.InvalidURL("malformed source URL")):
        result = capture.image(image)
    assert result["rendition"] == "inline_thumbnail" and result["url"] == image["inline_url"]
    assert result["requested_url"] == image["url"] and result["full_size_error"].startswith("InvalidURL:")
print("Passed malformed source request and observed inline fallback regression without network.")
