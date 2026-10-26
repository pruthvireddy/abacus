#!/usr/bin/env python3
"""Verify exact selected bytes and attachment headers from the local preview."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urlparse
from src.storage import save_json, sha, utc_now

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--work",required=True,type=Path)
parser.add_argument("--url",default="http://127.0.0.1:4174")
parser.add_argument("--browser-download",required=True,type=Path)
args=parser.parse_args()
assert urlparse(args.url).hostname in ("127.0.0.1","localhost","::1")
report=json.loads((args.work/"publication.json").read_text())
assert sha(args.browser_download)==report["downloads"][0]["sha256"]
records=[]
for item in report["downloads"]+[{"id":s["id"],"path":s["path"],"sha256":sha(args.work/s["path"])} for s in report["sections"] if s["kind"]=="figure"]:
    url=f"{args.url.rstrip('/')}/publications/{report['id']}/{item['path']}"
    with urlopen(url,timeout=15) as response:
        data=response.read();headers=dict(response.headers)
        assert response.status==200
    digest=hashlib.sha256(data).hexdigest();assert digest==item["sha256"]
    if item["path"].endswith(".csv"):
        assert headers["Content-Disposition"]==f'attachment; filename="{Path(item["path"]).name}"'
        assert headers["Content-Type"].startswith("text/csv")
    else:
        assert headers["Content-Type"].startswith("image/png")
    records.append({"id":item["id"],"url":url,"sha256":digest,"bytes":len(data),"headers":headers,"matched":True})
save_json(args.work/"download-verification.json",{"passed":True,"verified_at":utc_now(),"browser_download":{"path":str(args.browser_download),"sha256":report["downloads"][0]["sha256"],"matched":True},"http_assets":records})
print("Native browser CSV and all four HTTP CSV/six figure hashes and headers verified")
