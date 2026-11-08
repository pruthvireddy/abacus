"""Check the built reader's selected text and evidence order against saved reports."""
from html.parser import HTMLParser
import json
from pathlib import Path


class Reader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.sections = {}
        self.current = None
        self.depth = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "section":
            if self.current:
                self.depth += 1
            elif attributes.get("id", "").startswith("section-"):
                self.current = attributes["id"][8:]
                self.depth = 1
                self.sections[self.current] = []
        if self.current and tag in ("table", "img", "pre"):
            self.sections[self.current].append(f" [{tag.upper()}] ")

    def handle_endtag(self, tag):
        if tag == "section" and self.current:
            self.depth -= 1
            if self.depth == 0:
                self.current = None

    def handle_data(self, data):
        if self.current:
            self.sections[self.current].append(data)


def normalized(text):
    return " ".join(text.split())


def main():
    root = Path.cwd()
    stage = root / "work/30_verniman_pivot_statistics_es/20261108T040901Z_notebook_themes_v2"
    export = json.loads((stage / "publications/notebook-export.json").read_text())
    records = []
    for item in export["publications"]:
        report = json.loads((stage / "publications" / item["path"]).read_text())
        path = root / "apps/narada/out/reports" / report["id"] / "index.html"
        reader = Reader()
        reader.feed(path.read_text())
        assert list(reader.sections) == [section["id"] for section in report["sections"]]
        for section in report["sections"]:
            body = normalized("".join(reader.sections[section["id"]]))
            positions = [body.index(normalized(section[key])) for key in ("title", "description", "finding")]
            marker = "[TABLE]" if section["kind"] == "table" else "[IMG]"
            positions.append(body.index(marker))
            assert positions == sorted(positions), (section["id"], positions)
            assert "[PRE]" not in body
            records.append({"publication_id": report["id"], "insight_id": section["id"],
                            "text": "heading, full description and findings present",
                            "structure": "heading → description → findings → evidence", "passed": True})
        assert 'aria-label="Study question themes"' in path.read_text()
    assert len(records) == 21
    result = {"result": "passed", "themes": 6, "insights": len(records), "checks": records,
              "limitation": "Static HTML content/order verification; this does not establish visual layout or keyboard interaction."}
    with (stage / "static-reader-verification.json").open("x") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print("All 21 built insight sections preserve the complete selected narrative and heading/description/findings/evidence order.")


if __name__ == "__main__":
    main()
