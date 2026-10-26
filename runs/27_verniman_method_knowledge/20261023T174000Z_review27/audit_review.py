"""Read-only identity, coverage and Markdown-link audit for this source review.

Run from the Abacus root with the explicit stage or completed bundle path.
This checks recorded bytes/coverage declarations, never trading validity.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import re


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root, bundle = args.workspace_root.resolve(), args.bundle.resolve()
    errors = []

    def require(condition, message):
        if not condition:
            errors.append(message)

    def load(name):
        return json.loads((bundle / name).read_text())

    def check_bytes(path, sha, label):
        target = (root / path).resolve()
        require(target.is_relative_to(root), f"{label}: path outside workspace")
        if not target.is_file():
            errors.append(f"{label}: missing retained bytes {path}")
            return b""
        data = target.read_bytes()
        require(hashlib.sha256(data).hexdigest() == sha, f"{label}: hash mismatch")
        return data

    sources, media = load("source-observations.json"), load("media-inventory.json")
    coverage, images = load("review-coverage.json"), load("image-inventory.json")
    topic_ids = {f"T{i:02}" for i in range(1, 28)}
    require(len(sources) == 27 and {s["id"] for s in sources} == topic_ids,
            "expected all 27 unique source topics")
    for source in sources:
        check_bytes(source["capture"], source["html_sha256"], source["id"] + " HTML")
        check_bytes(source["article_text_file"], source["article_text_sha256"],
                    source["id"] + " article")
        matches = list((bundle / "knowledge-base/topics").glob(source["id"].lower() + "-*.md"))
        require(len(matches) == 1, f"{source['id']}: expected one topic note")
        if len(matches) == 1:
            require(source["url"] in matches[0].read_text(),
                    f"{source['id']}: topic note lacks exact primary URL")
    ids = {v["id"] for v in media}
    require(len(media) == 46 and len(ids) == 46, "expected 46 unique videos")
    require(ids == {v for source in sources for v in source["youtube_ids"]},
            "video inventory differs from article observations")
    reviews = coverage["reviews"]
    require(len(reviews) == 42 and len({v["video_id"] for v in reviews}) == 42,
            "expected 42 unique full-export review records")
    reviewed = {v["video_id"]: v for v in reviews}
    for video in media:
        require(set(video["topics"]).issubset(topic_ids), video["id"] + ": unknown parent topic")
        if video["status"] != "transcript_retrieved":
            require(video["id"] not in reviewed, video["id"] + ": unavailable export marked reviewed")
            continue
        data = check_bytes(video["retained_transcript"], video["transcript_sha256"], video["id"])
        if not data:
            continue
        record = reviewed.get(video["id"])
        require(record is not None, video["id"] + ": missing review attestation")
        if record is None:
            continue
        text = data.decode()
        stamps = re.findall(r"^\[([^]]+)\]", text, re.M)
        require(record["sha256"] == video["transcript_sha256"], video["id"] + ": review hash mismatch")
        require(len(text.splitlines()) == record["line_count"], video["id"] + ": line count mismatch")
        require(len(data) == record["byte_count"], video["id"] + ": byte count mismatch")
        require(stamps and [stamps[0], stamps[-1]] ==
                [record["first_timestamp"], record["last_timestamp"]],
                video["id"] + ": timestamp bounds mismatch")
        require((bundle / record["notes_file"]).is_file(), video["id"] + ": missing synthesis")
        require(not record["audio_verified"] and not record["video_frames_reviewed"],
                video["id"] + ": unexpected audiovisual claim")
    retained = [v for v in images if v.get("path")]
    require(len(images) == 16 and len(retained) == 11, "image inventory count mismatch")
    require(sum(v.get("kind") == "market_chart" for v in retained) == 6, "expected six inspected charts")
    require(sum(v.get("kind") == "instructional_slide" for v in retained) == 1, "expected one inspected slide")
    for record in retained:
        check_bytes(record["path"], record["sha256"], record["id"])
    spec = importlib.util.spec_from_file_location("review_agent_docs", root / "scripts/check-agent-docs.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    guides = tuple(str(p.relative_to(root)) for p in sorted((bundle / "knowledge-base").rglob("*.md")))
    errors.extend(module.check(root, guides))
    for error in errors:
        print(error)
    print(json.dumps({"status": "failed" if errors else "passed", "topics": len(sources),
                      "videos": len(media), "reviewed_exports": len(reviews),
                      "inspected_images": len(retained), "markdown_documents": len(guides),
                      "errors": len(errors), "scientific_validation": False}))
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
